"""Meta volcano — pure renderer (dialog + bundle 공유).

render_meta_volcano(ax, df, params) 는 MetaVolcanoDialog._do_plot 과 재현 번들 스크립트가
공유한다. X = mean/pooled log2FC, Y = -log10(meta p-value). concordant sig 유전자는
up(빨강)/down(파랑), discordant sig 는 주황, 나머지는 회색. 상위 N개는 adjustText 라벨.
Qt 비의존 — 색상/라벨 상수를 함수 내부에 내장한다. 반환값 (d, label_col) 은 다이얼로그
hover/export 에서 재사용한다.
"""
import numpy as np
import pandas as pd


def _found_in_num(v):
    try:
        return int(str(v).split('/')[0])
    except (ValueError, TypeError):
        return 0


def render_meta_volcano(ax, df, params):
    """Meta volcano를 ax에 그린다. (prepared_df, label_col) 반환.

    params: p_col, p_source_name, x_col, p_threshold, lfc_threshold,
            min_k, top_n, label_size
    """
    c_up, c_down, c_discord, c_ns = '#c0392b', '#2c6fbb', '#e08a1e', '#c8c8c8'
    x_labels = {
        'meta_effect_log2fc': 'Pooled log2 fold change (random-effects)',
        'meta_log2fc_mean': 'Mean log2 fold change',
        'meta_log2fe_mean': 'Mean log2 fold enrichment',
    }

    p_col = params.get('p_col')
    x_col = params.get('x_col')
    p_src_name = params.get('p_source_name', 'Fisher')
    p_thr = float(params.get('p_threshold', 0.05))
    lfc_thr = float(params.get('lfc_threshold', 1.0))
    min_k = int(params.get('min_k', 2))
    top_n = int(params.get('top_n', 10))
    lbl_size = int(params.get('label_size', 9))

    df = df.copy() if df is not None else pd.DataFrame()
    if not x_col or not p_col or x_col not in df.columns or p_col not in df.columns:
        ax.text(0.5, 0.5,
                "No meta-analysis columns found.\n"
                "Run Compare → Statistics Filtering on 2+ datasets first.",
                ha='center', va='center', transform=ax.transAxes, color='#888888')
        return pd.DataFrame(), None

    d = df.copy()
    d['_x'] = pd.to_numeric(d[x_col], errors='coerce')
    d['_p'] = pd.to_numeric(d[p_col], errors='coerce')
    d = d[d['_x'].notna() & d['_p'].notna()].copy()
    if 'meta_found_in' in d.columns:
        d['_k'] = d['meta_found_in'].map(_found_in_num)
        d = d[d['_k'] >= min_k]
    d['_p'] = d['_p'].clip(lower=1e-300, upper=1.0)
    d['_y'] = -np.log10(d['_p'])

    if d.empty:
        ax.text(0.5, 0.5, "No genes pass the 'found in ≥ N datasets' filter.",
                ha='center', va='center', transform=ax.transAxes, color='#888888')
        return d, None

    sig = (d['_p'] <= p_thr) & (d['_x'].abs() >= lfc_thr)
    direction = d.get('meta_direction', pd.Series('', index=d.index)).astype(str)
    concord = direction.eq('concordant')

    cat_up = sig & concord & (d['_x'] > 0)
    cat_down = sig & concord & (d['_x'] < 0)
    cat_disc = sig & ~concord
    cat_ns = ~sig

    for mask, color, label in (
        (cat_ns, c_ns, 'n.s.'),
        (cat_disc, c_discord, 'Sig. discordant'),
        (cat_up, c_up, 'Sig. up (concordant)'),
        (cat_down, c_down, 'Sig. down (concordant)'),
    ):
        if mask.any():
            ax.scatter(d.loc[mask, '_x'], d.loc[mask, '_y'], s=16,
                       c=color, label=label, edgecolors='none', alpha=0.8)

    ax.axhline(-np.log10(p_thr), color='#888888', ls='--', lw=0.7)
    if lfc_thr > 0:
        ax.axvline(lfc_thr, color='#888888', ls='--', lw=0.7)
        ax.axvline(-lfc_thr, color='#888888', ls='--', lw=0.7)
    ax.axvline(0, color='#cccccc', lw=0.6)

    label_col = next((c for c in ('symbol', 'gene_id', 'description', 'term_id')
                      if c in d.columns), None)

    if top_n > 0 and label_col:
        top = d[sig].nsmallest(top_n, '_p')
        texts = []
        for _, r in top.iterrows():
            name = str(r[label_col])
            if name and name != 'nan':
                texts.append(ax.text(r['_x'], r['_y'], name, fontsize=lbl_size,
                                     ha='center', va='center',
                                     bbox=dict(boxstyle='round,pad=0.15', fc='white',
                                               ec='none', alpha=0.7), zorder=500))
        if texts:
            try:
                from adjustText import adjust_text
                adjust_text(texts, ax=ax,
                            arrowprops=dict(arrowstyle='-', color='grey', lw=0.5),
                            expand=(1.15, 1.4), force_text=(0.4, 0.6),
                            only_move={'text': 'xy'})
            except ImportError:
                pass

    is_term = x_col == 'meta_log2fe_mean'
    ax.set_xlabel(x_labels.get(x_col, "Mean log2 fold change"))
    ax.set_ylabel(f"-log10(meta p-value, {p_src_name})")
    unit = "term" if is_term else "gene"
    ax.set_title(f"Meta Volcano — cross-dataset {unit} consistency",
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=7, loc='upper right', framealpha=0.9)
    return d, label_col
