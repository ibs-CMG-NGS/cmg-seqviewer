"""GO/KEGG multi-dataset comparison dot plot — pure renderer (dialog + bundle 공유).

render_go_comparison_dot(fig, df, params) 는 GOComparisonDotPlotDialog._do_plot 과
재현 번들 스크립트가 공유한다. 입력은 wide-format 비교 DataFrame(_compare_go_terms 산출:
term_id/description[/ontology] + {safe}_fe/{safe}_fdr/{safe}_gene_count 컬럼들).
함수 내부에서 long-format으로 재구성 → bubble plot. Qt 비의존.
"""
import numpy as np
import pandas as pd


def _build_long_df(df, dataset_names, safe_names, display_names):
    """wide → long: 데이터셋별 fe/fdr/gene_count 를 세로로 편다."""
    id_cols = ['term_id', 'description']
    if 'ontology' in df.columns:
        id_cols.append('ontology')
    if not dataset_names:
        return pd.DataFrame()
    records = []
    for ds_name, safe, disp in zip(dataset_names, safe_names, display_names):
        fe_col, fdr_col, gc_col = f"{safe}_fe", f"{safe}_fdr", f"{safe}_gene_count"
        tmp = df[id_cols].copy()
        tmp['dataset'] = ds_name
        tmp['display_name'] = disp
        tmp['fe'] = pd.to_numeric(df[fe_col] if fe_col in df.columns else None, errors='coerce')
        tmp['fdr'] = pd.to_numeric(df[fdr_col] if fdr_col in df.columns else None, errors='coerce')
        tmp['gene_count'] = pd.to_numeric(df[gc_col] if gc_col in df.columns else None, errors='coerce')
        records.append(tmp)
    return pd.concat(records, ignore_index=True) if records else pd.DataFrame()


