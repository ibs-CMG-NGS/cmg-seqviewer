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
      sorting('padj'|'log2fc'|'clustering'), colormap, colorbar_min, colorbar_max,
      show_colorbar(bool), labels_title/labels_xlabel/labels_ylabel,
      show_xticklabels/show_yticklabels
    """
    # 발현 sample 컬럼이 아닌 것으로 간주할 이름 패턴 (함수 내부 — 번들 inline 자기완결)
    exclude_patterns = [
        'basemean', 'base_mean', 'log2fold', 'log2fc', 'logfc', 'foldchange',
        'lfcse', 'stat', 'statistic', 'pval', 'padj', 'fdr', 'qvalue',
        'gene_id', 'gene', 'symbol', 'dataset', 'description', 'name',
    ]
    ax = fig.add_subplot(111)
    df = df.copy()

    n_genes = int(params.get('n_genes', 50))
    normalization = params.get('normalization', 'z-score')
    transpose = bool(params.get('transpose', False))
    sorting = params.get('sorting', 'padj')
    colormap = params.get('colormap', 'RdBu_r')
    cbar_min = params.get('colorbar_min')
    cbar_max = params.get('colorbar_max')

    # 발현 sample 컬럼 자동 감지
    sample_cols = [c for c in df.columns
                   if not any(p in c.lower() for p in exclude_patterns)
                   and pd.api.types.is_numeric_dtype(df[c])]
    if not sample_cols:
        ax.text(0.5, 0.5, 'No sample expression columns found.\n'
                'Heatmap requires sample count data.',
                ha='center', va='center', fontsize=14, transform=ax.transAxes)
        return None

    expr_data = df[sample_cols].copy().dropna()
    if len(expr_data) == 0:
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
    elif sorting == 'clustering':
        try:
            from scipy.cluster.hierarchy import linkage, dendrogram
            from scipy.spatial.distance import pdist
            lm = linkage(pdist(heatmap_data, metric='euclidean'), method='average')
            order = dendrogram(lm, no_plot=True)['leaves']
            heatmap_data = heatmap_data.iloc[order]
            gene_labels = [gene_labels[i] for i in order]
        except ImportError:
            pass

    if transpose:
        heatmap_data = heatmap_data.T

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

    # 라벨 (다이얼로그에선 PlotLabelsPanel이 이후 재적용; 번들에선 이게 최종)
    title = params.get('labels_title')
    if title:
        ax.set_title(title)
    if params.get('labels_xlabel'):
        ax.set_xlabel(params['labels_xlabel'])
    if params.get('labels_ylabel'):
        ax.set_ylabel(params['labels_ylabel'])
    if not params.get('show_xticklabels', True):
        ax.tick_params(axis='x', labelbottom=False)
    if not params.get('show_yticklabels', True):
        ax.tick_params(axis='y', labelleft=False)

    if params.get('show_colorbar', True):
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label(cbar_label, fontsize=10)

    return heatmap_data, gene_labels
