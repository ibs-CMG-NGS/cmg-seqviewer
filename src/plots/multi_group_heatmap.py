"""Multi-Group heatmap — pure renderer (dialog + bundle 공유).

render_multi_group_heatmap(df, params) 는 MultiGroupHeatmapDialog._do_plot 과 재현 번들
스크립트가 공유한다. 입력 df 는 유전자 × [gene_label + sample columns] 표(이미 padj/baseMean
필터 + top-N 적용된 것)이며, 함수 내부에서 행별 Z-score → seaborn.clustermap 을 그린다.

seaborn.clustermap 은 자체 Figure 를 만들므로, 관례(render(fig, ...))와 달리 (fig, info) 를
반환한다. info = {'cluster_gene_lists': {cid: [genes]}, 'cluster_colors': {cid: hex}}.
scipy / seaborn 이 필요하다. Qt 비의존.
"""
import numpy as np
import pandas as pd


def render_multi_group_heatmap(df, params):
    """유전자 × 샘플 표(df)로 Z-score clustermap 을 그려 (fig, info) 반환.

    params: gene_label_col, sample_columns(list, 순서=열 순서), sample_groups({g:[cols]}),
            group_colors({g:hex}), cmap, linkage, metric, cluster_rows(bool),
            cluster_cols(bool), cut(bool), k(int), z_auto(bool), z_min, z_max,
            show_gene_labels(bool), gene_fontsize, show_col_labels(bool),
            fig_width, fig_height, title
    """
    import matplotlib
    import matplotlib.pyplot as plt
    import seaborn as sns
    from scipy.stats import zscore as _zscore
    from scipy.cluster.hierarchy import linkage as _sc_linkage, fcluster as _sc_fcluster
    from scipy.spatial.distance import pdist as _sc_pdist

    # 클러스터 color bar 팔레트 (함수 내부에 인라인 → 번들 스크립트 자립)
    cluster_palette = [
        '#1B9E77', '#D95F02', '#7570B3', '#E7298A',
        '#66A61E', '#E6AB02', '#A6761D', '#666666',
        '#8DD3C7', '#BEBADA', '#FB8072', '#80B1D3',
    ]

    df = df.copy() if df is not None else pd.DataFrame()
    label_col = params.get('gene_label_col', 'gene_label')
    sample_cols = [c for c in (params.get('sample_columns') or []) if c in df.columns]

    if df.empty or not sample_cols:
        fig = plt.figure(figsize=(params.get('fig_width', 14), params.get('fig_height', 10)))
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "No data to plot.", ha='center', va='center',
                transform=ax.transAxes, fontsize=12, color='gray')
        ax.axis('off')
        return fig, {'cluster_gene_lists': {}, 'cluster_colors': {}}

    mat = df[sample_cols].copy()
    if label_col in df.columns:
        mat.index = df[label_col].astype(str).values
    else:
        mat.index = [str(i) for i in range(len(mat))]
    n_genes = len(mat)

    mat_z = mat.apply(_zscore, axis=1, result_type='broadcast').fillna(0)

    # 상단 그룹 color bar
    sample_groups = params.get('sample_groups') or {}
    group_colors = params.get('group_colors') or {}
    col_colors = None
    if sample_groups:
        colors = []
        for col in sample_cols:
            matched = None
            for gname, gcols in sample_groups.items():
                if col in gcols:
                    matched = gname
                    break
            colors.append(group_colors.get(matched, '#cccccc'))
        col_colors = pd.Series(colors, index=sample_cols, name="Group")

    linkage = params.get('linkage', 'ward')
    metric = params.get('metric', 'euclidean')
    if linkage == 'ward':
        metric = 'euclidean'
    do_cluster_rows = bool(params.get('cluster_rows', True))
    do_cut = bool(params.get('cut', False)) and do_cluster_rows
    k = int(params.get('k', 3))

    row_linkage_arr = None
    row_colors_cluster = None
    cluster_gene_lists: dict = {}
    cluster_colors: dict = {}
    n_excluded_flat = 0

    # correlation/cosine 거리는 분산이 0인(=모든 샘플에서 값이 동일한) 유전자에 대해
    # 정의되지 않는다(0/0 → NaN) — 실데이터에서 드물지 않으며, 그대로 두면 scipy.linkage 가
    # "condensed distance matrix must contain only finite values" 로 죽는다. 그런 유전자는
    # 애초에 correlation/cosine 관점에서 클러스터링에 기여할 신호가 없으므로, 이 두 metric을
    # 쓸 때만 클러스터링(과 표시)에서 제외한다. euclidean/ward(기본값)는 영향 없음.
    if do_cluster_rows and metric in ('correlation', 'cosine'):
        flat_mask = (mat_z == 0).all(axis=1)
        n_excluded_flat = int(flat_mask.sum())
        if n_excluded_flat:
            mat_z = mat_z.loc[~flat_mask]
            n_genes = len(mat_z)

    if mat_z.empty:
        fig = plt.figure(figsize=(params.get('fig_width', 14), params.get('fig_height', 10)))
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5,
                f"All {n_excluded_flat} genes have zero variance across samples\n"
                f"(undefined for {metric} distance). Try a different metric (euclidean)\n"
                f"or linkage (ward), or check your baseMean/padj filters.",
                ha='center', va='center', transform=ax.transAxes, fontsize=11, color='gray')
        ax.axis('off')
        return fig, {'cluster_gene_lists': {}, 'cluster_colors': {},
                     'n_excluded_flat': n_excluded_flat}

    will_cluster_rows = do_cluster_rows and len(mat_z) >= 2
    if will_cluster_rows:
        row_dist = _sc_pdist(mat_z.values, metric=metric)
        row_linkage_arr = _sc_linkage(row_dist, method=linkage)
        if do_cut:
            clust_labels = _sc_fcluster(row_linkage_arr, k, criterion='maxclust')
            k_actual = len(set(clust_labels.tolist()))
            c_pal = cluster_palette[:k_actual]
            row_colors_cluster = pd.Series(
                [c_pal[(c - 1) % len(c_pal)] for c in clust_labels],
                index=mat_z.index, name="Cluster")
            for gene, cid in zip(mat_z.index, clust_labels.tolist()):
                cluster_gene_lists.setdefault(int(cid), []).append(gene)
            cluster_colors = {c: c_pal[(c - 1) % len(c_pal)]
                              for c in set(clust_labels.tolist())}

    yticklabels = bool(params.get('show_gene_labels', True))
    xticklabels = bool(params.get('show_col_labels', True))
    z_auto = bool(params.get('z_auto', True))
    vmin = None if z_auto else float(params.get('z_min', -2.0))
    vmax = None if z_auto else float(params.get('z_max', 2.0))

    plt.close('all')
    cg = sns.clustermap(
        mat_z,
        figsize=(params.get('fig_width', 14), params.get('fig_height', 10)),
        cmap=params.get('cmap', 'RdBu_r'),
        col_colors=col_colors,
        row_colors=row_colors_cluster,
        row_cluster=will_cluster_rows,
        row_linkage=row_linkage_arr,
        col_cluster=bool(params.get('cluster_cols', False)),
        method=linkage,
        metric=metric,
        yticklabels=yticklabels,
        xticklabels=xticklabels,
        linewidths=0 if n_genes > 100 else 0.3,
        vmin=vmin,
        vmax=vmax,
        cbar_kws={"label": "Z-score", "orientation": "vertical"},
        cbar_pos=(0.02, 0.06, 0.02, 0.18),
    )

    if yticklabels:
        cg.ax_heatmap.tick_params(axis='y', labelsize=int(params.get('gene_fontsize', 7)))
    if xticklabels:
        cg.ax_heatmap.tick_params(axis='x', labelsize=9, rotation=45)
    cg.ax_heatmap.set_xlabel("")
    cg.ax_heatmap.set_ylabel("")

    title = params.get('title') or f"Multi-Group Heatmap  |  Z-score  |  n={n_genes}"
    cg.figure.suptitle(title, y=0.995, fontsize=10, va='top')
    bottom_margin = 0.12 if xticklabels else 0.04
    cg.figure.subplots_adjust(top=0.93, bottom=bottom_margin)

    return cg.figure, {'cluster_gene_lists': cluster_gene_lists,
                       'cluster_colors': cluster_colors,
                       'n_excluded_flat': n_excluded_flat}
