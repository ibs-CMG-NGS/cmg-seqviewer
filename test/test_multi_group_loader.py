"""MultiGroupLoader 샘플 컬럼 판별/자동 감지 테스트.

fdr/qvalue/cluster_id 같은 통계·메타 컬럼이 샘플로 오인되지 않아야 하고,
순수 발현행렬은 자동 감지되지 않지만 명시 로드(`--type multi_group`)로는
동작해야 한다.
"""

import pandas as pd

from models.data_models import DatasetType
from utils.multi_group_loader import MultiGroupLoader


def test_detect_sample_columns_excludes_metadata_columns():
    df = pd.DataFrame({
        "gene_id": ["G1", "G2"],
        "gene_symbol": ["A", "B"],
        "cluster_id": [1, 2],          # 숫자형이어도 샘플이 아님
        "fdr": [0.01, 0.02],           # adjusted p-value 계열
        "qvalue": [0.03, 0.04],
        "baseMean": [10.0, 20.0],
        "sample_a": [1.0, 2.0],
        "sample_b": [1.1, 2.1],
        "sample_c": [1.2, 2.2],
    })
    samples = MultiGroupLoader()._detect_sample_columns(df)
    assert samples == ["sample_a", "sample_b", "sample_c"]


def test_multi_group_detected_with_cluster_id_and_samples():
    df = pd.DataFrame({
        "gene_id": ["G1", "G2"],
        "cluster_id": [1, 2],
        "s1": [1.0, 2.0], "s2": [1.1, 2.1], "s3": [1.2, 2.2],
    })
    assert MultiGroupLoader.is_multi_group_dataframe(df)


def test_pure_expression_matrix_not_auto_detected_but_loads_explicitly():
    df = pd.DataFrame({
        "gene_id": ["G1", "G2"],
        "s1": [1.0, 2.0], "s2": [1.1, 2.1], "s3": [1.2, 2.2],
    })
    # padj도 cluster_id도 없으므로 자동 감지 대상은 아니다.
    assert not MultiGroupLoader.is_multi_group_dataframe(df)

    # 명시 로드 경로(--type multi_group)에서는 정상 동작해야 한다.
    ds = MultiGroupLoader().load_from_dataframe(df, name="matrix")
    assert ds.dataset_type == DatasetType.MULTI_GROUP
    assert ds.metadata["sample_columns"] == ["s1", "s2", "s3"]
    assert ds.metadata["sample_groups"] == {"s": ["s1", "s2", "s3"]}


def test_multi_group_loader_csv_without_padj():
    import tempfile
    from pathlib import Path

    df = pd.DataFrame({
        "gene_id": ["G1", "G2"],
        "s1": [1.0, 2.0], "s2": [1.1, 2.1], "s3": [1.2, 2.2],
    })
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "matrix.csv"
        df.to_csv(f, index=False)
        ds = MultiGroupLoader().load(f)
    assert ds.dataset_type == DatasetType.MULTI_GROUP
    assert len(ds.metadata["sample_columns"]) == 3
