"""ExpressionSummaryDialog smoke tests (pytest-qt)."""

import pandas as pd
import pytest

from models.data_models import Dataset, DatasetType
from gui.expression_summary_dialog import ExpressionSummaryDialog
from utils.expression_summary_loader import ExpressionSummaryLoader


@pytest.fixture(autouse=True)
def _clear_expression_state():
    ExpressionSummaryDialog._saved_states.clear()
    yield
    ExpressionSummaryDialog._saved_states.clear()


def _many_cell_types():
    df = pd.DataFrame({"gene_id": ["G1"], "gene_name": ["A"]})
    for i in range(15):
        df[f"CT_{i:02d}"] = [float(i)]
    return ExpressionSummaryLoader().load_from_dataframe(df, name="many")


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


def test_n_cells_map_handles_dataset_suffix():
    from gui.expression_summary_dialog import ExpressionSummaryDialog

    summary = pd.DataFrame({
        "cell_type": ["A", "A"],
        "dataset": ["d1", "d2"],
        "n_cells": [10, 20],
    })
    out = ExpressionSummaryDialog._n_cells_map(summary)
    assert out["A"] == 30.0
    assert out["A || d1"] == 10.0
    assert out["A || d2"] == 20.0


def test_dialog_with_companions(qtbot):
    ds = _dataset()
    ds.metadata["pct_matrix"] = ds.dataframe[["gene_id", "CT_A", "CT_B", "CT_C"]].copy()
    ds.metadata["pct_matrix"].loc[0, "CT_B"] = 0.0  # zero-expression dot is dropped
    ds.metadata["gene_index"] = pd.DataFrame({
        "gene_id": ["G1", "G2", "G3"],
        "gene_name": ["Nkx2-4", "Gaba1", "Tbr1"],
        "max_mean_expression": [9.0, 8.0, 7.0],
        "max_pct_expressing": [90.0, 80.0, 70.0],
        "n_cell_types_detected": [3, 3, 3],
        "top_cell_type": ["CT_A", "CT_B", "CT_C"],
        "top_mean_expression": [9.0, 8.0, 7.0],
    })
    ds.metadata["cell_type_summary"] = pd.DataFrame({
        "cell_type": ["CT_A", "CT_B", "CT_C"],
        "n_cells": [100, 200, 300],
    })
    ds.metadata["pct_scale"] = "0-100"

    dialog = ExpressionSummaryDialog(ds)
    qtbot.addWidget(dialog)
    assert "max mean" in dialog.gene_info_label.text() and "top=" in dialog.gene_info_label.text()
    dialog.min_ncells_spin.setValue(250)
    assert dialog.figure.axes
    dialog.view_combo.setCurrentIndex(1)
    assert dialog.figure.axes
    heat = dialog._heatmap_df()
    assert len(heat) == 1
    assert heat.drop(columns=["gene_id", "symbol"]).isna().sum().sum() == 0

def test_initial_selection_is_top10_by_mean(qtbot):
    dialog = ExpressionSummaryDialog(_many_cell_types())
    qtbot.addWidget(dialog)
    selected = set(dialog._selected_cell_types())
    assert len(selected) == 10
    # mean이 높은 CT_14 ... CT_05가 선택되어야 한다.
    assert selected == {f"CT_{i:02d}" for i in range(5, 15)}
    assert dialog.top_cell_spin.value() == 0


def test_cell_type_selection_is_restored_in_session(qtbot):
    ds = _many_cell_types()
    dialog = ExpressionSummaryDialog(ds)
    qtbot.addWidget(dialog)
    wanted = {"CT_00", "CT_01"}
    for i in range(dialog.cell_type_list.count()):
        item = dialog.cell_type_list.item(i)
        item.setSelected(item.text() in wanted)
    dialog._save_state()

    dialog2 = ExpressionSummaryDialog(ds)
    qtbot.addWidget(dialog2)
    assert set(dialog2._selected_cell_types()) == wanted


def test_filtered_sheet_uses_root_data_and_limits_genes(qtbot):
    root = _dataset()
    filtered = Dataset(
        name="Filtered: Gene List (1 genes)",
        dataset_type=DatasetType.EXPRESSION_SUMMARY,
        dataframe=root.dataframe[root.dataframe["gene_id"] == "G2"].copy(),
        metadata=root.metadata.copy(),
    )
    dialog = ExpressionSummaryDialog(
        filtered, source_dataset=root,
        initial_genes=["G2"], allowed_genes=["G2"])
    qtbot.addWidget(dialog)

    assert len(dialog.wide_df) == 3  # root full matrix
    assert [r["gene_id"] for r in dialog._gene_rows] == ["G2"]
    assert dialog._selected_genes == ["G2"]
    assert "g1" not in dialog._gene_key_to_id
    assert "g3" not in dialog._gene_key_to_id

