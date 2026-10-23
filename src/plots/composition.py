"""Cell-type composition plot — pure renderer (dialog + bundle 공유).

`render_composition(ax, df, params)`는 CompositionDialog._do_plot과 재현 번들
스크립트가 공유한다. 두 가지 보기:

- `ratio`  : 세포 타입별 PropRatio(비율 차이)를 발산형 막대로. FDR에 따라 색/별표.
- `means`  : 세포 타입별 조건 평균 비율(`PropMean.*`)을 그룹 막대로.

Qt/StandardColumns에 의존하지 않도록 표준 컬럼명을 문자열 리터럴로 쓴다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_GROUP_COLORS = [
    '#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B3',
    '#937860', '#DA8BC3', '#8C8C8C', '#CCB974', '#64B5CD',
]

_RATIO_COLORS = {
    'up': '#D62728',
    'down': '#1F77B4',
    'ns': '#BDBDBD',
}


def fdr_stars(value) -> str:
    """FDR → 별표 (0.001/0.01/0.05)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ''
    if np.isnan(v):
        return ''
    if v <= 0.001:
        return '***'
    if v <= 0.01:
        return '**'
    if v <= 0.05:
        return '*'
    return 'ns'


def select_composition_rows(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """현재 보기에서 그려질(=export 될) 행만 골라 정렬/상위 N 적용."""
    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty or 'cell_type' not in df.columns:
        return df

    mode = params.get('mode', 'ratio')
    fdr_col = params.get('fdr_col', 'fdr')
    pvalue_col = params.get('pvalue_col', 'pvalue')
    stat_col = fdr_col if fdr_col in df.columns else (
        pvalue_col if pvalue_col in df.columns else None)

    if params.get('significant_only') and stat_col:
        thr = float(params.get('fdr_threshold', 0.05))
        df = df[pd.to_numeric(df[stat_col], errors='coerce') <= thr]

    if mode == 'means':
        means = [c for c in params.get('mean_columns', []) if c in df.columns]
        if not means:
            return df.iloc[0:0]
        df = df.dropna(subset=['cell_type'])
        sort_by = params.get('sort_by', 'max mean')
        if sort_by == 'cell type':
            df = df.sort_values('cell_type', ascending=True)
        elif stat_col and sort_by == 'FDR':
            df = df.sort_values(stat_col, ascending=True)
        else:
            df = df.assign(_max_mean=df[means].max(axis=1)).sort_values(
                '_max_mean', ascending=False).drop(columns=['_max_mean'])
    else:
        ratio_col = params.get('ratio_col', 'prop_ratio')
        if ratio_col not in df.columns:
            return df.iloc[0:0]
        df = df.dropna(subset=['cell_type', ratio_col])
        sort_by = params.get('sort_by', 'ratio')
        if sort_by == 'cell type':
            df = df.sort_values('cell_type', ascending=True)
        elif stat_col and sort_by == 'FDR':
            df = df.sort_values(stat_col, ascending=True)
        else:
            df = df.assign(_abs=pd.to_numeric(df[ratio_col], errors='coerce').abs())
            df = df.sort_values('_abs', ascending=False).drop(columns=['_abs'])

    top_n = int(params.get('top_n', 30) or 30)
    return df.head(top_n) if top_n > 0 else df


def render_composition(ax, df, params):
    """Composition plot을 ax에 그린다. 데이터가 없으면 안내 문구만 표시."""
    params = params or {}
    mode = params.get('mode', 'ratio')
    input_empty = df is None or len(df) == 0
    df = select_composition_rows(df, params)

    if df.empty:
        msg = ('No data to display\nAdjust filters' if input_empty
               else 'No valid data to display\n(check PropMean/PropRatio/FDR columns)')
        ax.text(0.5, 0.5, msg, ha='center', va='center', transform=ax.transAxes)
        return None

    fdr_col = params.get('fdr_col', 'fdr')
    fdr_threshold = float(params.get('fdr_threshold', 0.05))
    fdr_values = (pd.to_numeric(df[fdr_col], errors='coerce')
                  if fdr_col in df.columns else pd.Series(np.nan, index=df.index))

    if mode == 'means':
        means = [c for c in params.get('mean_columns', []) if c in df.columns]
        conditions = list(params.get('conditions', [])) or means
        if not means:
            ax.text(0.5, 0.5, 'No PropMean.<condition> columns found.',
                    ha='center', va='center', transform=ax.transAxes)
            return None

        n = len(df)
        x = np.arange(n)
        width = 0.8 / len(means)
        percent = bool(params.get('percent', True))
        for i, (col, label) in enumerate(zip(means, conditions)):
            vals = pd.to_numeric(df[col], errors='coerce').fillna(0.0).to_numpy(dtype=float)
            if percent:
                vals = vals * 100.0
            ax.bar(x + (i - (len(means) - 1) / 2) * width, vals, width,
                   label=str(label), color=_GROUP_COLORS[i % len(_GROUP_COLORS)],
                   edgecolor='white', linewidth=0.4)

        ax.set_xticks(x)
        labels = [str(v) for v in df['cell_type']]
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel('Mean proportion (%)' if percent else 'Mean proportion')
        ax.set_xlabel(params.get('xlabel', 'Cell type'))
        if len(means) > 1:
            ax.legend(frameon=False, fontsize=8, title='Condition')
        if params.get('show_values', False):
            ax.margins(y=0.15)
        return None

    # ratio mode
    ratio = pd.to_numeric(df[params.get('ratio_col', 'prop_ratio')],
                          errors='coerce').fillna(0.0).to_numpy(dtype=float)
    n = len(df)
    y = np.arange(n)

    colors = []
    for val, fdr in zip(ratio, fdr_values.to_numpy()):
        if pd.isna(fdr) or fdr > fdr_threshold:
            colors.append(_RATIO_COLORS['ns'])
        elif val >= 0:
            colors.append(_RATIO_COLORS['up'])
        else:
            colors.append(_RATIO_COLORS['down'])

    ax.barh(y, ratio, color=colors, edgecolor='white', linewidth=0.4)
    ax.axvline(0, color='#555555', linewidth=0.8)

    ax.set_yticks(y)
    ax.set_yticklabels([str(v) for v in df['cell_type']])
    ax.set_xlabel(params.get('xlabel', 'PropRatio (difference in proportion)'))
    ax.set_ylabel('')
    ax.invert_yaxis()

    if params.get('show_values', True):
        span = max(np.nanmax(np.abs(ratio)) if n else 0.0, 1e-9)
        for yi, val, fdr in zip(y, ratio, fdr_values.to_numpy()):
            stars = fdr_stars(fdr)
            offset = span * 0.02 * (1 if val >= 0 else -1)
            ha = 'left' if val >= 0 else 'right'
            ax.text(val + offset, yi, stars, va='center', ha=ha, fontsize=8,
                    color='#333333')

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color=_RATIO_COLORS['up'], label='Increased (FDR ≤ threshold)'),
        Patch(color=_RATIO_COLORS['down'], label='Decreased (FDR ≤ threshold)'),
        Patch(color=_RATIO_COLORS['ns'], label='Not significant'),
    ], frameon=False, fontsize=7, loc='lower right')
    ax.margins(x=0.12)
    return None
