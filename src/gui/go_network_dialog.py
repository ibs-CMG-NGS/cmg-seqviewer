"""
GO/KEGG Network Visualization Dialog
"""

from typing import Optional
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSpinBox, QComboBox, QPushButton,
    QCheckBox, QDoubleSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar  # type: ignore
from matplotlib.figure import Figure
import networkx as nx

from models.data_models import Dataset
from models.standard_columns import StandardColumns


class GONetworkDialog(QDialog):
    """GO/KEGG Network 다이얼로그 (Clustered data용)"""
    
    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        
        # Clustered 데이터 확인
        self.is_clustered = 'cluster_id' in self.df.columns
        
        self.setWindowTitle("GO/KEGG Network Chart (Cluster-based)")
        self.setMinimumSize(1000, 800)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(12, 10))
        self.canvas = FigureCanvas(self.figure)
        
        # Network graph
        self.G = None
        
        self._init_ui()
        
        # 초기 네트워크 생성
        self._update_network()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 설정 패널
        settings_group = QGroupBox("Network Settings")
        settings_layout = QHBoxLayout()
        
        # Max terms
        settings_layout.addWidget(QLabel("Max terms:"))
        self.max_terms_spin = QSpinBox()
        self.max_terms_spin.setRange(10, 200)
        self.max_terms_spin.setValue(50)
        self.max_terms_spin.valueChanged.connect(self._update_network)
        settings_layout.addWidget(self.max_terms_spin)
        
        # Kappa threshold
        settings_layout.addWidget(QLabel("Kappa ≥"))
        self.kappa_spin = QDoubleSpinBox()
        self.kappa_spin.setRange(0.0, 1.0)
        self.kappa_spin.setValue(0.3)
        self.kappa_spin.setDecimals(2)
        self.kappa_spin.setSingleStep(0.05)
        self.kappa_spin.valueChanged.connect(self._update_network)
        settings_layout.addWidget(self.kappa_spin)
        
        # Node color
        settings_layout.addWidget(QLabel("Node color:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["Cluster", "FDR", "Direction", "Ontology"])
        self.color_combo.currentTextChanged.connect(self._update_network)
        settings_layout.addWidget(self.color_combo)
        
        # Node size
        settings_layout.addWidget(QLabel("Node size:"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(["Gene Count", "Degree", "Uniform"])
        self.size_combo.currentTextChanged.connect(self._update_network)
        settings_layout.addWidget(self.size_combo)
        
        # Layout
        settings_layout.addWidget(QLabel("Layout:"))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["Spring", "Circular", "Kamada-Kawai", "Spectral"])
        self.layout_combo.currentTextChanged.connect(self._update_network)
        settings_layout.addWidget(self.layout_combo)
        
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Filter 패널
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout()
        
        # FDR threshold
        filter_layout.addWidget(QLabel("FDR ≤"))
        self.fdr_threshold_spin = QDoubleSpinBox()
        self.fdr_threshold_spin.setRange(0.0, 1.0)
        self.fdr_threshold_spin.setValue(0.05)
        self.fdr_threshold_spin.setDecimals(3)
        self.fdr_threshold_spin.setSingleStep(0.01)
        self.fdr_threshold_spin.valueChanged.connect(self._update_network)
        filter_layout.addWidget(self.fdr_threshold_spin)
        
        # Show labels
        self.show_labels_check = QCheckBox("Show labels")
        self.show_labels_check.setChecked(True)
        self.show_labels_check.toggled.connect(self._update_network)
        filter_layout.addWidget(self.show_labels_check)
        
        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Matplotlib canvas
        layout.addWidget(self.canvas)
        
        # Navigation toolbar
        toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(toolbar)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self._update_network)
        button_layout.addWidget(refresh_btn)
        
        save_btn = QPushButton("Save Figure")
        save_btn.clicked.connect(self._save_figure)
        button_layout.addWidget(save_btn)
        
        export_btn = QPushButton("Export Network")
        export_btn.clicked.connect(self._export_network)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _calculate_kappa_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Kappa similarity matrix 계산"""
        if '_gene_set' not in df.columns:
            # Gene symbols을 set으로 변환
            if StandardColumns.GENE_SYMBOLS in df.columns:
                df['_gene_set'] = df[StandardColumns.GENE_SYMBOLS].apply(
                    lambda x: set(str(x).split('/')) if pd.notna(x) else set()
                )
            else:
                return pd.DataFrame()
        
        n = len(df)
        kappa_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                genes_i = df.iloc[i]['_gene_set']
                genes_j = df.iloc[j]['_gene_set']
                
                if len(genes_i) == 0 or len(genes_j) == 0:
                    continue
                
                # Jaccard similarity
                intersection = len(genes_i & genes_j)
                union = len(genes_i | genes_j)
                
                if union > 0:
                    kappa = intersection / union
                    kappa_matrix[i, j] = kappa
                    kappa_matrix[j, i] = kappa
        
        return pd.DataFrame(kappa_matrix, index=df.index, columns=df.index)
    
    def _update_network(self):
        """네트워크 업데이트 (클러스터 기반)"""
        self.figure.clear()
        
        # 클러스터링 데이터 확인
        if not self.is_clustered:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'This dialog requires clustered data.\n'
                   'Please run GO clustering first.',
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # 필터링된 데이터
        df = self.df.copy()
        
        if StandardColumns.FDR in df.columns:
            fdr_threshold = self.fdr_threshold_spin.value()
            df = df[df[StandardColumns.FDR] <= fdr_threshold]
        
        # 각 클러스터의 대표 항목 선택 (FDR 최소값)
        cluster_representatives = []
        for cluster_id in df['cluster_id'].unique():
            cluster_df = df[df['cluster_id'] == cluster_id]
            if StandardColumns.FDR in cluster_df.columns:
                # FDR 최소값인 항목을 대표로 선택
                rep_idx = cluster_df[StandardColumns.FDR].idxmin()
            else:
                # FDR 없으면 첫 번째 항목
                rep_idx = cluster_df.index[0]
            cluster_representatives.append(rep_idx)
        
        # 대표 항목만 사용
        df = df.loc[cluster_representatives]
        
        # Max terms 제한
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
        
        # Kappa matrix 계산 (클러스터 대표 항목 간)
        kappa_matrix = self._calculate_kappa_matrix(df)
        
        if kappa_matrix.empty:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No gene overlap data available',
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # Network graph 생성
        self.G = nx.Graph()
        
        # Nodes 추가 (클러스터 대표)
        for idx, row in df.iterrows():
            cluster_id = row['cluster_id']
            if StandardColumns.DESCRIPTION in df.columns:
                label = str(row[StandardColumns.DESCRIPTION]) if pd.notna(row[StandardColumns.DESCRIPTION]) else f"Cluster {cluster_id}"
                if len(label) > 40:
                    label = label[:37] + '...'
            else:
                label = f"Cluster {cluster_id}"
            
            self.G.add_node(idx, label=label, cluster=cluster_id)
        
        # Edges 추가 (Kappa threshold 기준)
        kappa_threshold = self.kappa_spin.value()
        for i in range(len(kappa_matrix)):
            for j in range(i+1, len(kappa_matrix)):
                kappa = kappa_matrix.iloc[i, j]
                if kappa >= kappa_threshold:
                    self.G.add_edge(df.index[i], df.index[j], weight=kappa)
        
        if len(self.G.edges()) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f'No edges with Kappa ≥ {kappa_threshold}\nTry lowering the threshold',
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # Layout 선택
        layout_type = self.layout_combo.currentText()
        if layout_type == "Spring":
            pos = nx.spring_layout(self.G, k=0.5, iterations=50)
        elif layout_type == "Circular":
            pos = nx.circular_layout(self.G)
        elif layout_type == "Kamada-Kawai":
            pos = nx.kamada_kawai_layout(self.G)
        else:  # Spectral
            pos = nx.spectral_layout(self.G)
        
        # Node colors
        color_by = self.color_combo.currentText()
        if color_by == "Cluster":
            # cluster_id를 숫자로 매핑 (문자열 cluster_id 지원)
            cluster_ids = [self.G.nodes[node]['cluster'] for node in self.G.nodes()]
            
            # 고유한 cluster_id 추출 및 숫자 매핑
            unique_clusters = sorted(set(cluster_ids), key=lambda x: (
                # Singleton은 끝으로, Small은 그 다음, 나머지는 숫자 순
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
        
        # Node sizes
        size_by = self.size_combo.currentText()
        if size_by == "Gene Count" and StandardColumns.GENE_COUNT in df.columns:
            node_sizes = [float(df.loc[node, StandardColumns.GENE_COUNT]) * 20 
                         for node in self.G.nodes()]
        elif size_by == "Degree":
            node_sizes = [dict(self.G.degree())[node] * 100 for node in self.G.nodes()]
        else:
            node_sizes = 300
        
        # Plotting
        ax = self.figure.add_subplot(111)
        
        # Draw edges with varying thickness based on kappa
        edge_weights = [self.G[u][v]['weight'] for u, v in self.G.edges()]
        edge_widths = [w * 5 for w in edge_weights]  # Scale for visibility
        nx.draw_networkx_edges(self.G, pos, alpha=0.4, width=edge_widths, 
                              edge_color='gray', ax=ax)
        
        # Draw nodes with better styling
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
        
        # Add colorbar for non-cluster coloring
        if color_by != "Cluster" and isinstance(node_colors, list):
            cbar = plt.colorbar(node_collection, ax=ax, shrink=0.8, pad=0.02)
            if color_by == "FDR":
                cbar.set_label('-log10(FDR)', fontsize=10)
            elif color_by == "Direction":
                cbar.set_label('Direction (0:UP, 1:DOWN, 2:TOTAL)', fontsize=10)
            elif color_by == "Ontology":
                cbar.set_label('Ontology', fontsize=10)
        
        # Draw labels with better styling
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
        
        # Add legend for cluster coloring
        if color_by == "Cluster":
            cluster_ids = [self.G.nodes[node]['cluster'] for node in self.G.nodes()]
            unique_clusters = sorted(set(cluster_ids), key=lambda x: (
                (2, 0) if x == 'Singleton' else 
                (1, 0) if x == 'Small' else 
                (0, int(x) if str(x).isdigit() else 0)
            ))
            
            # Create legend handles
            from matplotlib.patches import Patch
            from matplotlib import cm
            cmap = cm.get_cmap('tab20')
            
            legend_handles = []
            for cluster in unique_clusters[:20]:  # Limit to 20 for visibility
                cluster_to_num = {c: i for i, c in enumerate(unique_clusters)}
                color = cmap(cluster_to_num[cluster] / max(len(unique_clusters), 1))
                label = f"Cluster {cluster}"
                legend_handles.append(Patch(facecolor=color, edgecolor='black', label=label))
            
            ax.legend(handles=legend_handles, loc='upper left', 
                     bbox_to_anchor=(1.05, 1), fontsize=8,
                     framealpha=0.9, title='Clusters')
        
        # Title with statistics
        n_clusters = len(df['cluster_id'].unique())
        n_nodes = len(self.G.nodes())
        n_edges = len(self.G.edges())
        avg_degree = 2 * n_edges / n_nodes if n_nodes > 0 else 0
        
        title = f'GO/KEGG Cluster Network\n'
        title += f'Kappa ≥ {kappa_threshold} | {n_clusters} clusters | '
        title += f'{n_nodes} nodes | {n_edges} edges | Avg degree: {avg_degree:.1f}'
        ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
        ax.axis('off')
        
        # Layout 조정
        self.figure.tight_layout()
        
        self.canvas.draw()
    
    def _save_figure(self):
        """Figure 저장"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Figure",
            f"go_network_{self.dataset.name}.png",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;All Files (*)"
        )
        
        if file_path:
            self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "Success", f"Figure saved to:\n{file_path}")
    
    def _export_network(self):
        """네트워크 데이터 내보내기"""
        from PyQt6.QtWidgets import QFileDialog
        
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
