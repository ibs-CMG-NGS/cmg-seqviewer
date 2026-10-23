"""TF footprint activity scatter renderer (Qt-free; dialog + bundle shared)."""
from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

_COND1_SCORE = 'cond1_score'
_COND2_SCORE = 'cond2_score'
_FOOTPRINT_CHANGE = 'footprint_change'
_FOOTPRINT_PVALUE = 'footprint_pvalue'
_FOOTPRINT_MOTIF_NAME = 'fp_motif_name'


def render_tf_footprint(ax, df: pd.DataFrame, params: Mapping[str, Any]):
    params = dict(params or {})
    if df is None:
        df = pd.DataFrame()
    else:
        df = df.copy()

    for col in (_COND1_SCORE, _COND2_SCORE):
        if col not in df.columns:
            ax.text(0.5, 0.5,
                    f"Required column not found:\n{col}\n\n"
                    "Expected TOBIAS BINDetect bindetect_results.txt",
                    ha='center', va='center', fontsize=11)
            return {'n': 0}

    df[_COND1_SCORE] = pd.to_numeric(df[_COND1_SCORE], errors='coerce')
    df[_COND2_SCORE] = pd.to_numeric(df[_COND2_SCORE], errors='coerce')
    df = df.dropna(subset=[_COND1_SCORE, _COND2_SCORE])
    if df.empty:
        ax.text(0.5, 0.5, 'No valid data', ha='center', va='center')
        return {'n': 0}

    pval_cut = float(params.get('pval_cutoff', 0.05))
    min_change = float(params.get('min_change', 0.0))
    has_pval = _FOOTPRINT_PVALUE in df.columns
    has_change = _FOOTPRINT_CHANGE in df.columns
    if has_pval:
        df[_FOOTPRINT_PVALUE] = pd.to_numeric(df[_FOOTPRINT_PVALUE], errors='coerce')
    if has_change:
        df[_FOOTPRINT_CHANGE] = pd.to_numeric(df[_FOOTPRINT_CHANGE], errors='coerce')

    def classify(row):
        sig = has_pval and pd.notna(row.get(_FOOTPRINT_PVALUE)) \
            and row[_FOOTPRINT_PVALUE] <= pval_cut
        if not sig:
            return 'ns'
        if has_change and pd.notna(row.get(_FOOTPRINT_CHANGE)):
            if row[_FOOTPRINT_CHANGE] >= min_change:
                return 'gain'
            if row[_FOOTPRINT_CHANGE] <= -min_change:
                return 'loss'
        return 'ns'

    df['_cls'] = df.apply(classify, axis=1)
    colors = {'ns': '#cccccc', 'gain': '#e15759', 'loss': '#4e79a7'}
    alphas = {'ns': 0.3, 'gain': 0.85, 'loss': 0.85}
    cond1 = params.get('cond1') or 'Condition 1'
    cond2 = params.get('cond2') or 'Condition 2'
    labels_map = {'ns': 'Not significant', 'gain': f'{cond1} activated',
                  'loss': f'{cond2} activated'}
    dot_size = int(params.get('dot_size', 30))

    for cls in ('ns', 'gain', 'loss'):
        sub = df[df['_cls'] == cls]
        if sub.empty:
            continue
        ax.scatter(sub[_COND1_SCORE], sub[_COND2_SCORE],
                   c=colors[cls], alpha=alphas[cls], s=dot_size,
                   label=f"{labels_map[cls]} (n={len(sub)})",
                   zorder=2 if cls != 'ns' else 1, edgecolors='none')

    if params.get('show_diag', True):
        lim_min = min(ax.get_xlim()[0], ax.get_ylim()[0])
        lim_max = max(ax.get_xlim()[1], ax.get_ylim()[1])
        ax.plot([lim_min, lim_max], [lim_min, lim_max],
                color='gray', linestyle='--', linewidth=0.8, alpha=0.6, zorder=0)

    n_label = int(params.get('top_n_label', 0))
    if n_label > 0 and has_change:
        sig_df = df[df['_cls'] != 'ns'].copy().dropna(subset=[_FOOTPRINT_CHANGE])
        sig_df = sig_df.reindex(
            sig_df[_FOOTPRINT_CHANGE].abs().sort_values(ascending=False).index
        ).head(n_label)
        name_col = _FOOTPRINT_MOTIF_NAME if _FOOTPRINT_MOTIF_NAME in df.columns else None
        if name_col:
            for _, row in sig_df.iterrows():
                ax.annotate(str(row[name_col]),
                            (row[_COND1_SCORE], row[_COND2_SCORE]),
                            fontsize=7, xytext=(4, 4), textcoords='offset points',
                            color=colors.get(row['_cls'], 'black'))

    ax.set_xlabel(f'{cond1} mean footprint score')
    ax.set_ylabel(f'{cond2} mean footprint score')
    ax.set_title(f'TF Activity  —  {cond1} vs {cond2}\n'
                 f'(p ≤ {pval_cut}, |Δ| ≥ {min_change})')
    ax.legend(fontsize=8, framealpha=0.7)
    return {'n': int(len(df))}
