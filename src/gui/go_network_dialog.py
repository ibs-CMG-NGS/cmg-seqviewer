"""
GO/KEGG Network Visualization Dialog
"""

from typing import Optional
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox,
    QSpinBox, QComboBox, QPushButton,
    QCheckBox, QDoubleSpinBox, QMessageBox,
    QFileDialog, QFormLayout,
)
from PyQt6.QtCore import Qt
import networkx as nx

from models.data_models import Dataset
from models.standard_columns import StandardColumns
from gui.base_plot_dialog import BasePlotDialog


class GONetworkDialog(BasePlotDialog):
    """GO/KEGG Network 다이얼로그 (Clustered data용)"""

    def __init__(self, dataset: Dataset, parent=None):
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        self.is_clustered = 'cluster_id' in self.df.columns
        self.G = None

        super().__init__("GO/KEGG Network Chart (Cluster-based)", parent, figsize=(12, 10))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Network Settings
        settings_group = QGroupBox("Network Settings")
        settings_layout = QFormLayout()

        self.max_terms_spin = QSpinBox()
        self.max_terms_spin.setRange(10, 200)
        self.max_terms_spin.setValue(50)
        self.max_terms_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Max terms:", self.max_terms_spin)

        self.kappa_spin = QDoubleSpinBox()
        self.kappa_spin.setRange(0.0, 1.0)
        self.kappa_spin.setValue(0.3)
        self.kappa_spin.setDecimals(2)
        self.kappa_spin.setSingleStep(0.05)
        self.kappa_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Kappa ≥:", self.kappa_spin)

        self.color_combo = QComboBox()
        self.color_combo.addItems(["Cluster", "FDR", "Direction", "Ontology"])
        self.color_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Node color:", self.color_combo)

        self.size_combo = QComboBox()
        self.size_combo.addItems(["Gene Count", "Degree", "Uniform"])
        self.size_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Node size:", self.size_combo)

        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["Spring", "Circular", "Kamada-Kawai", "Spectral"])
        self.layout_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Layout:", self.layout_combo)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Filters
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout()

        self.fdr_threshold_spin = QDoubleSpinBox()
        self.fdr_threshold_spin.setRange(0.0, 1.0)
        self.fdr_threshold_spin.setValue(0.05)
        self.fdr_threshold_spin.setDecimals(3)
        self.fdr_threshold_spin.setSingleStep(0.01)
        self.fdr_threshold_spin.valueChanged.connect(self._update_plot)
        filter_layout.addRow("FDR ≤:", self.fdr_threshold_spin)

        self.show_labels_check = QCheckBox("Show labels")
        self.show_labels_check.setChecked(True)
        self.show_labels_check.toggled.connect(self._update_plot)
        filter_layout.addRow("", self.show_labels_check)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

    def _extra_buttons(self) -> list:
        return [("Export Network", self._export_network)]

    # ── Data helpers ──────────────────────────────────────────────────────

    def _calculate_kappa_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        if '_gene_set' not in df.columns:
            if StandardColumns.GENE_SYMBOLS in df.columns:
                df['_gene_set'] = df[StandardColumns.GENE_SYMBOLS].apply(
                    lambda x: set(str(x).split('/')) if pd.notna(x) else set()
                )
            else:
                return pd.DataFrame()

        n = len(df)
        kappa_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                genes_i = df.iloc[i]['_gene_set']
                genes_j = df.iloc[j]['_gene_set']

                if len(genes_i) == 0 or len(genes_j) == 0:
                    continue

                intersection = len(genes_i & genes_j)
                union = len(genes_i | genes_j)

                if union > 0:
                    kappa = intersection / union
                    kappa_matrix[i, j] = kappa
                    kappa_matrix[j, i] = kappa

        return pd.DataFrame(kappa_matrix, index=df.index, columns=df.index)

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()

        if not self.is_clustered:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'This dialog requires clustered data.\n'
                    'Please run GO clustering first.',
                    ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

        df = self.df.copy()

        if StandardColumns.FDR in df.columns:
            fdr_threshold = self.fdr_threshold_spin.value()
            df = df[df[StandardColumns.FDR] <= fdr_threshold]

        cluster_representatives = []
        for cluster_id in df['cluster_id'].unique():
            cluster_df = df[df['cluster_id'] == cluster_id]
            if StandardColumns.FDR in cluster_df.columns:
                rep_idx = cluster_df[StandardColumns.FDR].idxmin()
            else:
                rep_idx = cluster_df.index[0]
            cluster_representatives.append(rep_idx)

        df = df.loc[cluster_representatives]

        max_terms = self.max_terms_spin.value()
        if len(df) > max_terms:
            if StandardColumns.FDR in df.columns:
                df = df.nsmallest(max_terms, StandardColumns.FDR)
            else:
                df = df.head(max_terms)

        if len(df) < 2:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Not enough clusters for network\n(minimum 2 required)',
                    ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

        kappa_matrix = self._calculate_kappa_matrix(df)

        if kappa_matrix.empty:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No gene overlap data available',
                    ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

        self.G = nx.Graph()

        for idx, row in df.iterrows():
            cluster_id = row['cluster_id']
            if StandardColumns.DESCRIPTION in df.columns:
                label = str(row[StandardColumns.DESCRIPTION]) if pd.notna(row[StandardColumns.DESCRIPTION]) else f"Cluster {cluster_id}"
                if len(label) > 40:
                    label = label[:37] + '...'
            else:
                label = f"Cluster {cluster_id}"
            self.G.add_node(idx, label=label, cluster=cluster_id)

        kappa_threshold = self.kappa_spin.value()
        for i in range(len(kappa_matrix)):
            for j in range(i + 1, len(kappa_matrix)):
                kappa = kappa_matrix.iloc[i, j]
                if kappa >= kappa_threshold:
                    self.G.add_edge(df.index[i], df.index[j], weight=kappa)

        if len(self.G.edges()) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f'No edges with Kappa ≥ {kappa_threshold}\nTry lowering the threshold',
                    ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

        layout_type = self.layout_combo.currentText()
        if layout_type == "Spring":
            pos = nx.spring_layout(self.G, k=0.5, iterations=50)
        elif layout_type == "Circular":
            pos = nx.circular_layout(self.G)
        elif layout_type == "Kamada-Kawai":
            pos = nx.kamada_kawai_layout(self.G)
        else:
            pos = nx.spectral_layout(self.G)

        color_by = self.color_combo.currentText()
        if color_by == "Cluster":
            cluster_ids = [self.G.nodes[node]['cluster'] for node in self.G.nodes()]
            unique_clusters = sorted(set(cluster_ids), key=lambda x: (
                (2, 0) if x == 'Singleton' else
                (1, 0) if x == 'Small' else
                (0, int(x) if str(x).isdigit() else 0)
            ))
            cluster_to_num = {cluster: i for i, cluster in enumerate(unique_clusters)}
            node_colors = [cluster_to_num[cid] for cid in cluster_ids]
        elif color_by == "FDR" and StandardColumns.FDR in df.columns:
            node_colors = [-np.log10(float(df.loc[node, StandardColumns.FDR]))
                           for node in self.G.nodes()]
        elif color_by == "Direction" and StandardColumns.DIRECTION in df.columns:
            direction_map = {'UP': 0, 'DOWN': 1, 'TOTAL': 2}
            node_colors = [direction_map.get(str(df.loc[node, StandardColumns.DIRECTION]), 3)
                           for node in self.G.nodes()]
        elif color_by == "Ontology" and StandardColumns.ONTOLOGY in df.columns:
            ontology_map = {ont: i for i, ont in enumerate(df[StandardColumns.ONTOLOGY].unique())}
            node_colors = [ontology_map.get(str(df.loc[node, StandardColumns.ONTOLOGY]), 0)
                           for node in self.G.nodes()]
        else:
            node_colors = 'skyblue'

        size_by = self.size_combo.currentText()
        if size_by == "Gene Count" and StandardColumns.GENE_COUNT in df.columns:
            node_sizes = [float(df.loc[node, StandardColumns.GENE_COUNT]) * 20
                          for node in self.G.nodes()]
        elif size_by == "Degree":
            node_sizes = [dict(self.G.degree())[node] * 100 for node in self.G.nodes()]
        else:
            node_sizes = 300

        ax = self.figure.add_subplot(111)

        edge_weights = [self.G[u][v]['weight'] for u, v in self.G.edges()]
        edge_widths = [w * 5 for w in edge_weights]
        nx.draw_networkx_edges(self.G, pos, alpha=0.4, width=edge_widths,
                               edge_color='gray', ax=ax)

        import matplotlib.pyplot as plt
        node_collection = nx.draw_networkx_nodes(
            self.G, pos,
            node_color=node_colors,
            node_size=node_sizes,
            cmap='tab20' if color_by == "Cluster" else 'viridis',
            alpha=0.85,
            edgecolors='black',
            linewidths=2.0,
            ax=ax
        )

        if color_by != "Cluster" and isinstance(node_colors, list):
            cbar = plt.colorbar(node_collection, ax=ax, shrink=0.8, pad=0.02)
            if color_by == "FDR":
                cbar.set_label('-log10(FDR)', fontsize=10)
            elif color_by == "Direction":
                cbar.set_label('Direction (0:UP, 1:DOWN, 2:TOTAL)', fontsize=10)
            elif color_by == "Ontology":
                cbar.set_label('Ontology', fontsize=10)

        if self.show_labels_check.isChecked():
            labels = nx.get_node_attributes(self.G, 'label')
            nx.draw_networkx_labels(
                self.G, pos, labels,
                font_size=8,
                font_weight='bold',
                font_color='darkblue',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          edgecolor='none', alpha=0.7),
                ax=ax
            )

        if color_by == "Cluster":
            cluster_ids = [self.G.nodes[node]['cluster'] for node in self.G.nodes()]
            unique_clusters = sorted(set(cluster_ids), key=lambda x: (
                (2, 0) if x == 'Singleton' else
                (1, 0) if x == 'Small' else
                (0, int(x) if str(x).isdigit() else 0)
            ))

            from matplotlib.patches import Patch
            from matplotlib import cm
            cmap = cm.get_cmap('tab20')

            legend_handles = []
            for cluster in unique_clusters[:20]:
                cluster_to_num_loc = {c: i for i, c in enumerate(unique_clusters)}
                color = cmap(cluster_to_num_loc[cluster] / max(len(unique_clusters), 1))
                legend_handles.append(Patch(facecolor=color, edgecolor='black',
                                            label=f"Cluster {cluster}"))

            ax.legend(handles=legend_handles, loc='upper left',
                      bbox_to_anchor=(1.05, 1), fontsize=8,
                      framealpha=0.9, title='Clusters')

        n_clusters = len(df['cluster_id'].unique())
        n_nodes = len(self.G.nodes())
        n_edges = len(self.G.edges())
        avg_degree = 2 * n_edges / n_nodes if n_nodes > 0 else 0

        title = f'GO/KEGG Cluster Network\n'
        title += f'Kappa ≥ {kappa_threshold} | {n_clusters} clusters | '
        title += f'{n_nodes} nodes | {n_edges} edges | Avg degree: {avg_degree:.1f}'
        ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
        ax.axis('off')

        self.figure.tight_layout()
        self.canvas.draw()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_network(self):
        if self.G is None or len(self.G.nodes()) == 0:
            QMessageBox.warning(self, "No Network", "No network to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Network",
            f"go_network_{self.dataset.name}.graphml",
            "GraphML Files (*.graphml);;GML Files (*.gml);;All Files (*)"
        )

        if file_path:
            if file_path.endswith('.gml'):
                nx.write_gml(self.G, file_path)
            else:
                nx.write_graphml(self.G, file_path)
            QMessageBox.information(self, "Success", f"Network exported to:\n{file_path}")
