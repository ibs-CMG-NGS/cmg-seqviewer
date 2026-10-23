"""Bundle export coverage for newly added figure dialogs."""

import subprocess
import sys

import pandas as pd

from models.data_models import Dataset, DatasetType
from gui.motif_enrichment_dialog import MotifEnrichmentDialog
from gui.tf_footprint_dialog import TFFootprintDialog
from gui.tss_distance_dialog import TSSDistanceDialog
from gui.visualization_dialog import PadjHistogramDialog
from utils.figure_bundle_export import export_figure_bundle


def _run_script(bundle_dir):
    result = subprocess.run(
        [sys.executable, str(bundle_dir / "scripts" / "figure.py")],
        capture_output=True, text=True, cwd=str(bundle_dir))
    assert result.returncode == 0, result.stderr


def test_padj_histogram_bundle(qtbot, tmp_path):
    dialog = PadjHistogramDialog(pd.DataFrame({"padj": [0.01, 0.2, 0.8]}))
    qtbot.addWidget(dialog)
    ctx = dialog.get_bundle_context()
    out = export_figure_bundle(
        ctx, tmp_path / "padj", "pvalue_histogram",
        "P-value Histogram", "padj_histogram")
    assert "render_padj_histogram" in (out / "scripts" / "figure.py").read_text()
    _run_script(out)


def test_tss_distance_bundle(qtbot, tmp_path):
    ds = Dataset(
        "atac", DatasetType.ATAC_SEQ,
        dataframe=pd.DataFrame({"distance_to_tss": [-1000, 0, 2000, 6000]}))
    dialog = TSSDistanceDialog(ds)
    qtbot.addWidget(dialog)
    ctx = dialog.get_bundle_context()
    out = export_figure_bundle(
        ctx, tmp_path / "tss", "tss_distance",
        "TSS Distance", "tss_distance")
    assert "render_tss_distance" in (out / "scripts" / "figure.py").read_text()
    _run_script(out)


def test_motif_enrichment_bundle_comparison(qtbot, tmp_path):
    up = Dataset(
        "up", DatasetType.MOTIF_ENRICHMENT,
        dataframe=pd.DataFrame({
            "motif_name": ["A", "B"], "log_pvalue": [5, 3],
            "motif_qvalue": [0.01, 0.04], "target_pct": [10, 20],
        }))
    down = Dataset(
        "down", DatasetType.MOTIF_ENRICHMENT,
        dataframe=pd.DataFrame({
            "motif_name": ["C"], "log_pvalue": [4], "motif_qvalue": [0.02],
        }))
    dialog = MotifEnrichmentDialog(up, dataset_down=down)
    qtbot.addWidget(dialog)
    ctx = dialog.get_bundle_context()
    assert "direction" in ctx["dataframe"].columns
    out = export_figure_bundle(
        ctx, tmp_path / "motif", "motif_enrichment",
        "TF Motif Enrichment", "motif_enrichment")
    assert "render_motif_enrichment" in (out / "scripts" / "figure.py").read_text()
    _run_script(out)


def test_tf_footprint_bundle(qtbot, tmp_path):
    ds = Dataset(
        "fp", DatasetType.TF_FOOTPRINT,
        dataframe=pd.DataFrame({
            "cond1_score": [1, 2, 3], "cond2_score": [1.2, 1.8, 3.1],
            "footprint_change": [0.2, -0.2, 0.1],
            "footprint_pvalue": [0.01, 0.2, 0.03],
            "fp_motif_name": ["A", "B", "C"],
        }))
    dialog = TFFootprintDialog(ds)
    qtbot.addWidget(dialog)
    ctx = dialog.get_bundle_context()
    out = export_figure_bundle(
        ctx, tmp_path / "fp", "tf_footprint",
        "TF Activity", "tf_footprint")
    assert "render_tf_footprint" in (out / "scripts" / "figure.py").read_text()
    _run_script(out)


def test_comparison_dot_bundle(qtbot, tmp_path):
    from gui.visualization_dialog import DotPlotDialog
    df = pd.DataFrame({
        "symbol": ["A", "B"],
        "ds1_log2FC": [1.0, -2.0], "ds1_padj": [0.01, 0.2],
        "ds2_log2FC": [0.5, 2.0], "ds2_padj": [0.03, 0.001],
    })
    dialog = DotPlotDialog(df)
    qtbot.addWidget(dialog)
    ctx = dialog.get_bundle_context()
    out = export_figure_bundle(
        ctx, tmp_path / "dot", "comparison_dot",
        "Comparison Dot Plot", "comparison_dot")
    assert "render_comparison_dot" in (out / "scripts" / "figure.py").read_text()
    _run_script(out)


def test_chromvar_bundle_volcano(qtbot, tmp_path):
    from gui.chromvar_dialog import ChromVARDialog
    df = pd.DataFrame({
        "chromvar_tf_name": ["A", "B", "C"],
        "chromvar_motif_id": ["m1", "m2", "m3"],
        "chromvar_delta": [1.2, -0.8, 0.2],
        "chromvar_padj": [0.001, 0.02, 0.5],
        "chromvar_pvalue": [0.0001, 0.001, 0.2],
        "chromvar_mean_base": [1, 2, 3],
        "chromvar_mean_compare": [2.2, 1.2, 3.2],
    })
    ds = Dataset("tf", DatasetType.CHROMVAR_DIFF_TF, dataframe=df)
    dialog = ChromVARDialog(ds)
    qtbot.addWidget(dialog)
    ctx = dialog.get_bundle_context()
    out = export_figure_bundle(
        ctx, tmp_path / "chromvar", "chromvar",
        "chromVAR TF Activity", "chromvar")
    assert "render_chromvar" in (out / "scripts" / "figure.py").read_text()
    _run_script(out)
