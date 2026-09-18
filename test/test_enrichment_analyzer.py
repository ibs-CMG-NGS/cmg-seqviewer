"""
EnrichmentAnalyzer 테스트 (plan §12 — G8/G12/G13/G14/A3/A4/F3).

- 라우팅: Auto(온라인/로컬), 2A background 강제, mouse GO 로컬 전용, KEGG 오프라인 비활성
- 실패 분류: NO_INPUT_GENES / MAPPING / EMPTY_RESULT / NETWORK
- enrich_prerank 인터페이스(Phase 4) / libraries_for / metadata(§6.9)
"""

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import pandas as pd

from models.enrichment_models import EnrichmentRequest, ErrorKind
from utils.enrichment_analyzer import (
    EnrichmentAnalyzer,
    EnrichmentError,
    RawResult,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OBO = FIXTURES / "mini-obo.obo"
GMT_GO = FIXTURES / "gmt_go_bp.txt"
GMT_KEGG = FIXTURES / "gmt_kegg.txt"


class StubCache:
    def __init__(self, tmp_path: Path):
        self.cache_dir = tmp_path
        self.online = True
        self.gene2go_sample = None   # gzipped gene2go fixture path (있으면 복사)

    def detect_online(self, timeout: float = 3.0) -> bool:
        return self.online

    def ensure_gmt(self, name: str) -> Path:
        src = GMT_GO if "GO_" in name else GMT_KEGG
        dest = self.cache_dir / f"gmt_{name}.gmt"
        if not dest.exists():
            shutil.copyfile(src, dest)
        return dest

    def ensure_obo(self, organism: str) -> Path:
        dest = self.cache_dir / "go-basic.obo"
        if not dest.exists():
            shutil.copyfile(OBO, dest)
        return dest

    def ensure_gene2go(self, organism: str) -> Path:
        dest = self.cache_dir / f"gene2go_{organism}.gz"
        if not dest.exists():
            if self.gene2go_sample is not None:
                shutil.copyfile(self.gene2go_sample, dest)
            else:
                dest.write_bytes(b"")
        return dest

    def ensure_gene_info(self, organism: str) -> Path:
        dest = self.cache_dir / f"gene_info_{organism}.gz"
        if not dest.exists():
            dest.write_bytes(b"")
        return dest

    def sidecar(self, path: Path) -> dict:
        return {}


def make_an(tmp_path):
    cache = StubCache(tmp_path)
    return EnrichmentAnalyzer(cache=cache), cache


class FakeMapper:
    """테스트용 심볼 매퍼 — 하나의 심볼만 매핑 실패/성공 시뮬레이션."""

    def __init__(self, mapping=None):
        self.mapping = mapping or {"A": 1, "B": 2, "C": 3,
                                   "TRP53": 7157, "JUN": 3725, "FOS": 2353}

    def normalize_symbol(self, symbol):
        return str(symbol).strip().upper()  # human UPPER (테스트 데이터 기준)

    def map_symbols(self, symbols):
        return {s: self.mapping.get(s) for s in symbols}

    def mapped_entrez(self, symbols):
        seen, out = set(), []
        for s in symbols:
            g = self.mapping.get(s)
            if g and g not in seen:
                seen.add(g)
                out.append(g)
        return out

    def mapped_count(self, symbols):
        return sum(1 for s in symbols if self.mapping.get(s) is not None)

    def reverse_name(self, gid):
        rev = {7157: "TRP53", 3725: "JUN", 2353: "FOS", 1: "A", 2: "B", 3: "C"}
        return rev.get(gid)


@pytest.fixture
def an(tmp_path):
    return make_an(tmp_path)[0]


class TestLibraryTables:
    def test_human(self):
        t = EnrichmentAnalyzer.libraries_for("human")
        assert t["online"]["BP"] == "GO_Biological_Process_2023"
        assert t["online"]["KEGG"] == "KEGG_2021_Human"
        assert t["local"]["BP"] == "GOATOOLS"

    def test_mouse_go_absent(self):
        # A3/P0-7: mouse GO 온라인 라이브러리 없음 — 로컬 전용
        t = EnrichmentAnalyzer.libraries_for("mouse")
        assert "BP" not in t["online"]
        assert t["online"]["KEGG"] == "KEGG_2019_Mouse"

    def test_invalid_organism(self):
        with pytest.raises(ValueError):
            EnrichmentAnalyzer.libraries_for("rat")


class TestRouting:
    def test_auto_online_uses_enrichr(self, an, monkeypatch):
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())
        calls = {}
        monkeypatch.setattr(an, "_enrichr_call",
                            lambda name, genes, organism: calls.__setitem__("name", name) or
                            pd.DataFrame({"Term": ["T (GO:0000001)"], "Overlap": ["1/10"],
                                          "P-value": [0.01], "Adjusted P-value": [0.05],
                                          "Old P-value": [0], "Old Adjusted P-value": [0],
                                          "Odds Ratio": [1], "Combined Score": [1],
                                          "Genes": ["A;B"]}))
        results, warnings = an.enrich_ora(["A", "B"], organism="human",
                                          libraries=["BP"], engine="auto")
        assert results[0].engine == "enrichr"
        assert calls["name"] == "GO_Biological_Process_2023"

    def test_background_forces_local(self, an, monkeypatch):
        # 2A (G8): background 지정 + auto/online → 로컬 강제 + 경고
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())
        seen = []
        monkeypatch.setattr(an, "_goatools_call",
                            lambda study, pop, org, one_sided=False: (seen.append((study, pop)) or
                                                     [SimpleNamespace(**{})]))
        monkeypatch.setattr(an, "_assoc_term_sizes", lambda org, w: {})
        results, warnings = an.enrich_ora(["A", "B"], background=["A", "B", "C"],
                                          organism="human", libraries=["BP"], engine="online")
        assert results[0].engine == "goatools"
        assert any("W2" in w and "local engine forced" in w for w in warnings)
        assert seen[0][1] == [1, 2, 3]  # population = 매핑된 background

    def test_offline_go_local_kegg_inactive(self, an, monkeypatch):
        # F3: 오프라인 → GO 로컬, KEGG 비활성 경고 (ADR-1 Option 1)
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())
        monkeypatch.setattr(an, "_goatools_call",
                            lambda study, pop, org, one_sided=False: [SimpleNamespace(GO="GO:0000001")])
        monkeypatch.setattr(an, "_assoc_term_sizes", lambda org, w: {})
        results, warnings = an.enrich_ora(["A"], organism="human",
                                          libraries=["BP", "KEGG"], engine="offline")
        assert [r.engine for r in results] == ["goatools"]
        assert any("KEGG offline" in w for w in warnings)

    def test_mouse_go_local_priority(self, an, monkeypatch):
        # A3: mouse GO → 온라인이어도 로컬
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())
        monkeypatch.setattr(an, "_goatools_call",
                            lambda study, pop, org, one_sided=False: [SimpleNamespace(GO="GO:0000001")])
        monkeypatch.setattr(an, "_assoc_term_sizes", lambda org, w: {})
        results, warnings = an.enrich_ora(["A"], organism="mouse",
                                          libraries=["BP"], engine="auto")
        assert results[0].engine == "goatools"
        assert any("mouse GO" in w and "local" in w for w in warnings)


