"""TF motif enrichment renderer (Qt-free; dialog + bundle shared)."""
from __future__ import annotations

from typing import Any, Mapping, Optional

import numpy as np
import pandas as pd

_MOTIF_QVALUE = "motif_qvalue"
_MOTIF_LOG_PVALUE = "log_pvalue"
_MOTIF_PVALUE = "motif_pvalue"
_MOTIF_NAME = "motif_name"
_MOTIF_ID = "motif_id"
_TARGET_PCT = "target_pct"


def prepare_motif_df(df: pd.DataFrame, params: Mapping[str, Any]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    df = df.copy()
    qv = float((params or {}).get('qval_cutoff', 0.05))
    if _MOTIF_QVALUE in df.columns:
        df = df[pd.to_numeric(df[_MOTIF_QVALUE], errors='coerce') <= qv]
    if df.empty:
        return None

    if _MOTIF_LOG_PVALUE in df.columns:
        sort_col = _MOTIF_LOG_PVALUE
    elif _MOTIF_PVALUE in df.columns:
        pv = pd.to_numeric(df[_MOTIF_PVALUE], errors='coerce').clip(lower=1e-300)
        df[_MOTIF_LOG_PVALUE] = -np.log10(pv)
        sort_col = _MOTIF_LOG_PVALUE
    else:
        return None

    df[sort_col] = pd.to_numeric(df[sort_col], errors='coerce')
    df = df.dropna(subset=[sort_col])
    top_n = int((params or {}).get('top_n', 20))
    df = df.sort_values(sort_col, ascending=False).head(top_n)

    if _MOTIF_NAME not in df.columns:
        df[_MOTIF_NAME] = df.get(
            _MOTIF_ID, pd.Series('unknown', index=df.index))
    return df.reset_index(drop=True)


def _plot_single(ax, df: pd.DataFrame, params: Mapping[str, Any], label: str,
                 color: str):
    if df is None or df.empty:
        ax.text(0.5, 0.5, 'No significant motifs found\n(check q-value cutoff)',
                ha='center', va='center', fontsize=12)
        return
    y = np.arange(len(df))
    ax.barh(y, df[_MOTIF_LOG_PVALUE], color=color, alpha=0.85, height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(df[_MOTIF_NAME], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel('-log₁₀(p-value)')
    ax.set_title(label)

    if params.get('show_pct') and _TARGET_PCT in df.columns:
        ax2 = ax.twiny()
        ax2.barh(y, df[_TARGET_PCT], color='#e15759', alpha=0.3, height=0.7)
        ax2.set_xlabel('% of target peaks', color='#e15759')
        ax2.tick_params(axis='x', colors='#e15759')

    n_sig = (df[_MOTIF_QVALUE] <= float(params.get('qval_cutoff', 0.05))).sum() \
        if _MOTIF_QVALUE in df.columns else len(df)
    ax.set_title(f"{label}  (n={len(df)}, q≤{float(params.get('qval_cutoff', 0.05)):.3f}: {n_sig})")


def render_motif_enrichment(fig, df: pd.DataFrame, params: Mapping[str, Any]):
    params = dict(params or {})
    comparison = bool(params.get('comparison'))
    labels = params.get('labels') or {}

    if comparison and 'direction' in df.columns:
        directions = [d for d in ('UP', 'DOWN')
                      if d in set(df['direction'].dropna().astype(str))]
        if not directions:
            directions = list(dict.fromkeys(df['direction'].dropna().astype(str)))
        axes = fig.subplots(1, max(len(directions), 1), sharey=False)
        if not isinstance(axes, np.ndarray):
            axes = np.array([axes])
        colors = {'UP': '#e15759', 'DOWN': '#4e79a7'}
        for ax, direction in zip(axes, directions):
            sub = prepare_motif_df(
                df[df['direction'].astype(str) == direction], params)
            _plot_single(ax, sub, params, labels.get(direction, direction),
                         colors.get(direction, '#4e79a7'))
        return {'directions': directions}

    sub = prepare_motif_df(df, params)
    ax = fig.add_subplot(111)
    label = labels.get('single') or params.get('dataset_name') or 'Motifs'
    _plot_single(ax, sub, params, label, '#4e79a7')
    return {'directions': []}
