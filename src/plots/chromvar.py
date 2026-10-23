"""chromVAR differential TF activity renderer (Qt-free; dialog + bundle shared)."""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

_DELTA = 'chromvar_delta'
_PADJ = 'chromvar_padj'
_PVALUE = 'chromvar_pvalue'
_MEAN_BASE = 'chromvar_mean_base'
_MEAN_COMPARE = 'chromvar_mean_compare'
_TF_NAME = 'chromvar_tf_name'
_MOTIF_ID = 'chromvar_motif_id'


def prepare_chromvar_df(df: pd.DataFrame, params: Mapping[str, Any] | None = None):
    if df is None or df.empty:
        return None
    df = df.copy()
    for col in (_DELTA, _PADJ, _MEAN_BASE, _MEAN_COMPARE):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if _DELTA not in df.columns or _PADJ not in df.columns:
        return None
    df = df.dropna(subset=[_DELTA, _PADJ])
    if df.empty:
        return None
    df['chromvar_neg_log_padj'] = -np.log10(df[_PADJ].clip(lower=1e-300))
    return df.reset_index(drop=True)


def _name_col(df):
    return _TF_NAME if _TF_NAME in df.columns else _MOTIF_ID


def _label_top(ax, df, mask, sort_values, x_values, y_values, top_n, name_col):
    if not top_n:
        return
    sub = df[mask].copy()
    if sub.empty:
        return
    order = sort_values[mask].abs().sort_values(ascending=False).index
    sub = sub.loc[order].head(top_n)
    for idx, row in sub.iterrows():
        color = '#e15759' if row[_DELTA] > 0 else '#4e79a7'
        ax.annotate(str(row.get(name_col, '')),
                    (x_values.loc[idx], y_values.loc[idx]),
                    fontsize=7, xytext=(4, 4), textcoords='offset points',
                    color=color)


