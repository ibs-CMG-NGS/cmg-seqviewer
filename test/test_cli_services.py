"""CLI commands backed by the headless service layer."""

import json

import pandas as pd

import cli


def _de_csv(tmp_path):
    df = pd.DataFrame({
        "gene_id": ["G1", "G2", "G3"],
        "log2fc": [2.0, -3.0, 0.1],
        "adj_pvalue": [0.01, 0.02, 0.8],
        "base_mean": [100.0, 200.0, 50.0],
    })
    path = tmp_path / "de.csv"
    df.to_csv(path, index=False)
    return path


def test_summary_json(tmp_path, capsys):
    path = _de_csv(tmp_path)
    rc = cli.main(["summary", str(path), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["type"] == "differential_expression"
    assert out["row_count"] == 3


def test_query_to_file(tmp_path, capsys):
    path = _de_csv(tmp_path)
    out_path = tmp_path / "q.csv"
    rc = cli.main(["query", str(path), "--columns", "gene_id", "log2fc",
                   "--limit", "2", "--out", str(out_path)])
    assert rc == 0
    assert pd.read_csv(out_path).shape == (2, 2)


def test_export_to_file(tmp_path, capsys):
    path = _de_csv(tmp_path)
    out_path = tmp_path / "all.csv"
    rc = cli.main(["export", str(path), "--out", str(out_path)])
    assert rc == 0
    exported = pd.read_csv(out_path)
    assert len(exported) == 3
    assert "gene_id" in exported.columns


def test_plot_volcano(tmp_path, capsys):
    path = _de_csv(tmp_path)
    out_path = tmp_path / "volcano.png"
    rc = cli.main([
        "plot", str(path), "--plot-type", "volcano", "--out", str(out_path),
        "--params-json", '{"log2fc_threshold": 1.0, "padj_threshold": 0.05}',
    ])
    assert rc == 0
    assert out_path.exists() and out_path.stat().st_size > 0


def test_plot_unknown_type_fails(tmp_path, capsys):
    path = _de_csv(tmp_path)
    rc = cli.main(["plot", str(path), "--plot-type", "nope",
                   "--out", str(tmp_path / "x.png")])
    assert rc == 1
    assert "Unsupported plot_type" in capsys.readouterr().err


def test_schema_json(capsys):
    rc = cli.main(["schema", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert "volcano" in out["plot_types"]
    assert out["help_sections"]


def test_help_search_json(capsys):
    rc = cli.main(["help", "filter", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out
