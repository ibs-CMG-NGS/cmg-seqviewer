"""Gene expression distribution plot — pure renderer (dialog + bundle 공유).

Pseudobulk long-format 입력:

    gene_id | gene_name | cell_type | sample | condition | dataset |
    n_cells | pct_expressing | mean_expression

- x = cell type, y = expression
- group(violin/box) = condition/dataset/sample (기본 condition)
- pseudobulk: sample/replicate 값으로 violin/box/strip
- quantile: p10/p25/median/p75/p90로 box/range (violin 요청 시 box로 fallback)

Qt에 의존하지 않는다.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from matplotlib.patches import Patch

_GROUP_COLORS = (
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
)


def _truncate(label, limit: int = 40) -> str:
    text = str(label)
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


def _pct_factor(scale) -> float:
    text = str(scale or '0-1').replace(' ', '')
    return 1.0 if text in ('0-100', '0_100', 'percent', '%') else 100.0


def _group_column(df: pd.DataFrame, requested: str) -> str:
    for col in (requested, 'condition', 'dataset', 'sample'):
        if col and col in df.columns and df[col].notna().any():
            return col
    return ''


def _jitter(n: int, width: float) -> np.ndarray:
    if n <= 1:
        return np.zeros(n)
    # deterministic, symmetric jitter
    base = np.linspace(-0.5, 0.5, n)
    return base * width * 0.55


def _quantile_stats(sub: pd.DataFrame, value_col: str) -> Optional[dict]:
    if sub.empty:
        return None
    med = sub['median'].iloc[0] if 'median' in sub.columns else np.nan
    if pd.isna(med):
        return None
    q1 = sub['p25'].iloc[0] if 'p25' in sub.columns else med
    q3 = sub['p75'].iloc[0] if 'p75' in sub.columns else med
    lo = sub['p10'].iloc[0] if 'p10' in sub.columns else q1
    hi = sub['p90'].iloc[0] if 'p90' in sub.columns else q3
    return {
        'med': float(med),
        'q1': float(q1) if pd.notna(q1) else float(med),
        'q3': float(q3) if pd.notna(q3) else float(med),
        'whislo': float(lo) if pd.notna(lo) else float(med),
        'whishi': float(hi) if pd.notna(hi) else float(med),
        'fliers': [],
    }


def render_expression_distribution(fig, df: pd.DataFrame, params: Dict[str, Any]) -> dict:
    """Render violin/box/strip distribution panels into `fig`.

    Returns information about what was drawn (positions/labels/groups/warnings).
    The caller owns `fig.clear()` and layout.
    """
    params = dict(params or {})
    value_col = params.get('value_column', 'mean_expression')
    layout = str(params.get('layout') or '').lower()
    plot_type = str(params.get('plot_type') or 'violin').lower()
    group_by = _group_column(df, str(params.get('group_by') or 'condition'))
    min_n_cells = float(params.get('min_n_cells') or 0.0)
    min_pct = float(params.get('min_pct') or 0.0)
    pct_factor = _pct_factor(params.get('pct_scale', '0-1'))
    label_limit = int(params.get('label_limit') or 40)
    log_scale = bool(params.get('log_scale'))

    if df is None or df.empty:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No data.', ha='center', va='center',
                transform=ax.transAxes, color='#666666')
        return {'positions': [], 'labels': [], 'groups': [], 'warnings': []}

    work = df.copy()
    if min_n_cells > 0 and 'n_cells' in work.columns:
        work = work[pd.to_numeric(work['n_cells'], errors='coerce').fillna(0) >= min_n_cells]
    if min_pct > 0 and 'pct_expressing' in work.columns:
        pct = pd.to_numeric(work['pct_expressing'], errors='coerce').fillna(0) * pct_factor
        work = work[pct >= min_pct]
    if work.empty:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No data after filtering.', ha='center', va='center',
                transform=ax.transAxes, color='#666666')
        return {'positions': [], 'labels': [], 'groups': [], 'warnings': []}

    genes = list(params.get('genes') or [])
    if genes:
        wanted = {str(g).lower() for g in genes}
        mask = (work['gene_id'].astype(str).str.lower().isin(wanted)
                | work.get('gene_name', work['gene_id']).astype(str).str.lower().isin(wanted))
        work = work[mask]
    else:
        genes = list(dict.fromkeys(work['gene_id'].astype(str)))

    cell_types = list(params.get('cell_types') or [])
    if cell_types:
        wanted_ct = {str(c) for c in cell_types}
        work = work[work['cell_type'].astype(str).isin(wanted_ct)]
    else:
        cell_types = list(dict.fromkeys(work['cell_type'].astype(str)))

    if work.empty or not genes:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No data for the selected genes/cell types.',
                ha='center', va='center', transform=ax.transAxes, color='#666666')
        return {'positions': [], 'labels': [], 'groups': [], 'warnings': []}

    if not layout:
        layout = 'pseudobulk' if 'sample' in work.columns else 'quantile'

    groups: List[str] = []
    if group_by:
        groups = [str(g) for g in pd.unique(work[group_by].dropna())]
    if not groups:
        groups = ['All']

    if layout == 'quantile' and plot_type == 'violin':
        plot_type = 'box'
        warning = 'Quantile layout has no cell-level values; showing box/range.'
    else:
        warning = ''

    n_genes = len(genes)
    n_ct = len(cell_types)
    if n_ct == 0:
        return {'positions': [], 'labels': [], 'groups': groups, 'warnings': [warning]}

    axes = []
    for row in range(n_genes):
        ax = fig.add_subplot(n_genes, 1, row + 1)
        axes.append(ax)
        gene = genes[row]
        sub_gene = work[work['gene_id'].astype(str) == str(gene)]
        if sub_gene.empty:
            sub_gene = work[work.get('gene_name', work['gene_id']).astype(str) == str(gene)]
        gene_label = str(gene)
        if not sub_gene.empty and 'gene_name' in sub_gene.columns:
            name = str(sub_gene['gene_name'].iloc[0])
            if name and name.lower() != 'nan' and name != str(gene):
                gene_label = f"{name} ({gene})"
        ax.set_title(gene_label, fontsize=10, loc='left')

        base = np.arange(n_ct, dtype=float)
        n_groups = len(groups)
        width = 0.8 / max(n_groups, 1)
        handles = []
        for gi, group in enumerate(groups):
            color = _GROUP_COLORS[gi % len(_GROUP_COLORS)]
            handles.append(Patch(facecolor=color, alpha=0.65, label=group))
            offset = (gi - (n_groups - 1) / 2.0) * width
            for ci, ct in enumerate(cell_types):
                sub = sub_gene[sub_gene['cell_type'].astype(str) == str(ct)]
                if group_by and group != 'All':
                    sub = sub[sub[group_by].astype(str) == group]
                pos = base[ci] + offset
                if layout == 'quantile':
                    stats = _quantile_stats(sub, value_col)
                    if stats is not None:
                        bp = ax.bxp([stats], positions=[pos], widths=width * 0.85,
                                    patch_artist=True, showfliers=False,
                                    medianprops={'color': '#222222', 'linewidth': 1.0})
                        for box in bp['boxes']:
                            box.set_facecolor(color)
                            box.set_alpha(0.7)
                        for key in ('whiskers', 'caps'):
                            for artist in bp.get(key, []):
                                artist.set_color(color)
                    continue

                vals = pd.to_numeric(sub[value_col], errors='coerce').dropna().to_numpy()
                if vals.size == 0:
                    continue
                if plot_type in ('violin', 'box', 'box+points'):
                    if plot_type == 'violin' and vals.size >= 2:
                        parts = ax.violinplot(
                            [vals], positions=[pos], widths=width * 0.85,
                            showmeans=False, showextrema=False, showmedians=True)
                        for body in parts['bodies']:
                            body.set_facecolor(color)
                            body.set_edgecolor(color)
                            body.set_alpha(0.65)
                        medians = parts.get('cmedians')
                        if medians is not None:
                            medians.set_color('#222222')
                            medians.set_linewidth(1.0)
                    else:
                        bp = ax.boxplot(
                            [vals], positions=[pos], widths=width * 0.85,
                            patch_artist=True, showfliers=False,
                            medianprops={'color': '#222222', 'linewidth': 1.0})
                        for box in bp['boxes']:
                            box.set_facecolor(color)
                            box.set_alpha(0.7)
                        for key in ('whiskers', 'caps'):
                            for artist in bp.get(key, []):
                                artist.set_color(color)
                if plot_type in ('strip', 'box+points'):
                    jitter = _jitter(vals.size, width)
                    ax.scatter(np.full(vals.size, pos) + jitter, vals,
                               s=9, color=color, alpha=0.75, linewidths=0)

        ax.set_xticks(base)
        if row < n_genes - 1:
            # multi-gene panels share cell types; show labels only on the last panel
            ax.set_xticklabels([])
        else:
            ax.set_xticklabels([_truncate(ct, label_limit) for ct in cell_types])
            if n_ct > 8 or max(len(str(c)) for c in cell_types) > 12:
                for label in ax.get_xticklabels():
                    label.set_rotation(45)
                    label.set_horizontalalignment('right')
        ax.set_ylabel(str(params.get('ylabel') or 'Expression'))
        ax.grid(axis='y', color='#dddddd', linewidth=0.6, alpha=0.7)
        ax.set_axisbelow(True)
        if log_scale:
            ax.set_yscale('log')
        if n_ct:
            ax.set_xlim(-0.6, n_ct - 0.4)
        if handles and n_groups > 1:
            ax.legend(handles=handles, fontsize=7, frameon=False,
                      loc='upper right', ncol=min(n_groups, 3))

    if axes:
        axes[-1].set_xlabel(str(params.get('xlabel') or 'Cell type'))
    warnings = [warning] if warning else []
    return {
        'positions': base.tolist(),
        'labels': [str(c) for c in cell_types],
        'groups': groups,
        'warnings': warnings,
        'n_genes': n_genes,
    }
