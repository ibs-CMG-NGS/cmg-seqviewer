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
    QWidget, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
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
        # 그룹핑은 '추천 기본값'일 뿐이다: metadata 의 그룹이 복제를 제대로 묶으면 그대로,
        # 아니면(비어 있거나 샘플당 1개로 쪼개진 경우) 공용 규칙으로 조건을 추출해 복제를
        # 묶는다 (PCA와 동일 규칙). 어떤 경우든 아래 편집 테이블에서 사용자가 고칠 수 있어,
        # 이 네이밍 규칙이 안 맞는 다른 데이터셋에서도 그룹을 직접 지정할 수 있다.
        from utils.sample_grouping import auto_group_samples, useful_grouping
        if self.sample_columns and not useful_grouping(self.sample_groups, len(self.sample_columns)):
            self.sample_groups = auto_group_samples(self.sample_columns)

        # 샘플 → 그룹 역맵 (편집 테이블 초기값). 그룹에 없는 샘플은 빈 문자열(미지정).
        self._sample_to_group: dict = {}
        for _g, _cols in self.sample_groups.items():
            for _c in _cols:
                self._sample_to_group[_c] = _g
        for _c in self.sample_columns:
            self._sample_to_group.setdefault(_c, '')

        # 히트맵에 포함할 샘플(체크된 것만). 기본은 전부 포함. Apply 시 갱신.
        self._included_samples: set = set(self.sample_columns)

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

        # Sample Groups (editable) — auto 추론은 추천 기본값일 뿐, 사용자가 직접 고칠 수 있다.
        grp_box = QGroupBox("Sample Groups (editable)")
        grp_v = QVBoxLayout(grp_box)
        _grp_hint = QLabel("Edit each sample's group, then Apply. "
                           "Same label = same color; blank = ungrouped. "
                           "Untick a sample to exclude it from the heatmap.")
        _grp_hint.setWordWrap(True)
        grp_v.addWidget(_grp_hint)
        self.group_table = QTableWidget()
        self.group_table.setColumnCount(3)
        self.group_table.setHorizontalHeaderLabels(["✓", "Sample", "Group"])
        self.group_table.verticalHeader().setVisible(False)
        self.group_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked)
        _hh = self.group_table.horizontalHeader()
        _hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        _hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        _hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.group_table.setMaximumHeight(200)
        self._populate_group_table()
        grp_v.addWidget(self.group_table)
        # 전체 선택/해제 편의 버튼
        _sel_row = QHBoxLayout()
        _all_btn = QPushButton("Select all")
        _all_btn.clicked.connect(lambda: self._set_all_included(True))
        _none_btn = QPushButton("Clear all")
        _none_btn.clicked.connect(lambda: self._set_all_included(False))
        _sel_row.addWidget(_all_btn)
        _sel_row.addWidget(_none_btn)
        _sel_row.addStretch()
        grp_v.addLayout(_sel_row)
        apply_btn = QPushButton("Apply Groups")
        apply_btn.setToolTip("샘플 포함 여부와 그룹 지정을 적용하고 히트맵을 다시 그립니다.")
        apply_btn.clicked.connect(self._apply_group_table)
        grp_v.addWidget(apply_btn)
        layout.addWidget(grp_box)

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

        # 그룹 색 swatches — Apply Groups 시 재구성되도록 영속 컨테이너에 담는다.
        self._swatch_container = QWidget()
        self._swatch_layout = QGridLayout(self._swatch_container)
        self._swatch_layout.setContentsMargins(0, 0, 0, 0)
        self._swatch_layout.setSpacing(4)
        self._rebuild_group_swatches()
        display_form.addRow("Groups:", self._swatch_container)

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

    # ── Editable sample groups ─────────────────────────────────────────────

    def _recompute_group_colors(self):
        """현재 그룹 집합에 맞춰 색상 맵을 재구성한다(기존 색은 최대한 보존)."""
        new = {}
        for i, g in enumerate(self.sample_groups.keys()):
            new[g] = self._group_colors.get(g, _GROUP_PALETTE[i % len(_GROUP_PALETTE)])
        self._group_colors = new

    def _rebuild_group_swatches(self):
        """그룹 색 swatch 그리드를 현재 그룹/색상 상태로 다시 그린다."""
        layout = self._swatch_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for i, gname in enumerate(self.sample_groups.keys()):
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
            layout.addWidget(cell, row, col)

    def _populate_group_table(self):
        self.group_table.setRowCount(len(self.sample_columns))
        for r, col in enumerate(self.sample_columns):
            # col 0: include 체크박스
            chk = QTableWidgetItem()
            chk.setFlags((chk.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                         & ~Qt.ItemFlag.ItemIsEditable)
            chk.setCheckState(Qt.CheckState.Checked if col in self._included_samples
                              else Qt.CheckState.Unchecked)
            self.group_table.setItem(r, 0, chk)
            # col 1: 샘플명 (읽기 전용)
            sample_item = QTableWidgetItem(str(col))
            sample_item.setFlags(sample_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.group_table.setItem(r, 1, sample_item)
            # col 2: 그룹명 (편집)
            self.group_table.setItem(
                r, 2, QTableWidgetItem(str(self._sample_to_group.get(col, ''))))

    def _set_all_included(self, checked: bool):
        """모든 샘플 include 체크박스를 켜거나 끈다."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for r in range(self.group_table.rowCount()):
            item = self.group_table.item(r, 0)
            if item is not None:
                item.setCheckState(state)

    def _apply_group_table(self):
        """테이블의 include/그룹 지정을 읽어 포함 샘플·그룹핑·색상·swatch 를 갱신하고 다시 그린다."""
        mapping, groups, included = {}, {}, set()
        for r, col in enumerate(self.sample_columns):
            chk = self.group_table.item(r, 0)
            if chk is not None and chk.checkState() == Qt.CheckState.Checked:
                included.add(col)
            item = self.group_table.item(r, 2)
            g = (item.text().strip() if item else '')
            mapping[col] = g
            # 포함된 샘플만 그룹에 넣는다(제외된 샘플은 color bar/매트릭스에서 빠짐)
            if g and col in included:
                groups.setdefault(g, []).append(col)
        self._included_samples = included
        self._sample_to_group = mapping
        self.sample_groups = groups   # 전부 blank면 {} → 그룹 color bar 없음
        self._recompute_group_colors()
        self._rebuild_group_swatches()
        self._update_plot()

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

    # ── Render inputs (dialog + bundle 공유) ────────────────────────────────

    def _gene_labels(self, df_filtered) -> list:
        """gene_symbol(없으면 gene_id/index) 기반 유전자 라벨 리스트."""
        if 'gene_symbol' in df_filtered.columns:
            return df_filtered['gene_symbol'].fillna(
                df_filtered.get('gene_id', pd.Series(range(len(df_filtered)))).astype(str)
            ).astype(str).tolist()
        if 'gene_id' in df_filtered.columns:
            return df_filtered['gene_id'].astype(str).tolist()
        return list(df_filtered.index.astype(str))

    def _build_render_df(self):
        """렌더용 표(gene_label + 포함 샘플 열) 와 (n_genes, sample_cols) 반환.

        데이터가 없거나 표시할 샘플이 없으면 (None, reason, 0, []).
        """
        df_filtered = self._get_filtered_data()
        n_genes = len(df_filtered)
        if df_filtered.empty or not self.sample_columns:
            return None, "no_data", 0, []
        sample_cols = [
            c for c in self.sample_columns
            if c in df_filtered.columns and c in self._included_samples
        ]
        if not sample_cols:
            return None, "no_samples", n_genes, []
        render_df = df_filtered[sample_cols].copy()
        render_df.insert(0, 'gene_label', self._gene_labels(df_filtered))
        return render_df, None, n_genes, sample_cols

    def _plot_params(self, sample_cols=None, n_genes=None) -> dict:
        if sample_cols is None:
            sample_cols = [c for c in self.sample_columns if c in self._included_samples]
        title = (
            f"{self.dataset.name}  |  Z-score  |  "
            f"padj≤{self.padj_spin.value():.3g}, "
            f"baseMean≥{self.basemean_spin.value():.3g}"
            + (f", n={n_genes}" if n_genes is not None else "")
        )
        return {
            'gene_label_col': 'gene_label',
            'sample_columns': list(sample_cols),
            'sample_groups': {g: list(cols) for g, cols in self.sample_groups.items()},
            'group_colors': dict(self._group_colors),
            'cmap': self.cmap_combo.currentText(),
            'linkage': self.linkage_combo.currentText(),
            'metric': self.metric_combo.currentText(),
            'cluster_rows': self.cluster_rows_check.isChecked(),
            'cluster_cols': self.cluster_cols_check.isChecked(),
            'cut': self.enable_clusters_check.isChecked() and self.cluster_rows_check.isChecked(),
            'k': self.n_clusters_spin.value(),
            'z_auto': self.auto_scale_check.isChecked(),
            'z_min': self.vmin_spin.value(),
            'z_max': self.vmax_spin.value(),
            'show_gene_labels': self.show_gene_labels_check.isChecked(),
            'gene_fontsize': self.gene_fontsize_spin.value(),
            'show_col_labels': self.show_col_labels_check.isChecked(),
            'fig_width': self.fig_width_spin.value(),
            'fig_height': self.fig_height_spin.value(),
            'title': title,
        }

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()
        try:
            render_df, reason, n_genes, sample_cols = self._build_render_df()
            if render_df is None:
                ax = self.figure.add_subplot(111)
                msg = ("No samples selected.\nTick at least one sample in Sample Groups."
                       if reason == "no_samples"
                       else "No data after filtering.\nAdjust padj / baseMean thresholds.")
                ax.text(0.5, 0.5, msg, ha='center', va='center',
                        transform=ax.transAxes, fontsize=12, color='gray')
                self.canvas.draw()
                if reason == "no_data":
                    self.filter_info_label.setText("0")
                return

            self.filter_info_label.setText(str(n_genes))

            from plots.multi_group_heatmap import render_multi_group_heatmap
            fig, info = render_multi_group_heatmap(
                render_df, self._plot_params(sample_cols, n_genes))

            self._cluster_gene_lists = info.get('cluster_gene_lists', {})
            self._cluster_colors = info.get('cluster_colors', {})
            if self._cluster_gene_lists:
                parts = [f"C{c}: {len(g)}"
                         for c, g in sorted(self._cluster_gene_lists.items())]
                self.cluster_info_label.setText("  ".join(parts))
                self.go_enrichment_btn.setEnabled(True)
            else:
                self.cluster_info_label.setText("–")
                self.go_enrichment_btn.setEnabled(False)

            # seaborn clustermap creates its own figure — assign to self.figure and canvas
            self.figure = fig
            self.canvas.figure = fig
            fig.canvas = self.canvas
            self.canvas.draw()

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Heatmap plot failed: {e}", exc_info=True)
            QMessageBox.warning(self, "Plot Error", f"Failed to generate heatmap:\n{str(e)}")

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        render_df, reason, n_genes, sample_cols = self._build_render_df()
        if render_df is None:
            render_df = pd.DataFrame({'gene_label': []})
        slug = self._slugify(self.dataset.name)
        return {
            'figure': self.figure,
            'dataframe': render_df,
            'plot_params': self._plot_params(sample_cols, n_genes),
            'dataset_name': self.dataset.name,
            'plot_type': 'multi_group_heatmap',
            'figure_title': f"Multi-Group Heatmap — {self.dataset.name}",
            'figure_slug': f"{slug}_mg_heatmap",
            'source_stem': f"{slug}_mg_heatmap",
            'notes': 'Generated from cmg-seqviewer Multi-Group Heatmap '
                     '(gene x sample matrix; z-scored per row, clustermap).',
        }

    @staticmethod
    def _slugify(name: str) -> str:
        import re as _re
        return _re.sub(r'[^A-Za-z0-9._-]+', '_', str(name)).strip('_')[:60] or 'multi_group'

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
