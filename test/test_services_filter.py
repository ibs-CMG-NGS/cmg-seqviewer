"""FilterService unit tests (headless)."""

import pandas as pd

from models.data_models import Dataset, DatasetType, FilterCriteria, FilterMode
from services.filter_service import FilterService


def _de_dataset():
    return Dataset(
        "de", DatasetType.DIFFERENTIAL_EXPRESSION,
        dataframe=pd.DataFrame({
            "gene_id": ["G1", "G2", "G3"],
            "log2fc": [2.0, -3.0, 0.1],
            "adj_pvalue": [0.01, 0.02, 0.8],
        }),
    )


def test_statistical_filter():
    svc = FilterService()
    out = svc.filter(_de_dataset(), FilterCriteria(
        mode=FilterMode.STATISTICAL, adj_pvalue_max=0.05, log2fc_min=1.0))
    assert out is not None
    assert list(out["gene_id"]) == ["G1", "G2"]


def test_gene_list_filter_preserves_order():
    svc = FilterService()
    out = svc.filter(_de_dataset(), FilterCriteria(
        mode=FilterMode.GENE_LIST, gene_list=["G3", "G1"]))
    assert out is not None
    assert list(out["gene_id"]) == ["G3", "G1"]


def test_keyword_filter():
    svc = FilterService()
    out = svc.filter(_de_dataset(), FilterCriteria(
        mode=FilterMode.KEYWORD, search_keyword="G2", search_column="gene_id"))
    assert out is not None
    assert list(out["gene_id"]) == ["G2"]
