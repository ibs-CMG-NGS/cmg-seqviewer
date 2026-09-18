"""
컨버터 계약 단위/통합 테스트 (plan §12 — G4/G5/G6/G7/A4/A5).

`EnrichmentAnalyzer.to_standard()`가 §6.3~6.6 계약을 만족하는지 고정한다:
- `_gene_set` 다구분자 정규화 (A5) / term_id 정책 (G7/A1) / ratio·fold (G6)
- 라벨 → direction/ontology 왕복 (G5) / description canonical (A4)
- 기존 go_kegg_loader 표준화 파이프라인과의 재사용 호환 (G4)
"""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import pandas as pd

from utils.enrichment_analyzer import (
    EnrichmentAnalyzer,
    RawResult,
    _parse_overlap,
    _genes_to_slash,
    _strip_go_suffix,
)
from utils.go_kegg_loader import standardize_go_dataframe

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OBO = FIXTURES / "mini-obo.obo"
GMT_GO = FIXTURES / "gmt_go_bp.txt"
GMT_KEGG = FIXTURES / "gmt_kegg.txt"
ENR_GO = json.loads((FIXTURES / "enrichr_response_go_bp.json").read_text())
ENR_KEGG = json.loads((FIXTURES / "enrichr_response_kegg.json").read_text())


class StubCache:
    """실제 다운로드 없는 테스트 캐시 (ensure_* 는 tmp 파일 복사/생성)."""

    def __init__(self, tmp_path: Path):
        self.cache_dir = tmp_path
        self.online = True
        self._gmt_src = {
            "GO_Biological_Process_2023": GMT_GO,
            "KEGG_2021_Human": GMT_KEGG,
        }
        self._obo_src = OBO

    def detect_online(self, timeout: float = 3.0) -> bool:
        return self.online

    def ensure_gmt(self, name: str) -> Path:
        src = self._gmt_src[name]
        dest = self.cache_dir / f"gmt_{name}.gmt"
        if not dest.exists():
            shutil.copyfile(src, dest)
        return dest

    def ensure_obo(self, organism: str) -> Path:
        dest = self.cache_dir / "go-basic.obo"
        if not dest.exists():
            shutil.copyfile(self._obo_src, dest)
        return dest

    def ensure_gene2go(self, organism: str) -> Path:
        dest = self.cache_dir / f"gene2go_{organism}.gz"
        if not dest.exists():
            dest.write_bytes(b"")
        return dest

    def ensure_gene_info(self, organism: str) -> Path:
        dest = self.cache_dir / f"gene_info_{organism}.gz"
        if not dest.exists():
            dest.write_bytes(b"")
        return dest

    def sidecar(self, path: Path) -> dict:
        return {}


def make_enrichr_df(records, gene_set="GO_Biological_Process_2023") -> pd.DataFrame:
    rows = [dict(r, Gene_set=gene_set) for r in records]
    return pd.DataFrame(rows)


def make_ctxt(tmp_path):
    return EnrichmentAnalyzer(cache=StubCache(tmp_path))


# --------------------------------------------------------------------------
# 헬퍼 단위 (A5/G7 수준)
# --------------------------------------------------------------------------

class TestHelpers:
    def test_overlap_parse(self):
        assert _parse_overlap("3/14") == (3, 14)
        assert _parse_overlap("garbage") == (0, 0)

    def test_multi_delimiter_normalize(self):
        # A5: [;/,] 다구분자 → '/' 재조인
        assert _genes_to_slash("GENE1;GENE2/GENE3,GENE4") == "GENE1/GENE2/GENE3/GENE4"
        assert _genes_to_slash(" GENE1 ;GENE2 ") == "GENE1/GENE2"
        assert _genes_to_slash("") == ""
        assert _genes_to_slash(None) == ""

    def test_strip_go_suffix(self):
        assert _strip_go_suffix("Negative Regulation Of Cell Migration (GO:0030336)") \
            == "Negative Regulation Of Cell Migration"


# --------------------------------------------------------------------------
# enrichr GO → 표준 변환 (G4/G5/G6/G7/A4/A5)
# --------------------------------------------------------------------------

