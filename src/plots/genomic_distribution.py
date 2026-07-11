"""Genomic distribution pie — pure renderer (dialog + bundle 공유).

render_genomic_distribution(fig, df, params) 는 GenomicDistributionDialog._do_plot 과
재현 번들 스크립트가 공유한다. ATAC peak의 'annotation' 컬럼 분포를 Pie chart로 그린다.
Qt/StandardColumns 비의존 — annotation 정규화·색상은 함수 내부에 자기완결로 포함한다
(번들 inline 시 utils 의존 없이 독립 실행되도록).
"""
import pandas as pd


def render_genomic_distribution(fig, df, params):
    """annotation 분포 pie를 fig에 그린다. counts(Series) 반환. annotation 없으면 None.

    params: title, dataset_name, max_categories(기본 9)
    """
    # annotation 정규화(HOMER/ChIPseeker 표기 → 표준 대분류) — bundle 독립성 위해 내장
    canonical = {
        'promoter': 'Promoter', 'promoter-tss': 'Promoter',
        'distal intergenic': 'Distal Intergenic', 'intergenic': 'Intergenic',
        'intron': 'Intron', 'exon': 'Exon', 'cds': 'Exon',
        "3' utr": "3' UTR", "5' utr": "5' UTR",
        'downstream': 'Downstream', 'tts': 'TTS', 'enhancer': 'Enhancer',
    }
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

    def normalize(raw):
        if not isinstance(raw, str) or not raw.strip():
            return "Unknown"
        stripped = raw.split('(')[0].strip()
        c = canonical.get(stripped.lower())
        if c:
            return c
        return stripped[0].upper() + stripped[1:] if stripped else "Unknown"

    def color_for(cat, idx):
        return category_colors.get(cat, fallback_colors[idx % len(fallback_colors)])

    ax = fig.add_subplot(111)
    df = df if df is not None else pd.DataFrame()

    if 'annotation' not in df.columns or df['annotation'].isna().all():
        ax.text(0.5, 0.5,
                "Annotation data not available.\n"
                "This dataset does not contain an 'annotation' column.",
                ha='center', va='center', transform=ax.transAxes,
                fontsize=10, color='#888888',
                bbox=dict(boxstyle='round', fc='#f8f8f8', ec='#cccccc', alpha=0.8))
        return None

    normalized = df['annotation'].dropna().map(normalize)
    counts = normalized.value_counts()

    max_cats = int(params.get('max_categories', 9))
    if len(counts) > max_cats:
        top = counts.iloc[:max_cats]
        others = counts.iloc[max_cats:].sum()
        counts = pd.concat([top, pd.Series({'Others': others})])

    labels = counts.index.tolist()
    sizes = counts.values.tolist()
    colors = [color_for(lbl, i) for i, lbl in enumerate(labels)]

    wedges, _texts, autotexts = ax.pie(
        sizes, labels=None, colors=colors,
        autopct=lambda pct: f'{pct:.1f}%' if pct >= 3 else '',
        startangle=90,
        wedgeprops={'linewidth': 0.8, 'edgecolor': 'white'},
    )
    for at in autotexts:
        at.set_fontsize(8)

    legend_labels = [f"{lbl}  ({cnt:,})" for lbl, cnt in zip(labels, sizes)]
    ax.legend(wedges, legend_labels, title="Annotation",
              loc='center left', bbox_to_anchor=(1.0, 0.5), fontsize=8)

    total = sum(sizes)
    name = params.get('dataset_name', '')
    title = params.get('title') or (
        f"Genomic Distribution of Peaks\n{name}  |  Total: {total:,} peaks")
    ax.set_title(title, fontsize=11)
    return counts
