"""DE/DA count summary — pure renderer (dialog + bundle 공유).

render_count_summary(ax, df, params) 는 CountSummaryDialog._do_plot 과 재현 번들 스크립트가
공유한다. 입력 df 는 long-format: 컬럼 dataset(라벨), log2fc, adj_pvalue (여러 데이터셋을
세로로 이어붙인 것). 데이터셋별 유의 up/down 개수를 0 기준 누적 막대로 그린다.
Qt 비의존. 반환값(counts_df)은 다이얼로그 Export 에서 재사용한다.
"""
import numpy as np
import pandas as pd


def render_count_summary(ax, df, params):
    """0 기준 up/down 막대를 ax에 그린다. counts_df(label/up/down/total) 반환.

    params: fdr_max(0.05), lfc_min(1.0), as_pct(bool), unit('genes'|'peaks'), order(list)
    """
    from matplotlib.ticker import FuncFormatter

    up_color, down_color = '#c0392b', '#2c6fbb'
    fdr_max = float(params.get('fdr_max', 0.05))
    lfc_min = float(params.get('lfc_min', 1.0))
    as_pct = bool(params.get('as_pct', False))
    unit = params.get('unit', 'genes')

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty or 'dataset' not in df.columns:
        ax.text(0.5, 0.5, "No datasets to plot.", ha='center', va='center',
                transform=ax.transAxes, color='#888888')
        return pd.DataFrame()

    order = params.get('order') or list(pd.unique(df['dataset']))
    lfc = pd.to_numeric(df.get('log2fc'), errors='coerce')
    padj = pd.to_numeric(df.get('adj_pvalue'), errors='coerce')
    df = df.assign(_lfc=lfc, _padj=padj)

    rows = []
    for label in order:
        sub = df[df['dataset'] == label]
        total = int(sub['_lfc'].notna().sum())
        sig = sub[(sub['_padj'] <= fdr_max) & (sub['_lfc'].abs() >= lfc_min)]
        up = int((sig['_lfc'] > 0).sum())
        down = int((sig['_lfc'] < 0).sum())
        rows.append({'label': label, 'up': up, 'down': down, 'total': total})
    counts = pd.DataFrame(rows)
    if counts.empty:
        ax.text(0.5, 0.5, "No datasets to plot.", ha='center', va='center',
                transform=ax.transAxes, color='#888888')
        return counts

    ups = counts['up'].astype(float).tolist()
    downs = counts['down'].astype(float).tolist()
    if as_pct:
        totals = [t if t else 1 for t in counts['total'].tolist()]
        ups = [100.0 * u / t for u, t in zip(ups, totals)]
        downs = [100.0 * d / t for d, t in zip(downs, totals)]

    x = list(range(len(counts)))
    ax.bar(x, ups, color=up_color, label='Up-regulated')
    ax.bar(x, [-d for d in downs], color=down_color, label='Down-regulated')
    ax.axhline(0, color='#333333', linewidth=0.8)

    for xi, yu, n in zip(x, ups, counts['up'].tolist()):
        if n > 0:
            ax.text(xi, yu, f"{n:,}", ha='center', va='bottom', fontsize=8)
    for xi, yd, n in zip(x, downs, counts['down'].tolist()):
        if n > 0:
            ax.text(xi, -yd, f"{n:,}", ha='center', va='top', fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(counts['label'].tolist(), rotation=30, ha='right', fontsize=8)

    if as_pct:
        ax.set_ylabel(f"% of {unit}")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{abs(v):.0f}"))
    else:
        ax.set_ylabel(f"Number of {unit}")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{abs(int(v)):,}"))

    ax.set_title(
        f"Significant {unit} (FDR ≤ {fdr_max:g}, |log2FC| ≥ {lfc_min:g})",
        fontsize=12, fontweight='bold')
    ax.legend(fontsize=8, loc='upper right')
    ax.margins(y=0.15)
    return counts
