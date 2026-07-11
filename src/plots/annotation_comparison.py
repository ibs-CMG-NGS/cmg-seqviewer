"""Genomic annotation comparison — pure renderer (dialog + bundle 공유).

render_annotation_comparison(ax, df, params) 는 AnnotationComparisonDialog._do_plot 과
재현 번들 스크립트가 공유한다. 입력 df 는 long-format: 컬럼 dataset(라벨), annotation,
log2fc, adj_pvalue (여러 ATAC 데이터셋을 세로로 이어붙인 것). 표시 형식:
  - counts / proportion → 데이터셋당 카테고리 누적 막대
  - enrichment(log2 sig/all) → 배경 대비 유의 peak의 feature별 log2 enrichment 그룹 막대
Qt/utils 비의존 — annotation 정규화·정렬·색상을 함수 내부에 자기완결로 포함한다.
반환값(matrix_df)은 다이얼로그 Export 에서 재사용한다.
"""
import numpy as np
import pandas as pd


def render_annotation_comparison(ax, df, params):
    """annotation 비교 막대를 ax에 그린다. matrix_df(카테고리 × 데이터셋) 반환.

    params: peak_set('all'|'significant'), display('counts'|'proportion'|'enrichment'),
            fdr_max, lfc_min, order(list)
    """
    canonical = {
        'promoter': 'Promoter', 'promoter-tss': 'Promoter',
        'distal intergenic': 'Distal Intergenic', 'intergenic': 'Intergenic',
        'intron': 'Intron', 'exon': 'Exon', 'cds': 'Exon',
        "3' utr": "3' UTR", "5' utr": "5' UTR",
        'downstream': 'Downstream', 'tts': 'TTS', 'enhancer': 'Enhancer',
    }
    canonical_order = [
        'Promoter', "5' UTR", "3' UTR", 'Exon', 'Intron',
        'Downstream', 'TTS', 'Distal Intergenic', 'Intergenic', 'Enhancer',
    ]
    category_colors = {
        'Promoter': '#5b9bd5', "5' UTR": '#93c47d', "3' UTR": '#f4a2a2',
        'Exon': '#e69138', 'Intron': '#b4a7d6', 'Downstream': '#3d5a99',
        'TTS': '#c27ba0', 'Distal Intergenic': '#ffd966', 'Intergenic': '#f9cb9c',
        'Enhancer': '#76a5af',
    }
    fallback_colors = [
        '#a6a6a6', '#8c8c8c', '#bcbd22', '#17becf', '#7f7f7f',
        '#c49c94', '#dbdb8d', '#9edae5', '#c7c7c7', '#f7b6d2',
    ]
    dataset_colors = [
        '#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
        '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac',
    ]

    def normalize(raw):
        if not isinstance(raw, str) or not raw.strip():
            return "Unknown"
        stripped = raw.split('(')[0].strip()
        c = canonical.get(stripped.lower())
        if c:
            return c
        return stripped[0].upper() + stripped[1:] if stripped else "Unknown"

    def order_cats(cats):
        present = set(cats)
        ordered = [c for c in canonical_order if c in present]
        return ordered + sorted(present - set(ordered))

    def color_for(cat, idx):
        return category_colors.get(cat, fallback_colors[idx % len(fallback_colors)])

    fdr_max = float(params.get('fdr_max', 0.05))
    lfc_min = float(params.get('lfc_min', 1.0))
    display = params.get('display', 'counts')
    peak_set = params.get('peak_set', 'significant')

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty or 'dataset' not in df.columns or 'annotation' not in df.columns:
        ax.text(0.5, 0.5, "No annotation data in the selected datasets.",
                ha='center', va='center', transform=ax.transAxes, color='#888888')
        return None

    order = params.get('order') or list(pd.unique(df['dataset']))
    df['_lfc'] = pd.to_numeric(df.get('log2fc'), errors='coerce')
    df['_padj'] = pd.to_numeric(df.get('adj_pvalue'), errors='coerce')

    def ann_counts(sub, significant):
        s = sub
        if significant:
            s = sub[(sub['_padj'] <= fdr_max) & (sub['_lfc'].abs() >= lfc_min)]
        return s['annotation'].dropna().map(normalize).value_counts()

    per_all = {lbl: ann_counts(df[df['dataset'] == lbl], False) for lbl in order}

    # ── Enrichment: 배경 대비 유의 peak의 log2 enrichment (그룹 막대) ──
    if display == 'enrichment':
        per_sig = {lbl: ann_counts(df[df['dataset'] == lbl], True) for lbl in order}
        all_cats = set()
        for s in per_all.values():
            all_cats.update(s.index.tolist())
        ordered = order_cats(all_cats)
        if not ordered:
            ax.text(0.5, 0.5, "No annotation data in the selected datasets.",
                    ha='center', va='center', transform=ax.transAxes, color='#888888')
            return None
        K = len(ordered)
        enr = {}
        for lbl in order:
            allc, sigc = per_all[lbl], per_sig[lbl]
            all_tot, sig_tot = float(allc.sum()), float(sigc.sum())
            if sig_tot == 0 or all_tot == 0:
                enr[lbl] = [np.nan] * K
                continue
            row = []
            for cat in ordered:
                all_p = (float(allc.get(cat, 0)) + 0.5) / (all_tot + 0.5 * K)
                sig_p = (float(sigc.get(cat, 0)) + 0.5) / (sig_tot + 0.5 * K)
                row.append(float(np.log2(sig_p / all_p)))
            enr[lbl] = row
        matrix = pd.DataFrame(enr, index=ordered)

        n = len(order)
        width = 0.8 / max(n, 1)
        xbase = np.arange(K)
        for j, lbl in enumerate(order):
            offset = (j - (n - 1) / 2) * width
            ax.bar(xbase + offset, np.array(enr[lbl], dtype=float), width=width,
                   color=dataset_colors[j % len(dataset_colors)],
                   label=lbl, edgecolor='white', linewidth=0.3)
        ax.axhline(0, color='#333333', linewidth=0.8)
        ax.set_xticks(xbase)
        ax.set_xticklabels(ordered, rotation=30, ha='right', fontsize=8)
        ax.set_ylabel("log2( significant / all )")
        ax.set_title("Genomic annotation enrichment (significant vs background)",
                     fontsize=12, fontweight='bold')
        ax.legend(title="Dataset")
        return matrix

    # ── Counts / Proportion: 데이터셋당 카테고리 누적 막대 ──
    significant = (peak_set == 'significant')
    per_ds = {lbl: ann_counts(df[df['dataset'] == lbl], significant) for lbl in order}
    all_cats = set()
    for s in per_ds.values():
        all_cats.update(s.index.tolist())
    ordered = order_cats(all_cats)
    if not ordered:
        ax.text(0.5, 0.5, "No annotation data in the selected datasets.",
                ha='center', va='center', transform=ax.transAxes, color='#888888')
        return None

    matrix = pd.DataFrame(
        {lbl: {cat: float(per_ds[lbl].get(cat, 0)) for cat in ordered} for lbl in order}
    ).reindex(ordered)

    plot_mat = matrix.copy()
    as_prop = (display == 'proportion')
    if as_prop:
        col_sums = plot_mat.sum(axis=0).replace(0, np.nan)
        plot_mat = plot_mat.divide(col_sums, axis=1).fillna(0.0) * 100.0

    x = list(range(len(order)))
    bottom = np.zeros(len(order))
    for i, cat in enumerate(ordered):
        vals = plot_mat.loc[cat].to_numpy()
        ax.bar(x, vals, bottom=bottom, color=color_for(cat, i),
               label=cat, edgecolor='white', linewidth=0.4)
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(order, rotation=30, ha='right', fontsize=8)
    ax.set_ylabel("Proportion (%)" if as_prop else "Peak number")
    mode_txt = "significant peaks" if significant else "all peaks"
    ax.set_title(f"Genomic annotation distribution ({mode_txt})",
                 fontsize=12, fontweight='bold')
    ax.legend(title="Annotation")
    return matrix
