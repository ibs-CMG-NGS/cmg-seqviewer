"""ExpressionDistributionDialog smoke tests (pytest-qt)."""

import json

import pandas as pd

from models.data_models import Dataset, DatasetType
from gui.expression_distribution_dialog import ExpressionDistributionDialog
from utils.expression_distribution_loader import ExpressionDistributionLoader


def _df(n_cell_types=12):
    rows = []
    for gene in ("G1", "G2"):
        for i in range(n_cell_types):
            for sample, condition in (("s1", "Control"), ("s2", "Control"),
                                      ("s3", "Treated")):
                rows.append({
                    "gene_id": gene,
                    "gene_name": gene,
                    "cell_type": f"CT_{i:02d}",
                    "sample": sample,
                    "dataset": "ds1",
                    "condition": condition,
                    "n_cells": 20 + i,
                    "n_expressing": 10,
                    "pct_expressing": 50.0,
                    "mean_expression": float(i) + (0.5 if gene == "G2" else 0.0),
                    "mean_counts": float(i) * 2,
                })
    return pd.DataFrame(rows)


def _dataset(n_cell_types=12):
    df = _df(n_cell_types)
    ds = Dataset(
        name="dist",
        dataset_type=DatasetType.EXPRESSION_DISTRIBUTION,
        dataframe=df,
        metadata={
            "layout": "pseudobulk",
            "pct_scale": "0-100",
            "cell_types": [f"CT_{i:02d}" for i in range(n_cell_types)],
            "gene_count": 2,
            "cell_type_count": n_cell_types,
            "sample_count": 3,
            "distribution_schema": {"layout": "pseudobulk", "pct_scale": "0-100"},
        },
    )
    return ds


def test_dialog_opens_with_top10_and_violin(qtbot):
    dialog = ExpressionDistributionDialog(_dataset())
    qtbot.addWidget(dialog)
    assert dialog.figure.axes
    assert dialog._selected_genes == ["G2"]  # highest max mean by default
    assert len(dialog._selected_cell_types()) == 10
    assert dialog.plot_combo.currentText() == "Violin"
    assert dialog.group_combo.currentData() == "condition"


def test_add_gene_and_switch_plot(qtbot):
    dialog = ExpressionDistributionDialog(_dataset())
    qtbot.addWidget(dialog)
    dialog.gene_search.setText("G2")
    dialog._add_gene_from_search()
    assert "G2" in dialog._selected_genes
    dialog.plot_combo.setCurrentText("Box + points")
    assert dialog.figure.axes
    dialog.log_check.setChecked(True)
    assert dialog.figure.axes


def test_filters_and_export_context_are_json_safe(qtbot):
    dialog = ExpressionDistributionDialog(_dataset())
    qtbot.addWidget(dialog)
    dialog.min_ncells_spin.setValue(25)
    dialog.min_pct_spin.setValue(40)
    filtered = dialog._filtered_df()
    assert not filtered.empty
    assert filtered["n_cells"].min() >= 25

    ctx = dialog.get_bundle_context()
    assert ctx["plot_type"] == "expression_distribution"
    json.dumps(ctx["plot_params"])
    assert "mean_expression" in ctx["dataframe"].columns


def test_quantile_dialog_disables_violin(qtbot):
    df = _df(3).drop(columns=["sample"]).drop_duplicates(["gene_id", "cell_type"])
    for col, base in (("p10", 0.5), ("p25", 0.8), ("median", 1.0),
                      ("p75", 1.2), ("p90", 1.4)):
        df[col] = base
    ds = ExpressionDistributionLoader().load_from_dataframe(df, name="quant")
    dialog = ExpressionDistributionDialog(ds)
    qtbot.addWidget(dialog)
    assert dialog.plot_combo.currentText() == "Box"
    dialog.plot_combo.setCurrentText("Violin")
    assert dialog.plot_combo.currentText() == "Box"
    assert dialog.figure.axes


def test_bundle_script_is_generated(qtbot, tmp_path):
    from utils.figure_bundle_export import export_figure_bundle

    dialog = ExpressionDistributionDialog(_dataset())
    qtbot.addWidget(dialog)
    ctx = dialog.get_bundle_context()
    out = export_figure_bundle(
        ctx, tmp_path / "bundle", ctx["figure_slug"],
        ctx["figure_title"], ctx["plot_type"])

    script = (out / "scripts" / "figure.py").read_text(encoding="utf-8")
    assert "render_expression_distribution" in script
    assert "_GROUP_COLORS" in script


def test_empty_gene_or_cell_type_selection_shows_placeholder(qtbot):
    dialog = ExpressionDistributionDialog(_dataset())
    qtbot.addWidget(dialog)
    dialog.cell_type_list.clearSelection()
    dialog._update_plot()
    assert dialog._current_plot_df.empty
    assert dialog.figure.axes

    dialog._select_top10_cell_types()
    dialog._clear_genes()
    assert dialog._current_plot_df.empty
    assert dialog.figure.axes
