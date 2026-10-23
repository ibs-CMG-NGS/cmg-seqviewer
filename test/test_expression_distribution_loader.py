"""Expression distribution loader + manifest/DB import tests."""

import json

import pandas as pd

from models.data_models import DatasetType
from utils.database_manager import DatabaseManager
from utils.expression_distribution_loader import ExpressionDistributionLoader


def _pseudobulk_df():
    rows = []
    for gene_id, gene_name in (("G1", "Gene1"), ("G2", "Gene2")):
        for cell_type in ("CT_A", "CT_B"):
            for sample, condition in (("s1", "Control"), ("s2", "Control"),
                                      ("s3", "Treated")):
                value = 1.0 + (0.5 if gene_id == "G2" else 0.0)
                value += 0.2 if cell_type == "CT_B" else 0.0
                value += 0.3 if condition == "Treated" else 0.0
                rows.append({
                    "gene_id": gene_id,
                    "gene_name": gene_name,
                    "cell_type": cell_type,
                    "sample": sample,
                    "dataset": "ds1",
                    "condition": condition,
                    "n_cells": 20,
                    "n_expressing": 10,
                    "pct_expressing": 50.0,
                    "mean_expression": value,
                    "mean_counts": value * 2,
                })
    return pd.DataFrame(rows)


def _quantile_df():
    return pd.DataFrame({
        "gene_id": ["G1", "G1", "G2", "G2"],
        "gene_name": ["Gene1", "Gene1", "Gene2", "Gene2"],
        "cell_type": ["CT_A", "CT_B", "CT_A", "CT_B"],
        "dataset": ["ds1"] * 4,
        "condition": ["Control"] * 4,
        "n_cells": [20, 20, 20, 20],
        "mean_expression": [1.0, 2.0, 3.0, 4.0],
        "pct_expressing": [50.0, 60.0, 70.0, 80.0],
        "p10": [0.5, 1.0, 1.5, 2.0],
        "p25": [0.8, 1.5, 2.0, 2.5],
        "median": [1.0, 2.0, 3.0, 4.0],
        "p75": [1.2, 2.5, 3.5, 4.5],
        "p90": [1.5, 3.0, 4.0, 5.0],
    })


def _write_bundle(source, with_manifest=True):
    datasets = source / "datasets"
    datasets.mkdir(parents=True)
    _pseudobulk_df().to_parquet(datasets / "pilot_pseudobulk.parquet", index=False)
    pd.DataFrame({
        "gene_id": ["G1", "G2"],
        "gene_name": ["Gene1", "Gene2"],
        "max_mean_expression": [2.0, 2.5],
        "max_pct_expressing": [50.0, 50.0],
        "n_cell_types_detected": [2, 2],
    }).to_parquet(datasets / "pilot_gene_index.parquet", index=False)
    pd.DataFrame({
        "cell_type": ["CT_A", "CT_B"],
        "n_cells": [60, 60],
    }).to_parquet(datasets / "pilot_cell_type_summary.parquet", index=False)
    schema = {
        "schema_version": "1.0",
        "layout": "pseudobulk",
        "gene_id_type": "symbol",
        "cell_type_column": "cell_type",
        "sample_column": "sample",
        "sample_unit": "biological_replicate",
        "dataset_column": "dataset",
        "condition_column": "condition",
        "group_columns": ["condition", "dataset"],
        "value_column": "mean_expression",
        "pct_column": "pct_expressing",
        "n_cells_column": "n_cells",
        "pct_scale": "0-100",
        "n_genes": 2,
        "n_samples": 3,
        "companion_files": {
            "gene_index": "pilot_gene_index.parquet",
            "cell_type_summary": "pilot_cell_type_summary.parquet",
        },
    }
    if with_manifest:
        (source / "seqviewer_manifest.json").write_text(json.dumps({
            "schema_version": "1.0",
            "datasets": [{
                "dataset_id": "dist-pilot",
                "alias": "Pilot pseudobulk distribution",
                "original_filename": "pilot_pseudobulk.parquet",
                "file_path": "pilot_pseudobulk.parquet",
                "dataset_type": "expression_distribution",
                "organism": "Mus musculus",
                "row_count": 12,
                "gene_count": 2,
                "cell_type_count": 2,
                "sample_count": 3,
                "distribution_schema": schema,
            }]
        }), encoding="utf-8")
    return schema


def test_loader_pseudobulk_metadata_and_companions(tmp_path):
    schema = _write_bundle(tmp_path / "bundle")
    source = tmp_path / "bundle" / "datasets" / "pilot_pseudobulk.parquet"

    ds = ExpressionDistributionLoader(schema).load(source, "pilot")
    assert ds.dataset_type == DatasetType.EXPRESSION_DISTRIBUTION
    assert ds.is_valid
    assert len(ds.dataframe) == 12
    assert ds.metadata["layout"] == "pseudobulk"
    assert ds.metadata["gene_count"] == 2
    assert ds.metadata["cell_type_count"] == 2
    assert ds.metadata["sample_count"] == 3
    assert ds.metadata["pct_scale"] == "0-100"
    assert set(ds.metadata["conditions"]) == {"Control", "Treated"}
    assert isinstance(ds.metadata["gene_index"], pd.DataFrame)
    assert isinstance(ds.metadata["cell_type_summary"], pd.DataFrame)


def test_loader_quantile_layout():
    ds = ExpressionDistributionLoader().load_from_dataframe(
        _quantile_df(), name="quantiles")
    assert ds.is_valid
    assert ds.metadata["layout"] == "quantile"
    assert ds.metadata["sample_count"] == 0
    assert ds.metadata["cell_type_count"] == 2


def test_loader_rejects_pseudobulk_without_sample():
    df = _pseudobulk_df().drop(columns=["sample"])
    try:
        ExpressionDistributionLoader().load_from_dataframe(
            df, distribution_schema={"layout": "pseudobulk"})
    except ValueError as exc:
        assert "sample" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_manifest_import_loads_distribution_and_companions(tmp_path):
    source = tmp_path / "2026-ljh-mouse-scrna" / "export" / "seqviewer"
    _write_bundle(source, with_manifest=True)

    db = DatabaseManager(database_dir=tmp_path / "db")
    imported, skipped_dup, skipped_no_file = db.import_from_folder(source)
    assert (imported, skipped_dup, skipped_no_file) == (1, 0, 0)
    meta = db.metadata_list[0]
    assert meta.dataset_type == DatasetType.EXPRESSION_DISTRIBUTION
    assert meta.sample_count == 3
    assert meta.distribution_schema["layout"] == "pseudobulk"

    dataset = db.load_dataset(meta.dataset_id)
    assert dataset is not None
    assert dataset.dataset_type == DatasetType.EXPRESSION_DISTRIBUTION
    assert dataset.metadata["sample_count"] == 3
    assert isinstance(dataset.metadata.get("gene_index"), pd.DataFrame)
    assert isinstance(dataset.metadata.get("cell_type_summary"), pd.DataFrame)


def test_auto_detect_pseudobulk_bundle_without_manifest(tmp_path):
    source = tmp_path / "bundle"
    _write_bundle(source, with_manifest=False)

    db = DatabaseManager(database_dir=tmp_path / "db")
    imported, _, _ = db.import_from_folder(source)
    assert imported == 1
    meta = db.metadata_list[0]
    assert meta.dataset_type == DatasetType.EXPRESSION_DISTRIBUTION
    assert meta.distribution_schema["layout"] == "pseudobulk"
    assert meta.sample_count == 3
    # companion parquet은 독립 dataset으로 중복 등록되지 않는다.
    assert len(db.metadata_list) == 1
