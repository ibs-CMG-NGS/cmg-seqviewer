"""
CMG-SeqViewer CLI — non-interactive load/filter/export.

Reuses exactly the same import/detection layer the GUI uses
(utils.dataset_detection.load_any_dataset) and the same filter dispatch
(presenters.main_presenter.MainPresenter.compute_filtered_df) — no separate
CLI-only reimplementation of either, so GUI and CLI results never drift apart
the way the GUI's own column-mapping logic once did (fixed in the
import-generality work this followed).

There is no interactive column-mapping fallback here (no GUI to show a
dialog): an unrecognized file either loads cleanly via the same auto-detection
the GUI uses, or fails with a clear, actionable error (missing columns +
what's actually in the file) — the CLI never silently produces a broken
dataset.

Subcommands:
    load    — report a file's detected type/rows/columns/validity
    filter  — load + apply a statistical filter + export, flags only
    run     — load + filter + export, driven by a recipe file (utils/recipe.py)
    batch   — apply one recipe's filter/output settings across many input files

Usage:
    python -m cli load data.xlsx
    python -m cli load data.parquet --json          # CI용 기계 판독 출력
    python -m cli filter data.xlsx --adj-pvalue-max 0.05 --log2fc-min 1.0 --out filtered.xlsx
    python -m cli filter atac.parquet --type atac --out filtered.csv
    python -m cli run recipe.yaml
    python -m cli batch recipe.yaml --inputs "data/*.xlsx" --out-dir results/ --manifest results/manifest.json

`load`/`filter` accept CSV/TSV/Parquet inputs as well as Excel. `--type`
accepts atac / differential_expression / go_analysis / multi_group to bypass
auto-detection (e.g. for parquet exports from external pipelines).
"""

from __future__ import annotations

import argparse
import glob
import json
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


_TYPE_CHOICES = ["atac", "differential_expression", "go_analysis", "multi_group",
                 "composition", "expression_summary"]


