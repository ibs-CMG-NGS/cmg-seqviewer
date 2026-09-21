"""
EnrichmentWorker combined-direction (UP+DOWN+TOTAL) 테스트.

Pipeline-import 형식(final_go_result.xlsx)은 UP/DOWN/TOTAL 시트가 모두 한
데이터셋에 들어있다. direction=DIRECTION_ALL을 선택하면 in-app 분석도 같은
형태(한 데이터셋에 UP/DOWN/TOTAL 행이 모두 있는)를 만들어야 한다.
"""

import pandas as pd
import pytest

from models.enrichment_models import DIRECTION_ALL, EnrichmentRequest
from workers.go_workers import EnrichmentWorker


def make_de_df():
    # UP: TP53 (log2fc>=1, fdr<=0.05) / DOWN: MYC / not significant: FOS
    return pd.DataFrame({
        "symbol": ["TP53", "MYC", "FOS"],
        "log2fc": [2.0, -2.0, 0.1],
        "adj_pvalue": [0.001, 0.001, 0.9],
    })


class SpyAnalyzer:
    """direction별 enrich_ora 호출을 기록하고 라벨이 있는 더미 RawResult를 반환."""

    def __init__(self):
        self.ora_calls = []

    def enrich_ora(self, genes, background=None, organism=None, libraries=None,
                   engine=None, direction=None, population_symbols=None, one_sided=False):
        self.ora_calls.append({"genes": list(genes), "direction": direction})
        from utils.enrichment_analyzer import RawResult
        raw = RawResult(label=f"{direction}_BP" if direction != "KEGG" else f"KEGG_{direction}",
                        engine="enrichr", data=pd.DataFrame({"marker": [direction]}))
        return [raw], []

    def to_standard(self, raw_results, organism=None, **kw):
        # 각 raw_result의 marker 값을 gene_set 컬럼으로 그대로 보존해 검증 가능하게 함
        rows = [r.data.assign(gene_set=r.data["marker"]) for r in raw_results]
        return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(), []

    def build_metadata(self, request, raw_results, warnings, n_deg, n_bg, organism):
        return {"engine_effective": "local", "n_deg": n_deg}


def test_request_validate_direction_all_requires_dataset_source():
    req_ok = EnrichmentRequest(source="dataset", dataset_name="x", direction=DIRECTION_ALL,
                               fc_min=1.0, fdr_max=0.05, libraries=["BP"])
    assert req_ok.validate() == []

    req_bad = EnrichmentRequest(source="paste", direction=DIRECTION_ALL, libraries=["BP"])
    problems = req_bad.validate()
    assert any("direction" in p for p in problems)


def test_combined_direction_runs_up_down_total_and_merges(monkeypatch):
    req = EnrichmentRequest(source="dataset", dataset_name="ds", direction=DIRECTION_ALL,
                            fc_min=1.0, fdr_max=0.05, organism="human", libraries=["BP"],
                            engine="auto")
    spy = SpyAnalyzer()
    w = EnrichmentWorker(req, analyzer=spy, dataframe=make_de_df())
    results = {}
    w.result_ready.connect(lambda r: results.__setitem__("result", r))
    w.failed.connect(lambda p: results.__setitem__("failed", p))
    w.run()

    assert "failed" not in results, getattr(results.get("failed"), "message", None)
    assert [c["direction"] for c in spy.ora_calls] == ["UP", "DOWN", "TOTAL"]
    assert spy.ora_calls[0]["genes"] == ["TP53"]
    assert spy.ora_calls[1]["genes"] == ["MYC"]
    assert set(spy.ora_calls[2]["genes"]) == {"TP53", "MYC"}  # TOTAL = UP ∪ DOWN (|log2fc|>=1 & fdr<=.05)

    df = results["result"].dataframe
    assert set(df["gene_set"]) == {"UP", "DOWN", "TOTAL"}     # 하나의 데이터셋에 셋 다 병합


def test_combined_direction_skips_empty_direction_with_warning(monkeypatch):
    # DOWN 방향에 해당하는 유전자가 없는 데이터셋 (모두 up 또는 무의미)
    df_in = pd.DataFrame({
        "symbol": ["TP53", "FOS"],
        "log2fc": [2.0, 0.1],
        "adj_pvalue": [0.001, 0.9],
    })
    req = EnrichmentRequest(source="dataset", dataset_name="ds", direction=DIRECTION_ALL,
                            fc_min=1.0, fdr_max=0.05, organism="human", libraries=["BP"],
                            engine="auto")
    spy = SpyAnalyzer()
    w = EnrichmentWorker(req, analyzer=spy, dataframe=df_in)
    results = {}
    w.result_ready.connect(lambda r: results.__setitem__("result", r))
    w.run()

    assert [c["direction"] for c in spy.ora_calls] == ["UP", "TOTAL"]  # DOWN 스킵
    assert any("direction=DOWN" in warn and "skipped" in warn
              for warn in results["result"].warnings)


def test_combined_direction_fails_when_all_directions_empty():
    df_in = pd.DataFrame({
        "symbol": ["FOS"],
        "log2fc": [0.1],
        "adj_pvalue": [0.9],
    })
    req = EnrichmentRequest(source="dataset", dataset_name="ds", direction=DIRECTION_ALL,
                            fc_min=1.0, fdr_max=0.05, organism="human", libraries=["BP"],
                            engine="auto")
    spy = SpyAnalyzer()
    w = EnrichmentWorker(req, analyzer=spy, dataframe=df_in)
    results = {}
    w.failed.connect(lambda p: results.__setitem__("failed", p))
    w.run()

    assert "failed" in results
    assert not spy.ora_calls
