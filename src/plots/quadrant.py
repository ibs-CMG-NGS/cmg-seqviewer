"""Quadrant plot (RNA vs ATAC log2FC) — pure renderer (dialog + bundle 공유).

render_quadrant(ax, df, params) 는 QuadrantPlotDialog._do_plot 과 재현 번들 스크립트가
공유한다. X축 ATAC log2FC, Y축 RNA log2FC, concordance 카테고리별 색상 scatter.
Qt/models 비의존 — 컬럼명·카테고리·색상을 함수 내부에 자기완결로 포함한다.
반환값(scatter_data)은 다이얼로그 hover 툴팁에서 재사용한다.
"""
import numpy as np
import pandas as pd


def render_quadrant(ax, df, params):
    """Quadrant scatter를 ax에 그린다. 카테고리별 scatter_data(list[dict]) 반환.

    params: point_size(기본 30), alpha(기본 0.7), title
    """
    col_sym = 'symbol'
    col_rna = 'rna_log2fc'
    col_atac = 'atac_log2fc_mean'
    col_cat = 'concordance'
    col_padj = 'rna_padj'

    cat_all = [
        'Concordant_Both_UP', 'Concordant_Both_DOWN',
        'Discordant_RNA_UP_ATAC_DOWN', 'Discordant_RNA_DOWN_ATAC_UP',
        'RNA_only', 'ATAC_only', 'Not_significant',
    ]
    colors = {
        'Concordant_Both_UP': '#D73027', 'Concordant_Both_DOWN': '#4575B4',
        'Discordant_RNA_UP_ATAC_DOWN': '#FC8D59', 'Discordant_RNA_DOWN_ATAC_UP': '#91BFDB',
        'RNA_only': '#A6D96A', 'ATAC_only': '#FDAE61', 'Not_significant': '#CCCCCC',
    }

    point_size = int(params.get('point_size', 30))
    alpha = float(params.get('alpha', 0.7))
    title = params.get('title', 'Quadrant Plot')

    df = df.copy() if df is not None else pd.DataFrame()
    scatter_data = []
    if df.empty or col_rna not in df.columns or col_atac not in df.columns:
        ax.text(0.5, 0.5, "No integrated RNA/ATAC data.", ha='center', va='center',
                fontsize=13, transform=ax.transAxes)
        return scatter_data

    df = df.dropna(subset=[col_rna, col_atac])

    for cat in cat_all:
        sub = df[df[col_cat] == cat] if col_cat in df.columns else df.iloc[0:0]
        if sub.empty:
            continue
        ax.scatter(sub[col_atac], sub[col_rna], c=colors.get(cat, '#CCCCCC'),
                   s=point_size, alpha=alpha, linewidths=0.3, edgecolors='white',
                   label=f"{cat} (n={len(sub)})", zorder=3)
        padj_vals = sub[col_padj].values if col_padj in sub.columns else np.full(len(sub), np.nan)
        scatter_data.append({
            'x': sub[col_atac].values.astype(float),
            'y': sub[col_rna].values.astype(float),
            'symbol': sub[col_sym].values.astype(str) if col_sym in sub.columns
                      else np.array([''] * len(sub)),
            'padj': padj_vals.astype(float),
            'concordance': sub[col_cat].values.astype(str) if col_cat in sub.columns
                           else np.array([''] * len(sub)),
        })

    ax.axhline(0, color='gray', linewidth=0.8, linestyle='--', zorder=1)
    ax.axvline(0, color='gray', linewidth=0.8, linestyle='--', zorder=1)
    ax.set_xlabel("ATAC-seq log2FC (chromatin accessibility)", fontsize=11)
    ax.set_ylabel("RNA-seq log2FC (gene expression)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold')

    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    xpad = (xlim[1] - xlim[0]) * 0.03
    ypad = (ylim[1] - ylim[0]) * 0.03
    ax.text(xlim[1] - xpad, ylim[1] - ypad, "Q1\nBoth↑",
            ha='right', va='top', fontsize=8, color='#D73027', alpha=0.7)
    ax.text(xlim[0] + xpad, ylim[1] - ypad, "Q2\nRNA↑ATAC↓",
            ha='left', va='top', fontsize=8, color='#FC8D59', alpha=0.7)
    ax.text(xlim[0] + xpad, ylim[0] + ypad, "Q3\nBoth↓",
            ha='left', va='bottom', fontsize=8, color='#4575B4', alpha=0.7)
    ax.text(xlim[1] - xpad, ylim[0] + ypad, "Q4\nRNA↓ATAC↑",
            ha='right', va='bottom', fontsize=8, color='#91BFDB', alpha=0.7)

    ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=8, framealpha=0.7)
    return scatter_data
