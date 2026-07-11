"""Integrated volcano (RNA-seq DE colored by ATAC concordance) — pure renderer.

render_integrated_volcano(ax, df, params) 는 IntegratedVolcanoDialog._do_plot 과 재현
번들 스크립트가 공유한다. X축 RNA log2FC, Y축 -log10(RNA padj), 색=concordance 카테고리,
크기=ATAC peak count. Qt/models 비의존 — 컬럼명·카테고리·색상을 함수 내부에 내장한다.
반환값(scatter_data: list[(PathCollection, sub_df)])은 다이얼로그 hover 에서 재사용한다.
"""
import numpy as np
import pandas as pd


def render_integrated_volcano(ax, df, params):
    """Integrated volcano를 ax에 그린다. scatter_data(list[(sc, sub)]) 반환.

    params: padj_threshold(0.05), log2fc_threshold(1.0), base_size(30),
            scale_by_peak(bool), title
    """
    col_lfc = 'rna_log2fc'
    col_padj = 'rna_padj'
    col_cat = 'concordance'
    col_peak = 'peak_count'

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

    padj_thr = float(params.get('padj_threshold', 0.05))
    lfc_thr = float(params.get('log2fc_threshold', 1.0))
    base_sz = int(params.get('base_size', 30))
    scale_by_peak = bool(params.get('scale_by_peak', True))
    title = params.get('title', 'Integrated Volcano Plot')

    df = df.copy() if df is not None else pd.DataFrame()
    scatter_data = []
    if df.empty or col_lfc not in df.columns or col_padj not in df.columns:
        ax.text(0.5, 0.5, "No integrated RNA/ATAC data.", ha='center', va='center',
                fontsize=13, transform=ax.transAxes)
        return scatter_data

    df = df.dropna(subset=[col_lfc, col_padj]).copy()
    df['_neg_log10_padj'] = -np.log10(df[col_padj].clip(lower=1e-300))

    for cat in cat_all:
        sub = df[df[col_cat] == cat] if col_cat in df.columns else df.iloc[0:0]
        if sub.empty:
            continue
        if scale_by_peak and col_peak in sub.columns:
            peak_cnt = sub[col_peak].fillna(1).clip(lower=1)
            sizes = base_sz * (1 + np.log1p(peak_cnt) * 0.8)
        else:
            sizes = base_sz
        sc = ax.scatter(sub[col_lfc], sub['_neg_log10_padj'],
                        c=colors.get(cat, '#CCCCCC'), s=sizes, alpha=0.75,
                        linewidths=0.3, edgecolors='white',
                        label=f"{cat.replace('_', ' ')} (n={len(sub)})", zorder=3)
        scatter_data.append((sc, sub))

    ax.axhline(-np.log10(padj_thr), color='black', linestyle='--', linewidth=0.8, alpha=0.6)
    ax.axvline(lfc_thr, color='black', linestyle='--', linewidth=0.8, alpha=0.6)
    ax.axvline(-lfc_thr, color='black', linestyle='--', linewidth=0.8, alpha=0.6)

    ax.set_xlabel("RNA-seq log2FC", fontsize=11)
    ax.set_ylabel("-log10(RNA padj)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.25)
    ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=7.5, framealpha=0.7)
    return scatter_data