class TestErrors:
    def test_no_input_genes(self, an):
        with pytest.raises(EnrichmentError) as ei:
            an.enrich_ora([], organism="human", libraries=["BP"], engine="local")
        assert ei.value.kind == ErrorKind.NO_INPUT_GENES

    def test_mapping_zero(self, an, monkeypatch):
        monkeypatch.setattr(an, "_mapper_for",
                            lambda org: FakeMapper(mapping={"X": None}))
        with pytest.raises(EnrichmentError) as ei:
            an.enrich_ora(["X"], organism="human", libraries=["BP"], engine="local")
        assert ei.value.kind == ErrorKind.MAPPING

    def test_network_failure_raises(self, an, monkeypatch):
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())

        def boom(*a, **k):
            raise RuntimeError("connection reset")
        monkeypatch.setattr(an, "_enrichr_call", boom)
        with pytest.raises(EnrichmentError) as ei:
            an.enrich_ora(["A"], organism="human", libraries=["BP"], engine="online")
        assert ei.value.kind == ErrorKind.NETWORK

    def test_empty_result_raises(self, an, monkeypatch):
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())
        with pytest.raises(EnrichmentError) as ei:
            an.enrich_ora(["A"], organism="human",
                          libraries=["KEGG"], engine="offline")
        assert ei.value.kind == ErrorKind.EMPTY_RESULT


class TestPrerankInterface:
    def test_phase4_implemented(self, an, monkeypatch, tmp_path):
        """Phase 1 인터페이스 → Phase 4 구현. NotImplementedError 제거 검증 (G16)."""
        class Res:
            res2d = PRERANK_RAW
        monkeypatch.setattr("gseapy.prerank", lambda *a, **k: Res())
        an.cache = StubCache(tmp_path)
        results, _ = an.enrich_prerank([("IGFBP3", 2.5), ("COL1A1", -1.2)],
                                       organism="human", libraries=["BP"])
        assert results[0].engine == "prerank"


