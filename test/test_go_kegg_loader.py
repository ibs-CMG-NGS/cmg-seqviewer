"""
GOKEGGLoader 필수 컬럼 검증 테스트 (반입 일반성 감사 후속 — methods paper 대비).

standardize_columns()의 리터럴 컬럼명 매핑 목록에 없는 헤더를 쓰는 파이프라인
출력은, 매핑 콜백이 없으면 명확한 에러로 실패해야 하고 (과거엔 조용히
description/gene_count/fdr이 빈 Dataset이 만들어졌음), 콜백이 있으면 수동
매핑으로 복구할 수 있어야 한다.
"""

from pathlib import Path

import pandas as pd
import pytest

from models.data_models import DatasetType
from utils.go_kegg_loader import GOKEGGLoader, ensure_go_required_columns


def _unrecognized_go_df() -> pd.DataFrame:
    # 이 헤더들은 standardize_columns()의 ~45개 리터럴 매핑 중 어느 것과도 일치하지 않음
    # (예: 파이썬 GSEApy/goatools 직접 실행 결과의 자체 명명 규칙을 흉내).
    return pd.DataFrame([
        {"Name": "immune response", "Hits": 5, "Adj_P": 0.01, "Genes_Hit": "A;B;C;D;E"},
        {"Name": "cell adhesion", "Hits": 3, "Adj_P": 0.2, "Genes_Hit": "A;B;C"},
    ])


class TestEnsureGoRequiredColumns:
    def test_passes_through_when_already_standard(self):
        df = pd.DataFrame([
            {"term_id": "GO:0000001", "description": "x", "gene_count": 2, "fdr": 0.01},
        ])
        out = ensure_go_required_columns(df)
        assert list(out.columns) == list(df.columns)

    def test_raises_actionable_error_without_callback(self):
        df = _unrecognized_go_df()
        with pytest.raises(ValueError) as exc_info:
            ensure_go_required_columns(df)
        msg = str(exc_info.value)
        # 어떤 필드가 없는지 + 실제 사용 가능한 컬럼이 뭔지 둘 다 에러에 담겨야 함
        assert "description" in msg and "gene_count" in msg and "fdr" in msg
        assert "Name" in msg and "Hits" in msg  # available columns echoed back

    def test_callback_mapping_recovers(self):
        df = _unrecognized_go_df()

        def fake_mapper(d, dataset_type, auto_mapping):
            assert dataset_type == DatasetType.GO_ANALYSIS
            return {"description": "Name", "gene_count": "Hits", "fdr": "Adj_P"}

        out = ensure_go_required_columns(df, fake_mapper)
        assert {"description", "gene_count", "fdr"}.issubset(out.columns)
        assert out["description"].tolist() == ["immune response", "cell adhesion"]

    def test_callback_cancelled_raises(self):
        df = _unrecognized_go_df()
        with pytest.raises(ValueError, match="cancelled"):
            ensure_go_required_columns(df, lambda d, t, a: None)

    def test_callback_incomplete_mapping_still_raises(self):
        df = _unrecognized_go_df()
        # 사용자가 description만 매핑하고 gene_count/fdr은 남겨둔 경우
        with pytest.raises(ValueError, match="after manual mapping"):
            ensure_go_required_columns(df, lambda d, t, a: {"description": "Name"})


class TestGOKEGGLoaderValidation:
    def test_load_from_csv_files_unrecognized_headers_raises(self, tmp_path):
        df = _unrecognized_go_df()
        f = tmp_path / "custom_pipeline_go.csv"
        df.to_csv(f, index=False)
        with pytest.raises(ValueError, match="Missing required GO/KEGG columns"):
            GOKEGGLoader().load_from_csv_files([f])

    def test_load_from_csv_files_with_mapper_succeeds(self, tmp_path):
        df = _unrecognized_go_df()
        f = tmp_path / "custom_pipeline_go.csv"
        df.to_csv(f, index=False)

        def fake_mapper(d, dataset_type, auto_mapping):
            return {"description": "Name", "gene_count": "Hits", "fdr": "Adj_P"}

        dataset = GOKEGGLoader().load_from_csv_files([f], column_mapper_callback=fake_mapper)
        assert dataset.dataset_type == DatasetType.GO_ANALYSIS
        assert len(dataset.dataframe) == 2
        assert "description" in dataset.dataframe.columns

    def test_load_from_excel_recognized_headers_no_callback_needed(self, tmp_path):
        # 기존(인식되는) clusterProfiler 스타일 헤더는 여전히 콜백 없이 통과해야 함 (회귀 방지)
        df = pd.DataFrame([
            {"GO ID": "GO:0000001", "GO Term": "immune response", "Count": 5,
             "Adjusted P-value": 0.01, "Genes": "A;B"},
        ])
        f = tmp_path / "clusterprofiler_go.xlsx"
        with pd.ExcelWriter(f) as w:
            df.to_excel(w, sheet_name="BP", index=False)
        dataset = GOKEGGLoader().load_from_excel(f)
        assert dataset.dataset_type == DatasetType.GO_ANALYSIS
        assert dataset.dataframe.loc[0, "description"] == "immune response"
