"""Volcano plot — pure renderer (single source of truth for dialog + bundle).

render_volcano(ax, df, params) 는 화면 다이얼로그(VolcanoPlotWidget._draw_plot)와
재현 번들 스크립트가 공유한다. Qt/다이얼로그에 의존하지 않는다.
"""
import numpy as np
import pandas as pd


def _draw_volcano_labels(ax, df, params):
    """상위 N개(유의성) 또는 커스텀 유전자 이름 레이블."""
    mode = params.get('annotation_mode', 'none')
    if mode in (None, '', 'none'):
        return
    gene_col = next((c for c in ('nearest_gene', 'gene_name', 'symbol', 'gene_id')
                     if c in df.columns), None)
    if gene_col is None:
        return
    size = int(params.get('annotation_label_size', 8))
    if mode == 'top_n':
        n = int(params.get('annotation_top_n', 10))
        sig = df[df['regulation'].isin(['up', 'down'])].copy()
        if sig.empty:
            return
        sig['_score'] = sig['log2FC'].abs() * sig['-log10(padj)']
        targets = sig.nlargest(n, '_score')
    else:  # custom
        custom = params.get('annotation_custom_genes') or []
        if not custom:
            return
        wanted = {str(g).upper() for g in custom}
        targets = df[df[gene_col].astype(str).str.upper().isin(wanted)]
        if targets.empty:
            return
    for _, row in targets.iterrows():
        ax.annotate(
            str(row[gene_col]), xy=(row['log2FC'], row['-log10(padj)']),
            xytext=(4, 4), textcoords='offset points',
            fontsize=size, fontweight='bold', color='black',
            arrowprops=dict(arrowstyle='-', color='grey', lw=0.5, shrinkA=0, shrinkB=2),
            bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.6),
            zorder=500,
        )


def render_volcano(ax, df, params):
    """Volcano plot을 ax에 그린다. 분류된 DataFrame(regulation 포함)을 반환.

    params 키(= VolcanoPlotWidget.get_plot_params()):
      log2fc_threshold, padj_threshold, up_color/down_color/ns_color(hex), dot_size,
      x_min/x_max/y_min/y_max, annotation_mode/annotation_top_n/annotation_label_size/
      annotation_custom_genes, labels_title/labels_xlabel/labels_ylabel,
      show_legend/legend_position, show_xticklabels/show_yticklabels
    """
    df = df.copy()
    if 'log2FC' not in df.columns or 'padj' not in df.columns:
        ax.text(0.5, 0.5, 'Required columns not found:\nlog2FC and padj',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)
        return df

    lfc_thr = float(params.get('log2fc_threshold', 1.0))
    padj_thr = float(params.get('padj_threshold', 0.05))
    up_c = params.get('up_color', '#ff0000')
    down_c = params.get('down_color', '#0000ff')
    ns_c = params.get('ns_color', '#808080')
    dot = float(params.get('dot_size', 20))

    padj = pd.to_numeric(df['padj'], errors='coerce')
    df['-log10(padj)'] = -np.log10(padj.replace(0, 1e-300))
    df['regulation'] = 'ns'
    df.loc[(df['log2FC'] >= lfc_thr) & (padj <= padj_thr), 'regulation'] = 'up'
    df.loc[(df['log2FC'] <= -lfc_thr) & (padj <= padj_thr), 'regulation'] = 'down'

    for reg, color in [('ns', ns_c), ('down', down_c), ('up', up_c)]:
        sub = df[df['regulation'] == reg]
        ax.scatter(sub['log2FC'], sub['-log10(padj)'], c=color, s=dot, alpha=0.6,
                   label=f'{reg.upper()} ({len(sub)})', edgecolors='none')

    ax.axhline(-np.log10(padj_thr), color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax.axvline(lfc_thr, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax.axvline(-lfc_thr, color='black', linestyle='--', linewidth=1, alpha=0.5)

    xmin, xmax = params.get('x_min'), params.get('x_max')
    ymin, ymax = params.get('y_min'), params.get('y_max')
    if xmin is not None and xmax is not None:
        ax.set_xlim(float(xmin), float(xmax))
    if ymin is not None and ymax is not None:
        ax.set_ylim(float(ymin), float(ymax))
    ax.grid(True, alpha=0.3)

    _draw_volcano_labels(ax, df, params)

    # 라벨/범례/틱 (다이얼로그에선 PlotLabelsPanel이 이후 재적용해 우선; 번들에선 이게 최종)
    ax.set_xlabel(params.get('labels_xlabel') or 'Log2 Fold Change')
    ax.set_ylabel(params.get('labels_ylabel') or '-Log10(Padj)')
    title = params.get('labels_title')
    if title:
        ax.set_title(title)
    if not params.get('show_xticklabels', True):
        ax.tick_params(axis='x', labelbottom=False)
    if not params.get('show_yticklabels', True):
        ax.tick_params(axis='y', labelleft=False)
    if params.get('show_legend', True):
        loc = params.get('legend_position', 'best')
        if loc == 'outside right':
            ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize='small')
            ax.figure.subplots_adjust(right=0.78)
        else:
            ax.legend(loc=loc)
    return df
