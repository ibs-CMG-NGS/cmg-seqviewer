"""TSS-distance histogram renderer (Qt-free; dialog + bundle shared)."""
from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
from matplotlib.ticker import FuncFormatter


def render_tss_distance(ax, df: pd.DataFrame, params: Mapping[str, Any]):
    params = dict(params or {})
    dist_range = int(params.get('dist_range') or 50_000)
    bins = int(params.get('bins') or 100)

    if df is None or 'distance_to_tss' not in df.columns or df['distance_to_tss'].isna().all():
        ax.text(
            0.5, 0.5,
            "Distance-to-TSS data not available.\n"
            "This dataset does not contain a 'distance_to_tss' column.\n"
            "Load a full-format ATAC-seq Excel file to enable this plot.",
            ha='center', va='center', transform=ax.transAxes,
            fontsize=10, color='#888888',
            bbox=dict(boxstyle='round', fc='#f8f8f8', ec='#cccccc', alpha=0.8),
        )
        return {'total': 0, 'within_2kb': 0, 'within_5kb': 0}

    series = pd.to_numeric(df['distance_to_tss'], errors='coerce').dropna()
    clipped = series.clip(-dist_range, dist_range)
    ax.hist(clipped, bins=bins, range=(-dist_range, dist_range),
            color='#4e79a7', edgecolor='white', linewidth=0.3)

    for pos, label, ls, color in [
        (0, 'TSS', '-', '#e15759'),
        (-2_000, '−2kb', '--', '#888888'),
        (2_000, '+2kb', '--', '#888888'),
        (-5_000, '−5kb', ':', '#aaaaaa'),
        (5_000, '+5kb', ':', '#aaaaaa'),
    ]:
        if abs(pos) <= dist_range:
            ax.axvline(pos, linestyle=ls, color=color, linewidth=1.2, alpha=0.85)
            if pos == 0:
                ax.text(pos + dist_range * 0.01, ax.get_ylim()[1] * 0.95,
                        label, color=color, fontsize=8, va='top')

    ax.set_xlabel('Distance to TSS (bp)', fontsize=10)
    ax.set_ylabel('Number of Peaks', fontsize=10)
    title = params.get('title') or 'TSS Distance Distribution'
    ax.set_title(title, fontsize=11)

    def bp_to_kb(x, _):
        return f'{int(x / 1000)}kb' if x != 0 else '0'
    ax.xaxis.set_major_formatter(FuncFormatter(bp_to_kb))

    within_2kb = int((series.abs() <= 2_000).sum())
    within_5kb = int((series.abs() <= 5_000).sum())
    return {'total': int(len(series)),
            'within_2kb': within_2kb,
            'within_5kb': within_5kb}
