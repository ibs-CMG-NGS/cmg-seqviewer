"""Comparison dot plot renderer (Qt-free; dialog + bundle shared)."""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd


def render_comparison_dot(ax, df: pd.DataFrame, params: Mapping[str, Any]):
    params = dict(params or {})
    dataset_names = list(params.get('dataset_names') or [])
    if not dataset_names:
        ax.text(0.5, 0.5, 'No valid dataset columns found in comparison sheet.',
                ha='center', va='center', fontsize=14)
        return {'n_dots': 0}

    genes = []
    data = {name: {'log2fc': [], 'padj': []} for name in dataset_names}
    for idx, row in df.iterrows():
        gene = row.get('symbol', row.get('gene_id', f'Gene_{idx}'))
        genes.append(gene)
        for name in dataset_names:
            log_col = f'{name}_log2FC'
            padj_col = f'{name}_padj'
            if log_col not in df.columns:
                log_col = f'{name}_log2fc'
            if padj_col not in df.columns:
                padj_col = f'{name}_Padj'
            data[name]['log2fc'].append(row.get(log_col, np.nan))
            data[name]['padj'].append(row.get(padj_col, np.nan))

    gene_order = list(range(len(genes)))
    if params.get('cluster_genes') and len(genes) > 1:
        try:
            mat = np.array([data[name]['log2fc'] for name in dataset_names]).T
            mat = np.nan_to_num(mat, nan=0.0)
            if mat.shape[0] >= 2 and not np.all(mat == 0):
                from scipy.cluster.hierarchy import dendrogram, linkage
                order = dendrogram(linkage(mat, method='average', metric='euclidean'),
                                   no_plot=True)['leaves']
                gene_order = order
        except Exception:
            gene_order = list(range(len(genes)))

    genes_ordered = [genes[i] for i in gene_order]
    total_dots = len(genes) * len(dataset_names)
    base_size = 200 if total_dots < 100 else 100 if total_dots < 500 else 50

    def dot_size(padj):
        if pd.isna(padj):
            return base_size * 0.1
        if padj < 0.001:
            return base_size * 1.5
        if padj < 0.01:
            return base_size * 1.2
        if padj < 0.05:
            return base_size * 0.8
        return base_size * 0.4

    colormap = params.get('colormap') or 'RdBu_r'
    vmin = params.get('colorbar_min')
    vmax = params.get('colorbar_max')
    transpose = bool(params.get('transpose'))
    scatter = None

    if not transpose:
        for di, name in enumerate(dataset_names):
            for gi, original in enumerate(gene_order):
                log2fc = data[name]['log2fc'][original]
                if not pd.isna(log2fc):
                    scatter = ax.scatter(
                        di, gi, s=dot_size(data[name]['padj'][original]),
                        c=[log2fc], cmap=colormap, vmin=vmin, vmax=vmax,
                        alpha=0.7, edgecolors='black', linewidths=0.5)
        ax.set_xticks(range(len(dataset_names)))
        ax.set_xticklabels(dataset_names, rotation=45, ha='right')
        if len(genes) <= 50:
            ax.set_yticks(range(len(genes)))
            ax.set_yticklabels(genes_ordered, fontsize=8)
        ax.set_xlabel(params.get('xlabel') or 'Datasets', fontsize=12)
        ax.set_ylabel(params.get('ylabel') or 'Genes', fontsize=12)
        ax.set_xlim(-0.3, len(dataset_names) - 1 + 0.3)
        ax.set_ylim(-0.5, len(genes) - 0.5)
    else:
        for gi, original in enumerate(gene_order):
            for di, name in enumerate(dataset_names):
                log2fc = data[name]['log2fc'][original]
                if not pd.isna(log2fc):
                    scatter = ax.scatter(
                        gi, di, s=dot_size(data[name]['padj'][original]),
                        c=[log2fc], cmap=colormap, vmin=vmin, vmax=vmax,
                        alpha=0.7, edgecolors='black', linewidths=0.5)
        if len(genes) <= 50:
            ax.set_xticks(range(len(genes)))
            ax.set_xticklabels(genes_ordered, rotation=90, ha='right', fontsize=8)
        ax.set_yticks(range(len(dataset_names)))
        ax.set_yticklabels(dataset_names, fontsize=10)
        ax.set_xlabel(params.get('ylabel') or 'Genes', fontsize=12)
        ax.set_ylabel(params.get('xlabel') or 'Datasets', fontsize=12)
        ax.set_xlim(-0.3, len(genes) - 1 + 0.3)
        ax.set_ylim(-0.5, len(dataset_names) - 0.5)

    ax.set_title(params.get('title') or 'Dot Plot - Comparison Data',
                 fontsize=14, fontweight='bold')

    if scatter is not None:
        cbar = ax.figure.colorbar(scatter, ax=ax)
        cbar.set_label('Log2 Fold Change', fontsize=10)

    if params.get('show_legend'):
        from matplotlib.lines import Line2D
        elements = [
            Line2D([0], [0], marker='o', color='w', label='Padj < 0.001',
                   markerfacecolor='gray', markersize=12, markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='w', label='0.001 ≤ Padj < 0.01',
                   markerfacecolor='gray', markersize=10, markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='w', label='0.01 ≤ Padj < 0.05',
                   markerfacecolor='gray', markersize=8, markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='w', label='Padj ≥ 0.05',
                   markerfacecolor='gray', markersize=5, markeredgecolor='black'),
        ]
        ax.legend(handles=elements, loc='upper left', bbox_to_anchor=(1.15, 1),
                  fontsize=9, title='Significance')
    return {'n_dots': total_dots}
