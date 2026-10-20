"""
seqviewer_manifest.json 반입 테스트.

파이프라인이 manifest에 dataset_id/original_filename/file_path를 모두 채우지
않아도 반입되어야 하고(이전에는 조용히 컬럼 추측으로 fallback), 폴더명
/YYYY-initials-organism-type/에서 researcher/analysis_date가 보완되어야 한다.
"""

import json

import pandas as pd

from utils.database_manager import DatabaseManager


def _write_parquet(path):
    df = pd.DataFrame({
        "gene_id": ["G1", "G2"],
        "log2fc": [1.0, -2.0],
        "adj_pvalue": [0.01, 0.02],
        "baseMean": [100.0, 200.0],
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def test_manifest_minimal_fields_are_derived_and_path_fallback_applied(tmp_path):
    source = tmp_path / "2026-ljh-human-de"
    _write_parquet(source / "datasets" / "de.parquet")
    (source / "seqviewer_manifest.json").write_text(json.dumps({
        "datasets": [{
            "alias": "Tcell IFN DE",
            "original_filename": "de.parquet",
            "dataset_type": "differential_expression",
            "organism": "human",
        }]
    }), encoding="utf-8")

    db = DatabaseManager(database_dir=tmp_path / "db")
    imported, skipped_dup, skipped_no_file = db.import_from_folder(source)

    assert (imported, skipped_dup, skipped_no_file) == (1, 0, 0)
    meta = db.metadata_list[0]
    assert meta.alias == "Tcell IFN DE"
    assert meta.file_path == "de.parquet"          # original_filename에서 보완
    assert meta.dataset_id                         # manifest에 없어도 생성
    assert meta.researcher == ["ljh"]              # 폴더명에서 추론
    assert meta.analysis_date == "2026-01-01"
    assert "ljh" in meta.tags


def test_manifest_reimport_is_idempotent(tmp_path):
    source = tmp_path / "data"
    _write_parquet(source / "datasets" / "de.parquet")
    (source / "seqviewer_manifest.json").write_text(json.dumps({
        "datasets": [{
            "alias": "DE",
            "original_filename": "de.parquet",
            "dataset_type": "differential_expression",
        }]
    }), encoding="utf-8")

    db = DatabaseManager(database_dir=tmp_path / "db")
    assert db.import_from_folder(source)[0] == 1
    # dataset_id가 파일명 기반 uuid5로 고정되므로 재반입은 중복으로 건너뛴다.
    assert db.import_from_folder(source)[:2] == (0, 1)


def test_expression_summary_companions_imported_and_loaded(tmp_path):
    source = tmp_path / "hypomap_C66"
    ds_dir = source / "datasets"
    ds_dir.mkdir(parents=True)

    pd.DataFrame({"gene_id": ["G1", "G2"], "gene_name": ["A", "B"],
                  "CT_A": [1.0, 2.0], "CT_B": [3.0, 4.0]}).to_parquet(
        ds_dir / "mean.parquet")
    pd.DataFrame({"gene_id": ["G1", "G2"], "CT_A": [10.0, 20.0],
                  "CT_B": [30.0, 40.0]}).to_parquet(ds_dir / "pct.parquet")
    pd.DataFrame({"gene_id": ["G1", "G2"], "max_mean": [4.0, 3.0]}).to_parquet(
        ds_dir / "gene_index.parquet")
    pd.DataFrame({"cell_type": ["CT_A", "CT_B"], "n_cells": [100, 200]}).to_parquet(
        ds_dir / "summary.parquet")

    (source / "seqviewer_manifest.json").write_text(json.dumps({
        "datasets": [{
            "alias": "HypoMap C66",
            "file_path": "mean.parquet",
            "dataset_type": "expression_summary",
            "organism": "Mus musculus",
            "expression_schema": {
                "layout": "wide",
                "pct_scale": "0-100",
                "companion_files": {
                    "pct": "pct.parquet",
                    "gene_index": "gene_index.parquet",
                    "cell_type_summary": "summary.parquet",
                },
            },
        }]
    }), encoding="utf-8")

    db = DatabaseManager(database_dir=tmp_path / "db")
    assert db.import_from_folder(source)[0] == 1
    meta = db.metadata_list[0]
    assert meta.dataset_type.value == "expression_summary"
    # companion 파일은 datasets/에 복사되어야 한다.
    for name in ("pct.parquet", "gene_index.parquet", "summary.parquet"):
        assert (tmp_path / "db" / "datasets" / name).exists()

    dataset = db.load_dataset(meta.dataset_id)
    assert dataset is not None
    assert dataset.dataset_type.value == "expression_summary"
    assert dataset.metadata["cell_types"] == ["CT_A", "CT_B"]
    assert dataset.metadata["pct_matrix"] is not None
    assert dataset.metadata["gene_index"] is not None
    assert dataset.metadata["cell_type_summary"] is not None

    # metadata.json 재로드 후에도 expression_schema가 유지되어야 한다.
    db2 = DatabaseManager(database_dir=tmp_path / "db")
    reloaded = next(m for m in db2.metadata_list if m.dataset_type.value == "expression_summary")
    assert reloaded.expression_schema["companion_files"]["pct"] == "pct.parquet"
