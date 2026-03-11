#!/usr/bin/env python3
"""
merge_db.py — 파이프라인 폴더를 CMG SeqViewer DB에 병합하는 CLI 도구

파이프라인에서 생성된 metadata.json + parquet 파일들을 앱 데이터베이스에
직접 병합합니다. 앱을 열 필요 없이 커맨드라인에서 실행할 수 있습니다.

사용법:
  # 단일 폴더 병합
  python merge_db.py <source_dir>

  # 여러 폴더 한번에 병합
  python merge_db.py <source_dir1> <source_dir2> ...

  # 병합 대상 DB 폴더를 명시 (기본값: 앱 외부 데이터 폴더)
  python merge_db.py <source_dir> --target <target_db_dir>

  # 결과 확인만 (실제 파일 복사 없음)
  python merge_db.py <source_dir> --dry-run

예시:
  python merge_db.py ~/pipeline_run_2025/
  python merge_db.py run1/ run2/ run3/
  python merge_db.py ~/run1 --target ~/my_db
  python merge_db.py ~/run1 --dry-run
"""

import argparse
import json
import logging
import shutil
import sys
import uuid
from pathlib import Path
from datetime import datetime

# ── src 경로를 sys.path 에 추가 (프로젝트 루트에서 실행 시 필요) ─────────────
SCRIPT_DIR = Path(__file__).parent
SRC_DIR = SCRIPT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    import pandas as pd
    from models.data_models import PreloadedDatasetMetadata, DatasetType
    from utils.data_path_config import DataPathConfig
except ImportError as e:
    print(f"[ERROR] Failed to import project modules: {e}", file=sys.stderr)
    print("       Make sure to run this script from the project root directory.", file=sys.stderr)
    print("       Example:  python merge_db.py <source_dir>", file=sys.stderr)
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("merge_db")


def _detect_dataset_type(df: "pd.DataFrame") -> DatasetType | None:
    """parquet DataFrame 컬럼으로 DE/GO 타입 자동 판별"""
    cols = set(df.columns)
    de_required = {"gene_id", "log2fc", "adj_pvalue"}
    go_required = {"term_id", "description", "fdr"}
    if de_required.issubset(cols):
        return DatasetType.DIFFERENTIAL_EXPRESSION
    if go_required.issubset(cols):
        return DatasetType.GO_ANALYSIS
    return None


def _make_metadata_from_parquet(parquet_file: Path) -> PreloadedDatasetMetadata | None:
    """parquet 파일에서 최소 메타데이터 자동 생성"""
    import re
    try:
        df = pd.read_parquet(parquet_file, engine="pyarrow")
    except Exception as e:
        logger.warning(f"  Cannot read '{parquet_file.name}': {e}")
        return None

    dataset_type = _detect_dataset_type(df)
    if dataset_type is None:
        logger.warning(
            f"  Cannot determine type of '{parquet_file.name}' "
            "(no DE or GO standard columns). Skipping."
        )
        return None

    row_count = len(df)
    gene_count = 0
    significant_genes = 0

    if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
        gene_count = row_count
        if "adj_pvalue" in df.columns:
            try:
                significant_genes = int(
                    (pd.to_numeric(df["adj_pvalue"], errors="coerce") < 0.05).sum()
                )
            except Exception:
                pass

    stem = parquet_file.stem
    alias = re.sub(r"_[0-9a-f]{8}$", "", stem) or stem

    return PreloadedDatasetMetadata(
        dataset_id=str(uuid.uuid4()),
        alias=alias,
        original_filename=parquet_file.name,
        dataset_type=dataset_type,
        row_count=row_count,
        gene_count=gene_count,
        significant_genes=significant_genes,
        import_date=datetime.now().isoformat(),
        file_path=parquet_file.name,
        notes="Imported via merge_db.py (no metadata.json)",
    )


