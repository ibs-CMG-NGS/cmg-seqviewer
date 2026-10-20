"""CompositionDialog 스모크 테스트 (pytest-qt)."""

import pandas as pd

from gui.composition_dialog import CompositionDialog
from utils.composition_loader import CompositionLoader


def _dataset():
    df = pd.DataFrame({
        "cell_type": ["T", "B", "NK"],
        "PropMean.Control": [0.45, 0.30, 0.25],
        "PropMean.Treatment": [0.55, 0.20, 0.25],
        "PropRatio": [0.10, -0.10, 0.0],
        "P.Value": [0.001, 0.02, 0.9],
        "FDR": [0.003, 0.03, 0.95],
    })
    return CompositionLoader().load_from_dataframe(df, name="comp")


def test_dialog_constructs_and_switches_views(qtbot):
    dialog = CompositionDialog(_dataset())
    qtbot.addWidget(dialog)

    assert dialog.figure.axes
    assert dialog.ratio_radio.isChecked()

    dialog.means_radio.setChecked(True)
    assert dialog.means_radio.isChecked()
    assert dialog.figure.axes

    ctx = dialog.get_bundle_context()
    assert ctx["plot_type"] == "composition"
    assert ctx["plot_params"]["mode"] == "means"
    assert len(ctx["dataframe"]) == 3


def test_bundle_script_is_generated(qtbot, tmp_path):
    from utils.figure_bundle_export import export_figure_bundle

    dialog = CompositionDialog(_dataset())
    qtbot.addWidget(dialog)
    ctx = dialog.get_bundle_context()
    out = export_figure_bundle(
        ctx, tmp_path / "bundle", ctx["figure_slug"],
        ctx["figure_title"], ctx["plot_type"])

    script = (out / "scripts" / "figure.py").read_text(encoding="utf-8")
    assert "render_composition" in script
    assert "select_composition_rows" in script
