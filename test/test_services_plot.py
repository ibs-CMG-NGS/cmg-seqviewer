"""PlotService unit tests (Agg, no Qt)."""

import pandas as pd
import pytest

from services.plot_service import PlotService


def test_render_volcano_to_png(tmp_path):
    df = pd.DataFrame({
        "gene_id": ["G1", "G2", "G3"],
        "log2fc": [2.0, -3.0, 0.1],
        "adj_pvalue": [0.01, 0.02, 0.8],
    })
    out = PlotService().render(df, "volcano", tmp_path / "volcano.png",
                               params={"log2fc_threshold": 1.0,
                                       "padj_threshold": 0.05})
    assert out.exists()
    assert out.stat().st_size > 0


def test_render_rejects_unknown_plot_type(tmp_path):
    with pytest.raises(ValueError, match="Unsupported plot_type"):
        PlotService().render(pd.DataFrame({"x": [1]}), "nope",
                             tmp_path / "x.png")


def test_list_plot_types_contains_volcano():
    assert "volcano" in PlotService().list_plot_types()
