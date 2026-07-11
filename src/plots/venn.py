"""Venn diagram — pure renderer (dialog + bundle 공유).

render_venn(ax, df, params) 는 VennDiagramDialog._do_plot 과 재현 번들 스크립트가 공유한다.
입력 df 는 long-format 멤버십 테이블: 컬럼 dataset(라벨), item(gene symbol 또는 peak_id).
데이터셋별 집합을 재구성해 2-way/3-way Venn 을 그린다. matplotlib_venn 의존(없으면 안내 메시지).
Qt 비의존.
"""
import pandas as pd


def render_venn(ax, df, params):
    """Venn diagram을 ax에 그린다. gene_sets(list[set]) 반환. 그릴 수 없으면 None.

    params: set_labels(list, 2 or 3), unit('Gene'|'Peak'), filter_name(str)
    """
    labels = list(params.get('set_labels', []))
    unit = params.get('unit', 'Gene')
    filter_name = params.get('filter_name', 'All Genes')

    df = df.copy() if df is not None else pd.DataFrame()
    if df.empty or 'dataset' not in df.columns or 'item' not in df.columns or len(labels) < 2:
        ax.text(0.5, 0.5, "No overlap data to plot.", ha='center', va='center',
                transform=ax.transAxes, color='#888888')
        return None

    gene_sets = [set(df[df['dataset'] == lbl]['item'].dropna().unique()) for lbl in labels]

    try:
        from matplotlib_venn import venn2, venn3, venn2_circles, venn3_circles
    except ImportError:
        ax.text(0.5, 0.5, "matplotlib_venn is required to render this figure.\n"
                          "Install it with:  pip install matplotlib-venn",
                ha='center', va='center', transform=ax.transAxes, color='#888888')
        return gene_sets

    if len(gene_sets) == 2:
        venn = venn2(gene_sets, set_labels=labels, ax=ax, alpha=0.6)
        venn2_circles(gene_sets, ax=ax, linewidth=1.5)
        for rid, color in (('10', '#ff9999'), ('01', '#9999ff'), ('11', '#cc99cc')):
            patch = venn.get_patch_by_id(rid)
            if patch:
                patch.set_color(color)
    elif len(gene_sets) == 3:
        venn = venn3(gene_sets, set_labels=labels, ax=ax, alpha=0.6)
        venn3_circles(gene_sets, ax=ax, linewidth=1.5)
        colors = {
            '100': '#ff9999', '010': '#9999ff', '001': '#99ff99',
            '110': '#ffcc99', '101': '#ffff99', '011': '#99ffff', '111': '#cccccc',
        }
        for rid, color in colors.items():
            patch = venn.get_patch_by_id(rid)
            if patch:
                patch.set_color(color)
    else:
        ax.text(0.5, 0.5, "Venn diagram requires 2-3 datasets.", ha='center', va='center',
                transform=ax.transAxes, color='#888888')
        return gene_sets

    title = f"{unit} Overlap - {filter_name}\n"
    if len(gene_sets) == 2:
        common = gene_sets[0] & gene_sets[1]
        unique_0 = gene_sets[0] - gene_sets[1]
        unique_1 = gene_sets[1] - gene_sets[0]
        title += (f"Common: {len(common)} | "
                  f"Unique to {labels[0]}: {len(unique_0)} | "
                  f"Unique to {labels[1]}: {len(unique_1)}")
    else:
        common = gene_sets[0] & gene_sets[1] & gene_sets[2]
        title += f"Common to all: {len(common)}"

    ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
    return gene_sets
