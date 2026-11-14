"""Pure FilterEngine coverage for every dataset/filter mode."""

import pandas as pd

from models.data_models import Dataset, DatasetType, FilterCriteria, FilterMode
from services.filter_engine import FilterEngine


def _dataset(name, dataset_type, df):
    return Dataset(name, dataset_type, dataframe=df)


def test_column_subset_and_keyword_fallback():
    ds = _dataset(
        "de",
        DatasetType.DIFFERENTIAL_EXPRESSION,
        pd.DataFrame(
            {
                "gene_id": ["G1", "G2"],
                "symbol": ["Alpha", "Beta"],
                "log2fc": [2.0, -2.0],
                "adj_pvalue": [0.01, 0.02],
            }
        ),
    )
    engine = FilterEngine()
    subset = engine.filter(
        ds,
        FilterCriteria(
            mode=FilterMode.COLUMN_SUBSET, subset_columns=["symbol", "gene_id"]
        ),
    )
    assert list(subset.columns) == ["gene_id", "symbol"]

    hits = engine.filter(
        ds, FilterCriteria(mode=FilterMode.KEYWORD, search_keyword="alph")
    )
    assert list(hits["gene_id"]) == ["G1"]


def test_go_statistical_and_gene_symbols():
    ds = _dataset(
        "go",
        DatasetType.GO_ANALYSIS,
        pd.DataFrame(
            {
                "term_id": ["GO:1", "GO:2", "GO:3"],
                "description": ["a", "b", "c"],
                "fdr": [0.01, 0.2, 0.01],
                "ontology": ["BP", "BP", "CC"],
                "gene_set": ["UP", "UP", "UP"],
                "fold_enrichment": [2.0, 1.0, 3.0],
                "gene_count": [5, 2, 4],
                "gene_symbols": ["G1/G2", "G3", "G1"],
            }
        ),
    )
    engine = FilterEngine()
    out = engine.filter(
        ds,
        FilterCriteria(
            mode=FilterMode.STATISTICAL,
            fdr_max=0.05,
            ontology="BP",
            go_direction="UP",
            fold_enrichment_min=1.0,
            go_min_gene_count=2,
        ),
    )
    assert list(out["term_id"]) == ["GO:1"]

    genes = engine.filter(
        ds, FilterCriteria(mode=FilterMode.GENE_LIST, gene_list=["G1"])
    )
    assert list(genes["term_id"]) == ["GO:1", "GO:3"]

    terms = engine.filter(
        ds, FilterCriteria(mode=FilterMode.GENE_LIST, term_id_list=["GO:3", "GO:1"])
    )
    assert list(terms["term_id"]) == ["GO:3", "GO:1"]


def test_multi_group_and_composition():
    mg = _dataset(
        "mg",
        DatasetType.MULTI_GROUP,
        pd.DataFrame(
            {
                "gene_id": ["G1", "G2", "G3"],
                "padj": [0.01, 0.2, 0.01],
                "base_mean": [20, 30, 5],
            }
        ),
    )
    out = FilterEngine().filter(
        mg,
        FilterCriteria(
            mode=FilterMode.STATISTICAL, mg_padj_max=0.05, mg_basemean_min=10
        ),
    )
    assert list(out["gene_id"]) == ["G1"]

    comp = _dataset(
        "comp",
        DatasetType.COMPOSITION,
        pd.DataFrame(
            {
                "cell_type": ["A", "B", "C"],
                "fdr": [0.01, 0.2, 0.04],
                "prop_ratio": [0.5, 0.2, 0.3],
            }
        ),
    )
    out = FilterEngine().filter(
        comp, FilterCriteria(mode=FilterMode.STATISTICAL, fdr_max=0.05)
    )
    assert list(out["cell_type"]) == ["A", "C"]


def test_atac_statistics_and_gene_list():
    ds = _dataset(
        "atac",
        DatasetType.ATAC_SEQ,
        pd.DataFrame(
            {
                "peak_id": ["P1", "P2", "P3"],
                "nearest_gene": ["G1", "G2", "G1"],
                "log2fc": [2.0, -2.0, 0.5],
                "adj_pvalue": [0.01, 0.02, 0.01],
                "annotation": ["Promoter", "Enhancer", "Promoter"],
                "distance_to_tss": [100, 5000, 200],
                "peak_width": [500, 2000, 100],
            }
        ),
    )
    engine = FilterEngine()
    out = engine.filter(
        ds,
        FilterCriteria(
            mode=FilterMode.STATISTICAL,
            adj_pvalue_max=0.05,
            log2fc_min=1.0,
            atac_annotation="Promoter",
            atac_distance_max=1000,
            atac_peak_width_min=200,
        ),
    )
    assert list(out["peak_id"]) == ["P1"]

    genes = engine.filter(
        ds, FilterCriteria(mode=FilterMode.GENE_LIST, gene_list=["G1"])
    )
    assert list(genes["peak_id"]) == ["P1", "P3"]


def test_unsupported_and_empty_inputs_return_none():
    engine = FilterEngine()
    assert engine.filter(None, FilterCriteria()) is None
    ds = _dataset(
        "expr",
        DatasetType.EXPRESSION_SUMMARY,
        pd.DataFrame(
            {
                "gene_id": ["G1"],
                "cell_type": ["A"],
                "mean_expression": [1.0],
            }
        ),
    )
    assert engine.filter(ds, FilterCriteria(mode=FilterMode.STATISTICAL)) is None
    assert (
        engine.filter(ds, FilterCriteria(mode=FilterMode.KEYWORD, search_keyword=""))
        is None
    )
