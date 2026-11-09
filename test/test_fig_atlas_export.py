"""fig-atlas handoff bundle shape tests."""

import pandas as pd

from models.data_models import Dataset, DatasetType
from utils.figure_bundle_export import export_fig_atlas_bundle
from utils.expression_distribution_loader import ExpressionDistributionLoader

from gui.visualization_dialog import PadjHistogramDialog, DotPlotDialog
from gui.tss_distance_dialog import TSSDistanceDialog
from gui.motif_enrichment_dialog import MotifEnrichmentDialog
from gui.tf_footprint_dialog import TFFootprintDialog
from gui.chromvar_dialog import ChromVARDialog
from gui.expression_distribution_dialog import ExpressionDistributionDialog


def _export(dialog, tmp_path, name):
    ctx = dialog.get_bundle_context()
    out = export_fig_atlas_bundle(ctx, tmp_path / name, name, name)
    dialog.close()
    meta = (out / "metadata" / "metadata.yaml").read_text(encoding="utf-8")
    data = pd.read_csv(out / "inputs" / "data.csv")
    return out, meta, data


def test_padj_histogram_fig_atlas(qtbot, tmp_path):
    d = PadjHistogramDialog(pd.DataFrame({"padj": [0.01, 0.2, 0.8]}))
    qtbot.addWidget(d)
    out, meta, data = _export(d, tmp_path, "hist")
    assert "plot_type: histogram" in meta
    assert "x_col: padj" in meta
    assert "bins: 50" in meta
    assert "padj" in data.columns
    assert not (out / "scripts").exists()
    assert len(list((out / "outputs").glob("figure.*"))) == 0


def test_tss_distance_fig_atlas(qtbot, tmp_path):
    d = TSSDistanceDialog(Dataset(
        "atac", DatasetType.ATAC_SEQ,
        dataframe=pd.DataFrame({"distance_to_tss": [-1000, 0, 2000]})))
    qtbot.addWidget(d)
    out, meta, data = _export(d, tmp_path, "tss")
    assert "plot_type: histogram" in meta
    assert "x_col: distance_to_tss" in meta
    assert "bin_min: -50000.0" in meta
    assert "distance_to_tss" in data.columns


def test_motif_enrichment_fig_atlas(qtbot, tmp_path):
    up = Dataset("up", DatasetType.MOTIF_ENRICHMENT, dataframe=pd.DataFrame({
        "motif_name": ["A"], "log_pvalue": [5.0], "motif_qvalue": [0.01]}))
    down = Dataset("down", DatasetType.MOTIF_ENRICHMENT, dataframe=pd.DataFrame({
        "motif_name": ["B"], "log_pvalue": [4.0], "motif_qvalue": [0.02]}))
    d = MotifEnrichmentDialog(up, dataset_down=down)
    qtbot.addWidget(d)
    out, meta, data = _export(d, tmp_path, "motif")
    assert "plot_type: motif_dotplot" in meta
    assert "term_col: motif_name" in meta
    assert "class_col: direction" in meta
    assert "neg_log10_p" in data.columns
    assert "fc_min: 0.0" in meta
    assert "colorbar_label: -log10(p)" in meta
    assert set(data["direction"]) == {"UP", "DOWN"}


def test_tf_footprint_fig_atlas(qtbot, tmp_path):
    d = TFFootprintDialog(Dataset("fp", DatasetType.TF_FOOTPRINT, dataframe=pd.DataFrame({
        "cond1_score": [1.0], "cond2_score": [2.0],
        "footprint_change": [1.0], "footprint_pvalue": [0.01],
        "fp_motif_name": ["A"]})))
    qtbot.addWidget(d)
    out, meta, data = _export(d, tmp_path, "tf")
    assert "plot_type: threshold_scatter" in meta
    assert "effect_col: footprint_change" in meta
    assert "show_identity_line: true" in meta
    assert "cond1_score" in data.columns


def test_comparison_dot_fig_atlas(qtbot, tmp_path):
    d = DotPlotDialog(pd.DataFrame({
        "symbol": ["A"], "ds1_log2FC": [1.0], "ds1_padj": [0.01],
        "ds2_log2FC": [-2.0], "ds2_padj": [0.02]}))
    qtbot.addWidget(d)
    out, meta, data = _export(d, tmp_path, "dot")
    assert "plot_type: cross_condition_dotplot" in meta
    assert "value_col: Signed -log10(FDR)" in meta
    assert {"GO Term", "Condition", "Signed -log10(FDR)", "Gene Ratio"}.issubset(data.columns)
    assert len(data) == 2


def test_chromvar_fig_atlas(qtbot, tmp_path):
    d = ChromVARDialog(Dataset("tf", DatasetType.CHROMVAR_DIFF_TF, dataframe=pd.DataFrame({
        "chromvar_tf_name": ["A"], "chromvar_delta": [1.2],
        "chromvar_padj": [0.01], "chromvar_pvalue": [0.001]})))
    qtbot.addWidget(d)
    out, meta, data = _export(d, tmp_path, "chromvar")
    assert "plot_type: volcano" in meta
    assert "x_col:" not in meta
    assert "log2FC" in data.columns
    assert "padj" in data.columns


def test_expression_distribution_fig_atlas(qtbot, tmp_path):
    rows = []
    for gene in ("G1", "G2"):
        for ct in ("A", "B"):
            for sample, cond in (("s1", "Control"), ("s2", "Treated")):
                rows.append({"gene_id": gene, "gene_name": gene, "cell_type": ct,
                             "sample": sample, "dataset": "ds", "condition": cond,
                             "n_cells": 20, "pct_expressing": 50.0,
                             "mean_expression": 1.0})
    ds = ExpressionDistributionLoader().load_from_dataframe(pd.DataFrame(rows), name="dist")
    d = ExpressionDistributionDialog(ds)
    qtbot.addWidget(d)
    out, meta, data = _export(d, tmp_path, "dist")
    assert "plot_type: violin" in meta
    assert "x_col: cell_type" in meta
    assert "hue_col: condition" in meta
    assert "hue_order:" in meta
    assert {"cell_type", "condition", "mean_expression"}.issubset(data.columns)
    assert "category" not in data.columns


def test_go_dot_fig_atlas(tmp_path):
    df = pd.DataFrame({
        "term_id": ["GO:1"], "description": ["term"],
        "ontology": ["BP"], "gene_ratio": ["8/120"], "bg_ratio": ["80/18870"],
        "pvalue": [1e-5], "fdr": [0.001], "qvalue": [0.001],
        "gene_count": [8], "gene_symbols": ["A/B"], "fold_enrichment": [15.0],
        "direction": ["UP"], "gene_set": ["UP"],
    })
    out = export_fig_atlas_bundle(
        {"figure": None, "dataframe": df, "plot_params": {"top_n": 20},
         "plot_type": "go_dot", "figure_slug": "go_dot",
         "figure_title": "GO dot", "source_stem": "go_dot"},
        tmp_path / "go_dot", "go_dot", "GO dot")
    meta = (out / "metadata" / "metadata.yaml").read_text(encoding="utf-8")
    assert "plot_type: go_dot" in meta
    assert "x_axis: Gene Ratio" in meta
    assert "size_mode: Gene Count" in meta