def _plot_volcano(ax, df, params):
    padj_cut = float(params.get('padj_cutoff', 0.05))
    delta_cut = float(params.get('delta_cutoff', 0.5))
    dot_size = int(params.get('dot_size', 30))
    neg_log = df['chromvar_neg_log_padj']
    delta = df[_DELTA]
    sig_up = (df[_PADJ] <= padj_cut) & (delta >= delta_cut)
    sig_down = (df[_PADJ] <= padj_cut) & (delta <= -delta_cut)
    ns = ~(sig_up | sig_down)
    pairs = []
    for mask, color, label, alpha, zorder in (
            (ns, '#cccccc', f'NS (n={ns.sum()})', 0.5, 1),
            (sig_up, '#e15759', f'Increased (n={sig_up.sum()})', 0.85, 2),
            (sig_down, '#4e79a7', f'Decreased (n={sig_down.sum()})', 0.85, 2),
    ):
        sc = ax.scatter(delta[mask], neg_log[mask], c=color, s=dot_size,
                        alpha=alpha, label=label, zorder=zorder,
                        edgecolors='none')
        pairs.append((sc, df[mask].reset_index(drop=True)))
    ax.axhline(-np.log10(padj_cut), color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.axvline(delta_cut, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.axvline(-delta_cut, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    _label_top(ax, df, sig_up | sig_down, delta, delta, neg_log,
               int(params.get('top_n', 10)), _name_col(df))
    ax.set_xlabel('delta z-score  (compare − base)')
    ax.set_ylabel('-log₁₀(padj)')
    ax.set_title(params.get('title') or 'TF Activity Volcano')
    ax.legend(fontsize=8, framealpha=0.7)
    return pairs, _DELTA, 'chromvar_neg_log_padj'


def _plot_scatter(ax, df, params):
    padj_cut = float(params.get('padj_cutoff', 0.05))
    delta_cut = float(params.get('delta_cutoff', 0.5))
    dot_size = int(params.get('dot_size', 30))
    delta = df[_DELTA]
    x = df[_MEAN_BASE]
    y = df[_MEAN_COMPARE]
    sig_up = (df[_PADJ] <= padj_cut) & (delta >= delta_cut)
    sig_down = (df[_PADJ] <= padj_cut) & (delta <= -delta_cut)
    ns = ~(sig_up | sig_down)
    pairs = []
    for mask, color, label, alpha, zorder in (
            (ns, '#cccccc', f'NS (n={ns.sum()})', 0.4, 1),
            (sig_up, '#e15759', f'Increased (n={sig_up.sum()})', 0.85, 2),
            (sig_down, '#4e79a7', f'Decreased (n={sig_down.sum()})', 0.85, 2),
    ):
        sc = ax.scatter(x[mask], y[mask], c=color, s=dot_size,
                        alpha=alpha, label=label, zorder=zorder,
                        edgecolors='none')
        pairs.append((sc, df[mask].reset_index(drop=True)))
    lim = [min(x.min(), y.min()) - 0.2, max(x.max(), y.max()) + 0.2]
    ax.plot(lim, lim, color='gray', linestyle='--', linewidth=0.8, alpha=0.6, zorder=0)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    _label_top(ax, df, sig_up | sig_down, delta, x, y,
               int(params.get('top_n', 10)), _name_col(df))
    ax.set_xlabel('base (Control) mean z-score')
    ax.set_ylabel('compare mean z-score')
    ax.set_title(params.get('title') or 'TF Activity Scatter')
    ax.legend(fontsize=8, framealpha=0.7)
    return pairs, _MEAN_BASE, _MEAN_COMPARE


def _plot_heatmap(fig, df, params):
    from matplotlib.colors import TwoSlopeNorm
    ax = fig.add_subplot(111)
    if 'dataset' not in df.columns:
        ax.text(0.5, 0.5, 'Heatmap requires a dataset column.', ha='center', va='center')
        return None, None, None
    frames = {}
    for name, sub in df.groupby('dataset'):
        prepared = prepare_chromvar_df(sub, params)
        if prepared is None or prepared.empty:
            continue
        key_col = _name_col(prepared)
        frames[str(name)] = prepared.set_index(key_col)[_DELTA]
    if not frames:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
        return None, None, None
    mat = pd.DataFrame(frames).dropna(how='all')
    top_n = int(params.get('heatmap_top_n', 30))
    mat['_max_abs'] = mat.abs().max(axis=1)
    mat = mat.nlargest(top_n, '_max_abs').drop(columns='_max_abs')
    mat = mat.sort_values(mat.columns[0], ascending=False)
    if mat.empty:
        ax.text(0.5, 0.5, 'No significant TFs', ha='center', va='center')
        return None, None, None
    vmax = max(mat.abs().max().max(), 0.01)
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    im = ax.imshow(mat.values, aspect='auto', cmap='RdBu_r', norm=norm)
    fig.colorbar(im, ax=ax, label='delta z-score', shrink=0.8)
    ax.set_xticks(range(len(mat.columns)))
    ax.set_xticklabels(mat.columns, rotation=30, ha='right', fontsize=8)
    ax.set_yticks(range(len(mat.index)))
    ax.set_yticklabels(mat.index, fontsize=7)
    ax.set_title(f'TF Activity Heatmap  (top {top_n} by |delta|)', fontsize=10)
    return None, None, None


def render_chromvar(fig, df: pd.DataFrame, params: Mapping[str, Any]):
    params = dict(params or {})
    mode = str(params.get('mode') or 'volcano').lower()
    prepared = prepare_chromvar_df(df, params)
    if prepared is None or prepared.empty:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center')
        return {'mode': mode, 'hover_pairs': [], 'hover_x': '', 'hover_y': ''}
    if mode == 'heatmap':
        _plot_heatmap(fig, df, params)
        return {'mode': mode, 'hover_pairs': [], 'hover_x': '', 'hover_y': ''}
    ax = fig.add_subplot(111)
    if mode == 'scatter':
        pairs, hx, hy = _plot_scatter(ax, prepared, params)
    else:
        pairs, hx, hy = _plot_volcano(ax, prepared, params)
    fig.tight_layout()
    return {'mode': mode, 'hover_pairs': pairs, 'hover_x': hx, 'hover_y': hy}
