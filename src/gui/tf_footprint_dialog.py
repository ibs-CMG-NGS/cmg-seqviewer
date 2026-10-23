"""
TF Footprint Activity Dialog

TOBIAS BINDetect 결과를 TF Activity Scatter Plot으로 시각화한다.

- X축: cond1 mean footprint score
- Y축: cond2 mean footprint score
- 대각선 기준 위 = cond2에서 활성화된 TF (gain)
- 대각선 기준 아래 = cond1에서 활성화된 TF (loss)
- 점 색상: footprint_change 방향 + p-value 유의성
- 라벨: p-value cutoff 통과 TF에 자동 표시
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSpinBox, QCheckBox, QLabel,
    QFileDialog, QMessageBox,
)

from gui.base_plot_dialog import BasePlotDialog
from models.data_models import Dataset
from models.standard_columns import StandardColumns as SC
from utils.export_paths import remembered_save_path


class TFFootprintDialog(BasePlotDialog):
    """
    TOBIAS BINDetect TF Activity Scatter Plot 다이얼로그.

    X축 = cond1_score, Y축 = cond2_score.
    대각선 y=x 기준으로 위/아래에 활성화/억제된 TF 배치.
    """

    def __init__(self, dataset: Dataset, parent=None):
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset

        meta = dataset.metadata or {}
        self.cond1 = meta.get("cond1_name", "Condition 1")
        self.cond2 = meta.get("cond2_name", "Condition 2")

        super().__init__(
            f"TF Activity Plot — {dataset.name}  ({self.cond1} vs {self.cond2})",
            parent,
            figsize=(8, 7),
        )
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        info = QLabel(
            f"<b>X:</b> {self.cond1} score<br>"
            f"<b>Y:</b> {self.cond2} score<br>"
            "<small>점이 대각선 위 → cond2에서 더 결합<br>"
            "점이 대각선 아래 → cond1에서 더 결합</small>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        grp = QGroupBox("Plot Settings")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._pval_cutoff = QDoubleSpinBox()
        self._pval_cutoff.setRange(0.0, 1.0)
        self._pval_cutoff.setSingleStep(0.01)
        self._pval_cutoff.setDecimals(3)
        self._pval_cutoff.setValue(0.05)
        self._pval_cutoff.setToolTip("이 값 이하인 TF에 색상/라벨 표시")
        form.addRow("P-value cutoff:", self._pval_cutoff)

        self._min_change = QDoubleSpinBox()
        self._min_change.setRange(0.0, 5.0)
        self._min_change.setSingleStep(0.05)
        self._min_change.setDecimals(2)
        self._min_change.setValue(0.10)
        self._min_change.setToolTip("|change| 최솟값 (너무 작은 변화 제외)")
        form.addRow("|Change| ≥:", self._min_change)

        self._top_n_label = QSpinBox()
        self._top_n_label.setRange(0, 50)
        self._top_n_label.setValue(10)
        self._top_n_label.setToolTip("라벨 표시할 상위 TF 수 (|change| 기준)")
        form.addRow("Label top N:", self._top_n_label)

        self._dot_size = QSpinBox()
        self._dot_size.setRange(10, 200)
        self._dot_size.setValue(40)
        form.addRow("Dot size:", self._dot_size)

        self._show_diag = QCheckBox("Show diagonal (y=x)")
        self._show_diag.setChecked(True)
        form.addRow("", self._show_diag)

        grp.setLayout(form)
        layout.addWidget(grp)

        for w in [self._pval_cutoff, self._min_change, self._top_n_label, self._dot_size]:
            w.valueChanged.connect(self._update_plot)
        self._show_diag.stateChanged.connect(self._update_plot)

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Plot ──────────────────────────────────────────────────────────────

    def get_plot_params(self) -> dict:
        return {
            'pval_cutoff': self._pval_cutoff.value(),
            'min_change': self._min_change.value(),
            'dot_size': self._dot_size.value(),
            'show_diag': self._show_diag.isChecked(),
            'top_n_label': self._top_n_label.value(),
            'cond1': self.cond1,
            'cond2': self.cond2,
        }

    def _do_plot(self):
        from plots.tf_footprint import render_tf_footprint
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        render_tf_footprint(ax, self.dataset.dataframe, self.get_plot_params())
        self.figure.tight_layout()

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.dataset.dataframe,
            'plot_params': self.get_plot_params(),
            'dataset_name': self.dataset.name,
            'plot_type': 'tf_footprint',
            'figure_title': f'TF Activity — {self.dataset.name}',
            'figure_slug': 'tf_footprint',
            'source_stem': 'tf_footprint',
            'notes': 'Generated from cmg-seqviewer TF footprint activity',
        }

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        path, _ = remembered_save_path(
            self, "Export Footprint Data", "tf_footprint.xlsx",
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not path:
            return
        try:
            df = self.dataset.dataframe.copy()
            # 내보낼 때는 원래 조건명으로 컬럼 복원
            export_rename = {
                SC.COND1_SCORE: f"{self.cond1}_mean_score",
                SC.COND2_SCORE: f"{self.cond2}_mean_score",
                SC.COND1_BOUND: f"{self.cond1}_bound",
                SC.COND2_BOUND: f"{self.cond2}_bound",
                SC.FOOTPRINT_CHANGE: f"{self.cond1}_{self.cond2}_change",
                SC.FOOTPRINT_PVALUE: f"{self.cond1}_{self.cond2}_pvalue",
                SC.FOOTPRINT_MOTIF_NAME: "name",
                SC.FOOTPRINT_MOTIF_ID: "output_prefix",
            }
            df = df.rename(columns={k: v for k, v in export_rename.items() if k in df.columns})
            # 내부 분류 컬럼 제거
            df = df.drop(columns=[c for c in ["_cls", "fp_neg_log_pvalue"] if c in df.columns])

            if path.endswith(".csv"):
                df.to_csv(path, index=False)
            else:
                df.to_excel(path, index=False)
            QMessageBox.information(self, "Export", f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
