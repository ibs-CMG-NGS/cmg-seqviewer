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


def _write_de_file(path, genes):
    pd.DataFrame({
        "gene_id": genes,
        "log2fc": [2.0, -2.5, 1.5][:len(genes)],
        "adj_pvalue": [0.01, 0.02, 0.03][:len(genes)],
    }).to_csv(path, index=False)
    return path


def _make_database(tmp_path):
    (tmp_path / "datasets").mkdir()
    pd.DataFrame({
        "gene_id": ["G1", "G2"],
        "log2fc": [2.0, -1.0],
        "adj_pvalue": [0.01, 0.5],
    }).to_parquet(tmp_path / "datasets" / "de.parquet")
    (tmp_path / "metadata.json").write_text(json.dumps({
        "datasets": [{
            "dataset_id": "d1",
            "alias": "Test DE",
            "original_filename": "de.parquet",
            "dataset_type": "differential_expression",
            "row_count": 2,
            "file_path": "de.parquet",
        }]
    }), encoding="utf-8")
    return tmp_path


def test_datasets_list_and_describe(tmp_path, capsys):
    db = _make_database(tmp_path)
    rc = cli.main(["datasets", "list", "--database-dir", str(db), "--json"])
    rows = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert rows[0]["dataset_id"] == "d1"

    rc = cli.main(["datasets", "describe", "d1", "--database-dir", str(db),
                   "--json"])
    described = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert described["schema"]["rows"] == 2


def test_filter_gene_list_mode(tmp_path, capsys):
    path = _write_de_file(tmp_path / "de.csv", ["G1", "G2", "G3"])
    genes = tmp_path / "genes.txt"
    genes.write_text("G3\nG1\n", encoding="utf-8")
    out = tmp_path / "gene_filtered.csv"
    rc = cli.main(["filter", str(path), "--mode", "gene_list",
                   "--gene-list-file", str(genes), "--out", str(out)])
    assert rc == 0
    assert list(pd.read_csv(out)["gene_id"]) == ["G3", "G1"]


def test_filter_keyword_mode(tmp_path, capsys):
    path = _write_de_file(tmp_path / "de.csv", ["G1", "G2", "G3"])
    out = tmp_path / "keyword_filtered.csv"
    rc = cli.main(["filter", str(path), "--mode", "keyword",
                   "--keyword", "G2", "--search-column", "gene_id",
                   "--out", str(out)])
    assert rc == 0
    assert list(pd.read_csv(out)["gene_id"]) == ["G2"]


def test_filter_column_subset_mode(tmp_path, capsys):
    path = _write_de_file(tmp_path / "de.csv", ["G1", "G2", "G3"])
    out = tmp_path / "subset.csv"
    rc = cli.main(["filter", str(path), "--mode", "column-subset",
                   "--columns", "gene_id", "log2fc", "--out", str(out)])
    assert rc == 0
    assert list(pd.read_csv(out).columns) == ["gene_id", "log2fc"]


def test_filter_gene_list_requires_input(tmp_path, capsys):
    path = _write_de_file(tmp_path / "de.csv", ["G1", "G2", "G3"])
    rc = cli.main(["filter", str(path), "--mode", "gene_list"])
    assert rc == 1
    assert "gene-list-file or --term-id" in capsys.readouterr().err


def test_compare_json_and_out(tmp_path, capsys):
    a = _write_de_file(tmp_path / "a.csv", ["G1", "G2", "G3"])
    b = _write_de_file(tmp_path / "b.csv", ["G2", "G3", "G4"])
    out = tmp_path / "compare.csv"
    rc = cli.main(["compare", str(a), str(b), "--json", "--include-table",
                   "--out", str(out)])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["overlap_stats"]["common_genes_count"] == 2
    assert payload["artifact"] == str(out)
    assert out.exists()


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