class TestGoatoolsIntegration:
    """plan §12 Integration: mini-obo + sample gene2go 로컬 — fisher/fdr_bh 손계산 대조."""

    def test_local_goatools_matches_reference(self, tmp_path):
        import importlib.util
        from scipy.stats import fisher_exact
        from statsmodels.stats.multitest import multipletests

        spec = importlib.util.spec_from_file_location(
            "g2b", str(FIXTURES / "gene2go_sample_build.py"))
        g2b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(g2b)

        sample = tmp_path / "gene2go_9606_sample.gz"
        g2b.write_gene2go_sample(sample)
        cache = StubCache(tmp_path)
        cache.gene2go_sample = sample
        an = EnrichmentAnalyzer(cache=cache)

        records = an._goatools_call(g2b.STUDY, g2b.POPULATION, "human")
        rec_by_go = {r.GO: r for r in records}
        assert len(records) >= 4

        # 독립 대조 (GO:0000004 heart contraction): M=2(101,102), k=2, N=8, n=4
        for go_id, M, k, n in [("GO:0000004", 2, 2, 4),
                               ("GO:0000005", 3, 3, 4),
                               ("GO:0000007", 2, 2, 4)]:
            table = [[k, M - k], [n - k, (g2b.POPULATION.__len__() - M) - (n - k)]]
            _, p_two = fisher_exact(table, alternative="two-sided")   # goatools fisher_scipy와 동일 alternative
            assert rec_by_go[go_id].p_uncorrected == pytest.approx(p_two, rel=1e-6)

        # per-NS fdr_bh: BP 유의 p 목록 → statsmodels 다중보정 참조
        bp_raw = sorted((r.p_uncorrected for r in records if r.NS == "BP"))
        _, bp_fdr, _, _ = multipletests(bp_raw, method="fdr_bh")
        bp_recs = sorted((r for r in records if r.NS == "BP"),
                         key=lambda r: r.p_uncorrected)
        for rec, fdr_ref in zip(bp_recs, bp_fdr):
            assert rec.p_fdr_bh == pytest.approx(float(fdr_ref), rel=1e-6)

    def test_local_path_standard_conversion(self, tmp_path, monkeypatch):
        """GOATOOLS raw → to_standard 전체 경로 (G4/G6 + 종간 symbol 복원)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "g2b", str(FIXTURES / "gene2go_sample_build.py"))
        g2b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(g2b)

        sample = tmp_path / "gene2go_9606_sample.gz"
        g2b.write_gene2go_sample(sample)
        cache = StubCache(tmp_path)
        cache.gene2go_sample = sample
        an = EnrichmentAnalyzer(cache=cache)

        class FakeMapper:
            def reverse_name(self, gid):
                return {101: "GENE101", 102: "GENE102", 103: "GENE103",
                        104: "GENE104"}.get(gid)
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())

        records = an._goatools_call(g2b.STUDY, g2b.POPULATION, "human")
        raw = RawResult("UP_BP", "goatools", records, meta={"population": g2b.POPULATION})
        df, warnings = an.to_standard([raw], organism="human")
        assert "GO:0000004" in set(df["term_id"])
        assert df["gene_ratio"].astype(str).str.fullmatch(r"\d+/\d+").all()
        row = df[df["term_id"] == "GO:0000004"].iloc[0]
        assert row["bg_ratio"] == "2/8"          # M=assoc(2), N=population(8)
        assert set(row["_gene_set"]) == {"GENE101", "GENE102"}
        assert row["direction"] == "UP" and row["ontology"] == "BP"


class TestLiveNetwork:
    """`-m network` — 실제 호출 검증 (plan §15: Phase 1 pytest -m network 1회).

    기본 스위트에서 제외(pytest.ini addopts). 오프라인에서는 skip.
    """

    @pytest.mark.network
    def test_real_enrichr_online_path(self, tmp_path, monkeypatch):
        import gseapy
        from utils.enrichment_analyzer import EnrichmentAnalyzer
        an = EnrichmentAnalyzer(cache=StubCache(tmp_path))
        # 매퍼는 오프라인 테스트가 별도 검증 — 여기서는 온라인 Enrichr 경로만 실측 (plan §15)
        monkeypatch.setattr(an, "_mapper_for",
                            lambda org: FakeMapper({"TP53": 7157, "JUN": 3725,
                                                    "FOS": 2353, "BRCA1": 672,
                                                    "MYC": 4609}))
        results, warnings = an.enrich_ora(
            ["TP53", "JUN", "FOS", "BRCA1", "MYC"],
            organism="human", libraries=["BP"], engine="online")
        assert results[0].engine == "enrichr"
        df = results[0].data
        assert not df.empty
        assert "Term" in df.columns and "Overlap" in df.columns
        assert gseapy.__version__  # 버전 고정 기록 (P1-1)

    @pytest.mark.network
    def test_speedrichr_route_pinned(self):
        """architect 필수항목 1: gseapy 1.3.1 라이브러리명 background → Speedrichr 라우팅 pin.

        docstring('Enrichr library names에는 무시')은 doc-code drift이고 실제 코드는
        set/list background를 Speedrichr로 라우팅한다는 PoC 발견의 퇴행 감지용.
        """
        import inspect
        import gseapy
        from gseapy.enrichr import Enrichr
        src = inspect.getsource(gseapy.enrichr) + inspect.getsource(Enrichr)
        # 배경 라우팅 코드 경로 존재 확인 (Speedrichr / backgroundenrich / addbackground)
        assert any(k in src for k in ("speedrichr", "Speedrichr", "background"))
        # Speedrichr 라우팅 심볼 존재 — 또는 라우팅 명칭 변경 시 실패 (코드 drift 감지)
        assert any(k in src for k in ("addbackground", "backgroundenrich",
                                      "get_results_with_background"))
        # 분석기 가드: _enrichr_call은 background 파라미터를 가질 수 없다 (2A)
        from utils.enrichment_analyzer import EnrichmentAnalyzer as EA
        sig = inspect.signature(EA._enrichr_call)
        assert "background" not in sig.parameters
        assert sig.parameters["library_name"] and sig.parameters["gene_list"]


class TestMetadata:
    def test_build_metadata_recipe(self, an):
        req = EnrichmentRequest(source="paste", gene_list=["A", "B"],
                                direction="UP", organism="human",
                                libraries=["BP"], engine="local", fc_min=1.0)
        meta = an.build_metadata(req, [], ["W1 test"], n_deg=2, n_bg=10,
                                 organism="human")
        assert meta["enrichment_recipe"]["source"] == "paste"
        assert meta["enrichment_recipe"]["direction"] == "UP"
        assert meta["thresholds"]["fc_min"] == 1.0
        assert "W1 test" in meta["warnings"]
        assert "engines_used" in meta
        assert "engine_versions" in meta

    def test_request_recipe_roundtrip(self):
        req = EnrichmentRequest(source="dataset", dataset_name="D1",
                                direction="DOWN", organism="human",
                                libraries=["BP", "KEGG"], engine="auto",
                                fc_min=1.0, fdr_max=0.05,
                                ranked=[("A", 1.5), ("B", -2.0)])
        d = req.to_recipe_dict()
        assert d["ranked"] == [["A", 1.5], ["B", -2.0]]
        req2 = EnrichmentRequest.from_recipe_dict(d)
        assert req2.direction == "DOWN"
        assert req2.dataset_name == "D1"
        assert req2.ranked == [("A", 1.5), ("B", -2.0)]

    def test_request_validate(self):
        req = EnrichmentRequest(source="nope", direction="SIDEWAYS")
        problems = req.validate()
        assert any("source" in p for p in problems)
        assert any("direction" in p for p in problems)


# --------------------------------------------------------------------------
# population_symbols (architect P2-1 — 2A 미트리거, auto→local population)
# --------------------------------------------------------------------------

class TestPopulationSymbols:
    def test_population_symbols_no_2a_trigger(self, an, monkeypatch):
        # population_symbols 전달 → 온라인 경로 유지, 2A 경고 없음
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())
        calls = {}
        monkeypatch.setattr(an, "_enrichr_call",
                            lambda name, genes, organism: calls.__setitem__("name", name) or
                            pd.DataFrame({"Term": ["T (GO:0000001)"], "Overlap": ["1/10"],
                                          "P-value": [0.01], "Adjusted P-value": [0.05],
                                          "Old P-value": [0], "Old Adjusted P-value": [0],
                                          "Odds Ratio": [1], "Combined Score": [1],
                                          "Genes": ["A;B"]}))
        results, warnings = an.enrich_ora(["A", "B"], organism="human", libraries=["BP"],
                                          engine="online", population_symbols=["A", "B", "C"])
        assert results[0].engine == "enrichr"
        assert not any("로컬 엔진으로 강제" in w for w in warnings)  # 2A 미발동

    def test_population_symbols_local_population(self, an, monkeypatch):
        # 로컬 경로 population = population_symbols 매핑 결과
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())
        seen = []
        monkeypatch.setattr(an, "_goatools_call",
                            lambda study, pop, org, one_sided=False: (seen.append(pop) or
                                                     [SimpleNamespace(GO="GO:0000001", study_count=0)]))
        monkeypatch.setattr(an, "_assoc_term_sizes", lambda org, w: {})
        results, warnings = an.enrich_ora(["A", "B"], organism="human", libraries=["BP"],
                                          engine="local", population_symbols=["A", "B", "C"])
        assert results[0].engine == "goatools"
        assert seen[0] == [1, 2, 3]  # 매핑된 DE 전체 population


# --------------------------------------------------------------------------
# P3-2 오프라인 e2e (block_network) + P3-7 저장/복원 _gene_set 재파생
# --------------------------------------------------------------------------

@pytest.mark.offline
def test_offline_go_succeeds_kegg_skipped(tmp_path, block_network, monkeypatch):
    """실네트워크 차단 상태에서 GO 로컬 성공 + KEGG 비활성 (plan P3-2)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("g2b", str(FIXTURES / "gene2go_sample_build.py"))
    g2b = importlib.util.module_from_spec(spec); spec.loader.exec_module(g2b)
    sample = tmp_path / "gene2go_9606_sample.gz"
    g2b.write_gene2go_sample(sample)
    cache = StubCache(tmp_path)
    cache.gene2go_sample = sample
    cache.online = False
    an = EnrichmentAnalyzer(cache=cache)

    class M:
        def normalize_symbol(self, s): return s.strip().upper()
        def map_symbols(self, symbols):
            return {s: {"GENE101": 101, "GENE102": 102, "GENE103": 103,
                        "GENE104": 104}.get(s) for s in symbols}
        def mapped_count(self, symbols):
            return sum(1 for s in symbols if self.map_symbols([s])[s])
        def reverse_name(self, gid):
            return {101: "GENE101", 102: "GENE102", 103: "GENE103", 104: "GENE104"}.get(gid)
    monkeypatch.setattr(an, "_mapper_for", lambda org: M())

    results, warnings = an.enrich_ora(
        ["GENE101", "GENE102", "GENE103", "GENE104"],
        organism="human", libraries=["BP", "KEGG"], engine="offline",
        population_symbols=["GENE101", "GENE102", "GENE103", "GENE104"])
    assert [r.engine for r in results] == ["goatools"]       # GO 로컬 성공
    assert any("KEGG" in w for w in warnings)                # KEGG 비활성 안내
    df, _ = an.to_standard(results, organism="human")
    assert (df["ontology"] == "KEGG").sum() == 0             # KEGG 행 없음
    assert len(df) > 0


