"""PCA plot — pure renderer (dialog + bundle 공유).

render_pca(fig, df, params) 는 PCADialog._do_plot 과 재현 번들 스크립트가 공유한다.
PCA는 numpy SVD로 계산(sklearn 불필요). Qt/StandardColumns 비의존 — 샘플 컬럼 감지는
함수 내부에 자기완결로 포함한다.
"""
import numpy as np
import pandas as pd


def render_pca(fig, df, params):
    """PCA plot을 fig에 그린다. (scores_df, explained_ratio) 반환. 샘플 없으면 None.

    params: n_genes, transform('log2'|'log1p'|'none'), scaling('standard'|'none'),
            x_pc(1-base), y_pc(1-base), point_size, show_labels(bool), title
    """
    exclude = {
        'basemean', 'base_mean', 'log2fold', 'log2fc', 'logfc', 'foldchange',
        'lfcse', 'stat', 'statistic', 'pval', 'padj', 'fdr', 'qvalue', 'adj_p',
        'gene_id', 'gene', 'symbol', 'dataset', 'description', 'name',
        'pvalue', 'p_value',
    }
    ax = fig.add_subplot(111)
    df = df.copy() if df is not None else pd.DataFrame()

    sample_cols = [c for c in df.columns
                   if not any(p in c.lower() for p in exclude)
                   and pd.api.types.is_numeric_dtype(df[c])]
    if not sample_cols:
        ax.text(0.5, 0.5, 'No sample expression columns found.\n'
                'PCA requires per-sample count data.',
                ha='center', va='center', transform=ax.transAxes, fontsize=12)
        return None

    # 상위 N 유전자 (분산) → transform → 전치 → scaling → SVD
    expr = df[sample_cols].fillna(0)
    n = min(int(params.get('n_genes', 500)), len(expr))
    expr = expr.loc[expr.var(axis=1).nlargest(n).index]
    mat = expr.values.astype(float)
    transform = params.get('transform', 'log2')
    if transform == 'log2':
        mat = np.log2(mat + 1.0)
    elif transform == 'log1p':
        mat = np.log1p(mat)

    X = mat.T
    if params.get('scaling', 'standard') == 'standard':
        mean = X.mean(axis=0)
        std = X.std(axis=0, ddof=0)
        std[std == 0] = 1.0
        X = (X - mean) / std

    Xc = X - X.mean(axis=0)
    U, s, Vt = np.linalg.svd(Xc, full_matrices=False)
    ev = (s ** 2) / (Xc.shape[0] - 1)
    explained = (ev / ev.sum()).tolist()
    n_comp = min(len(sample_cols), Xc.shape[1], 10)
    scores = U[:, :n_comp] * s[:n_comp]
    scores_df = pd.DataFrame(scores, index=sample_cols,
                             columns=[f"PC{i+1}" for i in range(scores.shape[1])])
    explained = explained[:n_comp]

    xi = int(params.get('x_pc', 1)) - 1
    yi = int(params.get('y_pc', 2)) - 1
    if xi >= scores.shape[1] or yi >= scores.shape[1]:
        ax.text(0.5, 0.5, f"Only {scores.shape[1]} PCs available.\nReduce X/Y axis PC numbers.",
                ha='center', va='center', transform=ax.transAxes, fontsize=12)
        return scores_df, explained

    import matplotlib
    xs, ys = scores[:, xi], scores[:, yi]
    cmap = matplotlib.colormaps.get_cmap('tab10')
    colors = [cmap(i % 10) for i in range(len(sample_cols))]

    ax.scatter(xs, ys, s=int(params.get('point_size', 80)), c=colors, alpha=0.85,
               edgecolors='white', linewidths=0.8, zorder=3)
    if params.get('show_labels', True):
        for x, y, lbl in zip(xs, ys, sample_cols):
            ax.annotate(lbl, (x, y), xytext=(5, 5), textcoords='offset points',
                        fontsize=8, color='#222',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6, ec='none'))

    pct_x = explained[xi] * 100 if xi < len(explained) else 0
    pct_y = explained[yi] * 100 if yi < len(explained) else 0
    ax.set_xlabel(f"PC{xi+1}  ({pct_x:.1f}% variance)", fontsize=12)
    ax.set_ylabel(f"PC{yi+1}  ({pct_y:.1f}% variance)", fontsize=12)
    ax.set_title(params.get('title') or 'PCA — Sample Expression', fontsize=13, fontweight='bold')
    ax.axhline(0, color='#bbb', linewidth=0.8, linestyle='--', zorder=1)
    ax.axvline(0, color='#bbb', linewidth=0.8, linestyle='--', zorder=1)
    ax.grid(True, alpha=0.3, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    scree = "Explained variance:\n" + "  ".join(
        f"PC{i+1}: {v*100:.1f}%" for i, v in enumerate(explained[:5]))
    ax.text(0.99, 0.01, scree, transform=ax.transAxes, fontsize=7.5,
            ha='right', va='bottom', color='#666',
            bbox=dict(boxstyle='round', fc='white', alpha=0.7, ec='#ccc'))
    return scores_df, explained
