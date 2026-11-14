"""DatabaseService: headless list/describe/load over DatabaseManager."""

import json

import pandas as pd
import pytest

from services.database_service import DatabaseService


def _make_database(tmp_path):
    (tmp_path / "datasets").mkdir()
    pd.DataFrame(
        {
            "gene_id": ["G1", "G2"],
            "log2fc": [2.0, -1.0],
            "adj_pvalue": [0.01, 0.5],
        }
    ).to_parquet(tmp_path / "datasets" / "de.parquet")
    (tmp_path / "metadata.json").write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "dataset_id": "d1",
                        "alias": "Test DE",
                        "original_filename": "de.parquet",
                        "dataset_type": "differential_expression",
                        "row_count": 2,
                        "file_path": "de.parquet",
                        "tags": ["pilot"],
                        "organism": "Homo sapiens",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_list_and_filter(tmp_path):
    db = DatabaseService(_make_database(tmp_path))
    rows = db.list()
    assert len(rows) == 1
    assert rows[0]["dataset_id"] == "d1"
    assert rows[0]["alias"] == "Test DE"

    assert len(db.list(query="pilot")) == 1
    assert len(db.list(dataset_type="differential_expression")) == 1
    assert db.list(dataset_type="go_analysis") == []
    assert len(db.list(organism="homo")) == 1
    assert len(db.list(tags=["pilot"])) == 1
    assert db.list(tags=["missing"]) == []


def test_describe_and_load(tmp_path):
    db = DatabaseService(_make_database(tmp_path))
    meta = db.describe("d1", include_schema=False)
    assert "schema" not in meta
    assert meta["alias"] == "Test DE"

    described = db.describe("d1")
    assert described["schema"]["rows"] == 2
    assert described["schema"]["valid"] is True
    assert "file" not in described["schema"]

    dataset = db.load("d1")
    assert dataset.name == "Test DE"
    assert len(dataset.dataframe) == 2


def test_missing_dataset(tmp_path):
    db = DatabaseService(_make_database(tmp_path))
    with pytest.raises(ValueError, match="not found"):
        db.describe("nope")
    with pytest.raises(ValueError, match="could not be loaded"):
        db.load("nope")