@pytest.mark.offline
def test_first_run_offline_download_classified(tmp_path, block_network):
    """캐시 부재 첫 실행 + 오프라인 → ErrorKind.DOWNLOAD (P2-3/P3-2 UX 훅)."""
    an = EnrichmentAnalyzer(cache=StubCache(tmp_path))
    from utils.enrichment_analyzer import EnrichmentError
    with pytest.raises(EnrichmentError) as ei:
        an.enrich_ora(["A"], organism="human", libraries=["BP"], engine="offline")
    assert ei.value.kind == ErrorKind.DOWNLOAD


def test_project_restore_gene_set_rederived(tmp_path):
    """P3-7: 저장(parquet sets→lists) → 복원(로더 표준화) 시 _gene_set 재파생.

    기존 저장 경로는 _gene_set을 sorted-list로 저장하므로, 복원 프레임이
    gene_symbols 컬럼을 갖고 있으면 표준화 파이프라인이 set으로 재구성한다.
    """
    df = pd.DataFrame({
        "term_id": ["GO:0000004", "GO:0000007"],
        "description": ["heart contraction", "cell adhesion"],
        "gene_count": [2, 3], "fdr": [0.03, 0.31], "pvalue": [0.001, 0.2],
        "gene_ratio": ["2/10", "3/10"], "bg_ratio": ["4/100", "5/100"],
        "gene_symbols": ["GENE101/GENE102", "GENE102/GENE103/GENE104"],
        "_gene_set": [["GENE101", "GENE102"], ["GENE102", "GENE103", "GENE104"]],  # 복원 상태 (list)
    })
    p = tmp_path / "restored.parquet"
    df.to_parquet(p)
    restored = pd.read_parquet(p)
    assert not isinstance(restored["_gene_set"].iloc[0], set)  # 복원 상태 (set 아님 — parquet 배열)
    from utils.go_kegg_loader import standardize_go_dataframe
    std = standardize_go_dataframe(restored)
    assert std["_gene_set"].map(lambda s: isinstance(s, set)).all()   # set 재구성
    assert set(std.loc[0, "_gene_set"]) == {"GENE101", "GENE102"}


