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
