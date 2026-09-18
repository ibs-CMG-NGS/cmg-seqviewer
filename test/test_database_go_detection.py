"""database_manager GO/KEGG parquet 자동 임포트 감지 테스트.

- 회귀 대상: GUI 시작 시 'Cannot determine type ... Skipping' 경고로 스킵되던
  파이프라인 R-vocab GO/KEGG parquet을 GO_ANALYSIS로 자동 등록 (~근본 해결).
- _is_go_dataframe 어휘: 표준 / 점-구분 레거시 / R clusterProfiler / 카테고리 지시.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from utils.database_manager import _is_go_dataframe
from utils.go_kegg_loader import standardize_go_dataframe

# 실제 파이프라인 R-vocab 컬럼 (examples/Acute_1D_vs_Control_GO_KEGG.parquet 구조)
R_VOCAB = pd.DataFrame({
    "ID": ["GO:0006915", "GO:0007049"],
    "Description": ["apoptotic process", "cell cycle"],
    "GeneRatio": ["3/100", "4/100"],
    "BgRatio": ["30/1000", "40/1000"],
    "pvalue": [0.001, 0.01],
    "p.adjust": [0.02, 0.08],
    "qvalue": [0.02, 0.08],
    "geneID": ["TP53/JUN", "CCND1/CDK4"],
    "Count": [3, 4],
    "ontology": ["BP", "BP"],
})

STANDARD_VOCAB = pd.DataFrame({
    "term_id": ["GO:0006915"], "description": ["apoptotic process"], "fdr": [0.02],
})

DOTTED_VOCAB = pd.DataFrame({
    "GO.ID": ["GO:0006915"], "GO.Term": ["apoptotic process"],
    "Gene.Ratio": ["3/100"], "pvalue": [0.001], "Adjusted.P.value": [0.02],
})

ONTOLOGY_INDICATOR = pd.DataFrame({
    "ID": ["GO:1"], "Description": ["x"], "ontology": ["BP"],
})


class TestIsGoDataframe:
    @pytest.mark.parametrize("df", [R_VOCAB, STANDARD_VOCAB, DOTTED_VOCAB, ONTOLOGY_INDICATOR])
    def test_go_vocab_positive(self, df):
        assert _is_go_dataframe(df) is True

    def test_r_vocab_subset_without_ratio(self):
        # GeneRatio/BgRatio 없이 geneID+Count만 있어도 GO
        df = R_VOCAB.drop(columns=["GeneRatio", "BgRatio"])
        assert _is_go_dataframe(df) is True

    @pytest.mark.parametrize("name,df", [
        ("DE", pd.DataFrame({"gene_id": ["g1"], "log2fc": [1.0], "adj_pvalue": [0.01]})),
        ("ATAC", pd.DataFrame({"peak_id": ["p1"], "log2fc": [1.0], "adj_pvalue": [0.01]})),
        ("multi-group", pd.DataFrame({"gene_id": ["g1"], "basemean": [1], "stat": [1],
                                      "pvalue": [0.1], "padj": [0.1],
                                      "s1": [1.], "s2": [2.], "s3": [3.]})),
        ("generic id+desc", pd.DataFrame({"id": ["a"], "description": ["b"]})),
        ("generic id+desc+p", pd.DataFrame({"id": ["a"], "description": ["b"], "pvalue": [0.1]})),
        ("empty", pd.DataFrame()),
    ])
    def test_non_go_negative(self, name, df):
        assert _is_go_dataframe(df) is False


class TestGoStandardizeBranch:
    def test_r_vocab_standardizes_to_contract(self, tmp_path):
        """R-vocab → standardize_go_dataframe: 표준 컬럼/_gene_set 획득 (DB 브랜치 로직)."""
        out = standardize_go_dataframe(R_VOCAB.copy())
        assert {"term_id", "description", "fdr", "gene_symbols", "gene_count"} <= set(out.columns)
        assert out["term_id"].iloc[0] == "GO:0006915"
        assert set(out.loc[0, "_gene_set"]) == {"TP53", "JUN"}
        assert out["ontology"].iloc[0] in ("BP", "UNKNOWN")

    def test_branch_reesave_parquet(self, tmp_path):
        """DB 자동임포트 브랜치: gene_set 없는 GO parquet → 표준화 후 재저장."""
        from models.standard_columns import StandardColumns as SC
        f = tmp_path / "1D_vs_CONTROL_GO_KEGG.parquet"
        R_VOCAB.to_parquet(f)
        df = pd.read_parquet(f)
        # 브랜치와 동일한 호출 순서
        if SC.GENE_SET not in df.columns:
            df = standardize_go_dataframe(df)
            for col in (SC.DIRECTION, SC.ONTOLOGY, SC.GENE_SET):
                if col not in df.columns:
                    df[col] = "UNKNOWN"
            df.to_parquet(f, index=False)
        again = pd.read_parquet(f)
        assert "_gene_set" in again.columns
        assert again["gene_set"].iloc[0] == "UNKNOWN"  # R 파일엔 gene_set 없음 → fallback
        assert again["_gene_set"].map(lambda s: len(s) > 0).all()

class TestMultiGroupDetection:
    def test_p_value_coexpression_module_variant(self):
        from utils.multi_group_loader import MultiGroupLoader
        df = pd.DataFrame({
            "gene_symbol": ["a", "b", "c"], "gene_id": ["1", "2", "3"],
            "p_value": [0.01, 0.02, 0.03], "r_squared": [0.9, 0.8, 0.7],
            "cluster_id": ["C1", "C1", "C2"],
            "JHL_Con1_S20": [1.0, 2.0, 3.0], "JHL_Con2_S21": [1.1, 2.1, 3.1],
            "JHL_1D_1_S23": [2.0, 3.0, 4.0], "JHL_1D_2_S24": [2.2, 3.2, 4.2],
            "JHL_3D_1_S32": [4.0, 5.0, 6.0],
        })
        assert MultiGroupLoader.is_multi_group_dataframe(df) is True

    def test_de_not_reclassified(self):
        from utils.multi_group_loader import MultiGroupLoader
        df = pd.DataFrame({"gene_id": ["g"], "log2fc": [1.0], "padj": [0.01],
                           "s1": [1.0], "s2": [2.0], "s3": [3.0]})
        assert MultiGroupLoader.is_multi_group_dataframe(df) is False
