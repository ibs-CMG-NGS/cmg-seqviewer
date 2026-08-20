"""
DE/DA Count Summary Dialog

여러 DE / DA(ATAC) 데이터셋의 유의 up/down 개수를 0 기준 누적 막대로 집계·비교한다.
임계값(FDR, |log2FC|)은 다이얼로그 내에서 조절하며, 변경 시 즉시 재집계된다.
"""
import logging
from typing import List

import pandas as pd
from PyQt6.QtWidgets import (
    QVBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox, QCheckBox,
    QFileDialog, QMessageBox, QPushButton, QColorDialog,
)
from PyQt6.QtGui import QColor

from models.data_models import Dataset, DatasetType
from models.standard_columns import StandardColumns
from gui.base_plot_dialog import BasePlotDialog
from utils.export_paths import remembered_save_path


class CountSummaryDialog(BasePlotDialog):
    """선택한 DE/DA 데이터셋들의 유의 up/down 개수 누적 막대 차트."""

    def __init__(self, datasets: List[Dataset], parent=None):
        self.logger = logging.getLogger(__name__)
        self.datasets = datasets
        self._counts_df = None  # 마지막 집계 결과 (Export용)
        # 막대 색 (사용자 지정 가능). _setup_controls 가 super().__init__ 안에서 호출되므로
        # 그 전에 초기화한다.
        self._up_color = '#c0392b'
        self._down_color = '#2c6fbb'
        super().__init__("DE/DA Count Summary", parent, figsize=(9, 6))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        group = QGroupBox("Significance Thresholds")
        form = QFormLayout()

        self._fdr_spin = QDoubleSpinBox()
        self._fdr_spin.setDecimals(4)
        self._fdr_spin.setRange(0.0, 1.0)
        self._fdr_spin.setSingleStep(0.01)
        self._fdr_spin.setValue(0.05)
        self._fdr_spin.valueChanged.connect(self._update_plot)
        form.addRow("FDR ≤", self._fdr_spin)

        self._lfc_spin = QDoubleSpinBox()
        self._lfc_spin.setDecimals(3)
        self._lfc_spin.setRange(0.0, 20.0)
        self._lfc_spin.setSingleStep(0.1)
        self._lfc_spin.setValue(1.0)
        self._lfc_spin.valueChanged.connect(self._update_plot)
        form.addRow("|log2FC| ≥", self._lfc_spin)

        self._pct_check = QCheckBox("Show as % of total")
        self._pct_check.toggled.connect(self._update_plot)
        form.addRow(self._pct_check)

        group.setLayout(form)
        layout.addWidget(group)

        # ── Bar colors ──
        color_group = QGroupBox("Bar Colors")
        color_form = QFormLayout()
        self._up_swatch = self._make_color_swatch('_up_color')
        color_form.addRow("Up-regulated", self._up_swatch)
        self._down_swatch = self._make_color_swatch('_down_color')
        color_form.addRow("Down-regulated", self._down_swatch)
        color_group.setLayout(color_form)
        layout.addWidget(color_group)

    def _make_color_swatch(self, attr: str) -> QPushButton:
        """attr(예 '_up_color')에 연결된 색 스와치 버튼. 클릭 시 색 선택 → 재플롯."""
        btn = QPushButton()
        btn.setFixedSize(40, 22)
        btn.setToolTip("Click to change bar color")

        def _apply_style():
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {getattr(self, attr)}; "
                f"border: 1px solid #888; border-radius: 3px; }}")
        _apply_style()

        def _pick():
            color = QColorDialog.getColor(QColor(getattr(self, attr)), self, "Bar color")
            if color.isValid():
                setattr(self, attr, color.name())
                _apply_style()
                self._update_plot()

        btn.clicked.connect(_pick)
        return btn

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Plot ──────────────────────────────────────────────────────────────

    def _build_long_df(self):
        """데이터셋들을 long-format(dataset/log2fc/adj_pvalue)으로 병합. (df, order) 반환."""
        lfc_col = StandardColumns.LOG2FC
        padj_col = StandardColumns.ADJ_PVALUE
        frames, order = [], []
        for ds in self.datasets:
            label = ds.metadata.get('experiment_condition') or ds.name
            order.append(label)
            df = ds.dataframe
            if df is None or lfc_col not in df.columns or padj_col not in df.columns:
                continue
            frames.append(pd.DataFrame({
                'dataset': label,
                'log2fc': pd.to_numeric(df[lfc_col], errors='coerce').values,
                'adj_pvalue': pd.to_numeric(df[padj_col], errors='coerce').values,
            }))
        long_df = pd.concat(frames, ignore_index=True) if frames else \
            pd.DataFrame(columns=['dataset', 'log2fc', 'adj_pvalue'])
        return long_df, order

    def _plot_params(self, order=None) -> dict:
        if order is None:
            order = [ds.metadata.get('experiment_condition') or ds.name for ds in self.datasets]
        all_atac = all(ds.dataset_type == DatasetType.ATAC_SEQ for ds in self.datasets)
        return {
            'fdr_max': self._fdr_spin.value(),
            'lfc_min': self._lfc_spin.value(),
            'as_pct': self._pct_check.isChecked(),
            'unit': 'peaks' if all_atac else 'genes',
            'order': order,
            'up_color': self._up_color,
            'down_color': self._down_color,
        }

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/count_summary.py 에 있으며 번들과 공유한다."""
        from plots.count_summary import render_count_summary

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        long_df, order = self._build_long_df()
        self._counts_df = render_count_summary(ax, long_df, self._plot_params(order))
        self.figure.tight_layout()
        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        long_df, order = self._build_long_df()
        return {
            'figure': self.figure,
            'dataframe': long_df,
            'plot_params': self._plot_params(order),
            'dataset_name': 'count_summary',
            'plot_type': 'count_summary',
            'figure_title': 'DE/DA Count Summary',
            'figure_slug': 'count_summary',
            'source_stem': 'count_summary',
            'notes': 'Generated from cmg-seqviewer DE/DA Count Summary (long-format input)',
        }

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        if self._counts_df is None or self._counts_df.empty:
            QMessageBox.warning(self, "No Data", "There is no aggregated data to export.")
            return
        path, _ = remembered_save_path(
            self, "Export Count Summary", "count_summary.csv",
            "CSV (*.csv);;TSV (*.tsv);;Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            out = self._counts_df.rename(columns={'label': 'dataset'})
            if path.endswith('.xlsx'):
                out.to_excel(path, index=False)
            elif path.endswith('.tsv'):
                out.to_csv(path, sep='\t', index=False)
            else:
                out.to_csv(path, index=False)
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")