class TestEnrichrGoConversion:
    def test_full_contract(self, tmp_path):
        an = make_ctxt(tmp_path)
        raw = RawResult(
            label="UP_BP",
            engine="enrichr",
            data=make_enrichr_df(ENR_GO),
            meta={"population": []},
        )
        df, warnings = an.to_standard([raw], organism="human")

        assert set(df.columns) >= {
            "term_id", "description", "gene_count", "fdr", "pvalue",
            "gene_ratio", "bg_ratio", "fold_enrichment", "gene_symbols",
            "gene_set", "direction", "ontology", "_gene_set",
        }
        assert df["term_id"].str.fullmatch(r"GO:\d{7}").all()          # G7
        assert df["gene_ratio"].astype(str).str.fullmatch(r"\d+/\d+").all()  # G6
        assert df["bg_ratio"].astype(str).str.fullmatch(r"\d+/\d+").all()    # G6
        assert (df["gene_set"] == "UP_BP").all()                        # G5
        assert (df["direction"] == "UP").all()
        assert (df["ontology"] == "BP").all()
        assert df["_gene_set"].map(len).gt(0).all()                     # G4/A5
        row = df[df["term_id"] == "GO:0014912"].iloc[0]
        assert row["gene_ratio"] == "3/14"
        assert row["bg_ratio"] == "3/16"         # GMT by_id M=3, GO GMT 유니버스=16
        assert row["gene_count"] == 3
        # A4: obo 미존재 → GMT name (Title-Case) 사용
        assert row["description"] == "Negative Regulation Of Smooth Muscle Cell Migration"
        assert set(row["_gene_set"]) == {"IGFBP3", "SERPINE1", "TPM1"}
        assert pd.notna(row["fold_enrichment"])
        assert set(row["_gene_set"]) == {"IGFBP3", "SERPINE1", "TPM1"}
        assert pd.notna(row["fold_enrichment"])

    def test_description_canonical_obo_wins(self, tmp_path):
        # A4: 동일 term_id → obo name > GMT name > enrichr Term
        an = make_ctxt(tmp_path)
        df_in = make_enrichr_df([
            {"Gene_set": "GO_Biological_Process_2023",
             "Term": "Immune Response (GO:0000005)",
             "Overlap": "2/10", "P-value": 0.01, "Adjusted P-value": 0.05,
             "Old P-value": 0, "Old Adjusted P-value": 0,
             "Odds Ratio": 5, "Combined Score": 25, "Genes": "TRP53;JUN"},
        ])
        df, _ = an.to_standard([RawResult("UP_BP", "enrichr", df_in)], organism="human")
        # mini-obo에 존재 → obo 소문자 이름 우선 (GMT/Enrichr Title-Case 무시)
        assert df.loc[0, "description"] == "immune response"

    def test_kegg_empty_term_id(self, tmp_path):
        # G7/A1: 온라인 KEGG Term에 hsa id 없음 → term_id 빈 값 (4A)
        an = make_ctxt(tmp_path)
        raw = RawResult("TOTAL_KEGG", "enrichr", make_enrichr_df(ENR_KEGG, "KEGG_2021_Human"))
        df, warnings = an.to_standard([raw], organism="human")
        assert (df["term_id"] == "").all()
        assert (df["ontology"] == "KEGG").all()
        assert (df["direction"] == "TOTAL").all()
        # KEGG GMT 이름 매칭 (by_name) — Phagosome M=6, universe=3(M=6+7+5→유니크)
        row = df[df["description"] == "Phagosome"].iloc[0]
        assert row["gene_ratio"] == "6/152"
        assert row["bg_ratio"].split("/")[0] == "6"

    def test_gmt_missing_term_m_fallback(self, tmp_path):
        # W1: GMT 스냅샷에 없는 term → M=히트 수 근사 + 경고 (P0 architect finding 해소)
        an = make_ctxt(tmp_path)
        df_in = make_enrichr_df([
            {"Gene_set": "GO_Biological_Process_2023",
             "Term": "Totally Novel Term (GO:0000999)",
             "Overlap": "2/10", "P-value": 0.01, "Adjusted P-value": 0.05,
             "Old P-value": 0, "Old Adjusted P-value": 0,
             "Odds Ratio": 5, "Combined Score": 25, "Genes": "A;B"},
        ])
        df, warnings = an.to_standard([RawResult("UP_BP", "enrichr", df_in)], organism="human")
        assert any("W1" in w and "GMT" in w for w in warnings)
        assert df.loc[0, "bg_ratio"].split("/")[0] == "2"  # M=k 근사

    def test_fold_zero_denominator_nan(self, tmp_path):
        # G6: 0 분모 → NaN (기존 로더 수식)
        an = make_ctxt(tmp_path)
        df_in = pd.DataFrame([{
            "Gene_set": "GO_Biological_Process_2023",
            "Term": "No Such Term (GO:0000999)", "Overlap": "0/10",
            "P-value": 0.5, "Adjusted P-value": 0.9,
            "Old P-value": 0, "Old Adjusted P-value": 0,
            "Odds Ratio": 1, "Combined Score": 1, "Genes": "A;B",
        }])
        df, _ = an.to_standard([RawResult("UP_BP", "enrichr", df_in)], organism="human")
        # k=0 → M=k=0 → bg_ratio 0/16 → fold 분모 0 → NaN (기존 로더 수식)
        assert pd.isna(df.loc[0, "fold_enrichment"])

    def test_loader_roundtrip_compat(self, tmp_path):
        # G4: 변환 프레임이 기존 표준화 파이프라인을 재통과해도 계약 유지
        an = make_ctxt(tmp_path)
        raw = RawResult("DOWN_BP", "enrichr", make_enrichr_df(ENR_GO))
        df, _ = an.to_standard([raw], organism="human")
        again = standardize_go_dataframe(df)
        assert "description" in again.columns
        assert again["_gene_set"].map(len).gt(0).all()
        assert again.columns.duplicated().sum() == 0


