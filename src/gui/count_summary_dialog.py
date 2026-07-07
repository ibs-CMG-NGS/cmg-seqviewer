"""
DE/DA Count Summary Dialog

여러 DE / DA(ATAC) 데이터셋의 유의 up/down 개수를 0 기준 누적 막대로 집계·비교한다.
임계값(FDR, |log2FC|)은 다이얼로그 내에서 조절하며, 변경 시 즉시 재집계된다.
"""
import logging
from typing import List

import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter
from PyQt6.QtWidgets import (
    QVBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox, QCheckBox,
    QFileDialog, QMessageBox,
)

from models.data_models import Dataset, DatasetType
from models.standard_columns import StandardColumns
from gui.base_plot_dialog import BasePlotDialog

_UP_COLOR = '#c0392b'
_DOWN_COLOR = '#2c6fbb'


class CountSummaryDialog(BasePlotDialog):
    """선택한 DE/DA 데이터셋들의 유의 up/down 개수 누적 막대 차트."""

    def __init__(self, datasets: List[Dataset], parent=None):
        self.logger = logging.getLogger(__name__)
        self.datasets = datasets
        self._counts_df = None  # 마지막 집계 결과 (Export용)
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

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Plot ──────────────────────────────────────────────────────────────

    def _compute_counts(self):
        """데이터셋별 up/down/total 집계 → DataFrame."""
        padj_max = self._fdr_spin.value()
        lfc_min = self._lfc_spin.value()
        lfc_col = StandardColumns.LOG2FC
        padj_col = StandardColumns.ADJ_PVALUE

        rows = []
        for ds in self.datasets:
            df = ds.dataframe
            label = ds.metadata.get('experiment_condition') or ds.name
            if df is None or lfc_col not in df.columns or padj_col not in df.columns:
                rows.append({'label': label, 'up': 0, 'down': 0, 'total': 0})
                continue
            total = int(df[lfc_col].notna().sum())
            sig = df[(df[padj_col] <= padj_max) & (df[lfc_col].abs() >= lfc_min)]
            up = int((sig[lfc_col] > 0).sum())
            down = int((sig[lfc_col] < 0).sum())
            rows.append({'label': label, 'up': up, 'down': down, 'total': total})
        return pd.DataFrame(rows)

    def _do_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        counts = self._compute_counts()
        self._counts_df = counts
        if counts.empty:
            ax.text(0.5, 0.5, "No datasets to plot.", ha='center', va='center',
                    transform=ax.transAxes, color='#888888')
            self.canvas.draw()
            return

        as_pct = self._pct_check.isChecked()
        ups = counts['up'].astype(float).tolist()
        downs = counts['down'].astype(float).tolist()
        if as_pct:
            totals = [t if t else 1 for t in counts['total'].tolist()]
            ups = [100.0 * u / t for u, t in zip(ups, totals)]
            downs = [100.0 * d / t for d, t in zip(downs, totals)]

        x = list(range(len(counts)))
        ax.bar(x, ups, color=_UP_COLOR, label='Up-regulated')
        ax.bar(x, [-d for d in downs], color=_DOWN_COLOR, label='Down-regulated')
        ax.axhline(0, color='#333333', linewidth=0.8)

        # 막대 위/아래에 원본 개수 라벨
        raw_up = counts['up'].tolist()
        raw_down = counts['down'].tolist()
        for xi, yu, n in zip(x, ups, raw_up):
            if n > 0:
                ax.text(xi, yu, f"{n:,}", ha='center', va='bottom', fontsize=8)
        for xi, yd, n in zip(x, downs, raw_down):
            if n > 0:
                ax.text(xi, -yd, f"{n:,}", ha='center', va='top', fontsize=8)

        ax.set_xticks(x)
        ax.set_xticklabels(counts['label'].tolist(), rotation=30, ha='right', fontsize=8)

        all_atac = all(ds.dataset_type == DatasetType.ATAC_SEQ for ds in self.datasets)
        unit = 'peaks' if all_atac else 'genes'
        if as_pct:
            ax.set_ylabel(f"% of {unit}")
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{abs(v):.0f}"))
        else:
            ax.set_ylabel(f"Number of {unit}")
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{abs(int(v)):,}"))

        ax.set_title(
            f"Significant {unit} (FDR ≤ {self._fdr_spin.value():g}, "
            f"|log2FC| ≥ {self._lfc_spin.value():g})",
            fontsize=12, fontweight='bold',
        )
        ax.legend(fontsize=8, loc='upper right')
        ax.margins(y=0.15)
        self.figure.tight_layout()
        self.canvas.draw()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        if self._counts_df is None or self._counts_df.empty:
            QMessageBox.warning(self, "No Data", "There is no aggregated data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
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
