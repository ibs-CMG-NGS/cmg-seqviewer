"""Export a reproducible figure bundle for downstream figure-atlas workflows."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import matplotlib
matplotlib.use("Agg")
import pandas as pd


def export_figure_bundle(
    context: Mapping[str, Any],
    output_dir: str | Path,
    figure_slug: str,
    figure_title: str,
    plot_type: str,
) -> Path:
    """Create a single-figure export bundle from a plotting context.

    The bundle contains:
    - scripts/figure.py
    - inputs/data.csv
    - outputs/figure.png/pdf/svg
    - metadata/metadata.yaml
    - manifest.json
    """
    bundle_dir = Path(output_dir)
    if bundle_dir.exists() and not bundle_dir.is_dir():
        raise ValueError(f"Output path is not a directory: {bundle_dir}")

    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "inputs").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "outputs").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "metadata").mkdir(parents=True, exist_ok=True)

    fig = context.get("figure")
    if fig is None:
        raise ValueError("Bundle context must include a matplotlib Figure instance")

    dataframe = context.get("dataframe")
    if dataframe is None:
        dataframe = pd.DataFrame({"value": [0]})
    elif not isinstance(dataframe, pd.DataFrame):
        dataframe = pd.DataFrame(dataframe)

    plot_params = context.get("plot_params") or {}
    dataset_name = context.get("dataset_name") or "unknown"
    source_stem = context.get("source_stem") or figure_slug or "figure"
    notes = context.get("notes") or ""

    data_path = bundle_dir / "inputs" / "data.csv"
    dataframe.to_csv(data_path, index=False)

    optional_stats = context.get("statistics")
    if optional_stats is not None:
        if isinstance(optional_stats, pd.DataFrame):
            optional_stats.to_csv(bundle_dir / "inputs" / "statistics.csv", index=False)
        else:
            pd.DataFrame(optional_stats).to_csv(bundle_dir / "inputs" / "statistics.csv", index=False)

    output_stem = bundle_dir / "outputs" / "figure"
    fig.savefig(output_stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(output_stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output_stem.with_suffix(".svg"), bbox_inches="tight")

    if source_stem != "figure":
        fig.savefig(bundle_dir / "outputs" / f"{source_stem}.png", dpi=300, bbox_inches="tight")
        fig.savefig(bundle_dir / "outputs" / f"{source_stem}.pdf", bbox_inches="tight")
        fig.savefig(bundle_dir / "outputs" / f"{source_stem}.svg", bbox_inches="tight")

    script_path = bundle_dir / "scripts" / "figure.py"
    script_path.write_text(_build_regeneration_script(source_stem, plot_type, plot_params), encoding="utf-8")

    metadata_path = bundle_dir / "metadata" / "metadata.yaml"
    metadata_path.write_text(
        _build_metadata_yaml(
            figure_slug=figure_slug,
            figure_title=figure_title,
            plot_type=plot_type,
            source_stem=source_stem,
            dataset_name=dataset_name,
            plot_params=plot_params,
            notes=notes,
        ),
        encoding="utf-8",
    )

    manifest = {
        "status": "ok",
        "figure_slug": figure_slug,
        "figure_title": figure_title,
        "plot_type": plot_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [
            str(data_path.relative_to(bundle_dir)),
            str(script_path.relative_to(bundle_dir)),
            str(metadata_path.relative_to(bundle_dir)),
            str((bundle_dir / "outputs" / f"{source_stem}.png").relative_to(bundle_dir)),
            str((bundle_dir / "outputs" / f"{source_stem}.pdf").relative_to(bundle_dir)),
            str((bundle_dir / "outputs" / f"{source_stem}.svg").relative_to(bundle_dir)),
        ],
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return bundle_dir


def _build_metadata_yaml(
    *,
    figure_slug: str,
    figure_title: str,
    plot_type: str,
    source_stem: str,
    dataset_name: str,
    plot_params: Mapping[str, Any],
    notes: str,
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "figure_id: " + figure_slug,
        "figure_title: " + _yaml_quote(figure_title),
        "figure_slug: " + _yaml_quote(figure_slug),
        "plot_type: " + _yaml_quote(plot_type),
        "source_stem: " + _yaml_quote(source_stem),
        "dataset_name: " + _yaml_quote(dataset_name),
        "claim_boundary: " + _yaml_quote(notes or "No claim boundary provided"),
        "created_at: " + _yaml_quote(now),
        "app_version: " + _yaml_quote("cmg-seqviewer-bundle-export"),
        "input_files:",
        "  - inputs/data.csv",
        "output_files:",
        "  - outputs/figure.png",
        "  - outputs/figure.pdf",
        "  - outputs/figure.svg",
        "statistics_tables:",
        "  - inputs/statistics.csv",
        "plot_params:",
    ]
    for key, value in plot_params.items():
        lines.append(f"  {key}: {_yaml_quote(str(value))}")
    return "\n".join(lines) + "\n"


def _build_regeneration_script(source_stem: str, plot_type: str, plot_params: Mapping[str, Any]) -> str:
    params_repr = repr(dict(plot_params))
    
    if plot_type.lower() == "volcano":
        return _build_volcano_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "heatmap":
        return _build_heatmap_plot_script(source_stem, params_repr)
    else:
        # Generic fallback for other plot types
        return _build_generic_plot_script(source_stem, plot_type, params_repr)


def _render_source(module_name: str, *func_names: str) -> str | None:
    """src/plots/{module}.py 의 렌더 함수 소스를 번들 스크립트에 inline 하기 위해 추출.

    dev/소스 실행에선 inspect.getsource, 실패(frozen 등) 시 모듈 파일을 직접 읽어 반환.
    둘 다 실패하면 None (호출부가 generic 스크립트로 폴백).
    """
    import importlib
    import inspect
    try:
        mod = importlib.import_module(f"plots.{module_name}")
    except Exception:
        return None
    try:
        return "\n\n".join(inspect.getsource(getattr(mod, n)) for n in func_names)
    except (OSError, TypeError):
        try:
            return Path(mod.__file__).read_text(encoding="utf-8")
        except Exception:
            return None


def _build_volcano_plot_script(source_stem: str, params_repr: str) -> str:
    # 화면 다이얼로그와 동일한 render_volcano 를 그대로 inline (단일 진실 공급원)
    render_src = _render_source("volcano", "_draw_volcano_labels", "render_volcano")
    if render_src is None:
        # 소스 추출 불가(frozen 등) → 이미지/데이터는 이미 저장됨, 스크립트는 generic 폴백
        return _build_generic_plot_script(source_stem, "volcano", params_repr)

    return f'''"""Recreate the volcano plot from this bundle.