# --------------------------------------------------------------------------
# Phase 4 — GSEA prerank (M4b, G16): P4-1/P4-2/P4-3
# --------------------------------------------------------------------------

PRERANK_RAW = pd.DataFrame([
    {"Term": "Collagen Fibril Organization (GO:0030199)", "Gene_set": "gmt_GO_Biological_Process_2023.gmt",
     "NES": -1.78, "NOM p-val": 0.004, "FDR q-val": 0.05, "FWER p-val": 0.2,
     "Genes": "COL1A1;COL1A3;COL1A2;LOXL1"},
    {"Term": "Negative Regulation Of Smooth Muscle Cell Migration (GO:0014912)",
     "Gene_set": "gmt_GO_Biological_Process_2023.gmt",
     "NES": 1.52, "NOM p-val": 0.01, "FDR q-val": 0.07, "FWER p-val": 0.3,
     "Genes": "IGFBP3;SERPINE1;TPM1"},
])



ENR_GO_CTX = [
    {"Gene_set": "GO_Biological_Process_2023",
     "Term": "Collagen Fibril Organization (GO:0030199)",
     "Overlap": "2/10", "P-value": 0.01, "Adjusted P-value": 0.05,
     "Old P-value": 0, "Old Adjusted P-value": 0,
     "Odds Ratio": 5.0, "Combined Score": 25.0, "Genes": "COL1A1;COL1A3"},
]

def make_enrichr_df_ctx(records, gene_set="GO_Biological_Process_2023") -> pd.DataFrame:
    return pd.DataFrame([dict(r, Gene_set=gene_set) for r in records])