# --------------------------------------------------------------------------
# GOATOOLS raw → 표준 변환
# --------------------------------------------------------------------------

class TestGoatoolsConversion:
    def _records(self):
        return [
            SimpleNamespace(
                GO="GO:0000004", name="heart contraction",
                study_count=2, study_n=10,
                p_fdr_bh=0.03, p_uncorrected=0.001,
                study_items=[101, 102],
            ),
            SimpleNamespace(
                GO="GO:0000007", name="cell adhesion",
                study_count=1, study_n=10,
                p_fdr_bh=0.9, p_uncorrected=0.2,
                study_items=[103],
            ),
        ]

    def test_goatools_contract(self, tmp_path, monkeypatch):
        an = make_ctxt(tmp_path)

        class FakeMapper:
            def reverse_name(self, gid):
                return {101: "GENE1", 102: "GENE2", 103: "GENE3"}.get(gid)
        monkeypatch.setattr(an, "_mapper_for", lambda org: FakeMapper())
        monkeypatch.setattr(an, "_assoc_term_sizes", lambda org, w: {
            "GO:0000004": 50, "GO:0000007": 20})

        raw = RawResult("UP_BP", "goatools", self._records(),
                        meta={"population": [1, 2, 3, 4]})
        df, _ = an.to_standard([raw], organism="human")
        assert df["term_id"].str.fullmatch(r"GO:\d{7}").all()
        assert df["gene_ratio"].iloc[0] == "2/10"
        assert df["bg_ratio"].iloc[0] == "50/4"     # M=assoc, N=population
        assert set(df.loc[0, "_gene_set"]) == {"GENE1", "GENE2"}
        assert df.loc[0, "direction"] == "UP" and df.loc[0, "ontology"] == "BP"


# --------------------------------------------------------------------------
# 라벨 → direction/ontology 왕복 (G5 — 다운스트림 GO 필터 호환)
# --------------------------------------------------------------------------

class TestLabelRoundTrip:
    @pytest.mark.parametrize("label,exp", [
        ("UP_BP", ("UP", "BP")),
        ("DOWN_BP", ("DOWN", "BP")),
        ("TOTAL_MF", ("TOTAL", "MF")),
        ("UP_KEGG", ("UP", "KEGG")),
        ("DOWN_KEGG", ("DOWN", "KEGG")),
        ("TOTAL_KEGG", ("TOTAL", "KEGG")),
    ])
    def test_parse_label(self, label, exp):
        # go_kegg_loader._extract_direction_ontology와 왕복 일치 (plan §6.3)
        import pandas as pd
        from utils.go_kegg_loader import extract_direction_ontology
        df = pd.DataFrame({"gene_set": [label]})
        out = extract_direction_ontology(df)
        assert (out.loc[0, "direction"], out.loc[0, "ontology"]) == exp
