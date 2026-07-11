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
    elif plot_type.lower() == "go_dot":
        return _build_go_dot_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "go_bar":
        return _build_go_bar_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "ma":
        return _build_ma_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "pca":
        return _build_pca_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "genomic_distribution":
        return _build_genomic_distribution_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "gene_expression_bar":
        return _build_gene_expression_bar_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "go_comparison_dot":
        return _build_go_comparison_dot_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "quadrant":
        return _build_quadrant_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "integrated_volcano":
        return _build_integrated_volcano_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "meta_volcano":
        return _build_meta_volcano_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "count_summary":
        return _build_count_summary_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "annotation_comparison":
        return _build_annotation_comparison_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "venn":
        return _build_venn_plot_script(source_stem, params_repr)
    elif plot_type.lower() == "upset":
        return _build_upset_plot_script(source_stem, params_repr)
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


def _build_go_dot_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("go_dot", "_gene_ratio", "render_go_dot")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "go_dot", params_repr)

    return f'''"""Recreate the GO/KEGG dot plot from this bundle.

render_go_dot 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/go_dot.py ───────────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(float(plot_params.get("fig_width", 12)), float(plot_params.get("fig_height", 8))))
render_go_dot(fig, df, plot_params)

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_go_bar_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("go_bar", "render_go_bar")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "go_bar", params_repr)

    return f'''"""Recreate the GO/KEGG bar chart from this bundle.

render_go_bar 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/go_bar.py ───────────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(10, 8))
ax = fig.add_subplot(111)
render_go_bar(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_ma_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("ma", "render_ma")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "ma", params_repr)

    return f'''"""Recreate the MA plot from this bundle.

render_ma 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/ma.py ───────────────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(10, 8))
ax = fig.add_subplot(111)
render_ma(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_pca_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("pca", "render_pca")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "pca", params_repr)

    return f'''"""Recreate the PCA plot from this bundle.

render_pca 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다 (numpy SVD).
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/pca.py ──────────────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(8, 7))
render_pca(fig, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_genomic_distribution_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("genomic_distribution", "render_genomic_distribution")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "genomic_distribution", params_repr)

    return f'''"""Recreate the Genomic Distribution pie chart from this bundle.

render_genomic_distribution 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/genomic_distribution.py ─────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(7, 5))
render_genomic_distribution(fig, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_gene_expression_bar_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("gene_expression_bar", "render_gene_expression_bar")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "gene_expression_bar", params_repr)

    return f'''"""Recreate the Gene Expression Bar chart from this bundle.

render_gene_expression_bar 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
유의성 별표는 scipy가 있으면 계산, 없으면 생략된다 (함수 내부 try/except).
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/gene_expression_bar.py ──────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(10, 8))
ax = fig.add_subplot(111)
render_gene_expression_bar(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_go_comparison_dot_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("go_comparison_dot", "_build_long_df", "render_go_comparison_dot")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "go_comparison_dot", params_repr)

    return f'''"""Recreate the GO/KEGG Comparison Dot plot from this bundle.

render_go_comparison_dot 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
입력 data.csv 는 wide-format 비교 표이며, 함수 내부에서 long-format으로 재구성한다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/go_comparison_dot.py ────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(12, 9))
render_go_comparison_dot(fig, df, plot_params)

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_quadrant_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("quadrant", "render_quadrant")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "quadrant", params_repr)

    return f'''"""Recreate the Quadrant (RNA vs ATAC log2FC) plot from this bundle.

render_quadrant 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/quadrant.py ─────────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(7, 6))
ax = fig.add_subplot(111)
render_quadrant(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_integrated_volcano_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("integrated_volcano", "render_integrated_volcano")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "integrated_volcano", params_repr)

    return f'''"""Recreate the Integrated Volcano plot from this bundle.

render_integrated_volcano 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/integrated_volcano.py ───────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(7, 6))
ax = fig.add_subplot(111)
render_integrated_volcano(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_meta_volcano_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("meta_volcano", "_found_in_num", "render_meta_volcano")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "meta_volcano", params_repr)

    return f'''"""Recreate the Meta Volcano plot from this bundle.

render_meta_volcano 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
상위 N개 라벨은 adjustText가 있으면 자동 배치, 없으면 점 위에 표시된다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/meta_volcano.py ─────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(8, 7))
ax = fig.add_subplot(111)
render_meta_volcano(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_count_summary_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("count_summary", "render_count_summary")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "count_summary", params_repr)

    return f'''"""Recreate the DE/DA Count Summary chart from this bundle.

render_count_summary 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
inputs/data.csv 는 long-format(dataset/log2fc/adj_pvalue)이며, 데이터셋별 유의 up/down
개수를 함수 내부에서 재집계한다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/count_summary.py ────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(9, 6))
ax = fig.add_subplot(111)
render_count_summary(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_annotation_comparison_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("annotation_comparison", "render_annotation_comparison")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "annotation_comparison", params_repr)

    return f'''"""Recreate the Genomic Annotation Comparison chart from this bundle.

render_annotation_comparison 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
inputs/data.csv 는 long-format(dataset/annotation/log2fc/adj_pvalue)이며, annotation 정규화·
집계·enrichment 계산을 함수 내부에서 수행한다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/annotation_comparison.py ────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(9, 6))
ax = fig.add_subplot(111)
render_annotation_comparison(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_venn_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source("venn", "render_venn")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "venn", params_repr)

    return f'''"""Recreate the Venn diagram from this bundle.

render_venn 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다.
inputs/data.csv 는 long-format 멤버십 테이블(dataset/item)이며, matplotlib_venn 이 필요하다
(없으면 안내 메시지가 그려진다):  pip install matplotlib-venn
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/venn.py ─────────────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(10, 8))
ax = fig.add_subplot(111)
render_venn(ax, df, plot_params)
fig.tight_layout()

fig.savefig(root / "outputs" / "{source_stem}.png", dpi=300, bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.pdf", bbox_inches="tight")
fig.savefig(root / "outputs" / "{source_stem}.svg", bbox_inches="tight")
'''


def _build_upset_plot_script(source_stem: str, params_repr: str) -> str:
    render_src = _render_source(
        "upset", "_patched_plot_matrix", "_patched_label_sizes",
        "_apply_upset_patches", "render_upset")
    if render_src is None:
        return _build_generic_plot_script(source_stem, "upset", params_repr)

    return f'''"""Recreate the UpSet plot from this bundle.

render_upset 은 cmg-seqviewer 화면 렌더링과 동일한 함수를 inline 한 것이다. inputs/data.csv 는
long-format 멤버십 테이블(dataset/item)이며, upsetplot 이 필요하다 (없으면 안내 메시지):
    pip install upsetplot
pandas>=3.0 / numpy>=2.0 호환 패치도 함께 inline 되어 render 시점에 적용된다.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure

# ── inlined from src/plots/upset.py ────────────────────────────────────
{render_src}
# ───────────────────────────────────────────────────────────────────────

root = Path(__file__).resolve().parents[1]
plot_params = {params_repr}

df = pd.read_csv(root / "inputs" / "data.csv")
fig = Figure(figsize=(11, 7))
render_upset(fig, df, plot_params)

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