class TestPrerank:
    def test_prerank_mock_through_converter(self, an, tmp_path, monkeypatch):
        """P4-1: gseapy.prerank mock → 표준 컨버터 통과 (NES 보존, 라벨/term_id 정책)."""
        class Res:
            res2d = PRERANK_RAW
        called = {}

        def fake_prerank(rnk, gene_sets, **kw):
            called["gene_sets"] = gene_sets
            return Res()
        monkeypatch.setattr("gseapy.prerank", fake_prerank)
        cache = StubCache(tmp_path)

        def _ensure_gmt(name):
            import shutil
            dest = cache.cache_dir / f"gmt_{name}.gmt"
            if not dest.exists():
                shutil.copyfile(FIXTURES / "gmt_go_bp.txt", dest)
            return dest
        cache.ensure_gmt = _ensure_gmt
        cache.cache_dir = tmp_path
        an.cache = cache

        ranked = [("IGFBP3", 2.5), ("SERPINE1", 1.8), ("TPM1", 1.5),
                  ("COL1A1", -1.2), ("COL1A3", -2.0), ("COL1A2", -1.7), ("LOXL1", -1.5)]
        results, warns = an.enrich_prerank(ranked, organism="human", libraries=["BP"])
        assert results[0].engine == "prerank"
        assert called["gene_sets"]  # 캐시 GMT 경로 사용 (M4b: gene_sets=캐시 GMT)
        df, _ = an.to_standard(results, organism="human")
        assert "nes" in df.columns and df["nes"].notna().all()       # NES 보존
        assert df["gene_set"].tolist() == ["TOTAL_BP", "TOTAL_BP"]
        assert set(df["term_id"]) == {"GO:0030199", "GO:0014912"}
        assert df["gene_ratio"].astype(str).str.fullmatch(r"\d+/\d+").all()
        assert (df["direction"] == "TOTAL").all() and (df["ontology"] == "BP").all()

    def test_prerank_vs_ora_difference(self, an, monkeypatch, tmp_path):
        """P4-2: prerank 변환 결과는 NES/FWER 컬럼 보존, ORA 변환 결과에는 없음."""
        import shutil
        class Res:
            res2d = PRERANK_RAW
        monkeypatch.setattr("gseapy.prerank", lambda *a, **k: Res())
        cache = StubCache(tmp_path)
        cache.ensure_gmt = lambda name: (lambda tmp: (shutil.copyfile(
            FIXTURES / "gmt_go_bp.txt", tmp / f"gmt_{name}.gmt"), tmp / f"gmt_{name}.gmt")[1])(cache.cache_dir)
        an.cache = cache
        pk, _ = an.enrich_prerank([("IGFBP3", 2.5), ("COL1A1", -1.2)],
                                  organism="human", libraries=["BP"])
        pk_df, _ = an.to_standard(pk, organism="human")
        assert "nes" in pk_df.columns and "fwer_pvalue" in pk_df.columns   # GSEA 통계 보존
        # ORA 변환에는 없음
        ora = RawResult("TOTAL_BP", "enrichr", make_enrichr_df_ctx(ENR_GO_CTX))
        ora_df, _ = an.to_standard([ora], organism="human")
        assert "nes" not in ora_df.columns
        # 문서화 근거 (P4-2): 결과 해석 컬럼 차이 명시

    def test_worker_prerank_branch(self, monkeypatch, tmp_path):
        """P4-3 worker: meta + prerank 플래그 → extract_ranked → enrich_prerank 호출."""
        from workers.go_workers import EnrichmentWorker
        from models.enrichment_models import EnrichmentRequest
        meta = pd.DataFrame({"symbol": ["TP53", "JUN", "FOS"],
                             "meta_pvalue_fisher": [0.001, 0.01, 0.5],
                             "meta_log2fc_mean": [1.5, -1.2, 0.1],
                             "meta_fdr_fisher": [0.01, 0.1, 0.9]})

        class SpyAnalyzer:
            def __init__(self):
                self.calls = {}
            def enrich_prerank(self, ranked, organism=None, libraries=None, **kw):
                self.calls["ranked"] = ranked
                return ([], [])
            def enrich_ora(self, *a, **k):
                self.calls["ora"] = True
                raise AssertionError("enrich_ora called on the prerank path")
            def to_standard(self, raw, organism=None, **kw):
                import pandas as pd2
                return pd2.DataFrame(), []
            def build_metadata(self, *a, **k):
                return {"engine_effective": "local"}

        spy = SpyAnalyzer()
        req = EnrichmentRequest(source="meta", meta_cutoff=0.05, direction="TOTAL",
                                libraries=["BP"], engine="offline")
        req.extra["prerank"] = True
        w = EnrichmentWorker(req, analyzer=spy, dataframe=meta)
        w.run()
        assert "ranked" in spy.calls
        assert spy.calls["ranked"]                       # extract_ranked 결과 전달
        assert spy.calls["ranked"][0][0] == "TP53"        # 심볼 보존


# --------------------------------------------------------------------------
# gen-2/3 발견 수정 고정: KEGG by_name M 해석 + mouse prerank 스킵
# --------------------------------------------------------------------------

def test_prerank_kegg_gmt_m_by_name(tmp_path, monkeypatch):
    """QA 발견: KEGG prerank bg_ratio M은 캐시 GMT term 크기(by_name), k 아님."""
    import shutil
    class Res:
        res2d = pd.DataFrame([
            {"Term": "gmt_KEGG_2021_Human.gmt__Phagosome", "Gene_set": "x",
             "NES": -1.4, "NOM p-val": 0.01, "FDR q-val": 0.09, "FWER p-val": 0.4,
             "Lead_genes": "ITGB1;TUBA1B;ACTB"},
        ])
    monkeypatch.setattr("gseapy.prerank", lambda *a, **k: Res())
    cache = StubCache(tmp_path)
    cache.ensure_gmt = lambda name: (lambda t: (shutil.copyfile(
        FIXTURES / "gmt_kegg.txt", t / f"gmt_{name}.gmt"), t / f"gmt_{name}.gmt")[1])(cache.cache_dir)
    an = EnrichmentAnalyzer(cache=cache)
    ranked = [("ITGB1", 2.5), ("TUBA1B", -1.2), ("ACTB", 0.4), ("COL1A1", -0.9)]
    results, _ = an.enrich_prerank(ranked, organism="human", libraries=["KEGG"])
    df, _ = an.to_standard(results, organism="human")
    row = df.iloc[0]
    assert row["bg_count"] == 6              # GMT by_name['Phagosome']=6 (k=3 아님)
    assert row["bg_ratio"] == "6/10"
    assert row["description"] == "Phagosome"  # gmt 접두어 제거


