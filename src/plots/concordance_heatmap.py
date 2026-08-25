"""Concordance Heatmap (RNA vs ATAC log2FC + concordance category strip) — 순수 렌더러.

render_concordance_heatmap(fig, df, params) 는 ConcordanceHeatmapDialog._do_plot 과
재현 번들 스크립트가 공유한다. Qt/models 비의존 — 컬럼명·카테고리·색상을 함수 내부에
자기완결로 포함한다.
"""
import numpy as np
import pandas as pd
import matplotlib


def render_concordance_heatmap(fig, df, params):
    """Concordance heatmap을 fig에 그린다 (다중 axes: heat + category strip + legend).

    params: max_genes(기본 100), show_gene_labels(기본 False), title

    번들 재현 스크립트는 이 함수 소스만 inline하므로(모듈 top-level 상수는 포함되지
    않음), 카테고리 순서/색상은 반드시 함수 내부 로컬 변수로 자기완결시킨다
    (plots/quadrant.py 의 cat_all/colors 와 동일한 관례).
    """
    import matplotlib.patches as mpatches
    import matplotlib.colors as mcolors

    _CATEGORY_ORDER = [
        "Concordant_Both_UP", "Concordant_Both_DOWN",
        "Discordant_RNA_UP_ATAC_DOWN", "Discordant_RNA_DOWN_ATAC_UP",
        "RNA_only", "ATAC_only",
    ]
    _CATEGORY_COLORS = {
        "Concordant_Both_UP": "#D73027", "Concordant_Both_DOWN": "#4575B4",
        "Discordant_RNA_UP_ATAC_DOWN": "#FC8D59", "Discordant_RNA_DOWN_ATAC_UP": "#91BFDB",
        "RNA_only": "#A6D96A", "ATAC_only": "#FDAE61", "Not_significant": "#CCCCCC",
    }

    col_rna, col_atac = "rna_log2fc", "atac_log2fc_mean"
    col_cat, col_sym = "concordance", "symbol"
    max_genes = int(params.get("max_genes", 100))
    show_labels = bool(params.get("show_gene_labels", False))
    title = params.get("title", "Concordance Heatmap")

    df = df[df[col_cat].isin(_CATEGORY_ORDER)].dropna(subset=[col_rna, col_atac]) if df is not None else pd.DataFrame()

    cat_order = {c: i for i, c in enumerate(_CATEGORY_ORDER)}
    df = df.copy()
    if not df.empty:
        df["_cat_order"] = df[col_cat].map(cat_order)
        df = df.sort_values(["_cat_order", col_rna], ascending=[True, False])
        df = df.head(max_genes)

    if df.empty:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "No significant genes to display",
                ha="center", va="center", transform=ax.transAxes)
        return

    heatmap_data = df[[col_rna, col_atac]].values
    gene_names = df[col_sym].values if col_sym in df.columns else np.array([""] * len(df))
    categories = df[col_cat].values

    gs = fig.add_gridspec(1, 2, width_ratios=[10, 1], wspace=0.05)
    ax_heat = fig.add_subplot(gs[0])
    ax_ann = fig.add_subplot(gs[1])

    vmax = np.nanpercentile(np.abs(heatmap_data), 95)
    if vmax == 0:
        vmax = 1.0
    cmap = matplotlib.colormaps.get_cmap("RdBu_r")

    im = ax_heat.imshow(
        heatmap_data, aspect="auto", cmap=cmap,
        vmin=-vmax, vmax=vmax, interpolation="nearest",
    )

    ax_heat.set_xticks([0, 1])
    ax_heat.set_xticklabels(["RNA log2FC", "ATAC log2FC"], fontsize=9)
    ax_heat.set_title(title, fontsize=11, fontweight="bold")

    if show_labels:
        ax_heat.set_yticks(range(len(gene_names)))
        ax_heat.set_yticklabels(gene_names, fontsize=6)
    else:
        ax_heat.set_yticks([])

    ax_heat.set_ylabel(f"Genes (n={len(df)})", fontsize=9)

    fig.colorbar(im, ax=ax_heat, fraction=0.03, pad=0.02, label="log2FC")

    ann_colors = np.array([[
        mcolors.to_rgb(_CATEGORY_COLORS.get(c, "#CCCCCC"))
    ] for c in categories])

    ax_ann.imshow(ann_colors, aspect="auto", interpolation="nearest")
    ax_ann.set_xticks([0])
    ax_ann.set_xticklabels(["Cat."], fontsize=7)
    ax_ann.set_yticks([])

    patches = [
        mpatches.Patch(color=_CATEGORY_COLORS.get(c, "#CCCCCC"), label=c.replace("_", " "))
        for c in _CATEGORY_ORDER
        if c in df[col_cat].values
    ]
    # tight_layout에 legend는 잡히지 않으므로(matplotlib 알려진 제약) 미리 우측 22%를
    # legend용으로 비워두고, legend는 figure 좌표로 그 안에 배치한다 — 창 폭에 따라
    # 함께 스케일되므로 리사이즈해도 잘리지 않는다.
    fig.tight_layout(rect=[0, 0, 0.78, 1])
    fig.legend(
        handles=patches, bbox_to_anchor=(0.80, 0.92), loc="upper left",
        bbox_transform=fig.transFigure, fontsize=7, framealpha=0.7,
    )
