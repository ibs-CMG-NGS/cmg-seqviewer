"""Concordance Summary bar chart (7개 카테고리별 유전자 수) — 순수 렌더러.

render_concordance_summary(ax, df, params) 는 ConcordanceSummaryDialog._plot 과
재현 번들 스크립트가 공유한다. Qt/models 비의존 — 컬럼명·카테고리·색상을 함수 내부에
자기완결로 포함한다 (plots/quadrant.py 와 동일한 관례).
"""


def render_concordance_summary(ax, df, params):
    """7-category concordance bar chart를 ax에 그린다.

    params: title
    """
    col_cat = "concordance"
    title = params.get("title", "Concordance Summary")

    categories = [
        "Concordant_Both_UP", "Concordant_Both_DOWN",
        "Discordant_RNA_UP_ATAC_DOWN", "Discordant_RNA_DOWN_ATAC_UP",
        "RNA_only", "ATAC_only", "Not_significant",
    ]
    colors = {
        "Concordant_Both_UP": "#D73027", "Concordant_Both_DOWN": "#4575B4",
        "Discordant_RNA_UP_ATAC_DOWN": "#FC8D59", "Discordant_RNA_DOWN_ATAC_UP": "#91BFDB",
        "RNA_only": "#A6D96A", "ATAC_only": "#FDAE61", "Not_significant": "#CCCCCC",
    }

    if df is not None and col_cat in df.columns:
        counts = df[col_cat].value_counts()
        total = len(df)
    else:
        counts = {}
        total = 0

    counts_ordered = [counts.get(c, 0) for c in categories]
    bar_colors     = [colors.get(c, "#CCCCCC") for c in categories]
    short_labels   = [c.replace("_", "\n") for c in categories]

    bars = ax.bar(range(len(categories)), counts_ordered, color=bar_colors,
                   edgecolor="white", linewidth=0.5)

    for bar, cnt in zip(bars, counts_ordered):
        if cnt > 0:
            pct = 100 * cnt / total if total > 0 else 0
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"{cnt}\n({pct:.1f}%)",
                ha="center", va="bottom", fontsize=7,
            )

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(short_labels, fontsize=7, rotation=20, ha="right")
    ax.set_ylabel("Gene count", fontsize=10)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlim(-0.5, len(categories) - 0.5)
