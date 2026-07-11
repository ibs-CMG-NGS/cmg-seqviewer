"""Gene expression grouped bar + scatter — pure renderer (dialog + bundle 공유).

render_gene_expression_bar(ax, df, params) 는 GeneExpressionBarDialog._do_plot 과
재현 번들 스크립트가 공유한다. 유전자별 그룹 평균 막대 + (옵션) 개별점 지터 + 유의성 별표.
Qt 비의존 — 유전자 선택/정렬/통계 검정을 함수 내부에 자기완결로 포함한다.
"""
import numpy as np
import pandas as pd


def render_gene_expression_bar(ax, df, params):
    """그룹 막대 차트를 ax에 그린다. 선택된 df 반환. 데이터 없으면 None.

    params:
        gene_col, sample_groups({group: [cols]}), group_colors({group: hex}),
        max_genes, sort_by, error_bars('SEM'|'SD'|'None'), show_points(bool),
        log_y(bool), show_significance(bool), reference_group, test, name_hint, title
    """
    gene_col = params.get('gene_col')
    sample_groups = params.get('sample_groups') or {}
    group_colors = params.get('group_colors') or {}
    max_genes = int(params.get('max_genes', 15))
    sort_by = params.get('sort_by', 'Original (input order)')
    err_mode = params.get('error_bars', 'SEM')
    show_points = bool(params.get('show_points', True))
    is_log = bool(params.get('log_y', False))
    show_sig = bool(params.get('show_significance', False))
    ref_name = params.get('reference_group')
    test = params.get('test', 't-test (Welch)')
    name_hint = params.get('name_hint', '')

    def _p_to_stars(p):
        if p is None or (isinstance(p, float) and np.isnan(p)):
            return ''
        if p > 0.05:
            return 'ns'
        if p <= 1e-4:
            return '****'
        if p <= 1e-3:
            return '***'
        if p <= 1e-2:
            return '**'
        return '*'

    def _vals(row, cols):
        return pd.to_numeric(pd.Series([row[c] for c in cols]),
                             errors='coerce').dropna().to_numpy()

    def _pvalue(a, b):
        if a.size < 2 or b.size < 2:
            return float('nan')
        try:
            from scipy import stats
            if str(test).startswith('Mann'):
                _, p = stats.mannwhitneyu(a, b, alternative='two-sided')
            else:
                _, p = stats.ttest_ind(a, b, equal_var=False)
            return float(p)
        except Exception:
            return float('nan')

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty or gene_col is None or not sample_groups:
        ax.text(0.5, 0.5, "No sample columns / groups.", ha='center', va='center',
                fontsize=13, transform=ax.transAxes)
        ax.axis('off')
        return None

    # ── 유전자 선택/정렬 ──
    df = df[df[gene_col].notna()].drop_duplicates(subset=gene_col, keep='first')
    all_cols = [c for cols in sample_groups.values() for c in cols]
    df['_row_mean'] = df[all_cols].mean(axis=1, numeric_only=True) if all_cols else 0.0
    if sort_by == 'Mean expression (desc)':
        df = df.sort_values('_row_mean', ascending=False)
    elif sort_by == '|log2FC| (desc)' and 'log2fc' in df.columns:
        df = df.assign(_abs=pd.to_numeric(df['log2fc'], errors='coerce').abs())
        df = df.sort_values('_abs', ascending=False).drop(columns='_abs')
    elif sort_by == 'Symbol (A-Z)':
        df = df.sort_values(gene_col, ascending=True,
                            key=lambda s: s.astype(str).str.lower())
    df = df.head(max_genes).drop(columns='_row_mean', errors='ignore')
    if df.empty:
        ax.text(0.5, 0.5, "No genes to display.", ha='center', va='center',
                fontsize=13, transform=ax.transAxes)
        ax.axis('off')
        return None

    genes = df[gene_col].astype(str).to_list()
    group_items = list(sample_groups.items())
    n_genes, n_groups = len(genes), len(group_items)
    x = np.arange(n_genes)
    bar_width = 0.8 / max(1, n_groups)
    rng = np.random.default_rng(0)

    import matplotlib
    cmap = matplotlib.colormaps.get_cmap('tab10')
    bar_center, bar_top, global_top = {}, {}, 0.0

    for gi, (gname, cols) in enumerate(group_items):
        offset = (gi - (n_groups - 1) / 2.0) * bar_width
        centers = x + offset
        color = group_colors.get(gname) or matplotlib.colors.to_hex(cmap(gi % 10))
        means, errs, tops = [], [], []
        for _, row in df.iterrows():
            vals = _vals(row, cols)
            if vals.size == 0:
                means.append(np.nan); errs.append(0.0); tops.append(0.0); continue
            m = float(np.mean(vals))
            if err_mode == 'SD':
                e = float(np.std(vals, ddof=1)) if vals.size > 1 else 0.0
            elif err_mode == 'SEM':
                e = float(np.std(vals, ddof=1) / np.sqrt(vals.size)) if vals.size > 1 else 0.0
            else:
                e = 0.0
            means.append(m); errs.append(e); tops.append(max(m + e, float(np.max(vals))))

        yerr = errs if err_mode != 'None' else None
        ax.bar(centers, means, width=bar_width * 0.92, color=color,
               edgecolor='black', linewidth=0.5, label=gname,
               yerr=yerr, capsize=3, error_kw={'elinewidth': 0.8})

        for ci in range(n_genes):
            bar_center[(gi, ci)] = centers[ci]
            bar_top[(gi, ci)] = tops[ci]
            global_top = max(global_top, tops[ci])

        if show_points:
            for ci, (_, row) in enumerate(df.iterrows()):
                vals = _vals(row, cols)
                if vals.size == 0:
                    continue
                jitter = (rng.random(vals.size) - 0.5) * bar_width * 0.5
                ax.scatter(np.full(vals.size, centers[ci]) + jitter, vals,
                           s=18, color='black', alpha=0.7, zorder=3,
                           edgecolors='white', linewidths=0.3)

    if show_sig and n_groups >= 2 and ref_name in sample_groups:
        ref_idx = list(sample_groups.keys()).index(ref_name)
        ref_cols = sample_groups[ref_name]
        y_off = (global_top * 0.04) if global_top > 0 else 0.5
        for ci, (_, row) in enumerate(df.iterrows()):
            ref_vals = _vals(row, ref_cols)
            for gi, (gname, cols) in enumerate(group_items):
                if gi == ref_idx:
                    continue
                star = _p_to_stars(_pvalue(_vals(row, cols), ref_vals))
                if not star:
                    continue
                cx, top = bar_center[(gi, ci)], bar_top[(gi, ci)]
                ty = top * 1.08 if is_log else top + y_off
                ax.text(cx, ty, star, ha='center', va='bottom', color='black')
        if not is_log and global_top > 0:
            ax.set_ylim(top=global_top * 1.25)

    ax.set_xticks(x)
    ax.set_xticklabels(genes, rotation=45, ha='right')
    ax.set_ylabel("Expression (raw count)", fontweight='bold')
    if params.get('title'):
        ax.set_title(params['title'], fontweight='bold')
    elif len(genes) == 1:
        ax.set_title(f"{genes[0]} — Expression by Group", fontweight='bold')
    else:
        ax.set_title(name_hint and f"{name_hint} — Expression by Group"
                     or "Gene Expression by Group", fontweight='bold')
    if is_log:
        ax.set_yscale('log')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.legend(title="Group")
    return df
