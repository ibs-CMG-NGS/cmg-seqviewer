"""
GO/KEGG Multi-Dataset Comparison Dot Plot Dialog

Wide-format comparison DataFrame (from _compare_go_terms) 을 받아
Y축: GO term, X축: dataset, 크기: FE, 색: -log10(FDR) 형태의 bubble plot 생성.
"""

from typing import List
import pandas as pd
import numpy as np

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QWidget, QSpinBox, QComboBox, QPushButton, QCheckBox,
    QDoubleSpinBox, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt

from models.data_models import Dataset
from gui.base_plot_dialog import BasePlotDialog
from utils.export_paths import remembered_save_path


class GOComparisonDotPlotDialog(BasePlotDialog):
    """GO/KEGG Multi-Dataset Comparison Dot Plot 다이얼로그"""

    def __init__(self, dataset: Dataset, parent=None):
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        self._plotted_df = None  # 마지막 render_go_comparison_dot() 결과(선택+필터 반영) — Export 용

        meta = dataset.metadata or {}
        self.dataset_names: List[str] = meta.get('dataset_names', [])
        self.safe_names: List[str] = meta.get('safe_names', [])
        self.display_names: List[str] = meta.get(
            'display_names',
            [self._clean_display_name(n) for n in self.dataset_names]
        )

        super().__init__("GO/KEGG Comparison Dot Plot", parent, figsize=(12, 9))
        self._update_plot()

    @staticmethod
    def _clean_display_name(name: str) -> str:
        import re
        cleaned = re.sub(
            r'\s+(GO\+KEGG|KEGG\+GO|GO|KEGG|GO_KEGG|KEGG_GO)\s*$',
            '', name, flags=re.IGNORECASE
        )
        return cleaned.strip()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
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

        self.transpose_check = QCheckBox("Transpose (X: Terms, Y: Datasets)")
        self.transpose_check.setChecked(False)
        self.transpose_check.toggled.connect(self._on_transpose_changed)
        settings_layout.addRow("", self.transpose_check)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Color Bar Settings
        colorbar_group = QGroupBox("Color Bar Settings (-log10 FDR)")
        colorbar_layout = QFormLayout()

        self.palette_combo = QComboBox()
        self.palette_combo.addItems(
            ["YlOrRd", "viridis", "plasma", "coolwarm", "RdBu_r", "Spectral_r", "RdYlGn_r"]
        )
        self.palette_combo.currentTextChanged.connect(self._update_plot)
        colorbar_layout.addRow("Color Palette:", self.palette_combo)

        self.color_min_spin = QDoubleSpinBox()
        self.color_min_spin.setRange(0, 100)
        self.color_min_spin.setDecimals(2)
        self.color_min_spin.setValue(0.0)
        self.color_min_spin.setSingleStep(0.5)
        self.color_min_spin.valueChanged.connect(self._update_plot)
        colorbar_layout.addRow("-log10(FDR) Min:", self.color_min_spin)

        self.color_max_spin = QDoubleSpinBox()
        self.color_max_spin.setRange(0, 100)
        self.color_max_spin.setDecimals(2)
        self.color_max_spin.setValue(5.0)
        self.color_max_spin.setSingleStep(0.5)
        self.color_max_spin.valueChanged.connect(self._update_plot)
        color_auto_btn = QPushButton("Auto")
        color_auto_btn.setMaximumWidth(55)
        color_auto_btn.clicked.connect(self._auto_color_range)
        fdr_max_row = QWidget()
        fdr_max_rl = QHBoxLayout(fdr_max_row)
        fdr_max_rl.setContentsMargins(0, 0, 0, 0)
        fdr_max_rl.setSpacing(4)
        fdr_max_rl.addWidget(self.color_max_spin)
        fdr_max_rl.addWidget(color_auto_btn)
        colorbar_layout.addRow("-log10(FDR) Max:", fdr_max_row)
        colorbar_group.setLayout(colorbar_layout)
        layout.addWidget(colorbar_group)

        # track axis labels for use in _do_plot (updated by transpose toggle)
        self._xlabel_text = "Dataset"
        self._ylabel_text = "GO/KEGG Terms"

        # Plot Customization
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()

        self.width_spin = QSpinBox()
        self.width_spin.setRange(6, 24)
        self.width_spin.setValue(12)
        self.width_spin.valueChanged.connect(self._on_figure_size_changed)
        custom_layout.addRow("Width (in):", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(4, 20)
        self.height_spin.setValue(9)
        self.height_spin.valueChanged.connect(self._on_figure_size_changed)
        custom_layout.addRow("Height (in):", self.height_spin)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_transpose_changed(self, checked: bool):
        if checked:
            self._xlabel_text = "GO/KEGG Terms"
            self._ylabel_text = "Dataset"
        else:
            self._xlabel_text = "Dataset"
            self._ylabel_text = "GO/KEGG Terms"
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

    # ── Data helpers ──────────────────────────────────────────────────────

    def _build_long_df(self) -> pd.DataFrame:
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

    # ── Plot ──────────────────────────────────────────────────────────────

    def _plot_params(self) -> dict:
        return {
            'dataset_names': list(self.dataset_names),
            'safe_names': list(self.safe_names),
            'display_names': list(self.display_names),
            'top_n': self.top_n_spin.value(),
            'sort_by': self.sort_combo.currentText(),
            'min_datasets': self.min_datasets_spin.value(),
            'size_mode': self.size_combo.currentText(),
            'transpose': self.transpose_check.isChecked(),
            'palette': self.palette_combo.currentText(),
            'color_min': self.color_min_spin.value(),
            'color_max': self.color_max_spin.value(),
            'xlabel': self._xlabel_text,
            'ylabel': self._ylabel_text,
        }

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/go_comparison_dot.py 에 있으며 번들과 공유한다."""
        from plots.go_comparison_dot import render_go_comparison_dot

        self.figure.clear()
        # 실제 그려진(필터+top-N+정렬 반영) long_df 를 저장 — Export Data 가 별도 로직 없이 재사용한다.
        self._plotted_df = render_go_comparison_dot(self.figure, self.df, self._plot_params())
        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.df,
            'plot_params': self._plot_params(),
            'dataset_name': self.dataset.name,
            'plot_type': 'go_comparison_dot',
            'figure_title': 'GO/KEGG Comparison Dot Plot',
            'figure_slug': 'go_comparison_dot',
            'source_stem': 'go_comparison_dot',
            'notes': 'Generated from cmg-seqviewer GO/KEGG Comparison Dot plot',
        }

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        from PyQt6.QtWidgets import QFileDialog

        # 별도로 필터/top-N/정렬 로직을 복제하지 않고, 실제 그려진 long_df(render_go_comparison_dot
        # 의 반환값)를 그대로 쓴다 — 그림/export 불일치 방지.
        long_df = self._plotted_df
        if long_df is None or long_df.empty:
            QMessageBox.information(self, "No Data", "No data to export.")
            return

        export_cols = ['term_id', 'description']
        if 'ontology' in long_df.columns:
            export_cols.append('ontology')
        export_cols += ['dataset', 'fe', 'fdr', 'gene_count']
        export_df = long_df[[c for c in export_cols if c in long_df.columns]].copy()

        file_path, _ = remembered_save_path(
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
