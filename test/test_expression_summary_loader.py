"""ExpressionSummaryLoader / dot plot renderer tests."""

import pandas as pd
import pytest

from models.data_models import DatasetType
from utils.expression_summary_loader import ExpressionSummaryLoader


def _wide():
    return pd.DataFrame({
        "gene_id": ["G1", "G2", "G3"],
        "gene_name": ["Nkx2-4", "Gaba1", "Tbr1"],
        "CT_A": [1.0, 2.0, 3.0],
        "CT_B": [4.0, 5.0, 6.0],
        "CT_C": [7.0, 8.0, 9.0],
    })


def test_wide_load_and_standardize():
    ds = ExpressionSummaryLoader().load_from_dataframe(_wide(), name="expr")
    assert ds.dataset_type == DatasetType.EXPRESSION_SUMMARY
    assert ds.is_valid
    assert ds.metadata["cell_types"] == ["CT_A", "CT_B", "CT_C"]
    assert ds.metadata["gene_id_type"] == "symbol"
    assert str(ds.dataframe["CT_A"].dtype) == "float32"


def test_gene_name_fallback_and_first_column_gene_id():
    df = pd.DataFrame({"gene": ["G1", "G2"], "A": [1.0, 2.0], "B": [3.0, 4.0]})
    ds = ExpressionSummaryLoader().load_from_dataframe(df, name="expr")
    assert list(ds.dataframe["gene_id"]) == ["G1", "G2"]
    assert list(ds.dataframe["gene_name"]) == ["G1", "G2"]
    assert ds.metadata["cell_types"] == ["A", "B"]


def test_long_layout_pivots_to_wide():
    df = pd.DataFrame({
        "gene_id": ["G1", "G1", "G2"],
        "gene_name": ["A", "A", "B"],
        "cell_type": ["CT_A", "CT_B", "CT_A"],
        "dataset": ["ds1", "ds1", "ds1"],
        "n_cells": [10, 10, 10],
        "pct_expressing": [50.0, 0.0, 100.0],
        "mean_expression": [1.0, 2.0, 3.0],
    })
    ds = ExpressionSummaryLoader().load_from_dataframe(df, name="long")
    assert ds.metadata["layout"] == "long"
    assert ds.metadata["cell_types"] == ["CT_A || ds1", "CT_B || ds1"]
    assert ds.metadata["pct_scale"] == "0-100"
    assert ds.is_valid
    assert ds.metadata["pct_matrix"] is not None
    assert ds.metadata["gene_index"] is not None
    assert ds.metadata["cell_type_summary"] is not None
    # gene × cell type 값이 wide로 pivot된다.
    row = ds.dataframe.set_index("gene_id").loc["G1"]
    assert row["CT_A || ds1"] == 1.0
    assert row["CT_B || ds1"] == 2.0


def test_long_layout_row_cap(monkeypatch):
    import utils.expression_summary_loader as mod

    df = pd.DataFrame({
        "gene_id": ["G1", "G2", "G3"],
        "cell_type": ["CT_A", "CT_A", "CT_A"],
        "mean_expression": [1.0, 2.0, 3.0],
    })
    monkeypatch.setattr(mod, "MAX_LONG_ROWS", 2)
    with pytest.raises(ValueError, match="pivot limit"):
        ExpressionSummaryLoader().load_from_dataframe(df, name="long")


def test_companions_loaded(tmp_path):
    (tmp_path / "mean.parquet").parent.mkdir(exist_ok=True)
    _wide().to_parquet(tmp_path / "mean.parquet")
    pct = pd.DataFrame({"gene_id": ["G1", "G2", "G3"],
                        "CT_A": [10.0, 20.0, 30.0],
                        "CT_B": [40.0, 50.0, 60.0],
                        "CT_C": [70.0, 80.0, 90.0]})
    pct.to_parquet(tmp_path / "pct.parquet")
    pd.DataFrame({"gene_id": ["G1", "G2", "G3"],
                  "max_mean": [9.0, 8.0, 7.0]}).to_parquet(tmp_path / "gene_index.parquet")
    pd.DataFrame({"cell_type": ["CT_A", "CT_B", "CT_C"],
                  "n_cells": [10, 20, 30]}).to_parquet(tmp_path / "summary.parquet")

    schema = {
        "layout": "wide",
        "pct_scale": "0-100",
        "companion_files": {
            "pct": "pct.parquet",
            "gene_index": "gene_index.parquet",
            "cell_type_summary": "summary.parquet",
        },
    }
    ds = ExpressionSummaryLoader(schema).load(tmp_path / "mean.parquet", "expr")
    assert ds.metadata["pct_matrix"] is not None
    assert len(ds.metadata["pct_matrix"]) == 3
    assert ds.metadata["gene_index"] is not None
    assert ds.metadata["cell_type_summary"] is not None


def test_dot_plot_build_and_render():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from plots.expression_dot import build_expression_long, render_expression_dot

    long = build_expression_long(_wide(), genes=["Nkx2-4", "Gaba1"],
                                 cell_types=["CT_A", "CT_B"],
                                 pct_scale="0-1", min_pct=0.0, min_n_cells=0.0)
    assert len(long) == 4
    assert set(long["cell_type"]) == {"CT_A", "CT_B"}

    fig = Figure()
    ax = fig.add_subplot(111)
    info = render_expression_dot(ax, long, {"top_cell_types": 2, "label_limit": 20})
    assert info["points"]
    assert len(info["genes"]) == 2


def test_pct_scale_conversion():
    from plots.expression_dot import build_expression_long

    wide = pd.DataFrame({"gene_id": ["G1"], "gene_name": ["A"], "CT_A": [1.0]})
    pct_100 = pd.DataFrame({"gene_id": ["G1"], "CT_A": [50.0]})
    long = build_expression_long(wide, pct_100, genes=["G1"], cell_types=["CT_A"],
                                 pct_scale="0-100")
    assert long["pct_display"].iloc[0] == 50.0

    pct_01 = pd.DataFrame({"gene_id": ["G1"], "CT_A": [0.5]})
    long = build_expression_long(wide, pct_01, genes=["G1"], cell_types=["CT_A"],
                                 pct_scale="0-1")
    assert long["pct_display"].iloc[0] == 50.0