이 스크립트의 render_volcano 는 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다
(단일 진실 공급원). 외부에서 cmg-seqviewer 없이 독립 재현 가능.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/volcano.py ──────────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(12, 8))
ax = fig.add_subplot(111)
render_volcano(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_heatmap_plot_script(source_stem: str, params_repr: str) -> str:
    # 화면 다이얼로그와 동일한 render_heatmap 을 그대로 inline (단일 진실 공급원)
    render_src = _render_source("heatmap", "render_heatmap")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "heatmap", params_repr)

    return f'''"""Recreate the expression heatmap from this bundle.

render_heatmap 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
정렬을 'clustering'으로 저장한 경우 scipy가 필요하다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/heatmap.py ──────────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(float(plot_params.get("fig_width", 10)), float(plot_params.get("fig_height", 8))))
render_heatmap(fig, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_generic_plot_script(source_stem: str, plot_type: str, params_repr: str) -> str:
    return f'''"""Recreate the exported figure bundle from saved data."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

root = Path(__file__).resolve().parents[1]
data_path = root / "inputs" / "data.csv"
plot_params = {params_repr}

df = pd.read_csv(data_path)
fig = Figure(figsize=(4, 3))
ax = fig.add_subplot(111)
ax.plot(df.iloc[:, 0], df.iloc[:, 1])
ax.set_title("{plot_type}")
for key, value in plot_params.items():
    if key == "color":
        ax.plot(df.iloc[:, 0], df.iloc[:, 1], color=value)
fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _yaml_quote(value: Any) -> str:
    text = str(value)
    if text == "":
        return '""'
    if any(ch in text for ch in [":", "#", "[", "]", "{", "}", ",", "*"]):
        return '"' + text.replace('"', '\\"') + '"'
    return text


__all__ = ["export_figure_bundle"]
