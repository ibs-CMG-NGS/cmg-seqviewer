"""
GO/KEGG Multi-Dataset Comparison Dot Plot Dialog

Wide-format comparison DataFrame (from _compare_go_terms) 을 받아
Y축: GO term, X축: dataset, 크기: FE, 색: -log10(FDR) 형태의 bubble plot 생성.
"""

from typing import List, Optional
import pandas as pd
import numpy as np

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSpinBox, QComboBox, QPushButton,
    QDoubleSpinBox, QMessageBox, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
import logging
logging.getLogger('matplotlib').setLevel(logging.WARNING)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar  # type: ignore
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from models.data_models import Dataset


class GOComparisonDotPlotDialog(QDialog):
    """GO/KEGG Multi-Dataset Comparison Dot Plot 다이얼로그"""

    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()

        meta = dataset.metadata or {}
        self.dataset_names: List[str] = meta.get('dataset_names', [])
        self.safe_names: List[str] = meta.get('safe_names', [])

        # GO/KEGG suffix 제거한 표시용 이름
        self.display_names: List[str] = meta.get(
            'display_names',
            [self._clean_display_name(n) for n in self.dataset_names]
        )

        self.setWindowTitle("GO/KEGG Comparison Dot Plot")
        self.setMinimumSize(1100, 850)

        self.figure = Figure(figsize=(12, 9), constrained_layout=False)
        self.canvas = FigureCanvas(self.figure)

        self._init_ui()
        self._update_plot()

    @staticmethod
    def _clean_display_name(name: str) -> str:
        """dataset 이름에서 GO/KEGG 분석 타입 suffix 제거"""
        import re
        cleaned = re.sub(
            r'\s+(GO\+KEGG|KEGG\+GO|GO|KEGG|GO_KEGG|KEGG_GO)\s*$',
            '', name, flags=re.IGNORECASE
        )
        return cleaned.strip()

    # ──────────────────────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────────────────────

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # ── Left panel ────────────────────────────────────────────────────────
        left_panel = QVBoxLayout()

        # Plot Settings
        settings_group = QGroupBox("Plot Settings")
        settings_layout = QFormLayout()

        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(5, 100)
        self.top_n_spin.setValue(20)
        self.top_n_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Top N terms:", self.top_n_spin)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Average FE (desc)", "Average FDR (asc)"])
        self.sort_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Sort by:", self.sort_combo)

        n_ds = max(len(self.dataset_names), 1)
        self.min_datasets_spin = QSpinBox()
        self.min_datasets_spin.setRange(1, n_ds)
        self.min_datasets_spin.setValue(1)
        self.min_datasets_spin.setToolTip(
            "Only show terms present (non-NaN FE) in at least N datasets.\n"
            "Set to max for intersection only."
        )
        self.min_datasets_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Present in ≥ N datasets:", self.min_datasets_spin)

        self.size_combo = QComboBox()
        self.size_combo.addItems(["Fold Enrichment", "Gene Count"])
        self.size_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Dot Size:", self.size_combo)

        from PyQt6.QtWidgets import QCheckBox
        self.transpose_check = QCheckBox("Transpose (X: Terms, Y: Datasets)")
        self.transpose_check.setChecked(False)
        self.transpose_check.toggled.connect(self._on_transpose_changed)
        settings_layout.addRow("", self.transpose_check)

        settings_group.setLayout(settings_layout)
        left_panel.addWidget(settings_group)

        # Color Bar Settings
        colorbar_group = QGroupBox("Color Bar Settings (-log10 FDR)")
        colorbar_layout = QFormLayout()

        self.palette_combo = QComboBox()
        self.palette_combo.addItems(
            ["YlOrRd", "viridis", "plasma", "coolwarm", "RdBu_r", "Spectral_r", "RdYlGn_r"]
        )
        self.palette_combo.currentTextChanged.connect(self._update_plot)
        colorbar_layout.addRow("Color Palette:", self.palette_combo)

        color_range_layout = QHBoxLayout()
        self.color_min_spin = QDoubleSpinBox()
        self.color_min_spin.setRange(0, 100)
        self.color_min_spin.setDecimals(2)
        self.color_min_spin.setValue(0.0)
        self.color_min_spin.setSingleStep(0.5)
        self.color_min_spin.valueChanged.connect(self._update_plot)
        color_range_layout.addWidget(QLabel("Min:"))
        color_range_layout.addWidget(self.color_min_spin)

        self.color_max_spin = QDoubleSpinBox()
        self.color_max_spin.setRange(0, 100)
        self.color_max_spin.setDecimals(2)
        self.color_max_spin.setValue(5.0)
        self.color_max_spin.setSingleStep(0.5)
        self.color_max_spin.valueChanged.connect(self._update_plot)
        color_range_layout.addWidget(QLabel("Max:"))
        color_range_layout.addWidget(self.color_max_spin)

        color_auto_btn = QPushButton("Auto")
        color_auto_btn.setMaximumWidth(55)
        color_auto_btn.clicked.connect(self._auto_color_range)
        color_range_layout.addWidget(color_auto_btn)

        colorbar_layout.addRow("-log10(FDR) Range:", color_range_layout)
        colorbar_group.setLayout(colorbar_layout)
        left_panel.addWidget(colorbar_group)

        # Plot Customization
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()

        self.title_edit = QLineEdit("GO/KEGG Term Comparison")
        self.title_edit.textChanged.connect(self._update_plot)
        custom_layout.addRow("Title:", self.title_edit)

        self.xlabel_edit = QLineEdit("Dataset")
        self.xlabel_edit.textChanged.connect(self._update_plot)
        custom_layout.addRow("X Label:", self.xlabel_edit)

        self.ylabel_edit = QLineEdit("GO/KEGG Terms")
        self.ylabel_edit.textChanged.connect(self._update_plot)
        custom_layout.addRow("Y Label:", self.ylabel_edit)

        size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(6, 24)
        self.width_spin.setValue(12)
        self.width_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addWidget(QLabel("W:"))
        size_layout.addWidget(self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(4, 20)
        self.height_spin.setValue(9)
        self.height_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addWidget(QLabel("H:"))
        size_layout.addWidget(self.height_spin)
        custom_layout.addRow("Figure Size (in):", size_layout)

        custom_group.setLayout(custom_layout)
        left_panel.addWidget(custom_group)

        left_panel.addStretch()
        main_layout.addLayout(left_panel)

        # ── Right panel ───────────────────────────────────────────────────────
        right_panel = QVBoxLayout()
        right_panel.addWidget(self.canvas)

        toolbar = NavigationToolbar(self.canvas, self)
        right_panel.addWidget(toolbar)

        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self._update_plot)
        btn_layout.addWidget(refresh_btn)

        save_btn = QPushButton("Save Figure")
        save_btn.clicked.connect(self._save_figure)
        btn_layout.addWidget(save_btn)

        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self._export_data)
        btn_layout.addWidget(export_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        right_panel.addLayout(btn_layout)
        main_layout.addLayout(right_panel, stretch=3)

    # ──────────────────────────────────────────────────────────────────────────
    #  Data helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _build_long_df(self) -> pd.DataFrame:
        """Wide-format → long-format 변환"""
        df = self.df
        id_cols = ['term_id', 'description']
        if 'ontology' in df.columns:
            id_cols.append('ontology')

        if not self.dataset_names:
            return pd.DataFrame()

        records = []
        for ds_name, safe, disp in zip(self.dataset_names, self.safe_names, self.display_names):
            fe_col  = f"{safe}_fe"
            fdr_col = f"{safe}_fdr"
            gc_col  = f"{safe}_gene_count"

            tmp = df[id_cols].copy()
            tmp['dataset']      = ds_name
            tmp['display_name'] = disp
            tmp['fe']         = pd.to_numeric(df[fe_col]  if fe_col  in df.columns else None, errors='coerce')
            tmp['fdr']        = pd.to_numeric(df[fdr_col] if fdr_col in df.columns else None, errors='coerce')
            tmp['gene_count'] = pd.to_numeric(df[gc_col]  if gc_col  in df.columns else None, errors='coerce')
            records.append(tmp)

        if not records:
            return pd.DataFrame()

        return pd.concat(records, ignore_index=True)

    def _get_plot_data(self):
        """Top-N 필터 + present-in-N 필터 적용 후 long_df 반환"""
        long_df = self._build_long_df()
        n_ds = len(self.dataset_names)

        # present-in ≥ N datasets 필터 (FE 가 non-NaN인 dataset 수 기준)
        min_ds = self.min_datasets_spin.value()
        if min_ds > 1:
            fe_count = long_df.groupby('term_id')['fe'].apply(
                lambda x: x.notna().sum()
            )
            valid_terms = fe_count[fe_count >= min_ds].index
            long_df = long_df[long_df['term_id'].isin(valid_terms)]

        if long_df.empty:
            return long_df

        # Top N 선택 기준 계산
        sort_by = self.sort_combo.currentText()
        if sort_by == "Average FE (desc)":
            rank = (
                long_df.groupby('term_id')['fe']
                .mean()
                .sort_values(ascending=False)
            )
        else:  # Average FDR (asc)
            rank = (
                long_df.groupby('term_id')['fdr']
                .mean()
                .sort_values(ascending=True)
            )

        top_n = self.top_n_spin.value()
        top_terms = rank.head(top_n).index
        long_df = long_df[long_df['term_id'].isin(top_terms)]

        # Y축 순서: 정렬 기준 반대 (위 → 높은 FE / 낮은 FDR)
        term_order = list(rank[rank.index.isin(top_terms)].index)
        long_df['_y_rank'] = long_df['term_id'].map(
            {t: i for i, t in enumerate(reversed(term_order))}
        )

        return long_df

    def _on_transpose_changed(self, checked: bool):
        """Transpose 토글 시 X/Y label 자동 교환"""
        self.xlabel_edit.blockSignals(True)
        self.ylabel_edit.blockSignals(True)
        if checked:
            self.xlabel_edit.setText("GO/KEGG Terms")
            self.ylabel_edit.setText("Dataset")
        else:
            self.xlabel_edit.setText("Dataset")
            self.ylabel_edit.setText("GO/KEGG Terms")
        self.xlabel_edit.blockSignals(False)
        self.ylabel_edit.blockSignals(False)
        self._update_plot()

    def _auto_color_range(self):
        long_df = self._build_long_df()
        fdr_vals = long_df['fdr'].dropna()
        fdr_vals = fdr_vals[fdr_vals > 0]
        if len(fdr_vals) > 0:
            log_vals = -np.log10(fdr_vals)
            self.color_min_spin.setValue(float(log_vals.min()))
            self.color_max_spin.setValue(float(log_vals.max()))
            self._update_plot()

    def _on_figure_size_changed(self):
        self.figure.set_size_inches(self.width_spin.value(), self.height_spin.value())
        self.canvas.draw()

    # ──────────────────────────────────────────────────────────────────────────
    #  Plot
    # ──────────────────────────────────────────────────────────────────────────

    def _update_plot(self):
        self.figure.clear()

        long_df = self._get_plot_data()

        if long_df.empty:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data to display\nAdjust filters',
                    ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

        ax = self.figure.add_subplot(111)

        # ── 축 매핑 ────────────────────────────────────────────────────────
        transpose = self.transpose_check.isChecked()

        # dataset display name 순서
        ds_order      = self.dataset_names
        disp_order    = self.display_names   # 표시용 이름 (suffix 제거)
        ds_idx        = {ds: i for i, ds in enumerate(ds_order)}
        long_df       = long_df.copy()
        long_df['_ds_idx'] = long_df['dataset'].map(ds_idx)

        # description label 얻기 (term_id → description)
        desc_map = (
            self.df.set_index('term_id')['description']
            .to_dict() if 'description' in self.df.columns else {}
        )

        # term rank → label
        y_ranks = sorted(long_df['_y_rank'].dropna().unique())
        term_by_rank = {}
        for _, row in long_df.drop_duplicates('_y_rank').iterrows():
            term_by_rank[row['_y_rank']] = row['term_id']

        term_labels = []
        for rank in y_ranks:
            tid  = term_by_rank.get(rank, '')
            desc = desc_map.get(tid, tid)
            label = str(desc)
            if len(label) > 55:
                label = label[:52] + '...'
            term_labels.append(label)

        # transpose 에 따른 실제 x/y 좌표 결정
        if transpose:
            # X = term rank,  Y = dataset index
            long_df['_x'] = long_df['_y_rank']
            long_df['_y'] = long_df['_ds_idx']
            x_ticks  = y_ranks
            x_labels = term_labels
            y_ticks  = list(range(len(disp_order)))
            y_labels = disp_order
            x_rot    = 40
            x_ha     = 'right'
            y_fs     = 10
        else:
            # X = dataset index,  Y = term rank
            long_df['_x'] = long_df['_ds_idx']
            long_df['_y'] = long_df['_y_rank']
            x_ticks  = list(range(len(disp_order)))
            x_labels = disp_order
            y_ticks  = y_ranks
            n_terms  = len(y_ranks)
            y_fs     = 9 if n_terms <= 15 else (8 if n_terms <= 25 else 7)
            y_labels = term_labels
            x_rot    = 35
            x_ha     = 'right'

        # ── 색 / 크기 계산 ─────────────────────────────────────────────────
        size_mode = self.size_combo.currentText()
        cmap      = self.palette_combo.currentText()
        vmin      = self.color_min_spin.value()
        vmax      = self.color_max_spin.value()
        if vmin >= vmax:
            vmax = vmin + 1.0

        # −log10(FDR)
        fdr_col  = long_df['fdr'].copy()
        fdr_col  = fdr_col.clip(lower=1e-300)
        neg_log_fdr = -np.log10(fdr_col)

        # Dot size (고정 생물학적 기준 범위로 정규화)
        _CMP_SIZE_NORM = {
            "Fold Enrichment": (20.0,  [(2.0, "2×"),       (5.0,  "5×"),       (15.0, "≥15×")]),
            "Gene Count":      (100.0, [(10,  "10 genes"),  (30,   "30 genes"),  (80,   "≥80 genes")]),
        }
        _S_MIN, _S_MAX = 40, 400

        if size_mode == "Fold Enrichment":
            raw_size = pd.to_numeric(long_df['fe'], errors='coerce').fillna(0)
        else:
            raw_size = pd.to_numeric(long_df['gene_count'], errors='coerce').fillna(0)

        s_min, s_max = float(raw_size.min()), float(raw_size.max())
        if size_mode in _CMP_SIZE_NORM:
            _cmp_norm_max, _cmp_size_rep = _CMP_SIZE_NORM[size_mode]
            sizes = _S_MIN + np.clip(raw_size / _cmp_norm_max, 0, 1) * (_S_MAX - _S_MIN)
        else:
            _cmp_norm_max, _cmp_size_rep = None, None
            sizes = pd.Series(150.0, index=raw_size.index)

        # ── Scatter: non-NaN FE (실제 값 있는 점) ─────────────────────────
        has_fe   = long_df['fe'].notna()
        has_fdr  = long_df['fdr'].notna()

        # 실제 데이터 점 (FE + FDR 모두 있음)
        mask_full = has_fe & has_fdr
        if mask_full.any():
            sc = ax.scatter(
                long_df.loc[mask_full, '_x'],
                long_df.loc[mask_full, '_y'],
                s=sizes[mask_full],
                c=neg_log_fdr[mask_full],
                cmap=cmap, vmin=vmin, vmax=vmax,
                alpha=0.85, edgecolors='black', linewidth=0.4, zorder=3
            )
        else:
            # colorbar 참조용 dummy scatter
            sc = ax.scatter([], [], c=[], cmap=cmap, vmin=vmin, vmax=vmax)

        # FE 있는데 FDR 없는 경우 (회색 점)
        mask_no_fdr = has_fe & ~has_fdr
        if mask_no_fdr.any():
            ax.scatter(
                long_df.loc[mask_no_fdr, '_x'],
                long_df.loc[mask_no_fdr, '_y'],
                s=sizes[mask_no_fdr],
                color='lightgray', edgecolors='gray', linewidth=0.4,
                alpha=0.6, zorder=2
            )

        # FE 없는 (dataset에 해당 term 없음) → 빈 테두리 원
        mask_absent = ~has_fe
        if mask_absent.any():
            ax.scatter(
                long_df.loc[mask_absent, '_x'],
                long_df.loc[mask_absent, '_y'],
                s=40,
                facecolors='none', edgecolors='#cccccc', linewidth=0.6,
                alpha=0.5, zorder=1
            )

        # ── Axes ───────────────────────────────────────────────────────────
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_labels, rotation=x_rot, ha=x_ha, fontsize=9)
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels, fontsize=y_fs)
        ax.set_xlabel(self.xlabel_edit.text(), fontsize=11, fontweight='bold')
        ax.set_ylabel(self.ylabel_edit.text(), fontsize=11, fontweight='bold')
        ax.set_title(self.title_edit.text(), fontsize=13, fontweight='bold')
        ax.grid(axis='both', alpha=0.2, linestyle='--')

        # 축 범위 여유
        if transpose:
            ax.set_xlim(min(y_ranks) - 0.6, max(y_ranks) + 0.6)
            ax.set_ylim(-0.6, len(disp_order) - 0.4)
        else:
            ax.set_xlim(-0.6, len(disp_order) - 0.4)
            if y_ranks:
                ax.set_ylim(min(y_ranks) - 0.6, max(y_ranks) + 0.6)

        # ── Colorbar ───────────────────────────────────────────────────────
        try:
            cbar = self.figure.colorbar(sc, ax=ax, shrink=0.5, pad=0.02, anchor=(0, 1.0))
            cbar.set_label('-log10(FDR)', fontsize=10)
        except Exception:
            pass  # empty scatter 등에서 colorbar 생성 실패 시 무시

        # ── Size legend (고정 3단계) ────────────────────────────────────
        if _cmp_size_rep is not None and _cmp_norm_max is not None:
            _leg_fontsize = 8

            def _ms(v):
                s = _S_MIN + np.clip(v / _cmp_norm_max, 0, 1) * (_S_MAX - _S_MIN)
                return 2.0 * np.sqrt(s / np.pi)  # scatter s(면적 pt²) → Line2D markersize(지름 pt)

            # 최대 원 지름 기준으로 labelspacing 동적 계산 (겁침 방지)
            _max_diam = max(_ms(v) for v, _ in _cmp_size_rep)
            _labelspacing = _max_diam / _leg_fontsize + 0.5

            legend_elements = [
                Line2D([0], [0], marker='o', color='none',
                       markerfacecolor='#808080', markeredgecolor='#333333',
                       markeredgewidth=0.8, markersize=_ms(v), label=lbl)
                for v, lbl in _cmp_size_rep
            ]
            leg = ax.legend(handles=legend_elements, title=size_mode,
                            loc='upper left', fontsize=_leg_fontsize,
                            title_fontsize=_leg_fontsize,
                            labelspacing=_labelspacing,
                            handlelength=0, handletextpad=1.2,
                            borderpad=0.9, framealpha=0.95,
                            edgecolor='#bbbbbb', fancybox=False,
                            bbox_to_anchor=(1.02, 0.30))
            leg.get_title().set_fontweight('bold')
        # ── Layout ─────────────────────────────────────────────────────────
        try:
            if transpose:
                self.figure.tight_layout(rect=(0, 0, 0.82, 1))
            else:
                self.figure.tight_layout(rect=(0, 0, 0.82, 1))
        except Exception:
            if transpose:
                self.figure.subplots_adjust(left=0.12, right=0.82, bottom=0.30)
            else:
                self.figure.subplots_adjust(left=0.35, right=0.82, bottom=0.15)

        self.canvas.draw()

    # ──────────────────────────────────────────────────────────────────────────
    #  Export
    # ──────────────────────────────────────────────────────────────────────────

    def _save_figure(self):
        from PyQt6.QtWidgets import QFileDialog
        import matplotlib

        default_name = f"go_comparison_dot_plot.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", default_name,
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;TIFF Files (*.tiff);;All Files (*)"
        )
        if not file_path:
            return

        if '.' not in file_path.split('/')[-1].split('\\')[-1]:
            file_path += '.png'

        fmt = file_path.rsplit('.', 1)[-1].lower()
        supported = self.figure.canvas.get_supported_filetypes()
        if fmt not in supported:
            QMessageBox.warning(
                self, "Unsupported Format",
                f"The format '.{fmt}' is not supported.\n"
                f"Supported: {', '.join(sorted(supported.keys()))}"
            )
            return

        try:
            if fmt in ('png', 'tiff', 'tif', 'jpg', 'jpeg'):
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
            else:
                self.figure.savefig(file_path, bbox_inches='tight')
            QMessageBox.information(self, "Saved", f"Figure saved:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save figure:\n{str(e)}")

    def _export_data(self):
        from PyQt6.QtWidgets import QFileDialog

        long_df = self._get_plot_data()
        if long_df.empty:
            QMessageBox.information(self, "No Data", "No data to export.")
            return

        export_cols = ['term_id', 'description']
        if 'ontology' in long_df.columns:
            export_cols.append('ontology')
        export_cols += ['dataset', 'fe', 'fdr', 'gene_count']
        export_df = long_df[[c for c in export_cols if c in long_df.columns]].copy()

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "go_comparison_data.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
        )
        if not file_path:
            return

        try:
            if file_path.endswith('.xlsx'):
                export_df.to_excel(file_path, index=False)
            else:
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                export_df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Exported", f"Data exported:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export data:\n{str(e)}")
