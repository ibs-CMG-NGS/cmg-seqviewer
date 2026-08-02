import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

from utils.figure_bundle_export import export_figure_bundle


def test_export_figure_bundle_creates_required_files(tmp_path):
    fig = Figure(figsize=(4, 3))
    ax = fig.add_subplot(111)
    ax.plot([0, 1, 2], [1, 3, 2])
    ax.set_title("Demo")

    df = pd.DataFrame({"gene": ["A", "B", "C"], "value": [1, 2, 3]})
    context = {
        "figure": fig,
        "dataframe": df,
        "plot_params": {"color": "red"},
        "dataset_name": "demo",
        "plot_type": "line",
        "figure_title": "Demo Figure",
        "figure_slug": "demo_figure",
        "source_stem": "demo_figure",
        "notes": "example bundle",
    }

    bundle_dir = export_figure_bundle(context, tmp_path / "bundle", "demo_figure", "Demo Figure", "line")

    assert bundle_dir.exists()
    assert (bundle_dir / "scripts" / "figure.py").exists()
    assert (bundle_dir / "inputs" / "data.csv").exists()
    assert (bundle_dir / "outputs" / "figure.png").exists()
    assert (bundle_dir / "outputs" / "figure.pdf").exists()
    assert (bundle_dir / "outputs" / "figure.svg").exists()
    assert (bundle_dir / "metadata" / "metadata.yaml").exists()

    metadata = (bundle_dir / "metadata" / "metadata.yaml").read_text(encoding="utf-8")
    assert "figure_title" in metadata
    assert "plot_type" in metadata

    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "ok"


def test_generated_regeneration_script_runs(tmp_path):
    fig = Figure(figsize=(4, 3))
    ax = fig.add_subplot(111)
    ax.plot([0, 1, 2], [1, 3, 2])
    ax.set_title("Demo")

    df = pd.DataFrame({"gene": ["A", "B", "C"], "value": [1, 2, 3]})
    context = {
        "figure": fig,
        "dataframe": df,
        "plot_params": {"x_min": None, "show_legend": True, "color": "red"},
        "dataset_name": "demo",
        "plot_type": "line",
        "figure_title": "Demo Figure",
        "figure_slug": "demo_figure",
        "source_stem": "demo_figure",
        "notes": "example bundle",
    }

    bundle_dir = export_figure_bundle(context, tmp_path / "bundle", "demo_figure", "Demo Figure", "line")
    script_path = bundle_dir / "scripts" / "figure.py"

    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, cwd=str(bundle_dir))
    assert result.returncode == 0, result.stderr
    assert (bundle_dir / "outputs" / "demo_figure.png").exists()


def test_volcano_plot_regeneration_script_runs(tmp_path):
    """Test that a volcano plot bundle generates a correct regeneration script."""
    import numpy as np
    
    # Create a simple volcano plot figure
    fig = Figure(figsize=(12, 8))
    ax = fig.add_subplot(111)
    ax.plot([0, 1], [1, 2])
    ax.set_title("Volcano Plot")
    
    # Create realistic volcano plot data
    np.random.seed(42)
    n_genes = 100
    log2fc = np.random.normal(0, 2, n_genes)
    padj = np.random.exponential(0.1, n_genes)
    padj = np.clip(padj, 1e-100, 1.0)
    
    df = pd.DataFrame({
        "gene": [f"Gene_{i}" for i in range(n_genes)],
        "log2FC": log2fc,
        "padj": padj,
    })
    
    context = {
        "figure": fig,
        "dataframe": df,
        "plot_params": {
            "padj_threshold": 0.05,
            "log2fc_threshold": 1.0,
            "down_color": "#0000ff",
            "up_color": "#ff0000",
            "ns_color": "#808080",
            "dot_size": 20,
            "x_min": None,
            "x_max": None,
            "y_min": None,
            "y_max": None,
            "labels_title": "Volcano Plot",
            "labels_xlabel": "Log2 Fold Change",
            "labels_ylabel": "-Log10(Padj)",
            "show_legend": True,
            "legend_position": "best",
        },
        "dataset_name": "volcano_test",
        "plot_type": "volcano",
        "figure_title": "Volcano Plot",
        "figure_slug": "volcano_plot",
        "source_stem": "volcano_plot",
        "notes": "Test volcano plot bundle",
    }
    
    bundle_dir = export_figure_bundle(
        context, tmp_path / "bundle", "volcano_plot", "Volcano Plot", "volcano"
    )
    script_path = bundle_dir / "scripts" / "figure.py"
    
    # Verify script is generated and executable
    assert script_path.exists()
    script_content = script_path.read_text(encoding="utf-8")
    assert "regulation" in script_content
    assert "scatter" in script_content
    
    # Run the script and verify outputs
    result = subprocess.run(
        [sys.executable, str(script_path)], 
        capture_output=True, text=True, cwd=str(bundle_dir)
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert (bundle_dir / "outputs" / "volcano_plot.png").exists()

