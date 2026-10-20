"""ExpressionSummaryDialog smoke tests (pytest-qt)."""

import pandas as pd

from gui.expression_summary_dialog import ExpressionSummaryDialog
from utils.expression_summary_loader import ExpressionSummaryLoader


def _dataset():
    df = pd.DataFrame({
        "gene_id": ["G1", "G2", "G3"],
        "gene_name": ["Nkx2-4", "Gaba1", "Tbr1"],
        "CT_A": [1.0, 2.0, 3.0],
        "CT_B": [4.0, 5.0, 6.0],
        "CT_C": [7.0, 8.0, 9.0],
    })
    return ExpressionSummaryLoader().load_from_dataframe(df, name="expr")


def test_dialog_opens_and_plots_dot(qtbot):
    dialog = ExpressionSummaryDialog(_dataset())
    qtbot.addWidget(dialog)
    assert dialog.figure.axes
    assert dialog._selected_genes == ["G1"]
    assert dialog.view_combo.currentIndex() == 0

    # 다른 유전자 추가
    dialog.gene_search.setText("Gaba1")
    dialog._add_gene_from_search()
    assert "G2" in dialog._selected_genes
    assert dialog.figure.axes


def test_dialog_switches_to_heatmap(qtbot):
    dialog = ExpressionSummaryDialog(_dataset())
    qtbot.addWidget(dialog)
    dialog.view_combo.setCurrentIndex(1)
    assert dialog.figure.axes


def test_bundle_context_is_serializable(qtbot):
    import json
    dialog = ExpressionSummaryDialog(_dataset())
    qtbot.addWidget(dialog)
    ctx = dialog.get_bundle_context()
    assert ctx["plot_type"] == "expression_dot"
    # plot_params must contain no DataFrame (project/bundle JSON safe)
    json.dumps(ctx["plot_params"])
    assert "mean_expression" in ctx["dataframe"].columns

    dialog.view_combo.setCurrentIndex(1)
    ctx = dialog.get_bundle_context()
    assert ctx["plot_type"] == "heatmap"
    json.dumps(ctx["plot_params"])


def test_dialog_with_companions(qtbot):
    ds = _dataset()
    ds.metadata["pct_matrix"] = ds.dataframe[["gene_id", "CT_A", "CT_B", "CT_C"]].copy()
    ds.metadata["gene_index"] = pd.DataFrame({
        "gene_id": ["G1", "G2", "G3"],
        "gene_name": ["Nkx2-4", "Gaba1", "Tbr1"],
        "max_mean": [9.0, 8.0, 7.0],
        "max_pct": [90.0, 80.0, 70.0],
        "n_cell_types_detected": [3, 3, 3],
    })
    ds.metadata["cell_type_summary"] = pd.DataFrame({
        "cell_type": ["CT_A", "CT_B", "CT_C"],
        "n_cells": [100, 200, 300],
    })
    ds.metadata["pct_scale"] = "0-100"

    dialog = ExpressionSummaryDialog(ds)
    qtbot.addWidget(dialog)
    assert "max mean" in dialog.gene_info_label.text()
    dialog.min_ncells_spin.setValue(250)
    assert dialog.figure.axes
    dialog.view_combo.setCurrentIndex(1)
    assert dialog.figure.axes

