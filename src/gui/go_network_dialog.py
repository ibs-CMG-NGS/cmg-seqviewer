"""
GO/KEGG Cluster Visualization Dialog

두 개의 탭을 제공한다:
  Tab 1 - Cluster Network : 클러스터 드롭다운으로 선택한 클러스터(혹은 전체
                             대표 term)의 Jaccard 유사도 기반 네트워크
  Tab 2 - Summary Dot Plot: 전체 클러스터 대표 term 요약 dot plot
                             (X축 = -log10 FDR, 점 크기 = 클러스터 멤버 수)
"""

from typing import Optional
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.patches import Patch

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QTabWidget, QWidget,
    QSpinBox, QComboBox, QPushButton, QCheckBox, QDoubleSpinBox,
    QMessageBox, QFileDialog, QFormLayout, QLabel,
)
from PyQt6.QtCore import Qt

from models.data_models import Dataset
from models.standard_columns import StandardColumns
from gui.base_plot_dialog import BasePlotDialog


class GONetworkDialog(BasePlotDialog):
    """GO/KEGG 클러스터 시각화 다이얼로그 (Network + Dot Plot)."""

    def __init__(self, dataset: Dataset, parent=None):
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        self.is_clustered = StandardColumns.CLUSTER_ID in self.df.columns
        self.G: Optional[nx.Graph] = None

        # 유효 클러스터 ID (숫자 문자열만)
        if self.is_clustered:
            self._valid_ids = sorted(
                {c for c in self.df[StandardColumns.CLUSTER_ID]
                 if isinstance(c, str) and c.isdigit()},
                key=int
            )
        else:
            self._valid_ids = []

        super().__init__("GO/KEGG Cluster Dot Plot", parent, figsize=(12, 10))
        self.resize(1100, 750)
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        self._ctrl_tabs = QTabWidget()
        self._ctrl_tabs.currentChanged.connect(self._update_plot)

        # ── Tab 1: Network ───────────────────────────────────────────────────
        net_widget = QWidget()
        net_form = QFormLayout(net_widget)
        net_form.setVerticalSpacing(8)

        self._cluster_combo = QComboBox()
        self._cluster_combo.addItem("All (Representatives)")
        for cid in self._valid_ids:
            self._cluster_combo.addItem(f"Cluster {cid}")
        self._cluster_combo.currentTextChanged.connect(self._update_plot)
        net_form.addRow("Cluster:", self._cluster_combo)

        self._fdr_spin = QDoubleSpinBox()
        self._fdr_spin.setRange(0.0, 1.0)
        self._fdr_spin.setValue(0.05)
        self._fdr_spin.setDecimals(3)
        self._fdr_spin.setSingleStep(0.01)
        self._fdr_spin.valueChanged.connect(self._update_plot)
        net_form.addRow("FDR ≤:", self._fdr_spin)

        self._edge_spin = QDoubleSpinBox()
        self._edge_spin.setRange(0.0, 1.0)
        self._edge_spin.setValue(0.1)
        self._edge_spin.setDecimals(2)
        self._edge_spin.setSingleStep(0.05)
        self._edge_spin.valueChanged.connect(self._update_plot)
        net_form.addRow("Edge (Jaccard ≥):", self._edge_spin)

        self._net_node_size_combo = QComboBox()
        self._net_node_size_combo.addItems(["Gene Count", "Degree", "Uniform"])
        self._net_node_size_combo.currentTextChanged.connect(self._update_plot)
        net_form.addRow("Node size:", self._net_node_size_combo)

        self._net_node_color_combo = QComboBox()
        self._net_node_color_combo.addItems(["FDR", "Ontology", "Direction", "Cluster"])
        self._net_node_color_combo.currentTextChanged.connect(self._update_plot)
        net_form.addRow("Node color:", self._net_node_color_combo)

        self._layout_combo = QComboBox()
        self._layout_combo.addItems(["Spring", "Kamada-Kawai", "Circular", "Spectral"])
        self._layout_combo.currentTextChanged.connect(self._update_plot)
        net_form.addRow("Layout:", self._layout_combo)

        self._show_labels_check = QCheckBox("Show labels")
        self._show_labels_check.setChecked(True)
        self._show_labels_check.toggled.connect(self._update_plot)
        net_form.addRow("", self._show_labels_check)

        # Network 탭 비활성화 — 재사용 시 아래 주석 해제
        # self._ctrl_tabs.addTab(net_widget, "Network")

        # ── Tab 2: Dot Plot ──────────────────────────────────────────────────
        dot_widget = QWidget()
        dot_form = QFormLayout(dot_widget)
        dot_form.setVerticalSpacing(8)

        self._xaxis_combo = QComboBox()
        self._xaxis_combo.addItems(["-log10(FDR)", "Gene Ratio", "Fold Enrichment"])
        # 권장 기본: 효과 크기(Fold Enrichment)를 X축, 유의성(FDR)은 색으로 → 정보 중복 없음
        self._xaxis_combo.setCurrentText("Fold Enrichment")
        self._xaxis_combo.currentTextChanged.connect(self._update_plot)
        dot_form.addRow("X axis:", self._xaxis_combo)

        self._dot_color_combo = QComboBox()
        self._dot_color_combo.addItems(["FDR", "Ontology", "Direction"])
        self._dot_color_combo.currentTextChanged.connect(self._update_plot)
        dot_form.addRow("Color by:", self._dot_color_combo)

        # 점 크기 기준: 클러스터 멤버 수(주제 폭) 또는 대표 term의 유전자 수(근거)
        self._dot_size_combo = QComboBox()
        self._dot_size_combo.addItems(["Cluster size", "Gene count"])
        self._dot_size_combo.currentTextChanged.connect(self._update_plot)
        dot_form.addRow("Dot size by:", self._dot_size_combo)

        self._dot_sort_combo = QComboBox()
        self._dot_sort_combo.addItems(["FDR", "Cluster Size", "Term Name"])
        self._dot_sort_combo.currentTextChanged.connect(self._update_plot)
        dot_form.addRow("Sort by:", self._dot_sort_combo)

        self._top_n_spin = QSpinBox()
        self._top_n_spin.setRange(5, 200)
        self._top_n_spin.setValue(30)
        self._top_n_spin.valueChanged.connect(self._update_plot)
        dot_form.addRow("Top N clusters:", self._top_n_spin)

        # ── Dot Size ─────────────────────────────────────────────────────────
        size_group = QGroupBox("Dot Size")
        size_form = QFormLayout(size_group)
        size_form.setVerticalSpacing(6)

        self._dot_size_min_spin = QDoubleSpinBox()
        self._dot_size_min_spin.setRange(10.0, 1000.0)
        self._dot_size_min_spin.setValue(40.0)
        self._dot_size_min_spin.setDecimals(0)
        self._dot_size_min_spin.setSingleStep(10.0)
        self._dot_size_min_spin.setToolTip("단일 멤버 클러스터의 최소 점 크기 (pt²)")
        self._dot_size_min_spin.valueChanged.connect(self._update_plot)
        size_form.addRow("Min size:", self._dot_size_min_spin)

        self._dot_size_scale_spin = QDoubleSpinBox()
        self._dot_size_scale_spin.setRange(1.0, 500.0)
        self._dot_size_scale_spin.setValue(20.0)
        self._dot_size_scale_spin.setDecimals(1)
        self._dot_size_scale_spin.setSingleStep(5.0)
        self._dot_size_scale_spin.setToolTip("멤버 수 × 이 값 = 점 크기 (pt²)")
        self._dot_size_scale_spin.valueChanged.connect(self._update_plot)
        size_form.addRow("Scale (×members):", self._dot_size_scale_spin)

        self._size_legend_check = QCheckBox("Show size legend")
        self._size_legend_check.setChecked(True)
        self._size_legend_check.toggled.connect(self._update_plot)
        size_form.addRow("", self._size_legend_check)

        dot_form.addRow(size_group)

        # ── Axis Range ───────────────────────────────────────────────────────
        axis_group = QGroupBox("Axis Range")
        axis_form = QFormLayout(axis_group)
        axis_form.setVerticalSpacing(6)

        # X range
        xrange_row = QWidget()
        xrange_layout = QHBoxLayout(xrange_row)
        xrange_layout.setContentsMargins(0, 0, 0, 0)
        self._xauto_check = QCheckBox("Auto")
        self._xauto_check.setChecked(True)
        self._xauto_check.toggled.connect(self._on_xauto_toggled)
        self._xauto_check.toggled.connect(self._update_plot)
        xrange_layout.addWidget(self._xauto_check)
        xrange_layout.addWidget(QLabel("Min:"))
        self._xmin_spin = QDoubleSpinBox()
        self._xmin_spin.setRange(-1000.0, 1000.0)
        self._xmin_spin.setValue(0.0)
        self._xmin_spin.setDecimals(2)
        self._xmin_spin.setEnabled(False)
        self._xmin_spin.valueChanged.connect(self._update_plot)
        xrange_layout.addWidget(self._xmin_spin)
        xrange_layout.addWidget(QLabel("Max:"))
        self._xmax_spin = QDoubleSpinBox()
        self._xmax_spin.setRange(-1000.0, 1000.0)
        self._xmax_spin.setValue(10.0)
        self._xmax_spin.setDecimals(2)
        self._xmax_spin.setEnabled(False)
        self._xmax_spin.valueChanged.connect(self._update_plot)
        xrange_layout.addWidget(self._xmax_spin)
        axis_form.addRow("X:", xrange_row)

        # Y range
        yrange_row = QWidget()
        yrange_layout = QHBoxLayout(yrange_row)
        yrange_layout.setContentsMargins(0, 0, 0, 0)
        self._yauto_check = QCheckBox("Auto")
        self._yauto_check.setChecked(True)
        self._yauto_check.toggled.connect(self._on_yauto_toggled)
        self._yauto_check.toggled.connect(self._update_plot)
        yrange_layout.addWidget(self._yauto_check)
        yrange_layout.addWidget(QLabel("Min:"))
        self._ymin_spin = QSpinBox()
        self._ymin_spin.setRange(-1, 500)
        self._ymin_spin.setValue(0)
        self._ymin_spin.setEnabled(False)
        self._ymin_spin.setToolTip("Visible row index (0 = bottom term)")
        self._ymin_spin.valueChanged.connect(self._update_plot)
        yrange_layout.addWidget(self._ymin_spin)
        yrange_layout.addWidget(QLabel("Max:"))
        self._ymax_spin = QSpinBox()
        self._ymax_spin.setRange(0, 500)
        self._ymax_spin.setValue(30)
        self._ymax_spin.setEnabled(False)
        self._ymax_spin.setToolTip("Visible row index (n-1 = top term)")
        self._ymax_spin.valueChanged.connect(self._update_plot)
        yrange_layout.addWidget(self._ymax_spin)
        axis_form.addRow("Y (rows):", yrange_row)

        dot_form.addRow(axis_group)

        # ── Colorbar ─────────────────────────────────────────────────────────
        cbar_group = QGroupBox("Colorbar  (FDR color mode only)")
        cbar_form = QFormLayout(cbar_group)
        cbar_form.setVerticalSpacing(6)

        # Z range
        zrange_row = QWidget()
        zrange_layout = QHBoxLayout(zrange_row)
        zrange_layout.setContentsMargins(0, 0, 0, 0)
        self._zauto_check = QCheckBox("Auto")
        self._zauto_check.setChecked(True)
        self._zauto_check.toggled.connect(self._on_zauto_toggled)
        self._zauto_check.toggled.connect(self._update_plot)
        zrange_layout.addWidget(self._zauto_check)
        zrange_layout.addWidget(QLabel("Min FDR:"))
        self._zmin_spin = QDoubleSpinBox()
        self._zmin_spin.setRange(0.0, 1.0)
        self._zmin_spin.setValue(0.000001)
        self._zmin_spin.setDecimals(6)
        self._zmin_spin.setSingleStep(0.0001)
        self._zmin_spin.setEnabled(False)
        self._zmin_spin.setToolTip("Color scale lower bound (most significant FDR)")
        self._zmin_spin.valueChanged.connect(self._update_plot)
        zrange_layout.addWidget(self._zmin_spin)
        zrange_layout.addWidget(QLabel("Max:"))
        self._zmax_spin = QDoubleSpinBox()
        self._zmax_spin.setRange(0.0, 1.0)
        self._zmax_spin.setValue(0.05)
        self._zmax_spin.setDecimals(4)
        self._zmax_spin.setSingleStep(0.005)
        self._zmax_spin.setEnabled(False)
        self._zmax_spin.setToolTip("Color scale upper bound (least significant FDR)")
        self._zmax_spin.valueChanged.connect(self._update_plot)
        zrange_layout.addWidget(self._zmax_spin)
        cbar_form.addRow("Z range:", zrange_row)

        self._cbar_cmap_combo = QComboBox()
        self._cbar_cmap_combo.addItems([
            'YlOrRd_r', 'RdPu_r', 'Blues_r', 'Greens_r', 'Purples_r',
            'viridis_r', 'plasma_r', 'magma_r', 'BuPu_r', 'RdYlBu',
        ])
        self._cbar_cmap_combo.currentTextChanged.connect(self._update_plot)
        cbar_form.addRow("Colormap:", self._cbar_cmap_combo)

        self._cbar_pos_combo = QComboBox()
        self._cbar_pos_combo.addItems(["right", "left", "bottom", "top"])
        self._cbar_pos_combo.currentTextChanged.connect(self._update_plot)
        cbar_form.addRow("Position:", self._cbar_pos_combo)

        self._cbar_size_spin = QDoubleSpinBox()
        self._cbar_size_spin.setRange(0.1, 1.0)
        self._cbar_size_spin.setValue(0.6)
        self._cbar_size_spin.setSingleStep(0.05)
        self._cbar_size_spin.setDecimals(2)
        self._cbar_size_spin.valueChanged.connect(self._update_plot)
        cbar_form.addRow("Size:", self._cbar_size_spin)

        dot_form.addRow(cbar_group)

        self._ctrl_tabs.addTab(dot_widget, "Dot Plot")

        layout.addWidget(self._ctrl_tabs)

    def _extra_buttons(self) -> list:
        # Network 탭 비활성화 중 — 재사용 시 아래 주석 해제
        # return [("Export Network", self._export_network)]
        return []

    # ── Auto-toggle helpers ───────────────────────────────────────────────────

    def _on_xauto_toggled(self, checked: bool):
        self._xmin_spin.setEnabled(not checked)
        self._xmax_spin.setEnabled(not checked)

    def _on_yauto_toggled(self, checked: bool):
        self._ymin_spin.setEnabled(not checked)
        self._ymax_spin.setEnabled(not checked)

    def _on_zauto_toggled(self, checked: bool):
        self._zmin_spin.setEnabled(not checked)
        self._zmax_spin.setEnabled(not checked)

    # ── Plot dispatcher ───────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()

        if not self.is_clustered:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5,
                    "이 다이얼로그는 클러스터링된 데이터가 필요합니다.\n"
                    "GO Clustering 다이얼로그에서 Apply를 먼저 실행하세요.",
                    ha='center', va='center', fontsize=13,
                    color='#555', wrap=True)
            ax.axis('off')
            self.canvas.draw()
            return

        # Network 탭 비활성화 중 — 항상 Dot Plot 표시
        # if self._ctrl_tabs.currentIndex() == 0:
        #     self._do_cluster_network()
        # else:
        self._do_dotplot()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_gene_sets(self, df: pd.DataFrame) -> dict:
        """index → set(genes) 딕셔너리 반환."""
        gene_col = next(
            (c for c in [StandardColumns.GENE_SYMBOLS, 'geneID', 'Genes', 'genes']
             if c in df.columns), None
        )
        result = {}
        for idx, row in df.iterrows():
            if gene_col:
                val = row.get(gene_col, '')
                result[idx] = set(str(val).split('/')) if pd.notna(val) and str(val).strip() else set()
            else:
                result[idx] = set()
        return result

    def _get_representatives(self, df: pd.DataFrame) -> pd.DataFrame:
        """각 유효 클러스터에서 FDR 최솟값 term 1개를 대표로 추출."""
        reps = []
        for cid in self._valid_ids:
            sub = df[df[StandardColumns.CLUSTER_ID] == cid]
            if sub.empty:
                continue
            if StandardColumns.FDR in sub.columns:
                reps.append(sub[StandardColumns.FDR].idxmin())
            else:
                reps.append(sub.index[0])
        return df.loc[reps].copy() if reps else pd.DataFrame(columns=df.columns)

    def _build_network(self, plot_df: pd.DataFrame, edge_threshold: float) -> nx.Graph:
        """Jaccard 유사도 기반 네트워크 구성."""
        gene_sets = self._get_gene_sets(plot_df)
        desc_col = next(
            (c for c in [StandardColumns.DESCRIPTION, 'Description', 'Term', 'term']
             if c in plot_df.columns), None
        )

        G = nx.Graph()
        for idx, row in plot_df.iterrows():
            label = str(row[desc_col]) if desc_col else str(idx)
            if len(label) > 55:
                label = label[:52] + '...'
            G.add_node(idx,
                       label=label,
                       cluster=row.get(StandardColumns.CLUSTER_ID, ''))

        nodes = list(plot_df.index)
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                gi = gene_sets.get(nodes[i], set())
                gj = gene_sets.get(nodes[j], set())
                union = len(gi | gj)
                if union == 0:
                    continue
                jac = len(gi & gj) / union
                if jac >= edge_threshold:
                    G.add_edge(nodes[i], nodes[j], weight=jac)
        return G

    def _compute_layout(self, G: nx.Graph) -> dict:
        layout = self._layout_combo.currentText()
        n = len(G.nodes())
        if layout == "Spring":
            k = max(0.5, 2.0 / max(1, n ** 0.5))
            return nx.spring_layout(G, k=k, seed=42, iterations=60)
        elif layout == "Kamada-Kawai":
            try:
                return nx.kamada_kawai_layout(G)
            except Exception:
                return nx.spring_layout(G, seed=42)
        elif layout == "Circular":
            return nx.circular_layout(G)
        else:
            return nx.spectral_layout(G) if n > 2 else nx.spring_layout(G, seed=42)

    def _node_colors(self, G: nx.Graph, plot_df: pd.DataFrame, color_by: str):
        """(colors, cmap, use_colorbar, colorbar_label, legend_handles) 반환."""
        nodes = list(G.nodes())

        if color_by == "FDR" and StandardColumns.FDR in plot_df.columns:
            vals = [float(plot_df.loc[n, StandardColumns.FDR]) if n in plot_df.index else 1.0
                    for n in nodes]
            colors = [-np.log10(max(v, 1e-300)) for v in vals]
            return colors, 'YlOrRd', True, '-log10(FDR)', []

        if color_by == "Ontology" and StandardColumns.ONTOLOGY in plot_df.columns:
            onts = list(dict.fromkeys(
                str(plot_df.loc[n, StandardColumns.ONTOLOGY]) if n in plot_df.index else ''
                for n in nodes
            ))
            cmap_ont = cm.tab10
            ont_map = {o: cmap_ont(i / max(len(onts), 1)) for i, o in enumerate(onts)}
            colors = [ont_map.get(
                str(plot_df.loc[n, StandardColumns.ONTOLOGY]) if n in plot_df.index else '', '#aaa'
            ) for n in nodes]
            handles = [Patch(color=ont_map[o], label=o) for o in onts]
            return colors, None, False, '', handles

        if color_by == "Direction" and StandardColumns.DIRECTION in plot_df.columns:
            dir_c = {'UP': '#e74c3c', 'DOWN': '#3498db', 'TOTAL': '#95a5a6'}
            colors = [dir_c.get(
                str(plot_df.loc[n, StandardColumns.DIRECTION]) if n in plot_df.index else 'TOTAL',
                '#95a5a6'
            ) for n in nodes]
            seen = {str(plot_df.loc[n, StandardColumns.DIRECTION])
                    for n in nodes if n in plot_df.index}
            handles = [Patch(color=dir_c.get(d, '#aaa'), label=d) for d in seen]
            return colors, None, False, '', handles

        # Cluster (default)
        cluster_vals = [G.nodes[n].get('cluster', 0) for n in nodes]
        unique_c = list(dict.fromkeys(cluster_vals))
        c_map = {c: i for i, c in enumerate(unique_c)}
        colors = [c_map.get(c, 0) for c in cluster_vals]
        return colors, 'tab20', False, '', []

    def _node_sizes(self, G: nx.Graph, plot_df: pd.DataFrame) -> list:
        size_by = self._net_node_size_combo.currentText()
        nodes = list(G.nodes())
        if size_by == "Gene Count" and StandardColumns.GENE_COUNT in plot_df.columns:
            return [max(80, float(plot_df.loc[n, StandardColumns.GENE_COUNT]) * 30)
                    if n in plot_df.index else 200 for n in nodes]
        if size_by == "Degree":
            deg = dict(G.degree())
            return [max(100, deg.get(n, 1) * 150) for n in nodes]
        return [300] * len(nodes)

    # ── Network tab plot ──────────────────────────────────────────────────────

    def _do_cluster_network(self):
        df = self.df.copy()

        # FDR 필터
        fdr_thr = self._fdr_spin.value()
        if StandardColumns.FDR in df.columns:
            df = df[df[StandardColumns.FDR] <= fdr_thr]

        selected = self._cluster_combo.currentText()

        if selected == "All (Representatives)":
            plot_df = self._get_representatives(df)
            title_prefix = f"All Clusters — Representatives (FDR ≤ {fdr_thr})"
        else:
            cid = selected.replace("Cluster ", "")
            plot_df = df[df[StandardColumns.CLUSTER_ID] == cid].copy()
            title_prefix = f"Cluster {cid}"

        ax = self.figure.add_subplot(111)

        if plot_df.empty:
            ax.text(0.5, 0.5, 'No data\n(FDR filter too strict?)',
                    ha='center', va='center', fontsize=13)
            ax.axis('off')
            self.canvas.draw()
            return

        if len(plot_df) == 1:
            desc_col = next((c for c in [StandardColumns.DESCRIPTION, 'Description']
                             if c in plot_df.columns), None)
            name = str(plot_df.iloc[0][desc_col]) if desc_col else 'Single term'
            ax.text(0.5, 0.5, f"{name}\n\n(단일 term — 연결 없음)",
                    ha='center', va='center', fontsize=11, wrap=True)
            ax.set_title(title_prefix, fontsize=12, fontweight='bold')
            ax.axis('off')
            self.canvas.draw()
            return

        edge_thr = self._edge_spin.value()
        G = self._build_network(plot_df, edge_thr)
        self.G = G

        if len(G.nodes()) == 0:
            ax.text(0.5, 0.5, 'No nodes to display', ha='center', va='center')
            ax.axis('off')
            self.canvas.draw()
            return

        pos = self._compute_layout(G)

        color_by = self._net_node_color_combo.currentText()
        node_col, cmap, use_cbar, cbar_label, legend_handles = \
            self._node_colors(G, plot_df, color_by)
        node_sz = self._node_sizes(G, plot_df)

        # 엣지
        if G.edges():
            weights = [G[u][v]['weight'] for u, v in G.edges()]
            nx.draw_networkx_edges(G, pos, alpha=0.4,
                                   width=[w * 5 for w in weights],
                                   edge_color='#888888', ax=ax)

        # 노드
        nc = nx.draw_networkx_nodes(
            G, pos,
            node_color=node_col,
            node_size=node_sz,
            cmap=cmap if cmap else None,
            alpha=0.85,
            edgecolors='black',
            linewidths=1.5,
            ax=ax
        )

        if use_cbar and nc is not None:
            self.figure.colorbar(nc, ax=ax, shrink=0.75, label=cbar_label)

        if legend_handles:
            ax.legend(handles=legend_handles, loc='upper left',
                      bbox_to_anchor=(1.01, 1), fontsize=8,
                      framealpha=0.9, title=color_by)

        # 레이블
        if self._show_labels_check.isChecked():
            nx.draw_networkx_labels(
                G, pos,
                nx.get_node_attributes(G, 'label'),
                font_size=7, font_weight='bold',
                bbox=dict(boxstyle='round,pad=0.3',
                          facecolor='white', edgecolor='none', alpha=0.75),
                ax=ax
            )

        n_nodes, n_edges = len(G.nodes()), len(G.edges())
        avg_deg = 2 * n_edges / n_nodes if n_nodes else 0
        ax.set_title(
            f"{title_prefix}\n"
            f"{n_nodes} nodes | {n_edges} edges | "
            f"Jaccard ≥ {edge_thr} | avg degree {avg_deg:.1f}",
            fontsize=11, fontweight='bold'
        )
        ax.axis('off')
        self.figure.tight_layout()

    # ── Dot Plot tab ──────────────────────────────────────────────────────────

    def _build_rep_df(self):
        """유효 클러스터 대표 term 표(rep_df)에 _cluster_size 를 붙여 반환. 없으면 None."""
        rep_df = self._get_representatives(self.df)
        if rep_df is None or rep_df.empty:
            return None
        cluster_sizes = self.df.groupby(StandardColumns.CLUSTER_ID).size().to_dict()
        rep_df = rep_df.copy()
        rep_df['_cluster_size'] = rep_df[StandardColumns.CLUSTER_ID].map(cluster_sizes).fillna(1)
        return rep_df

    def _dotplot_params(self) -> dict:
        x_auto = self._xauto_check.isChecked()
        y_auto = self._yauto_check.isChecked()
        return {
            'x_axis': self._xaxis_combo.currentText(),
            'color_by': self._dot_color_combo.currentText(),
            'size_by': self._dot_size_combo.currentText(),
            'sort_by': self._dot_sort_combo.currentText(),
            'top_n': self._top_n_spin.value(),
            'dot_size_min': self._dot_size_min_spin.value(),
            'dot_size_scale': self._dot_size_scale_spin.value(),
            'cmap': self._cbar_cmap_combo.currentText(),
            'z_auto': self._zauto_check.isChecked(),
            'z_min': self._zmin_spin.value(),
            'z_max': self._zmax_spin.value(),
            'colorbar_loc': self._cbar_pos_combo.currentText(),
            'colorbar_shrink': self._cbar_size_spin.value(),
            'show_size_legend': self._size_legend_check.isChecked(),
            'x_min': None if x_auto else self._xmin_spin.value(),
            'x_max': None if x_auto else self._xmax_spin.value(),
            'y_min': None if y_auto else self._ymin_spin.value(),
            'y_max': None if y_auto else self._ymax_spin.value(),
        }

    def _do_dotplot(self):
        """렌더는 순수 함수 src/plots/go_cluster_dot.py 에 있으며 번들과 공유한다."""
        from plots.go_cluster_dot import render_go_cluster_dot

        rep_df = self._build_rep_df()
        if rep_df is None:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No clustered data available',
                    ha='center', va='center', fontsize=13)
            ax.axis('off')
            self.canvas.draw()
            return

        # 동적 figure 크기 (표시될 term 수 기반)
        n_shown = min(len(rep_df), self._top_n_spin.value())
        dpi = self.figure.dpi
        canvas_w_px = self.canvas.width()
        w_in = (canvas_w_px / dpi) if canvas_w_px > 50 else 8.0
        self.figure.set_size_inches(w_in, max(5.0, n_shown * 0.38 + 1.5))

        render_go_cluster_dot(self.figure, rep_df, self._dotplot_params())

        # Y auto 시 spinbox 범위를 현재 term 수에 맞게 갱신 (UI 편의)
        if self._yauto_check.isChecked():
            self._ymax_spin.blockSignals(True)
            self._ymax_spin.setMaximum(max(n_shown - 1, 0))
            self._ymax_spin.setValue(max(n_shown - 1, 0))
            self._ymin_spin.setMaximum(max(n_shown - 1, 0))
            self._ymax_spin.blockSignals(False)

        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        rep_df = self._build_rep_df()
        return {
            'figure': self.figure,
            'dataframe': rep_df if rep_df is not None else pd.DataFrame(),
            'plot_params': self._dotplot_params(),
            'dataset_name': getattr(getattr(self, 'dataset', None), 'name', 'go_cluster'),
            'plot_type': 'go_cluster_dot',
            'figure_title': 'GO Cluster Summary Dot Plot',
            'figure_slug': 'go_cluster_dot',
            'source_stem': 'go_cluster_dot',
            'notes': 'Generated from cmg-seqviewer GO Cluster Dot plot (cluster representatives)',
        }

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_network(self):
        if self.G is None or len(self.G.nodes()) == 0:
            QMessageBox.warning(self, "No Network",
                                "Network 탭에서 네트워크를 먼저 생성하세요.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Network",
            "go_network.graphml",
            "GraphML Files (*.graphml);;GML Files (*.gml);;All Files (*)"
        )
        if file_path:
            if file_path.endswith('.gml'):
                nx.write_gml(self.G, file_path)
            else:
                nx.write_graphml(self.G, file_path)
            QMessageBox.information(self, "Success",
                                    f"Network exported to:\n{file_path}")
