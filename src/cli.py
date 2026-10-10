"""
CMG-SeqViewer CLI — non-interactive load/filter/export.

Reuses exactly the same import/detection layer the GUI uses
(utils.dataset_detection.load_any_dataset) and the same filter dispatch
(presenters.main_presenter.MainPresenter.compute_filtered_df) — no separate
CLI-only reimplementation of either, so GUI and CLI results never drift apart
(see docs/planning/CLI_PLAN.md and the import-generality fixes this followed).

There is no interactive column-mapping fallback here (no GUI to show a
dialog): an unrecognized file either loads cleanly via the same auto-detection
the GUI uses, or fails with a clear, actionable error (missing columns +
what's actually in the file) — the CLI never silently produces a broken
dataset.

Usage:
    python -m cli load data.xlsx
    python -m cli filter data.xlsx --adj-pvalue-max 0.05 --log2fc-min 1.0 --out filtered.xlsx
    python -m cli filter atac.parquet --type atac --out filtered.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pandas as pd


def _build_presenter():
    """Qt 이벤트 루프/QApplication 없이 MainPresenter를 만든다 (compute_filtered_df
    등 순수 로직 메서드만 쓰므로 GUI 위젯은 전혀 필요 없음 — Phase 0 타당성 검증에서
    확인됨)."""
    from presenters.main_presenter import MainPresenter
    return MainPresenter(SimpleNamespace())


def _dataset_type_hint(type_arg: Optional[str]):
    if not type_arg:
        return None
    from models.data_models import DatasetType
    mapping = {
        "atac": DatasetType.ATAC_SEQ,
    }
    if type_arg not in mapping:
        raise ValueError(f"--type must be one of {sorted(mapping)}, got {type_arg!r}")
    return mapping[type_arg]


def _load(file_path: Path, type_arg: Optional[str], logger: logging.Logger):
    """load_any_dataset()을 호출 — 컬럼 매핑 콜백은 항상 None (CLI는 대화형 UI가
    없으므로, 인식 실패 시 조용히 넘어가지 않고 바로 예외를 낸다)."""
    from utils.data_loader import DataLoader
    from utils.dataset_detection import load_any_dataset

    hint = _dataset_type_hint(type_arg)
    return load_any_dataset(
        file_path, DataLoader(), dataset_type_hint=hint,
        column_mapper_callback=None, logger=logger,
    )


def _write_table(df: pd.DataFrame, out_path: Path) -> None:
    suffix = out_path.suffix.lower()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if suffix in (".xlsx", ".xls"):
        df.to_excel(out_path, index=False)
    elif suffix == ".csv":
        df.to_csv(out_path, index=False)
    elif suffix == ".tsv":
        df.to_csv(out_path, index=False, sep="\t")
    elif suffix == ".parquet":
        df.to_parquet(out_path, index=False)
    else:
        raise ValueError(
            f"Unsupported output format: {suffix!r} (use .xlsx/.csv/.tsv/.parquet)")


def cmd_load(args: argparse.Namespace) -> int:
    logger = logging.getLogger("cmg_cli.load")
    dataset = _load(Path(args.file), args.type, logger)
    df = dataset.dataframe
    print(f"type: {dataset.dataset_type.value}")
    print(f"rows: {len(df)}")
    print(f"columns: {list(df.columns)}")
    print(f"valid: {dataset.is_valid}")
    return 0


def cmd_filter(args: argparse.Namespace) -> int:
    logger = logging.getLogger("cmg_cli.filter")
    dataset = _load(Path(args.file), args.type, logger)

    from models.data_models import FilterCriteria, FilterMode
    criteria = FilterCriteria(
        mode=FilterMode.STATISTICAL,
        adj_pvalue_max=args.adj_pvalue_max,
        log2fc_min=args.log2fc_min,
        regulation_direction=args.regulation,
        fdr_max=args.fdr_max,
        fold_enrichment_min=args.fold_enrichment_min,
        go_min_gene_count=args.go_min_gene_count,
        ontology=args.ontology,
        go_direction=args.go_direction,
        mg_padj_max=args.mg_padj_max,
        mg_basemean_min=args.mg_basemean_min,
        atac_annotation=args.atac_annotation,
        atac_distance_max=args.atac_distance_max,
        atac_peak_width_min=args.atac_peak_width_min,
        atac_peak_width_max=args.atac_peak_width_max,
    )

    presenter = _build_presenter()
    presenter.current_dataset = dataset
    filtered = presenter.compute_filtered_df(criteria)
    if filtered is None:
        print("Filter produced no result (unsupported dataset type/mode combination).",
              file=sys.stderr)
        return 1

    print(f"filtered: {len(filtered)}/{len(dataset.dataframe)} rows")
    if args.out:
        _write_table(filtered, Path(args.out))
        print(f"wrote: {args.out}")
    else:
        print(filtered.to_string(index=False))
    return 0


def _add_filter_args(parser: argparse.ArgumentParser) -> None:
    """데이터셋 타입마다 다른 필터 파라미터 전부 — compute_filtered_df가 타입을 보고
    해당하는 것만 쓰고 나머지는 무시한다 (FilterCriteria 기본값과 동일)."""
    parser.add_argument("--type", choices=["atac"], default=None,
                        help="명시적 데이터셋 타입 힌트 (자동 감지를 건너뜀; 현재 atac만 지원)")
    parser.add_argument("--adj-pvalue-max", type=float, default=0.05,
                        help="DE/ATAC: adjusted p-value 상한 (default: 0.05)")
    parser.add_argument("--log2fc-min", type=float, default=1.0,
                        help="DE/ATAC: |log2FC| 하한 (default: 1.0)")
    parser.add_argument("--regulation", choices=["up", "down", "both"], default="both",
                        help="DE/ATAC: 방향 제한 (default: both)")
    parser.add_argument("--fdr-max", type=float, default=0.05,
                        help="GO/KEGG: FDR 상한 (default: 0.05)")
    parser.add_argument("--fold-enrichment-min", type=float, default=0.0,
                        help="GO/KEGG: fold enrichment 하한 (default: 0.0)")
    parser.add_argument("--go-min-gene-count", type=int, default=3,
                        help="GO/KEGG: term당 최소 유전자 수 (default: 3, 0=제한 없음)")
    parser.add_argument("--ontology", default="All",
                        help="GO/KEGG: All/BP/MF/CC/KEGG (default: All)")
    parser.add_argument("--go-direction", default="All",
                        help="GO/KEGG: All/UP/DOWN/TOTAL (default: All)")
    parser.add_argument("--mg-padj-max", type=float, default=0.05,
                        help="Multi-Group: adjusted p-value 상한 (default: 0.05)")
    parser.add_argument("--mg-basemean-min", type=float, default=10.0,
                        help="Multi-Group: baseMean 하한 (default: 10.0)")
    parser.add_argument("--atac-annotation", default="All",
                        help="ATAC: 주석 카테고리 (default: All)")
    parser.add_argument("--atac-distance-max", type=int, default=None,
                        help="ATAC: |distance_to_tss| 상한 (bp)")
    parser.add_argument("--atac-peak-width-min", type=int, default=None,
                        help="ATAC: peak width 하한 (bp)")
    parser.add_argument("--atac-peak-width-max", type=int, default=None,
                        help="ATAC: peak width 상한 (bp)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cmg-seqviewer-cli",
        description="CMG-SeqViewer non-interactive load/filter/export "
                    "(same import + filter logic as the GUI).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="디버그 로그 출력")
    sub = parser.add_subparsers(dest="command", required=True)

    p_load = sub.add_parser("load", help="파일을 로드해 타입/행수/컬럼/유효성만 보고")
    p_load.add_argument("file", help="DE/GO/ATAC/chromVAR/motif/footprint 등 입력 파일")
    p_load.add_argument("--type", choices=["atac"], default=None,
                        help="명시적 데이터셋 타입 힌트 (자동 감지를 건너뜀)")
    p_load.set_defaults(func=cmd_load)

    p_filter = sub.add_parser("filter", help="로드 + 통계 필터 적용 + 결과 export")
    p_filter.add_argument("file", help="입력 파일")
    p_filter.add_argument("--out", default=None,
                          help="출력 파일 경로 (.xlsx/.csv/.tsv/.parquet) — 생략하면 표준출력")
    _add_filter_args(p_filter)
    p_filter.set_defaults(func=cmd_filter)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 — CLI 경계: 메시지 출력 후 non-zero 종료
        print(f"Error: {exc}", file=sys.stderr)
        if args.verbose:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())