def render_go_comparison_dot(fig, df, params):
    """비교 dot plot을 fig에 그린다. 필터된 long_df 반환. 데이터 없으면 None.

    params: dataset_names, safe_names, display_names, top_n, sort_by,
            min_datasets, size_mode, transpose, palette, color_min, color_max,
            xlabel, ylabel
    """
    from matplotlib.lines import Line2D

    df = df.copy() if df is not None else pd.DataFrame()
    dataset_names = params.get('dataset_names', [])
    safe_names = params.get('safe_names', [])
    display_names = params.get('display_names', []) or [str(n) for n in dataset_names]

    long_df = _build_long_df(df, dataset_names, safe_names, display_names)

    # min datasets 필터
    min_ds = int(params.get('min_datasets', 1))
    if not long_df.empty and min_ds > 1:
        fe_count = long_df.groupby('term_id')['fe'].apply(lambda x: x.notna().sum())
        valid = fe_count[fe_count >= min_ds].index
        long_df = long_df[long_df['term_id'].isin(valid)]

    if long_df.empty:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No data to display\nAdjust filters',
                ha='center', va='center', fontsize=14)
        return None

    # 정렬 + top N + y 순위
    sort_by = params.get('sort_by', 'Average FE (desc)')
    if sort_by == 'Average FE (desc)':
        rank = long_df.groupby('term_id')['fe'].mean().sort_values(ascending=False)
    else:
        rank = long_df.groupby('term_id')['fdr'].mean().sort_values(ascending=True)
    top_n = int(params.get('top_n', 20))
    top_terms = rank.head(top_n).index
    long_df = long_df[long_df['term_id'].isin(top_terms)].copy()
    term_order = list(rank[rank.index.isin(top_terms)].index)
    long_df['_y_rank'] = long_df['term_id'].map(
        {t: i for i, t in enumerate(reversed(term_order))})

    ax = fig.add_subplot(111)
    transpose = bool(params.get('transpose', False))
    ds_order = dataset_names
    disp_order = display_names
    ds_idx = {ds: i for i, ds in enumerate(ds_order)}
    long_df['_ds_idx'] = long_df['dataset'].map(ds_idx)

    desc_map = (df.set_index('term_id')['description'].to_dict()
                if 'description' in df.columns else {})

    y_ranks = sorted(long_df['_y_rank'].dropna().unique())
    term_by_rank = {}
    for _, row in long_df.drop_duplicates('_y_rank').iterrows():
        term_by_rank[row['_y_rank']] = row['term_id']
    term_labels = []
    for r in y_ranks:
        tid = term_by_rank.get(r, '')
        label = str(desc_map.get(tid, tid))
        if len(label) > 55:
            label = label[:52] + '...'
        term_labels.append(label)

    if transpose:
        long_df['_x'] = long_df['_y_rank']
        long_df['_y'] = long_df['_ds_idx']
        x_ticks, x_labels = y_ranks, term_labels
        y_ticks, y_labels = list(range(len(disp_order))), disp_order
        x_rot, x_ha, y_fs = 40, 'right', 10
    else:
        long_df['_x'] = long_df['_ds_idx']
        long_df['_y'] = long_df['_y_rank']
        x_ticks, x_labels = list(range(len(disp_order))), disp_order
        y_ticks = y_ranks
        n_terms = len(y_ranks)
        y_fs = 9 if n_terms <= 15 else (8 if n_terms <= 25 else 7)
        y_labels = term_labels
        x_rot, x_ha = 35, 'right'

    size_mode = params.get('size_mode', 'Fold Enrichment')
    cmap = params.get('palette', 'YlOrRd')
    vmin = float(params.get('color_min', 0.0))
    vmax = float(params.get('color_max', 5.0))
    if vmin >= vmax:
        vmax = vmin + 1.0

    neg_log_fdr = -np.log10(long_df['fdr'].clip(lower=1e-300))

    size_norm = {
        "Fold Enrichment": (20.0, [(2.0, "2×"), (5.0, "5×"), (15.0, "≥15×")]),
        "Gene Count": (100.0, [(10, "10 genes"), (30, "30 genes"), (80, "≥80 genes")]),
    }
    s_min, s_max = 40, 400
    if size_mode == 'Fold Enrichment':
        raw_size = pd.to_numeric(long_df['fe'], errors='coerce').fillna(0)
    else:
        raw_size = pd.to_numeric(long_df['gene_count'], errors='coerce').fillna(0)
    if size_mode in size_norm:
        norm_max, size_rep = size_norm[size_mode]
        sizes = s_min + np.clip(raw_size / norm_max, 0, 1) * (s_max - s_min)
    else:
        norm_max, size_rep = None, None
        sizes = pd.Series(150.0, index=raw_size.index)

    has_fe = long_df['fe'].notna()
    has_fdr = long_df['fdr'].notna()

    mask_full = has_fe & has_fdr
    if mask_full.any():
        sc = ax.scatter(long_df.loc[mask_full, '_x'], long_df.loc[mask_full, '_y'],
                        s=sizes[mask_full], c=neg_log_fdr[mask_full],
                        cmap=cmap, vmin=vmin, vmax=vmax, alpha=0.85,
                        edgecolors='black', linewidth=0.4, zorder=3)
    else:
        sc = ax.scatter([], [], c=[], cmap=cmap, vmin=vmin, vmax=vmax)

    mask_no_fdr = has_fe & ~has_fdr
    if mask_no_fdr.any():
        ax.scatter(long_df.loc[mask_no_fdr, '_x'], long_df.loc[mask_no_fdr, '_y'],
                   s=sizes[mask_no_fdr], color='lightgray', edgecolors='gray',
                   linewidth=0.4, alpha=0.6, zorder=2)

    mask_absent = ~has_fe
    if mask_absent.any():
        ax.scatter(long_df.loc[mask_absent, '_x'], long_df.loc[mask_absent, '_y'],
                   s=40, facecolors='none', edgecolors='#cccccc',
                   linewidth=0.6, alpha=0.5, zorder=1)

    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_labels, rotation=x_rot, ha=x_ha, fontsize=9)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, fontsize=y_fs)
    ax.set_xlabel(params.get('xlabel') or ('GO/KEGG Terms' if transpose else 'Dataset'),
                  fontsize=11, fontweight='bold')
    ax.set_ylabel(params.get('ylabel') or ('Dataset' if transpose else 'GO/KEGG Terms'),
                  fontsize=11, fontweight='bold')
    ax.set_title("GO/KEGG Term Comparison", fontsize=13, fontweight='bold')
    ax.grid(axis='both', alpha=0.2, linestyle='--')

    if transpose:
        ax.set_xlim(min(y_ranks) - 0.6, max(y_ranks) + 0.6)
        ax.set_ylim(-0.6, len(disp_order) - 0.4)
    else:
        ax.set_xlim(-0.6, len(disp_order) - 0.4)
        if y_ranks:
            ax.set_ylim(min(y_ranks) - 0.6, max(y_ranks) + 0.6)

    try:
        cbar = fig.colorbar(sc, ax=ax, shrink=0.5, pad=0.02, anchor=(0, 1.0))
        cbar.set_label('-log10(FDR)', fontsize=10)
    except Exception:
        pass

    if size_rep is not None and norm_max is not None:
        leg_fs = 8

        def _ms(v):
            s = s_min + np.clip(v / norm_max, 0, 1) * (s_max - s_min)
            return 2.0 * np.sqrt(s / np.pi)

        max_diam = max(_ms(v) for v, _ in size_rep)
        elements = [Line2D([0], [0], marker='o', color='none',
                           markerfacecolor='#808080', markeredgecolor='#333333',
                           markeredgewidth=0.8, markersize=_ms(v), label=lbl)
                    for v, lbl in size_rep]
        leg = ax.legend(handles=elements, title=size_mode, loc='upper left',
                        fontsize=leg_fs, title_fontsize=leg_fs,
                        labelspacing=max_diam / leg_fs + 0.5,
                        handlelength=0, handletextpad=1.2, borderpad=0.9,
                        framealpha=0.95, edgecolor='#bbbbbb', fancybox=False,
                        bbox_to_anchor=(1.02, 0.30))
        leg.get_title().set_fontweight('bold')

    try:
        fig.tight_layout(rect=(0, 0, 0.82, 1))
    except Exception:
        if transpose:
            fig.subplots_adjust(left=0.12, right=0.82, bottom=0.30)
        else:
            fig.subplots_adjust(left=0.35, right=0.82, bottom=0.15)

    return long_df
