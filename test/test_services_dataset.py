"""DatasetService unit tests (headless, no Qt)."""

import json

import pandas as pd
import pytest

from services.dataset_service import DatasetService


def _write_de(tmp_path):
    df = pd.DataFrame({
        "gene_id": ["G1", "G2", "G3"],
        "log2fc": [2.0, -3.0, 0.1],
        "adj_pvalue": [0.01, 0.02, 0.8],
        "base_mean": [100.0, 200.0, 50.0],
    })
    path = tmp_path / "de.csv"
    df.to_csv(path, index=False)
    return path


def test_load_describe_summary_query_export(tmp_path):
    svc = DatasetService()
    ds = svc.load(_write_de(tmp_path))
    assert ds.dataset_type.value == "differential_expression"

    report = svc.describe(ds)
    assert report["rows"] == 3
    assert report["valid"] is True
    assert report["missing_required_columns"] == []
    assert report["file"].endswith("de.csv")

    summary = svc.summary(ds)
    json.dumps(summary)  # must be JSON-safe
    assert summary["type"] == "differential_expression"

    q = svc.query(ds, columns=["gene_id", "log2fc"], limit=2, offset=1)
    assert list(q.columns) == ["gene_id", "log2fc"]
    assert len(q) == 2

    out = svc.export(q, tmp_path / "out.tsv")
    assert out.exists()
    assert pd.read_csv(out, sep="\t").shape == (2, 2)


def test_query_rejects_unknown_column(tmp_path):
    svc = DatasetService()
    ds = svc.load(_write_de(tmp_path))
    with pytest.raises(ValueError, match="Unknown column"):
        svc.query(ds, columns=["nope"])


def test_export_rejects_unknown_format(tmp_path):
    svc = DatasetService()
    ds = svc.load(_write_de(tmp_path))
    with pytest.raises(ValueError, match="Unsupported output format"):
        svc.export(ds, tmp_path / "out.unknown", fmt="unknown")
