"""
ATACSeqLoader 필수 컬럼 검증 테스트 (반입 일반성 감사 후속 — methods paper 대비).

COLUMN_PATTERNS에 없는 헤더를 쓰는 파이프라인 출력은, 매핑 콜백이 없으면
명확한 에러로 실패해야 하고(과거엔 조용히 peak_id/log2fc/adj_pvalue가 빈
Dataset이 만들어졌음), 콜백이 있으면 수동 매핑으로 복구할 수 있어야 한다.
"""

import pandas as pd
import pytest

from models.data_models import DatasetType
from utils.atac_seq_loader import ATACSeqLoader


def _unrecognized_atac_df() -> pd.DataFrame:
    # COLUMN_PATTERNS의 어떤 패턴과도 일치하지 않는 임의 명명 규칙.
    return pd.DataFrame([
        {"Region": "region_1", "LFC": 1.5, "FDR_adj": 0.01},
        {"Region": "region_2", "LFC": -0.8, "FDR_adj": 0.2},
    ])


class TestATACSeqLoaderValidation:
    def test_unrecognized_headers_raise_without_callback(self, tmp_path):
        df = _unrecognized_atac_df()
        f = tmp_path / "custom_pipeline_atac.parquet"
        df.to_parquet(f)
        with pytest.raises(ValueError, match="Missing required ATAC-seq columns"):
            ATACSeqLoader().load(f)

    def test_callback_mapping_recovers(self, tmp_path):
        df = _unrecognized_atac_df()
        f = tmp_path / "custom_pipeline_atac.parquet"
        df.to_parquet(f)

        def fake_mapper(d, dataset_type, auto_mapping):
            assert dataset_type == DatasetType.ATAC_SEQ
            return {"peak_id": "Region", "log2fc": "LFC", "adj_pvalue": "FDR_adj"}

        dataset = ATACSeqLoader().load(f, column_mapper_callback=fake_mapper)
        assert dataset.dataset_type == DatasetType.ATAC_SEQ
        assert {"peak_id", "log2fc", "adj_pvalue"}.issubset(dataset.dataframe.columns)
        assert dataset.is_valid

    def test_callback_cancelled_raises(self, tmp_path):
        df = _unrecognized_atac_df()
        f = tmp_path / "custom_pipeline_atac.parquet"
        df.to_parquet(f)
        with pytest.raises(ValueError, match="cancelled"):
            ATACSeqLoader().load(f, column_mapper_callback=lambda d, t, a: None)

    def test_recognized_headers_no_callback_needed(self, tmp_path):
        # 기존(인식되는) DESeq2 스타일 헤더는 여전히 콜백 없이 통과해야 함 (회귀 방지)
        df = pd.DataFrame([
            {"peak_id": "Interval_1", "chr": "chr1", "start": 100, "end": 200,
             "log2FoldChange": 1.2, "padj": 0.01},
        ])
        f = tmp_path / "standard_atac.parquet"
        df.to_parquet(f)
        dataset = ATACSeqLoader().load(f)
        assert dataset.dataset_type == DatasetType.ATAC_SEQ
        assert dataset.is_valid