def test_mouse_prerank_go_skipped_w1(tmp_path, monkeypatch):
    """A3: mouse prerank GO(GMT 없음) 스킵 + KEGG 시도."""
    class Res:
        res2d = pd.DataFrame([{"Term": "Phagosome", "Gene_set": "x",
                               "NES": 1.0, "NOM p-val": 0.05, "FDR q-val": 0.2,
                               "FWER p-val": 0.5, "Lead_genes": "A;B"}])
    monkeypatch.setattr("gseapy.prerank", lambda *a, **k: Res())
    cache = StubCache(tmp_path)
    cache.ensure_gmt = lambda name: (lambda t: (t / f"gmt_{name}.gmt")).__call__(cache.cache_dir)
    cache.ensure_gmt = lambda name: ((cache.cache_dir / f"gmt_{name}.gmt"))
    an = EnrichmentAnalyzer(cache=cache)
    results, warns = an.enrich_prerank([("A", 1.0), ("B", -0.5)],
                                       organism="mouse", libraries=["BP", "KEGG"])
    assert [r.label for r in results] == ["KEGG_TOTAL"]    # GO 스킵 (파이프라인 관례)
    assert any("no prerank GMT snapshot for mouse BP" in w and "skipped" in w for w in warns)


# --------------------------------------------------------------------------
# 파이프라인 반입 ↔ in-app 결과 포맷 정합 (사용자 요구: gene_set 관례 + 헤더 순서)
# --------------------------------------------------------------------------

class TestPipelineParity:
    def test_shared_column_relative_order_matches_pipeline(self, an, monkeypatch, tmp_path):
        """in-app to_standard 공통 컬럼 상대순서 == 파이프라인 반입(로더) 상대순서."""
        import shutil
        # 파이프라인 반입 경로: 시트 이름=gene_set, R 어휘 컬럼 (final_go_result.xlsx 형태)
        # 실제 파이프라인 파일(final_go_result.xlsx) 레이아웃: R 어휘 + category/subcategory,
        # gene_set 컬럼 없음 → 로더가 시트명으로 스탬프
        r = pd.DataFrame([{
            "ID": "GO:0000004", "Description": "heart contraction",
            "GeneRatio": "2/10", "BgRatio": "4/100",
            "pvalue": 0.01, "p.adjust": 0.05, "qvalue": 0.05,
            "geneID": "A/B", "Count": 2, "category": "BP",
            "subcategory": "-",
        }])
        from pathlib import Path
        f = tmp_path / "pipe_sample.xlsx"
        with pd.ExcelWriter(f) as w:
            r.to_excel(w, sheet_name="DOWN_BP", index=False)
        from utils.go_kegg_loader import GOKEGGLoader
        pipe = GOKEGGLoader().load_from_excel(Path(f), name="pipe")

        # in-app 표준 변환
        an.cache = StubCache(tmp_path)
        import json
        rec = json.loads((Path("test/fixtures/enrichr_response_go_bp.json")).read_text())[0]
        df_in = pd.DataFrame([rec])
        app_df, _ = an.to_standard([RawResult("DOWN_BP", "enrichr", df_in)],
                                   organism="human")
        shared = [c for c in pipe.dataframe.columns if c in app_df.columns]
        app_seq = [c for c in app_df.columns if c in set(shared)]
        assert app_seq == shared, f"공통 컬럼 상대순서 불일치: {app_seq} vs {shared}"

    def test_inapp_kegg_label_matches_pipeline(self, an, monkeypatch, tmp_path):
        """in-app KEGG gene_set = KEGG_{direction} (파이프라인 시트명과 동일)."""
        import shutil
        class Res:
            res2d = pd.DataFrame([{"Term": "Phagosome", "NES": 1.0,
                                   "NOM p-val": 0.05, "FDR q-val": 0.2,
                                   "FWER p-val": 0.5, "Lead_genes": "A;B"}])
        monkeypatch.setattr("gseapy.prerank", lambda *a, **k: Res())
        cache = StubCache(tmp_path)
        cache.ensure_gmt = lambda name: (lambda t: (shutil.copyfile(
            FIXTURES / "gmt_kegg.txt", t / f"gmt_{name}.gmt"),
            t / f"gmt_{name}.gmt")[1])(cache.cache_dir)
        an.cache = cache
        res, _ = an.enrich_prerank([("A", 1.0), ("B", -0.5)],
                                   organism="human", libraries=["KEGG"])
        assert res[0].label == "KEGG_TOTAL"
        df, _ = an.to_standard(res, organism="human")
        row = df.iloc[0]
        assert row["gene_set"] == "KEGG_TOTAL"
        assert row["direction"] == "TOTAL" and row["ontology"] == "KEGG"

    def test_pipeline_kegg_sheet_labels_parse(self, tmp_path):
        """파이프라인 시트명(KEGG_DOWN 등) → direction/ontology 왕복 (검증)."""
        from utils.go_kegg_loader import extract_direction_ontology
        df = pd.DataFrame({"gene_set": ["KEGG_DOWN", "KEGG_TOTAL", "DOWN_BP"]})
        out = extract_direction_ontology(df)
        assert list(out["direction"]) == ["DOWN", "TOTAL", "DOWN"]
        assert list(out["ontology"]) == ["KEGG", "KEGG", "BP"]


