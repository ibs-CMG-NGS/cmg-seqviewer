"""
Multi-Group Heatmap Dialog

LRT omnibus test 결과 + normalized abundance 데이터를 Z-score 기반
hierarchical clustermap 으로 시각화합니다.

Features:
  - padj / baseMean 필터
  - 상위 N 유전자 제한 (정렬 기준: padj 오름차순)
  - Z-score 정규화 (row 단위, 각 유전자 평균=0 표준편차=1)
  - 그룹별 color annotation bar (상단)
  - gene_symbol 레이블 (없으면 gene_id)
  - seaborn.clustermap 기반 (linkage 방법 선택)
  - Parquet 내보내기 (DB import 대비)
  - PNG / SVG / PDF 저장
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton,
    QCheckBox, QMessageBox, QFormLayout, QFileDialog,
    QWidget, QGridLayout
)
from PyQt6.QtCore import Qt

from models.data_models import Dataset, NormalizationType
from gui.base_plot_dialog import BasePlotDialog


# 그룹별 기본 색상 팔레트 (최대 12 그룹)
_GROUP_PALETTE = [
    '#E41A1C', '#377EB8', '#4DAF4A', '#FF7F00',
    '#984EA3', '#A65628', '#F781BF', '#999999',
    '#66C2A5', '#FC8D62', '#8DA0CB', '#E78AC3',
]

# 클러스터 color bar 팔레트 (그룹 팔레트와 시각적으로 구분)
_CLUSTER_PALETTE = [
    '#1B9E77', '#D95F02', '#7570B3', '#E7298A',
    '#66A61E', '#E6AB02', '#A6761D', '#666666',
    '#8DD3C7', '#BEBADA', '#FB8072', '#80B1D3',
]


class MultiGroupHeatmapDialog(BasePlotDialog):
    """Multi-Group Heatmap 다이얼로그"""

    def __init__(self, dataset: Dataset, parent=None):
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        self.sample_columns: list = dataset.metadata.get('sample_columns', [])
        self.sample_groups: dict = dataset.metadata.get('sample_groups', {})
        self.normalization_type: NormalizationType = dataset.metadata.get(
            'normalization_type', NormalizationType.NORMALIZED_COUNT
        )

        # metadata가 없을 때 dataframe에서 sample_columns/sample_groups 추론
        if not self.sample_columns and not self.df.empty:
            import re as _re
            _stat_lower = {
                'gene_id', 'gene_symbol', 'gene_name', 'basemean',
                'stat', 'pvalue', 'padj', 'lfcse', 'log2foldchange', 'log2fc',
            }
            self.sample_columns = [
                c for c in self.df.columns
                if c.lower() not in _stat_lower
                and pd.api.types.is_numeric_dtype(self.df[c])
            ]
        if not self.sample_groups and self.sample_columns:
            import re as _re
            _groups: dict = {}
            for col in self.sample_columns:
                m = _re.match(r'(.+?)\d+$', col)
                grp = m.group(1) if m else col
                _groups.setdefault(grp, []).append(col)
            self.sample_groups = _groups

        # 이미 gene-list 필터링된 child sheet 여부 감지
        self._is_prefiltered: bool = dataset.name.startswith('Filtered:')

        # 클러스터 결과 저장
        self._cluster_gene_lists: dict = {}
        self._cluster_colors: dict = {}

        # group color swatches state
        self._group_colors: dict = {}
        if self.sample_groups:
            group_names = list(self.sample_groups.keys())
            for i, gname in enumerate(group_names):
                self._group_colors[gname] = _GROUP_PALETTE[i % len(_GROUP_PALETTE)]

        super().__init__(f"Multi-Group Heatmap — {dataset.name}", parent, figsize=(14, 10))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Data Filter
        filter_group = QGroupBox("Data Filter")
        filter_grid = QGridLayout()
        filter_grid.setSpacing(4)
        filter_grid.setColumnStretch(1, 1)
        filter_grid.setColumnStretch(3, 1)

        self.padj_spin = QDoubleSpinBox()
        self.padj_spin.setRange(0.0001, 1.0)
        self.padj_spin.setSingleStep(0.01)
        self.padj_spin.setDecimals(4)
        self.padj_spin.setValue(1.0 if self._is_prefiltered else 0.05)
        self.padj_spin.setToolTip("LRT adjusted p-value cutoff")

        self.basemean_spin = QDoubleSpinBox()
        self.basemean_spin.setRange(0.0, 100000.0)
        self.basemean_spin.setSingleStep(5.0)
        self.basemean_spin.setDecimals(1)
        self.basemean_spin.setValue(0.0 if self._is_prefiltered else 10.0)
        self.basemean_spin.setToolTip("Minimum mean expression (removes low-expression genes)")

        filter_grid.addWidget(QLabel("padj ≤"), 0, 0)
        filter_grid.addWidget(self.padj_spin, 0, 1)
        filter_grid.addWidget(QLabel("baseMean ≥"), 0, 2)
        filter_grid.addWidget(self.basemean_spin, 0, 3)

        _row = 1
        if self._is_prefiltered:
            prefilter_label = QLabel("Pre-filtered — filters relaxed")
            prefilter_label.setStyleSheet("color: #1565C0; font-size: 8pt;")
            filter_grid.addWidget(prefilter_label, _row, 0, 1, 4)
            _row += 1

        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(10, 5000)
        self.top_n_spin.setSingleStep(50)
        self.top_n_spin.setValue(200)
        self.top_n_spin.setToolTip("Maximum genes to show (sorted by padj ascending)")

        self.filter_info_label = QLabel("–")
        self.filter_info_label.setStyleSheet("color: #555; font-size: 9pt;")

        filter_grid.addWidget(QLabel("Top N:"), _row, 0)
        filter_grid.addWidget(self.top_n_spin, _row, 1)
        filter_grid.addWidget(QLabel("Shown:"), _row, 2)
        filter_grid.addWidget(self.filter_info_label, _row, 3)

        filter_group.setLayout(filter_grid)
        layout.addWidget(filter_group)

        # Clustering
        cluster_group = QGroupBox("Clustering")
        cluster_grid = QGridLayout()
        cluster_grid.setSpacing(4)
        cluster_grid.setColumnStretch(1, 1)
        cluster_grid.setColumnStretch(3, 1)

        self.linkage_combo = QComboBox()
        self.linkage_combo.addItems(["ward", "average", "complete", "single"])
        self.linkage_combo.setToolTip("Linkage method for hierarchical clustering")

        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["euclidean", "correlation", "cosine"])
        self.metric_combo.setToolTip("Distance metric (ward requires euclidean)")

        cluster_grid.addWidget(QLabel("Linkage:"), 0, 0)
        cluster_grid.addWidget(self.linkage_combo, 0, 1)
        cluster_grid.addWidget(QLabel("Metric:"), 0, 2)
        cluster_grid.addWidget(self.metric_combo, 0, 3)

        self.cluster_rows_check = QCheckBox("Cluster genes (rows)")
        self.cluster_rows_check.setChecked(True)
        self.cluster_cols_check = QCheckBox("Cluster samples (cols)")
        self.cluster_cols_check.setChecked(False)
        self.cluster_cols_check.setToolTip("Uncheck to keep original sample order")

        cluster_grid.addWidget(self.cluster_rows_check, 1, 0, 1, 2)
        cluster_grid.addWidget(self.cluster_cols_check, 1, 2, 1, 2)

        cluster_group.setLayout(cluster_grid)
        layout.addWidget(cluster_group)

        # Gene Clusters
        cut_group = QGroupBox("Gene Clusters")
        cut_grid = QGridLayout()
        cut_grid.setSpacing(4)
        cut_grid.setColumnStretch(1, 1)
        cut_grid.setColumnStretch(3, 1)

        self.enable_clusters_check = QCheckBox("Cut dendrogram into clusters")
        self.enable_clusters_check.setChecked(False)
        self.enable_clusters_check.setToolTip(
            "Row dendrogram을 k개 클러스터로 분할 (Cluster genes 체크 필요)"
        )
        cut_grid.addWidget(self.enable_clusters_check, 0, 0, 1, 4)

        self.n_clusters_spin = QSpinBox()
        self.n_clusters_spin.setRange(2, 20)
        self.n_clusters_spin.setValue(3)
        self.n_clusters_spin.setEnabled(False)
        self.n_clusters_spin.setToolTip("Dendrogram을 분할할 클러스터 개수 (k)")
        self.enable_clusters_check.toggled.connect(self.n_clusters_spin.setEnabled)

        self.cluster_info_label = QLabel("–")
        self.cluster_info_label.setStyleSheet("color: #555; font-size: 9pt;")
        self.cluster_info_label.setWordWrap(True)

        cut_grid.addWidget(QLabel("k ="), 1, 0)
        cut_grid.addWidget(self.n_clusters_spin, 1, 1)
        cut_grid.addWidget(QLabel("Sizes:"), 1, 2)
        cut_grid.addWidget(self.cluster_info_label, 1, 3)

        self.go_enrichment_btn = QPushButton("GO Enrichment (per cluster)...")
        self.go_enrichment_btn.setEnabled(False)
        self.go_enrichment_btn.setToolTip(
            "Coming soon: Enrichr 온라인 GO enrichment analysis 클러스터별 실행.\n"
            "클러스터 활성화 후 Refresh Plot을 누르면 활성화됩니다."
        )
        cut_grid.addWidget(self.go_enrichment_btn, 2, 0, 1, 4)

        cut_group.setLayout(cut_grid)
        layout.addWidget(cut_group)

        # Display
        display_group = QGroupBox("Display")
        display_form = QFormLayout()
        display_form.setSpacing(6)

        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(["RdBu_r", "coolwarm", "bwr", "PiYG", "vlag", "seismic"])
        display_form.addRow("Color map:", self.cmap_combo)

        if self.sample_groups:
            group_names = list(self.sample_groups.keys())
            swatch_grid = QGridLayout()
            swatch_grid.setSpacing(4)
            for i, gname in enumerate(group_names):
                row, col = divmod(i, 2)
                cell = QWidget()
                cell_hbox = QHBoxLayout(cell)
                cell_hbox.setContentsMargins(0, 0, 0, 0)
                cell_hbox.setSpacing(3)
                name_lbl = QLabel(gname)
                name_lbl.setMaximumWidth(55)
                swatch_btn = QPushButton()
                swatch_btn.setFixedSize(22, 22)
                swatch_btn.setToolTip(f"Click to change color for {gname}")
                hex_color = self._group_colors[gname]
                swatch_btn.setStyleSheet(
                    f"QPushButton {{ background-color: {hex_color}; "
                    f"border: 1px solid #888; border-radius: 3px; }}"
                )

                def _make_picker(btn, name):
                    def _pick():
                        from PyQt6.QtWidgets import QColorDialog
                        from PyQt6.QtGui import QColor
                        old = QColor(self._group_colors.get(name, '#cccccc'))
                        color = QColorDialog.getColor(old, self, f"Color for {name}")
                        if color.isValid():
                            h = color.name()
                            self._group_colors[name] = h
                            btn.setStyleSheet(
                                f"QPushButton {{ background-color: {h}; "
                                f"border: 1px solid #888; border-radius: 3px; }}"
                            )
                    return _pick

                swatch_btn.clicked.connect(_make_picker(swatch_btn, gname))
                cell_hbox.addWidget(name_lbl)
                cell_hbox.addWidget(swatch_btn)
                swatch_grid.addWidget(cell, row, col)
            display_form.addRow("Groups:", swatch_grid)

        self.show_gene_labels_check = QCheckBox("Show gene labels")
        self.show_gene_labels_check.setChecked(True)
        self.show_gene_labels_check.setToolTip("Disable for large gene sets (>300)")
        display_form.addRow("", self.show_gene_labels_check)

        self.gene_fontsize_spin = QSpinBox()
        self.gene_fontsize_spin.setRange(4, 14)
        self.gene_fontsize_spin.setValue(7)
        display_form.addRow("Gene label size:", self.gene_fontsize_spin)

        self.show_col_labels_check = QCheckBox("Show sample labels")
        self.show_col_labels_check.setChecked(True)
        display_form.addRow("", self.show_col_labels_check)

        norm_label_text = self.normalization_type.value.replace('_', ' ').title()
        self.norm_info_label = QLabel(norm_label_text)
        self.norm_info_label.setStyleSheet("color: #555; font-size: 9pt;")
        display_form.addRow("Normalization:", self.norm_info_label)
        display_form.addRow(QLabel("Z-score: row (per gene)"))

        display_group.setLayout(display_form)
        layout.addWidget(display_group)

        # Color Scale
        scale_group = QGroupBox("Color Scale")
        scale_grid = QGridLayout()
        scale_grid.setSpacing(4)
        scale_grid.setColumnStretch(1, 1)
        scale_grid.setColumnStretch(3, 1)

        self.auto_scale_check = QCheckBox("Auto scale")
        self.auto_scale_check.setChecked(True)
        self.auto_scale_check.setToolTip("Automatically set vmin/vmax from data")
        scale_grid.addWidget(self.auto_scale_check, 0, 0, 1, 4)

        self.vmin_spin = QDoubleSpinBox()
        self.vmin_spin.setRange(-20.0, 0.0)
        self.vmin_spin.setSingleStep(0.5)
        self.vmin_spin.setDecimals(1)
        self.vmin_spin.setValue(-2.0)
        self.vmin_spin.setEnabled(False)
        scale_grid.addWidget(QLabel("Z min:"), 1, 0)
        scale_grid.addWidget(self.vmin_spin, 1, 1)

        self.vmax_spin = QDoubleSpinBox()
        self.vmax_spin.setRange(0.0, 20.0)
        self.vmax_spin.setSingleStep(0.5)
        self.vmax_spin.setDecimals(1)
        self.vmax_spin.setValue(2.0)
        self.vmax_spin.setEnabled(False)
        scale_grid.addWidget(QLabel("Z max:"), 1, 2)
        scale_grid.addWidget(self.vmax_spin, 1, 3)

        def _on_auto_scale_toggled(checked):
            self.vmin_spin.setEnabled(not checked)
            self.vmax_spin.setEnabled(not checked)
        self.auto_scale_check.toggled.connect(_on_auto_scale_toggled)

        scale_group.setLayout(scale_grid)
        layout.addWidget(scale_group)

        # Figure Size
        size_group = QGroupBox("Figure Size (inches)")
        size_grid = QGridLayout()
        size_grid.setSpacing(4)
        size_grid.setColumnStretch(1, 1)
        size_grid.setColumnStretch(3, 1)

        self.fig_width_spin = QSpinBox()
        self.fig_width_spin.setRange(8, 30)
        self.fig_width_spin.setValue(14)
        size_grid.addWidget(QLabel("Width:"), 0, 0)
        size_grid.addWidget(self.fig_width_spin, 0, 1)

        self.fig_height_spin = QSpinBox()
        self.fig_height_spin.setRange(6, 30)
        self.fig_height_spin.setValue(10)
        size_grid.addWidget(QLabel("Height:"), 0, 2)
        size_grid.addWidget(self.fig_height_spin, 0, 3)

        size_group.setLayout(size_grid)
        layout.addWidget(size_group)

    def _extra_buttons(self) -> list:
        return [
            ("Export CSV", self._export_csv),
            ("Export Parquet", self._export_parquet),
        ]

    # ── Data ──────────────────────────────────────────────────────────────

    def _get_filtered_data(self) -> pd.DataFrame:
        df = self.df.copy()

        if 'padj' in df.columns:
            df = df[df['padj'] <= self.padj_spin.value()]
        if 'baseMean' in df.columns:
            df = df[df['baseMean'] >= self.basemean_spin.value()]

        if df.empty:
            return pd.DataFrame()

        if 'padj' in df.columns:
            df = df.sort_values('padj')
        df = df.head(self.top_n_spin.value())

        return df

    def _make_col_colors(self, sample_cols: list) -> Optional[pd.Series]:
        if not self.sample_groups:
            return None

        group_color_map = dict(self._group_colors)
        colors = []
        for col in sample_cols:
            matched = None
            for group_name, group_cols in self.sample_groups.items():
                if col in group_cols:
                    matched = group_name
                    break
            colors.append(group_color_map.get(matched, '#cccccc'))

        return pd.Series(colors, index=sample_cols, name="Group")

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()

        try:
            df_filtered = self._get_filtered_data()
            n_genes = len(df_filtered)

            if df_filtered.empty or not self.sample_columns:
                ax = self.figure.add_subplot(111)
                ax.text(0.5, 0.5, "No data after filtering.\nAdjust padj / baseMean thresholds.",
                        ha='center', va='center', transform=ax.transAxes, fontsize=12, color='gray')
                self.canvas.draw()
                self.filter_info_label.setText("0")
                return

            self.filter_info_label.setText(str(n_genes))

            available_sample_cols = [c for c in self.sample_columns if c in df_filtered.columns]
            mat = df_filtered[available_sample_cols].copy()

            if 'gene_symbol' in df_filtered.columns:
                gene_labels = df_filtered['gene_symbol'].fillna(
                    df_filtered.get('gene_id', pd.Series(range(len(df_filtered)))).astype(str)
                ).tolist()
            else:
                id_col = 'gene_id' if 'gene_id' in df_filtered.columns else df_filtered.index
                gene_labels = df_filtered[id_col].astype(str).tolist() if 'gene_id' in df_filtered.columns \
                         else list(df_filtered.index.astype(str))
            mat.index = gene_labels

            from scipy.stats import zscore as _zscore
            mat_z = mat.apply(_zscore, axis=1, result_type='broadcast')
            mat_z = mat_z.fillna(0)

            col_colors = self._make_col_colors(available_sample_cols)

            linkage = self.linkage_combo.currentText()
            metric = self.metric_combo.currentText()
            if linkage == 'ward':
                metric = 'euclidean'

            do_cluster_rows = self.cluster_rows_check.isChecked()
            do_cut = self.enable_clusters_check.isChecked() and do_cluster_rows
            k = self.n_clusters_spin.value()

            from scipy.cluster.hierarchy import linkage as _sc_linkage, fcluster as _sc_fcluster
            from scipy.spatial.distance import pdist as _sc_pdist

            row_linkage_arr = None
            row_colors_cluster = None
            self._cluster_gene_lists = {}
            self._cluster_colors = {}

            if do_cluster_rows:
                row_dist = _sc_pdist(mat_z.values, metric=metric)
                row_linkage_arr = _sc_linkage(row_dist, method=linkage)

                if do_cut:
                    clust_labels = _sc_fcluster(row_linkage_arr, k, criterion='maxclust')
                    k_actual = len(set(clust_labels.tolist()))
                    c_pal = _CLUSTER_PALETTE[:k_actual]
                    row_colors_cluster = pd.Series(
                        [c_pal[(c - 1) % len(c_pal)] for c in clust_labels],
                        index=mat_z.index,
                        name="Cluster",
                    )
                    for gene, cid in zip(mat_z.index, clust_labels.tolist()):
                        self._cluster_gene_lists.setdefault(int(cid), []).append(gene)
                    self._cluster_colors = {
                        c: c_pal[(c - 1) % len(c_pal)]
                        for c in set(clust_labels.tolist())
                    }

            fig_w = self.fig_width_spin.value()
            fig_h = self.fig_height_spin.value()

            plt.close('all')

            yticklabels = self.show_gene_labels_check.isChecked()
            xticklabels = self.show_col_labels_check.isChecked()
            gene_fontsize = self.gene_fontsize_spin.value()

            vmin = None if self.auto_scale_check.isChecked() else self.vmin_spin.value()
            vmax = None if self.auto_scale_check.isChecked() else self.vmax_spin.value()

            cg = sns.clustermap(
                mat_z,
                figsize=(fig_w, fig_h),
                cmap=self.cmap_combo.currentText(),
                col_colors=col_colors,
                row_colors=row_colors_cluster,
                row_cluster=do_cluster_rows,
                row_linkage=row_linkage_arr,
                col_cluster=self.cluster_cols_check.isChecked(),
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
                cg.ax_heatmap.tick_params(axis='y', labelsize=gene_fontsize)
            if xticklabels:
                cg.ax_heatmap.tick_params(axis='x', labelsize=9, rotation=45)

            cg.ax_heatmap.set_xlabel("")
            cg.ax_heatmap.set_ylabel("")

            if self._cluster_gene_lists:
                parts = [
                    f"C{c}: {len(g)}"
                    for c, g in sorted(self._cluster_gene_lists.items())
                ]
                self.cluster_info_label.setText("  ".join(parts))
                self.go_enrichment_btn.setEnabled(True)
            else:
                self.cluster_info_label.setText("–")
                self.go_enrichment_btn.setEnabled(False)

            auto_title = (
                f"{self.dataset.name}  |  Z-score  |  "
                f"padj≤{self.padj_spin.value():.3g}, "
                f"baseMean≥{self.basemean_spin.value():.3g}, "
                f"n={n_genes}"
            )
            cg.figure.suptitle(auto_title, y=0.995, fontsize=10, va='top')

            has_xlabels = self.show_col_labels_check.isChecked()
            bottom_margin = 0.12 if has_xlabels else 0.04
            cg.figure.subplots_adjust(top=0.93, bottom=bottom_margin)

            # seaborn clustermap creates its own figure — assign to self.figure and canvas
            self.figure = cg.figure
            self.canvas.figure = cg.figure
            cg.figure.canvas = self.canvas
            self.canvas.draw()

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Heatmap plot failed: {e}", exc_info=True)
            QMessageBox.warning(self, "Plot Error", f"Failed to generate heatmap:\n{str(e)}")

    # ── Export ────────────────────────────────────────────────────────────

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", f"{self.dataset.name}_filtered",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            df_filtered = self._get_filtered_data()
            if self._cluster_gene_lists:
                label_to_cluster = {
                    gene: cid
                    for cid, genes in self._cluster_gene_lists.items()
                    for gene in genes
                }
                label_col = (
                    'gene_symbol' if 'gene_symbol' in df_filtered.columns
                    else ('gene_id' if 'gene_id' in df_filtered.columns else None)
                )
                if label_col:
                    df_filtered = df_filtered.copy()
                    df_filtered.insert(
                        df_filtered.columns.get_loc(label_col) + 1,
                        'gene_cluster',
                        df_filtered[label_col].map(label_to_cluster),
                    )
            df_filtered.to_csv(path, index=False)
            QMessageBox.information(self, "Exported", f"Data exported to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))

    def _export_parquet(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to Parquet", f"{self.dataset.name}",
            "Parquet Files (*.parquet)"
        )
        if not path:
            return
        try:
            from utils.multi_group_loader import MultiGroupLoader
            loader = MultiGroupLoader()
            loader.export_to_parquet(self.dataset, Path(path))
            QMessageBox.information(self, "Exported", f"Parquet saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))