def _dataset_type_hint(type_arg: Optional[str]):
    if not type_arg:
        return None
    from models.data_models import DatasetType
    mapping = {
        "atac": DatasetType.ATAC_SEQ,
        "differential_expression": DatasetType.DIFFERENTIAL_EXPRESSION,
        "go_analysis": DatasetType.GO_ANALYSIS,
        "multi_group": DatasetType.MULTI_GROUP,
        "composition": DatasetType.COMPOSITION,
        "expression_summary": DatasetType.EXPRESSION_SUMMARY,
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


def _dataset_report(dataset) -> dict:
    """`load --json` 출력 — 파이프라인 CI가 타입/행수/컬럼/필수 컬럼 충족 여부를
    기계적으로 검증할 수 있는 최소 스키마."""
    from models.data_models import DatasetType
    from models.standard_columns import StandardColumns

    required = {
        DatasetType.DIFFERENTIAL_EXPRESSION: StandardColumns.get_de_required(),
        DatasetType.GO_ANALYSIS: StandardColumns.get_go_required(),
        DatasetType.ATAC_SEQ: StandardColumns.get_atac_required(),
        DatasetType.COMPOSITION: StandardColumns.get_composition_required(),
        DatasetType.EXPRESSION_SUMMARY: StandardColumns.get_expression_summary_required(),
    }.get(dataset.dataset_type, [])
    present = list(dataset.dataframe.columns)
    return {
        "dataset_type": dataset.dataset_type.value,
        "rows": len(dataset.dataframe),
        "columns": present,
        "valid": bool(dataset.is_valid),
        "required_columns": list(required),
        "missing_required_columns": [c for c in required if c not in present],
    }


def cmd_load(args: argparse.Namespace) -> int:
    logger = logging.getLogger("cmg_cli.load")
    dataset = _load(Path(args.file), args.type, logger)
    if args.json:
        report = _dataset_report(dataset)
        report["file"] = str(args.file)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
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


def _load_and_filter(file_path: Path, type_arg: Optional[str], criteria, logger: logging.Logger):
    """load_any_dataset + compute_filtered_df를 한 번에 — run/batch가 공유.

    Returns:
        (dataset, filtered_df). filtered_df는 지원 안 되는 타입/모드 조합이면 None.
    """
    dataset = _load(file_path, type_arg, logger)
    presenter = _build_presenter()
    presenter.current_dataset = dataset
    filtered = presenter.compute_filtered_df(criteria)
    return dataset, filtered


def cmd_run(args: argparse.Namespace) -> int:
    """recipe 파일 하나를 recipe.input 단일 파일에 적용 — load -> filter -> export."""
    logger = logging.getLogger("cmg_cli.run")
    from utils.recipe import Recipe

    recipe = Recipe.load(Path(args.recipe))
    criteria = recipe.build_filter_criteria()
    dataset, filtered = _load_and_filter(Path(recipe.input), recipe.type, criteria, logger)

    print(f"loaded: {recipe.input} ({dataset.dataset_type.value}, {len(dataset.dataframe)} rows)")
    if filtered is None:
        print("Filter produced no result (unsupported dataset type/mode combination).",
              file=sys.stderr)
        return 1

    print(f"filtered: {len(filtered)}/{len(dataset.dataframe)} rows")
    out_table = recipe.output.get("table")
    if out_table:
        _write_table(filtered, Path(out_table))
        print(f"wrote: {out_table}")
    else:
        print(filtered.to_string(index=False))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """recipe의 filter/output 설정(recipe.input은 무시)을 --inputs 글롭에 매칭되는
    모든 파일에 반복 적용 — 탐색 단계에서 확정한 절차를 여러 데이터셋에 그대로
    재현할 때 쓴다. 한 파일이 실패해도 나머지는 계속 처리하고, 끝에 성공/실패
    개수로 exit code를 정한다(부분 실패 시 1)."""
    logger = logging.getLogger("cmg_cli.batch")
    from utils.recipe import Recipe

    recipe = Recipe.load(Path(args.recipe))
    criteria = recipe.build_filter_criteria()

    inputs = sorted({Path(p) for pattern in args.inputs for p in glob.glob(pattern)})
    if not inputs:
        print(f"No files matched: {args.inputs}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir) if args.out_dir else None
    out_suffix = Path(recipe.output.get("table", "filtered.xlsx")).suffix or ".xlsx"

    manifest = []
    failures = 0
    for f in inputs:
        entry: dict = {"input": str(f)}
        try:
            dataset, filtered = _load_and_filter(f, recipe.type, criteria, logger)
            if filtered is None:
                raise ValueError("Filter produced no result (unsupported type/mode)")
            entry.update(
                status="ok",
                dataset_type=dataset.dataset_type.value,
                rows_total=len(dataset.dataframe),
                rows_filtered=len(filtered),
            )
            if out_dir is not None:
                out_path = out_dir / f"{f.stem}{out_suffix}"
                _write_table(filtered, out_path)
                entry["output"] = str(out_path)
            print(f"[ok] {f.name}: {len(filtered)}/{len(dataset.dataframe)} rows")
        except Exception as exc:  # noqa: BLE001 — 한 파일 실패가 배치 전체를 막지 않게
            entry.update(status="failed", error=str(exc))
            failures += 1
            print(f"[FAIL] {f.name}: {exc}", file=sys.stderr)
        manifest.append(entry)

    if args.manifest:
        Path(args.manifest).parent.mkdir(parents=True, exist_ok=True)
        Path(args.manifest).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"wrote manifest: {args.manifest}")

    print(f"batch complete: {len(inputs) - failures}/{len(inputs)} succeeded")
    return 1 if failures else 0


def _add_filter_args(parser: argparse.ArgumentParser) -> None:
    """데이터셋 타입마다 다른 필터 파라미터 전부 — compute_filtered_df가 타입을 보고
    해당하는 것만 쓰고 나머지는 무시한다 (FilterCriteria 기본값과 동일)."""
    parser.add_argument("--type", choices=_TYPE_CHOICES, default=None,
                        help="명시적 데이터셋 타입 힌트 (자동 감지를 건너뜀)")
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
    p_load.add_argument("--type", choices=_TYPE_CHOICES, default=None,
                        help="명시적 데이터셋 타입 힌트 (자동 감지를 건너뜀)")
    p_load.add_argument("--json", action="store_true",
                        help="판정 결과를 JSON으로 출력 (CI 기계 판독용)")
    p_load.set_defaults(func=cmd_load)

    p_filter = sub.add_parser("filter", help="로드 + 통계 필터 적용 + 결과 export")
    p_filter.add_argument("file", help="입력 파일")
    p_filter.add_argument("--out", default=None,
                          help="출력 파일 경로 (.xlsx/.csv/.tsv/.parquet) — 생략하면 표준출력")
    _add_filter_args(p_filter)
    p_filter.set_defaults(func=cmd_filter)

    p_run = sub.add_parser("run", help="recipe 파일(utils/recipe.py) 하나를 단일 입력에 적용")
    p_run.add_argument("recipe", help="recipe .yaml/.yml/.json 경로")
    p_run.set_defaults(func=cmd_run)

    p_batch = sub.add_parser(
        "batch", help="recipe의 filter/output 설정을 여러 입력 파일에 반복 적용")
    p_batch.add_argument("recipe",
                         help="recipe .yaml/.yml/.json 경로 (recipe의 input 키는 무시됨)")
    p_batch.add_argument("--inputs", nargs="+", required=True,
                         help="글롭 패턴(들) — 예: \"data/*.xlsx\" \"more/*.parquet\"")
    p_batch.add_argument("--out-dir", default=None,
                         help="필터링된 결과를 저장할 디렉터리 (생략하면 export 없이 요약만)")
    p_batch.add_argument("--manifest", default=None,
                         help="파일별 성공/실패·행수 요약을 쓸 JSON 경로")
    p_batch.set_defaults(func=cmd_batch)

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