class TestSnapshotProvenanceMetadata:
    def test_build_metadata_records_annotation_snapshots(self, an, monkeypatch):
        """검증권장 2: 결과 metadata에 사용 주석 스냅샷(sha256/획득일) 기록."""
        from models.enrichment_models import EnrichmentRequest
        class ProvCache:
            cache_dir = "ignored"
            def snapshot_provenance(self, rel):
                if rel.startswith(("go-basic", "gene2go", "gene_info")):
                    return {"file": rel, "sha256": "abc", "fetched_at": "2026-09-03",
                            "source": "https://example/x", "pinned": False}
                return {}
        an.cache = ProvCache()
        req = EnrichmentRequest(source="dataset", dataset_name="D", organism="mouse",
                                libraries=["BP"], fc_min=1.0, fdr_max=0.05)
        meta = an.build_metadata(req, [], [RawResult("UP_BP", "goatools", [])],
                                 organism="mouse", n_deg=10, n_bg=100)
        assert "annotation_snapshots" in meta
        snap = meta["annotation_snapshots"]
        assert snap["gene2go"]["sha256"] == "abc"
        assert snap["obo"]["file"] == "go-basic.obo"


# --------------------------------------------------------------------------
# 잔여 추천: 로컬 GO 단측(enrichment) Fisher 옵션 (파이프라인 정합)
# --------------------------------------------------------------------------

class TestOneSidedFisher:
    def test_apply_one_sided_matches_pipeline(self):
        """GO:0000004 (k=2,M=2,n=4,N=8): 단측 0.2143, 양측 0.4286 (Phase-1 손계산 대조)."""
        from types import SimpleNamespace
        from utils.enrichment_analyzer import _apply_one_sided_fisher
        recs = [
            SimpleNamespace(GO="GO:0000004", NS="BP", study_count=2, study_n=4,
                            pop_count=2, pop_n=8, p_uncorrected=0.4286, p_fdr_bh=0.4286),
            SimpleNamespace(GO="GO:0000005", NS="BP", study_count=1, study_n=4,
                            pop_count=1, pop_n=8, p_uncorrected=0.5, p_fdr_bh=0.5),
        ]
        out = _apply_one_sided_fisher(recs)
        assert abs(out[0].p_uncorrected - 0.2143) < 1e-3          # 단측 재계산
        assert out[0].p_fdr_bh is not None and out[0].p_fdr_bh >= 0
        # 2번째 term (k=1,M=1,n=4,N=8): 단측 p = 35/70 = 0.5
        assert abs(out[1].p_uncorrected - 0.5) < 1e-3

    def test_enrich_ora_forwards_one_sided_to_goatools(self, an, monkeypatch):
        """enrich_ora(one_sided=True) → _goatools_call에 전달; 기본 False 유지."""
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())
        seen = {}

        def fake_gt(study, pop, organism, one_sided=False):
            seen["os"] = one_sided
            return [SimpleNamespace(GO="GO:0000001", NS="BP", study_count=1, study_n=4,
                                    pop_count=1, pop_n=8, p_uncorrected=0.5, p_fdr_bh=0.5)]
        monkeypatch.setattr(an, "_goatools_call", fake_gt)
        monkeypatch.setattr(an, "_assoc_term_sizes", lambda org, w: {})

        an.enrich_ora(["A"], organism="human", libraries=["BP"], engine="local", one_sided=True)
        assert seen.get("os") is True
        an.enrich_ora(["A"], organism="human", libraries=["BP"], engine="local")
        assert seen.get("os") is False

    def test_build_metadata_stat_test(self, an, monkeypatch):
        from models.enrichment_models import EnrichmentRequest
        an.cache = StubCache(Path(tmp_path_fix := "/tmp"))
        req = EnrichmentRequest(source="paste", gene_list=["A"], organism="human")
        req.extra["one_sided"] = True
        meta = an.build_metadata(req, [], [], organism="human", n_deg=1, n_bg=1)
        assert meta["stat_test"] == "fisher_one_sided"
        req2 = EnrichmentRequest(source="paste", gene_list=["A"])
        meta2 = an.build_metadata(req2, [], [], organism="human", n_deg=1, n_bg=1)
        assert meta2["stat_test"] == "fisher_two_sided"
