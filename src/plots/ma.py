"""MA plot — pure renderer (dialog + bundle 공유).

render_ma(ax, df, params) 는 MAPlotDialog._do_plot 과 재현 번들 스크립트가 공유한다.
X축 = log2(base_mean), Y축 = log2FC. Qt/StandardColumns 비의존(표준 컬럼명 리터럴).
"""
import numpy as np
import pandas as pd


def render_ma(ax, df, params):
    """MA plot을 ax에 그린다. (분류된 df) 반환. 필수 컬럼 없으면 None.

    params: padj_threshold, log2fc_threshold, dot_size,
            up_color/down_color/ns_color(hex), x_min/x_max/y_min/y_max,
            title/xlabel/ylabel, show_legend,
            annotation_mode('none'|'top_n'|'custom'), annotation_top_n,
            annotation_label_size, annotation_custom_genes
    """
    if df is None or df.empty:
        ax.text(0.5, 0.5, 'No data available.', ha='center', va='center',
                fontsize=14, transform=ax.transAxes)
        return None
    if 'base_mean' not in df.columns or 'log2fc' not in df.columns:
        missing = [c for c in ('base_mean', 'log2fc') if c not in df.columns]
        ax.text(0.5, 0.5, f'Required columns not found:\n{", ".join(missing)}',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)
        return None

    padj_thr = float(params.get('padj_threshold', 0.05))
    lfc_thr = float(params.get('log2fc_threshold', 1.0))
    dot = float(params.get('dot_size', 15))
    up_c = params.get('up_color', '#c0392b')
    down_c = params.get('down_color', '#2c6fbb')
    ns_c = params.get('ns_color', '#b0b0b0')

    df = df.copy()
    df['_x'] = np.log2(pd.to_numeric(df['base_mean'], errors='coerce').clip(lower=1e-6))
    df['_y'] = pd.to_numeric(df['log2fc'], errors='coerce')

    df['_reg'] = 'ns'
    if 'adj_pvalue' in df.columns:
        padj = pd.to_numeric(df['adj_pvalue'], errors='coerce')
        df.loc[(df['_y'] >= lfc_thr) & (padj <= padj_thr), '_reg'] = 'up'
        df.loc[(df['_y'] <= -lfc_thr) & (padj <= padj_thr), '_reg'] = 'down'

    for reg, color in [('ns', ns_c), ('down', down_c), ('up', up_c)]:
        sub = df[df['_reg'] == reg]
        ax.scatter(sub['_x'], sub['_y'], c=color, s=dot, alpha=0.5,
                   label=f"{reg.upper()} ({len(sub):,})", edgecolors='none')

    ax.axhline(0, color='black', linewidth=0.8, alpha=0.6)
    ax.axhline(lfc_thr, color='gray', linewidth=0.8, linestyle='--', alpha=0.7)
    ax.axhline(-lfc_thr, color='gray', linewidth=0.8, linestyle='--', alpha=0.7)

    ax.set_xlabel(params.get('xlabel') or 'log2(Mean)', fontsize=12)
    ax.set_ylabel(params.get('ylabel') or 'log2 Fold Change', fontsize=12)
    ax.set_title(params.get('title') or 'MA Plot', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    xmin, xmax = params.get('x_min'), params.get('x_max')
    ymin, ymax = params.get('y_min'), params.get('y_max')
    if xmin is not None and xmax is not None:
        ax.set_xlim(float(xmin), float(xmax))
    if ymin is not None and ymax is not None:
        ax.set_ylim(float(ymin), float(ymax))

    if params.get('show_legend', True):
        ax.legend(loc='upper right', fontsize=10)

    # gene 라벨 (top_n / custom)
    mode = params.get('annotation_mode', 'none')
    if mode not in (None, '', 'none'):
        gene_col = next((c for c in ('nearest_gene', 'symbol', 'gene_id', 'peak_id')
                         if c in df.columns), None)
        sig = df[df['_reg'].isin(['up', 'down'])].copy()
        if gene_col is not None and not sig.empty:
            size = int(params.get('annotation_label_size', 8))
            if mode == 'top_n':
                if 'adj_pvalue' in sig.columns:
                    sig['_score'] = sig['_y'].abs() * (
                        -np.log10(pd.to_numeric(sig['adj_pvalue'], errors='coerce').replace(0, 1e-300)))
                else:
                    sig['_score'] = sig['_y'].abs()
                targets = sig.nlargest(int(params.get('annotation_top_n', 10)), '_score')
            else:
                custom = {str(g).upper() for g in (params.get('annotation_custom_genes') or [])}
                targets = sig[sig[gene_col].astype(str).str.upper().isin(custom)] if custom else sig.iloc[0:0]
            texts = [ax.text(row['_x'], row['_y'], str(row[gene_col]),
                             fontsize=size, ha='center', va='center',
                             bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.7),
                             zorder=500)
                     for _, row in targets.iterrows()]
            if texts:
                try:
                    from adjustText import adjust_text
                    adjust_text(texts, ax=ax,
                                arrowprops=dict(arrowstyle='-', color='grey', lw=0.5),
                                expand=(1.15, 1.4), force_text=(0.4, 0.6),
                                only_move={'text': 'xy'})
                except ImportError:
                    pass
    return df
