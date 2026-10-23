"""Gene × cell-type expression dot plot — pure renderer (dialog + bundle 공유).

`render_expression_dot(ax, long_df, params)`는 **long-format** 표를 받는다:

    gene_id | gene_name | cell_type | mean_expression | pct_expressing | n_cells

- x = cell type, y = gene (default is transposed: x = gene, y = cell type so
  long cell-type labels fit on the y-axis)
- dot size = pct_expressing (0–100)
- dot color = mean_expression
- n_cells / pct threshold 미만은 회색으로 표시

wide mean/pct 행렬은 `build_expression_long()`으로 long 표를 만든 뒤 전달한다.
Qt에 의존하지 않는다.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def _truncate(label, limit: int = 32) -> str:
    text = str(label)
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


def _pct_scale_factor(scale) -> float:
    """저장된 pct 값의 스케일 → 0–100로 변환하는 배율.

    `0-1`이면 100을 곱하고, 이미 `0-100`이면 그대로 둔다.
    """
    text = str(scale or '0-1').replace(' ', '')
    if text in ('0-100', '0_100', 'percent', '%'):
        return 1.0
    return 100.0


def _resolve_gene_rows(df: pd.DataFrame, genes: List[str],
                       gene_id_col: str, gene_name_col: str) -> pd.DataFrame:
    if not genes:
        return df.iloc[0:0]
    ids = df[gene_id_col].astype(str)
    names = (df[gene_name_col].astype(str)
             if gene_name_col and gene_name_col in df.columns else ids)
    wanted_lower = {str(g).strip().lower() for g in genes if str(g).strip()}
    mask = ids.str.lower().isin(wanted_lower) | names.str.lower().isin(wanted_lower)
    return df[mask]


def build_expression_long(
    wide_df: pd.DataFrame,
    pct_df: Optional[pd.DataFrame] = None,
    genes: Optional[List[str]] = None,
    gene_id_col: str = 'gene_id',
    gene_name_col: str = 'gene_name',
    cell_types: Optional[List[str]] = None,
    n_cells: Optional[Dict[str, Any]] = None,
    pct_scale='0-1',
    min_pct: float = 0.0,
    min_n_cells: float = 0.0,
    drop_zero: bool = True,
) -> pd.DataFrame:
    """wide mean(+pct) 행렬에서 선택 유전자 × 세포타입 long 표를 만든다."""
    if wide_df is None or wide_df.empty or gene_id_col not in wide_df.columns:
        return pd.DataFrame(columns=['gene_id', 'gene_name', 'cell_type',
                                     'mean_expression', 'pct_expressing',
                                     'n_cells', 'pct_display', 'dimmed'])
    df = _resolve_gene_rows(wide_df, list(genes or []), gene_id_col, gene_name_col)
    if df.empty:
        return pd.DataFrame(columns=['gene_id', 'gene_name', 'cell_type',
                                     'mean_expression', 'pct_expressing',
                                     'n_cells', 'pct_display', 'dimmed'])

    cell_types = [c for c in (cell_types or []) if c in df.columns]
    pct_lookup = None
    if pct_df is not None and gene_id_col in pct_df.columns:
        pct_lookup = pct_df.drop_duplicates(subset=[gene_id_col]).set_index(gene_id_col)

    n_cells = dict(n_cells or {})
    factor = _pct_scale_factor(pct_scale)
    rows = []
    for _, row in df.iterrows():
        gid = str(row[gene_id_col])
        gname = str(row[gene_name_col]) if gene_name_col in df.columns else gid
        for ct in cell_types:
            try:
                mean = float(row[ct])
            except (TypeError, ValueError):
                continue
            if pd.isna(mean):
                continue
            pct = np.nan
            if pct_lookup is not None and ct in pct_lookup.columns and gid in pct_lookup.index:
                try:
                    pct = float(pct_lookup.at[gid, ct])
                except (TypeError, ValueError):
                    pct = np.nan
            try:
                n = float(n_cells.get(ct, np.nan))
            except (TypeError, ValueError):
                n = np.nan
            rows.append({
                'gene_id': gid, 'gene_name': gname, 'cell_type': ct,
                'mean_expression': mean, 'pct_expressing': pct, 'n_cells': n,
            })

    long = pd.DataFrame(rows)
    if long.empty:
        return long
    long['pct_display'] = pd.to_numeric(long['pct_expressing'], errors='coerce') * factor
    if long['pct_display'].isna().all():
        long['pct_display'] = 50.0
    elif drop_zero:
        # long export와 동일하게 n_expressing=0(=pct 0) 행은 표시하지 않는다.
        long = long[long['pct_display'] > 0].copy()
        if long.empty:
            return long
    low_n = long['n_cells'].notna() & (long['n_cells'] < float(min_n_cells or 0.0))
    low_pct = long['pct_display'].notna() & (long['pct_display'] < float(min_pct or 0.0))
    long['dimmed'] = low_n | low_pct
    return long


def render_expression_dot(ax, df, params):
    """Long-format expression 표를 dot plot으로 그린다. hover용 info 반환."""
    params = params or {}
    df = df.copy() if df is not None else pd.DataFrame()
    required = {'gene_name', 'cell_type', 'mean_expression'}
    if df.empty or not required.issubset(df.columns):
        ax.text(0.5, 0.5, 'No expression data to display\n(select genes and cell types)',
                ha='center', va='center', transform=ax.transAxes, color='#666666')
        return {'points': []}

    cmap = params.get('cmap', 'viridis')
    label_limit = int(params.get('label_limit', 32) or 32)
    top_n = int(params.get('top_cell_types', 0) or 0)

    if top_n > 0:
        scores = df.groupby('cell_type')['mean_expression'].mean().sort_values(ascending=False)
        keep = list(scores.index[:top_n])
        df = df[df['cell_type'].isin(keep)]

    cell_types = list(dict.fromkeys(df['cell_type'].astype(str).tolist()))
    genes = list(dict.fromkeys(df['gene_name'].astype(str).tolist()))
    if not cell_types or not genes:
        ax.text(0.5, 0.5, 'No data after filtering.',
                ha='center', va='center', transform=ax.transAxes, color='#666666')
        return {'points': []}

    ct_index = {c: i for i, c in enumerate(cell_types)}
    gene_index = {g: i for i, g in enumerate(genes)}
    # 기본은 cell type을 y축에 두어 긴 라벨을 잘리지 않게 한다 (scRNA dot plot 관례).
    transpose = bool(params.get('transpose', True))
    if transpose:
        x = df['gene_name'].astype(str).map(gene_index).to_numpy(dtype=float)
        y = df['cell_type'].astype(str).map(ct_index).to_numpy(dtype=float)
    else:
        x = df['cell_type'].astype(str).map(ct_index).to_numpy(dtype=float)
        y = df['gene_name'].astype(str).map(gene_index).to_numpy(dtype=float)

    size_min, size_max = 12.0, 260.0
    if 'pct_display' in df.columns:
        pct_vals = (pd.to_numeric(df['pct_display'], errors='coerce')
                    .fillna(0.0).clip(lower=0.0, upper=100.0).to_numpy(dtype=float))
    else:
        pct_vals = np.full(len(df), 50.0, dtype=float)
    sizes = size_min + (pct_vals / 100.0) * (size_max - size_min)
    means = pd.to_numeric(df['mean_expression'], errors='coerce').to_numpy(dtype=float)
    finite = means[np.isfinite(means)]
    vmin = float(finite.min()) if finite.size else 0.0
    vmax = float(finite.max()) if finite.size else 1.0
    if vmin == vmax:
        vmax = vmin + 1e-9

    dimmed = (df['dimmed'].to_numpy(dtype=bool)
              if 'dimmed' in df.columns else np.zeros(len(df), dtype=bool))
    sc = ax.scatter(x[~dimmed], y[~dimmed], s=sizes[~dimmed], c=means[~dimmed],
                    cmap=cmap, vmin=vmin, vmax=vmax, edgecolors='white',
                    linewidths=0.3, zorder=3)
    if dimmed.any():
        ax.scatter(x[dimmed], y[dimmed], s=sizes[dimmed], c='#cccccc',
                   edgecolors='white', linewidths=0.2, alpha=0.6, zorder=2)

    if transpose:
        ax.set_xticks(range(len(genes)))
        ax.set_xticklabels(genes, fontsize=8,
                           rotation=45 if len(genes) > 12 else 0,
                           ha='right' if len(genes) > 12 else 'center')
        ax.set_yticks(range(len(cell_types)))
        ax.set_yticklabels([_truncate(c, label_limit) for c in cell_types],
                           fontsize=7)
        ax.set_xlabel(params.get('xlabel', 'Gene'))
        ax.set_ylabel(params.get('ylabel', 'Cell type'))
        # 왼쪽 라벨 길이에 맞춰 여백을 자동 확보한다.
        max_len = max((len(str(c)) for c in cell_types), default=0)
        left = min(0.55, max(0.12, 0.006 * max_len + 0.06))
        ax.figure.subplots_adjust(left=left, right=0.86, bottom=0.12, top=0.95)
    else:
        ax.set_xticks(range(len(cell_types)))
        ax.set_xticklabels([_truncate(c, label_limit) for c in cell_types],
                           rotation=60, ha='right', fontsize=7)
        ax.set_yticks(range(len(genes)))
        ax.set_yticklabels(genes, fontsize=8)
        ax.set_xlabel(params.get('xlabel', 'Cell type'))
        ax.set_ylabel(params.get('ylabel', 'Gene'))
        max_len = max((len(str(c)) for c in cell_types), default=0)
        bottom = min(0.45, max(0.18, 0.006 * max_len + 0.08))
        ax.figure.subplots_adjust(left=0.10, right=0.86, bottom=bottom, top=0.95)
    ax.grid(True, color='#eeeeee', linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.025, pad=0.01)
    cbar.set_label('Mean expression')

    handles = []
    for val in (10, 50, 100):
        size = 12.0 + (val / 100.0) * (260.0 - 12.0)
        handles.append(ax.scatter([], [], s=size, c='#777777', edgecolors='white'))
    ax.legend(handles, ['10%', '50%', '100%'], title='% expressing',
              frameon=False, fontsize=7, labelspacing=1.0,
              loc='upper left', bbox_to_anchor=(1.02, 1.0))

    points = df.to_dict('records')
    return {
        'points': points,
        'cell_types': cell_types,
        'genes': genes,
        'x': x.tolist(),
        'y': y.tolist(),
        'mean': means.tolist(),
        'pct': pct_vals.tolist(),
        'dimmed': dimmed.tolist(),
    }
