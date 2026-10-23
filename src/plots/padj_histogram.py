"""P-value histogram renderer (Qt-free; dialog + bundle shared)."""
from __future__ import annotations

from typing import Any, Mapping

import pandas as pd


def render_padj_histogram(ax, df: pd.DataFrame, params: Mapping[str, Any]):
    pvalue_type = str((params or {}).get('pvalue_type') or 'padj')
    bin_count = int((params or {}).get('bin_count') or 50)

    if df is None or pvalue_type not in df.columns:
        ax.text(0.5, 0.5, f'Required column not found: {pvalue_type}',
                ha='center', va='center', fontsize=14)
        return {'total': 0, 'mean': None, 'median': None}

    data = pd.to_numeric(df[pvalue_type], errors='coerce').dropna()
    ax.hist(data, bins=bin_count, color='steelblue', edgecolor='black', alpha=0.7)

    if pvalue_type == 'padj':
        xlabel = 'Adjusted P-value'
        title = 'Distribution of Adjusted P-values'
    else:
        xlabel = 'Original P-value'
        title = 'Distribution of Original P-values'

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    stats_text = (f'Total: {len(data)}\n'
                  f'Mean: {data.mean():.4f}\n'
                  f'Median: {data.median():.4f}')
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
            fontsize=10)
    return {'total': int(len(data)),
            'mean': float(data.mean()) if len(data) else None,
            'median': float(data.median()) if len(data) else None}