def _load_target_metadata(target_meta_file: Path) -> list:
    """대상 metadata.json 로드"""
    if not target_meta_file.exists():
        return []
    try:
        with open(target_meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [PreloadedDatasetMetadata.from_dict(item) for item in data.get("datasets", [])]
    except Exception as e:
        logger.error(f"Failed to read target metadata.json: {e}")
        return []


def _save_target_metadata(target_meta_file: Path, metadata_list: list):
    """대상 metadata.json 저장"""
    data = {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "datasets": [m.to_dict() for m in metadata_list],
    }
    with open(target_meta_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def merge_folder(
    source_dir: Path,
    target_datasets_dir: Path,
    target_meta_file: Path,
    dry_run: bool = False,
) -> tuple:
    """
    단일 source_dir 을 target DB 에 병합.

    Returns:
        (imported, skipped_dup, skipped_no_file)
    """
    imported = 0
    skipped_dup = 0
    skipped_no_file = 0

    if not source_dir.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        return 0, 0, 0

    # 대상 메타데이터 로드
    target_metadata = _load_target_metadata(target_meta_file)
    existing_ids = {m.dataset_id for m in target_metadata}
    existing_files = {m.file_path for m in target_metadata}

    meta_file = source_dir / "metadata.json"

    if meta_file.exists():
        # ── metadata.json 기반 병합 ──────────────────────────────────────
        logger.info(f"Found metadata.json in {source_dir}")
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"  Failed to read metadata.json: {e}")
            return 0, 0, 0

        source_datasets_dir = source_dir / "datasets"

        for item in data.get("datasets", []):
            try:
                meta = PreloadedDatasetMetadata.from_dict(item)
            except Exception as e:
                logger.warning(f"  Invalid metadata entry, skipping: {e}")
                skipped_no_file += 1
                continue

            meta.file_path = Path(meta.file_path).name

            if meta.dataset_id in existing_ids or meta.file_path in existing_files:
                logger.info(f"  SKIP (duplicate): {meta.alias}")
                skipped_dup += 1
                continue

            # parquet 탐색
            src_parquet = source_datasets_dir / meta.file_path
            if not src_parquet.exists():
                src_parquet = source_dir / meta.file_path
            if not src_parquet.exists():
                logger.warning(f"  SKIP (file not found): {meta.alias} — {meta.file_path}")
                skipped_no_file += 1
                continue

            # 파일명 충돌 방지
            dest_name = meta.file_path
            dest_path = target_datasets_dir / dest_name
            if dest_path.exists():
                suffix = str(uuid.uuid4())[:8]
                dest_name = f"{Path(dest_name).stem}_{suffix}.parquet"
                dest_path = target_datasets_dir / dest_name

            if dry_run:
                logger.info(f"  [DRY-RUN] Would import: {meta.alias} → {dest_name}")
            else:
                target_datasets_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_parquet, dest_path)
                meta.file_path = dest_name
                target_metadata.append(meta)
                existing_ids.add(meta.dataset_id)
                existing_files.add(meta.file_path)
                logger.info(f"  IMPORTED: {meta.alias} → {dest_name}")

            imported += 1

    else:
        # ── metadata.json 없음: parquet 스캔 후 자동 판별 ───────────────
        logger.info(f"No metadata.json found in {source_dir}. Scanning for parquet files...")
        source_datasets_dir = source_dir / "datasets"
        scan_dir = source_datasets_dir if source_datasets_dir.exists() else source_dir

        for parquet_file in sorted(scan_dir.glob("*.parquet")):
            if parquet_file.name in existing_files:
                logger.info(f"  SKIP (duplicate file): {parquet_file.name}")
                skipped_dup += 1
                continue

            meta = _make_metadata_from_parquet(parquet_file)
            if meta is None:
                skipped_no_file += 1
                continue

            dest_name = parquet_file.name
            dest_path = target_datasets_dir / dest_name
            if dest_path.exists():
                suffix = str(uuid.uuid4())[:8]
                dest_name = f"{parquet_file.stem}_{suffix}.parquet"
                dest_path = target_datasets_dir / dest_name

            if dry_run:
                logger.info(f"  [DRY-RUN] Would auto-import: {meta.alias} → {dest_name}")
            else:
                target_datasets_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(parquet_file, dest_path)
                meta.file_path = dest_name
                target_metadata.append(meta)
                existing_ids.add(meta.dataset_id)
                existing_files.add(meta.file_path)
                logger.info(f"  AUTO-IMPORTED: {meta.alias} → {dest_name}")

            imported += 1

    # 변경 사항 저장
    if imported > 0 and not dry_run:
        _save_target_metadata(target_meta_file, target_metadata)

    return imported, skipped_dup, skipped_no_file


def main():
    parser = argparse.ArgumentParser(
        description="Merge pipeline output folders into the CMG SeqViewer database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "sources",
        nargs="+",
        metavar="SOURCE_DIR",
        help="One or more source directories containing metadata.json + parquet files.",
    )
    parser.add_argument(
        "--target",
        metavar="TARGET_DB_DIR",
        default=None,
        help=(
            "Target database directory (must contain or will create metadata.json + datasets/).\n"
            "Defaults to the app's external data directory."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be imported without actually copying files.",
    )
    args = parser.parse_args()

    # ── 대상 DB 디렉토리 결정 ──────────────────────────────────────────────
    if args.target:
        target_db_dir = Path(args.target).resolve()
    else:
        DataPathConfig.ensure_external_data_structure()
        target_db_dir = DataPathConfig.get_external_data_dir()

    target_datasets_dir = target_db_dir / "datasets"
    target_meta_file = target_db_dir / "metadata.json"

    logger.info(f"Target DB: {target_db_dir}")
    if args.dry_run:
        logger.info("*** DRY-RUN mode — no files will be written ***")

    # ── 각 소스 폴더 병합 ─────────────────────────────────────────────────
    total_imported = 0
    total_dup = 0
    total_missing = 0

    for src in args.sources:
        source_dir = Path(src).resolve()
        logger.info(f"\n── Merging: {source_dir}")
        n_imp, n_dup, n_miss = merge_folder(
            source_dir, target_datasets_dir, target_meta_file, dry_run=args.dry_run
        )
        total_imported += n_imp
        total_dup += n_dup
        total_missing += n_miss

    # ── 요약 출력 ─────────────────────────────────────────────────────────
    print()
    print("=" * 50)
    print("  MERGE SUMMARY")
    print("=" * 50)
    print(f"  Sources processed : {len(args.sources)}")
    print(f"  Imported          : {total_imported}")
    print(f"  Skipped (dup)     : {total_dup}")
    print(f"  Skipped (missing) : {total_missing}")
    if args.dry_run:
        print("  (DRY-RUN — nothing was written)")
    else:
        print(f"  Target DB         : {target_db_dir}")
    print("=" * 50)

    sys.exit(0 if total_missing == 0 else 1)


if __name__ == "__main__":
    main()
