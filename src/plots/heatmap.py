"""Expression heatmap — pure renderer (shared by dialog + reproduction bundle).

render_heatmap(fig, df, params) 는 화면 다이얼로그(HeatmapWidget._draw_heatmap)와
재현 번들 스크립트가 공유한다. Qt/다이얼로그에 의존하지 않는다. colorbar를 그리므로
ax가 아니라 Figure를 받는다.
"""
import numpy as np
import pandas as pd


def render_heatmap(fig, df, params):
    """Heatmap을 fig에 그린다. (heatmap_data, gene_labels) 반환. 실패 시 None.

    params 키(= HeatmapWidget.get_plot_params()):
      n_genes, normalization('z-score'|'minmax'|'log2'|'none'), transpose(bool),
      sorting('padj'|'log2fc'|'clustering'), show_dendrogram(bool),
      colormap, colorbar_min, colorbar_max,
      show_colorbar(bool), labels_title/labels_xlabel/labels_ylabel,
      show_xticklabels/show_yticklabels

    show_dendrogram=True 이면 계층적 클러스터링으로 행(유전자)을 재정렬하고 히트맵 왼쪽에
    유전자 덴드로그램을 그린다(transpose 시에는 생략). 클러스터링 순서는 scipy 가 자동 계산.
    """
    # 발현 sample 컬럼이 아닌 것으로 간주할 이름 패턴 (함수 내부 — 번들 inline 자기완결)
    exclude_patterns = [
        'basemean', 'base_mean', 'log2fold', 'log2fc', 'logfc', 'foldchange',
        'lfcse', 'stat', 'statistic', 'pval', 'padj', 'fdr', 'qvalue',
        'gene_id', 'gene', 'symbol', 'dataset', 'description', 'name',
    ]
    df = df.copy()

    n_genes = int(params.get('n_genes', 50))
    normalization = params.get('normalization', 'z-score')
    transpose = bool(params.get('transpose', False))
    sorting = params.get('sorting', 'padj')
    show_dendrogram = bool(params.get('show_dendrogram', False))
    colormap = params.get('colormap', 'RdBu_r')
    cbar_min = params.get('colorbar_min')
    cbar_max = params.get('colorbar_max')

    # 덴드로그램을 켜면 클러스터링 정렬로 강제 (덴드로그램은 leaf 순서를 그림)
    if show_dendrogram and not transpose:
        sorting = 'clustering'

    # 발현 sample 컬럼 자동 감지
    sample_cols = [c for c in df.columns
                   if not any(p in c.lower() for p in exclude_patterns)
                   and pd.api.types.is_numeric_dtype(df[c])]
    # 의미 있는 heatmap 은 최소 2개 sample 컬럼이 필요하다. GO/KEGG 등 발현이 아닌
    # 데이터셋을 잘못 선택하면 여기서 걸러 안내 메시지를 띄운다(크래시 방지).
    if len(sample_cols) < 2:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5,
                'Heatmap requires per-sample expression data\n'
                '(at least 2 sample columns).\n\n'
                'This dataset does not look like sample expression data\n'
                '(e.g. a GO/KEGG enrichment table).',
                ha='center', va='center', fontsize=12, transform=ax.transAxes,
                color='#666666')
        return None

    expr_data = df[sample_cols].copy().dropna()
    if len(expr_data) == 0:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No valid data after removing NaN values',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)
        return None

    # 상위 N 유전자 (padj 있으면 그것으로, 없으면 분산)
    if 'padj' in df.columns and df.loc[expr_data.index, 'padj'].dropna().shape[0] > 0:
        valid_padj = df.loc[expr_data.index, 'padj'].dropna()
        top_idx = valid_padj.nsmallest(min(n_genes, len(valid_padj))).index
    else:
        variances = expr_data.var(axis=1)
        top_idx = variances.nlargest(min(n_genes, len(expr_data))).index

    if 'symbol' in df.columns:
        gene_labels = df.loc[top_idx, 'symbol'].tolist()
    elif 'gene_id' in df.columns:
        gene_labels = df.loc[top_idx, 'gene_id'].tolist()
    else:
        gene_labels = top_idx.tolist()
    expr_data = expr_data.loc[top_idx]

    # 정규화
    if normalization == 'z-score':
        heatmap_data = expr_data.apply(lambda x: (x - x.mean()) / (x.std() + 1e-10), axis=1)
        cbar_label = 'Z-score'
    elif normalization == 'minmax':
        heatmap_data = expr_data.apply(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-10), axis=1)
        cbar_label = 'Normalized (0-1)'
    elif normalization == 'log2':
        heatmap_data = np.log2(expr_data + 1)
        cbar_label = 'Log2(count + 1)'
    else:
        heatmap_data = expr_data
        cbar_label = 'Raw count'

    # 정렬
    if sorting == 'padj' and 'padj' in df.columns:
        sort_order = df.loc[heatmap_data.index, 'padj'].argsort()
        heatmap_data = heatmap_data.iloc[sort_order]
        gene_labels = [gene_labels[i] for i in sort_order]
    elif sorting == 'log2fc' and 'log2FC' in df.columns:
        sort_order = df.loc[heatmap_data.index, 'log2FC'].abs().argsort()[::-1]
        heatmap_data = heatmap_data.iloc[sort_order]
        gene_labels = [gene_labels[i] for i in sort_order]
    linkage_matrix = None
    if sorting == 'clustering':
        try:
            from scipy.cluster.hierarchy import linkage, dendrogram
            from scipy.spatial.distance import pdist
            if len(heatmap_data) >= 2:
                # pdist/linkage 는 비유한값(NaN/inf)이 있으면 실패한다 → 0으로 대체해 방어
                clust_input = heatmap_data.replace([np.inf, -np.inf], np.nan).fillna(0.0)
                linkage_matrix = linkage(pdist(clust_input, metric='euclidean'),
                                         method='average')
                order = dendrogram(linkage_matrix, no_plot=True)['leaves']
                heatmap_data = heatmap_data.iloc[order]
                gene_labels = [gene_labels[i] for i in order]
        except Exception:
            # 클러스터링 실패는 치명적이지 않다 — 덴드로그램 없이 원래 순서로 진행
            linkage_matrix = None

    if transpose:
        heatmap_data = heatmap_data.T

    # 덴드로그램: transpose가 아니고 linkage가 있을 때만 왼쪽에 유전자 덴드로그램 축을 둔다
    draw_dendro = show_dendrogram and linkage_matrix is not None and not transpose
    if draw_dendro:
        gs = fig.add_gridspec(1, 2, width_ratios=[0.18, 1.0], wspace=0.02)
        ax_dendro = fig.add_subplot(gs[0, 0])
        ax = fig.add_subplot(gs[0, 1], sharey=None)
        from scipy.cluster.hierarchy import dendrogram
        dendrogram(linkage_matrix, ax=ax_dendro, orientation='left',
                   no_labels=True, link_color_func=lambda k: '#555555')
        ax_dendro.invert_yaxis()   # imshow(origin='upper') 행 순서와 leaf 순서 정렬
        ax_dendro.axis('off')
    else:
        ax = fig.add_subplot(111)

    ax.set_gid('heatmap_main')   # 다이얼로그가 덴드로그램/colorbar 축과 구분해 찾도록
    im = ax.imshow(heatmap_data, cmap=colormap, aspect='auto',
                   interpolation='nearest', vmin=cbar_min, vmax=cbar_max)

    # 틱 레이블 (개수 적을 때만)
    if transpose:
        if len(heatmap_data.index) <= 50:
            ax.set_yticks(range(len(heatmap_data.index)))
            ax.set_yticklabels(heatmap_data.index, fontsize=8)
        if len(gene_labels) <= 20:
            ax.set_xticks(range(len(gene_labels)))
            ax.set_xticklabels(gene_labels, rotation=90, fontsize=8, ha='right')
    else:
        if len(heatmap_data.columns) <= 50:
            ax.set_xticks(range(len(heatmap_data.columns)))
            ax.set_xticklabels(heatmap_data.columns, rotation=90, fontsize=8)
        if len(gene_labels) <= 20:
            ax.set_yticks(range(len(gene_labels)))
            ax.set_yticklabels(gene_labels, fontsize=8)
        if draw_dendro:
            ax.yaxis.tick_right()   # 왼쪽은 덴드로그램 → 유전자 라벨은 오른쪽에

    # 라벨 (다이얼로그에선 PlotLabelsPanel이 이후 재적용; 번들에선 이게 최종)
    title = params.get('labels_title')
    if title:
        ax.set_title(title)
    if params.get('labels_xlabel'):
        ax.set_xlabel(params['labels_xlabel'])
    # 덴드로그램이 있으면 유전자 라벨이 오른쪽으로 이동하므로 좌측 y축 제목은 생략한다
    # (왼쪽은 덴드로그램, 오른쪽 gene tick label이 행을 식별).
    if params.get('labels_ylabel') and not draw_dendro:
        ax.set_ylabel(params['labels_ylabel'])
    if not params.get('show_xticklabels', True):
        ax.tick_params(axis='x', labelbottom=False)
    if not params.get('show_yticklabels', True):
        # 덴드로그램 시엔 오른쪽 라벨만 끈다(왼쪽엔 애초에 없음)
        ax.tick_params(axis='y', labelright=False) if draw_dendro \
            else ax.tick_params(axis='y', labelleft=False)

    if params.get('show_colorbar', True):
        # 덴드로그램 시 오른쪽 gene tick label과 colorbar가 겹치지 않도록 간격 확대
        cbar_pad = 0.14 if draw_dendro else 0.02
        cbar = fig.colorbar(im, ax=ax, pad=cbar_pad)
        cbar.set_label(cbar_label, fontsize=10)

    return heatmap_data, gene_labels
