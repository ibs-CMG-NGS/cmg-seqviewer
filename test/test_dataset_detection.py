"""
utils.dataset_detection.load_any_dataset() 테스트.

MainPresenter.load_dataset()에서 추출한 파일->Dataset 판별 로직 — presenter/뷰
없이 순수하게 동작해야 CLI가 같은 경로를 재사용할 수 있다. 여기서는 추출 자체가
행동을 안 바꿨는지(각 분기 1개씩) + Qt 전혀 없이 동작하는지를 확인한다. 각 로더
자체의 상세 동작(컬럼 매핑 등)은 test_go_kegg_loader.py / test_atac_seq_loader.py /
test_data_loader_column_mapping.py에서 이미 다룬다.
"""

import pandas as pd

from models.data_models import DatasetType
from utils.data_loader import DataLoader
from utils.dataset_detection import load_any_dataset, looks_like_go_frame


class TestLoadAnyDatasetNoQt:
    """PyQt6 임포트/인스턴스 없이 순수하게 동작하는지 — CLI 전제 조건."""

    def test_de_excel(self, tmp_path):
        df = pd.DataFrame({
            "gene_id": ["G1", "G2"], "log2fc": [1.0, -2.0], "adj_pvalue": [0.01, 0.02],
        })
        f = tmp_path / "de.xlsx"
        df.to_excel(f, index=False)
        ds = load_any_dataset(f, DataLoader())
        assert ds.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION
        assert ds.is_valid

    def test_go_excel(self, tmp_path):
        df = pd.DataFrame([
            {"GO ID": "GO:0000001", "GO Term": "x", "Count": 3, "Adjusted P-value": 0.01},
        ])
        f = tmp_path / "go.xlsx"
        with pd.ExcelWriter(f) as w:
            df.to_excel(w, sheet_name="BP", index=False)
        ds = load_any_dataset(f, DataLoader())
        assert ds.dataset_type == DatasetType.GO_ANALYSIS

    def test_atac_via_hint_overrides_detection(self, tmp_path):
        # peak-id 패턴과 안 맞는 헤더도 힌트로 강제 가능 (§감사 finding #5)
        df = pd.DataFrame([{"Region": "r1", "LFC": 1.2, "FDR_adj": 0.01}])
        f = tmp_path / "weird_atac.parquet"
        df.to_parquet(f)

        def fake_mapper(d, dt, auto):
            return {"peak_id": "Region", "log2fc": "LFC", "adj_pvalue": "FDR_adj"}

        ds = load_any_dataset(f, DataLoader(), dataset_type_hint=DatasetType.ATAC_SEQ,
                              column_mapper_callback=fake_mapper)
        assert ds.dataset_type == DatasetType.ATAC_SEQ
        assert ds.is_valid

    def test_go_frame_parquet_restore(self, tmp_path):
        df = pd.DataFrame([
            {"term_id": "GO:0000001", "description": "x", "gene_count": 2, "fdr": 0.01,
             "ontology": "BP", "direction": "TOTAL", "gene_set": "TOTAL"},
        ])
        f = tmp_path / "go_frame.parquet"
        df.to_parquet(f)
        ds = load_any_dataset(f, DataLoader())
        assert ds.dataset_type == DatasetType.GO_ANALYSIS

    def test_multi_group_csv(self, tmp_path):
        df = pd.DataFrame({
            "gene_id": ["G1", "G2", "G3"],
            "padj": [0.01, 0.2, 0.03],
            "sample_a": [1.0, 2.0, 3.0],
            "sample_b": [1.1, 2.1, 3.1],
            "sample_c": [1.2, 2.2, 3.2],
        })
        f = tmp_path / "mg.csv"
        df.to_csv(f, index=False)
        ds = load_any_dataset(f, DataLoader())
        assert ds.dataset_type == DatasetType.MULTI_GROUP

    def test_missing_required_columns_raises_without_mapper(self, tmp_path):
        df = pd.DataFrame({"Name": ["immune response"], "Hits": [5], "Adj_P": [0.01]})
        f = tmp_path / "unrecognized_go.csv"
        df.to_csv(f, index=False)
        # 이 파일은 어떤 전용 감지기와도 안 맞아 기본 DE 폴백으로 떨어지고,
        # column_mapper_callback 없이는 필수 컬럼 누락으로 명확히 실패해야 한다
        # (조용히 깨진 Dataset을 만들지 않음 — §반입 일반성 감사 원칙).
        import pytest
        with pytest.raises(ValueError):
            load_any_dataset(f, DataLoader())


def test_looks_like_go_frame():
    assert looks_like_go_frame(pd.DataFrame(columns=["term_id", "description", "ontology"]))
    assert not looks_like_go_frame(pd.DataFrame(columns=["gene_id", "log2fc", "adj_pvalue"]))
