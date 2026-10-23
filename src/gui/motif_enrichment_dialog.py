"""
TF Motif Enrichment Dialog

HOMER knownResults.txt 또는 MEME AME 결과를 가로 막대 그래프로 시각화한다.
UP / DOWN 두 결과를 나란히 비교하는 모드도 지원한다.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QSpinBox, QDoubleSpinBox, QCheckBox, QLabel, QFileDialog, QMessageBox,
)

from gui.base_plot_dialog import BasePlotDialog
from models.data_models import Dataset
from models.standard_columns import StandardColumns as SC
from utils.export_paths import remembered_save_path


class MotifEnrichmentDialog(BasePlotDialog):
    """
    TF Motif Enrichment 가로 막대 그래프 다이얼로그.

    단일 데이터셋(UP 또는 DOWN peak 결과) 또는
    두 데이터셋(UP + DOWN)을 나란히 비교하는 모드를 지원한다.
    """

    def __init__(
        self,
        dataset: Dataset,
        dataset_down: Optional[Dataset] = None,
        parent=None,
    ):
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset
        self.dataset_down = dataset_down

        title = f"TF Motif Enrichment — {dataset.name}"
        if dataset_down:
            title += f"  vs  {dataset_down.name}"
        super().__init__(title, parent, figsize=(10, 7))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        grp = QGroupBox("Plot Settings")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._top_n = QSpinBox()
        self._top_n.setRange(5, 100)
        self._top_n.setValue(20)
        self._top_n.setToolTip("상위 N개 TF 표시 (-log10 p 기준)")
        form.addRow("Top N motifs:", self._top_n)

        self._qval_cutoff = QDoubleSpinBox()
        self._qval_cutoff.setRange(0.0, 1.0)
        self._qval_cutoff.setSingleStep(0.01)
        self._qval_cutoff.setDecimals(3)
        self._qval_cutoff.setValue(0.05)
        self._qval_cutoff.setToolTip("q-value 컷오프 (없으면 p-value만 사용)")
        form.addRow("Q-value cutoff:", self._qval_cutoff)

        self._show_pct = QCheckBox("Show % bar")
        self._show_pct.setChecked(False)
        self._show_pct.setToolTip("오른쪽 Y축에 foreground 비율(%) 오버레이")
        form.addRow("", self._show_pct)

        grp.setLayout(form)
        layout.addWidget(grp)

        if self.dataset_down is not None:
            info = QLabel(
                f"<b>UP:</b> {self.dataset.name}<br>"
                f"<b>DOWN:</b> {self.dataset_down.name}"
            )
            info.setWordWrap(True)
            layout.addWidget(info)

        for widget in [self._top_n, self._qval_cutoff, self._show_pct]:
            try:
                widget.valueChanged.connect(self._update_plot)
            except AttributeError:
                widget.stateChanged.connect(self._update_plot)

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Plot ──────────────────────────────────────────────────────────────

    def get_plot_params(self) -> dict:
        labels = {'single': self.dataset.name}
        if self.dataset_down is not None:
            labels = {'UP': self.dataset.name, 'DOWN': self.dataset_down.name}
        return {
            'top_n': self._top_n.value(),
            'qval_cutoff': self._qval_cutoff.value(),
            'show_pct': self._show_pct.isChecked(),
            'comparison': self.dataset_down is not None,
            'labels': labels,
            'dataset_name': self.dataset.name,
        }

    def _bundle_df(self) -> pd.DataFrame:
        df = self.dataset.dataframe.copy()
        if self.dataset_down is None:
            return df
        up = df.assign(direction='UP')
        down = self.dataset_down.dataframe.copy().assign(direction='DOWN')
        return pd.concat([up, down], ignore_index=True)

    def _do_plot(self):
        from plots.motif_enrichment import render_motif_enrichment
        self.figure.clear()
        render_motif_enrichment(self.figure, self._bundle_df(), self.get_plot_params())
        self.figure.tight_layout()

    def get_bundle_context(self) -> dict:
        params = self.get_plot_params()
        return {
            'figure': self.figure,
            'dataframe': self._bundle_df(),
            'plot_params': params,
            'dataset_name': self.dataset.name,
            'plot_type': 'motif_enrichment',
            'figure_title': 'TF Motif Enrichment',
            'figure_slug': 'motif_enrichment',
            'source_stem': 'motif_enrichment',
            'notes': 'Generated from cmg-seqviewer TF motif enrichment',
        }

    # ── Helpers ───────────────────────────────────────────────────────────

    def _prepare(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        필터링 + 정렬 + 상위 N개 반환.
        motif_pvalue 또는 log_pvalue 중 사용 가능한 것으로 정렬.
        """
        df = df.copy()

        # q-value 컷오프 적용 (컬럼이 있을 때만)
        qv = self._qval_cutoff.value()
        if SC.MOTIF_QVALUE in df.columns:
            df = df[pd.to_numeric(df[SC.MOTIF_QVALUE], errors="coerce") <= qv]

        if df.empty:
            return None

        # 정렬 기준 선택
        if SC.MOTIF_LOG_PVALUE in df.columns:
            sort_col = SC.MOTIF_LOG_PVALUE
        elif SC.MOTIF_PVALUE in df.columns:
            pv = pd.to_numeric(df[SC.MOTIF_PVALUE], errors="coerce").clip(lower=1e-300)
            df[SC.MOTIF_LOG_PVALUE] = -np.log10(pv)
            sort_col = SC.MOTIF_LOG_PVALUE
        else:
            return None

        df[sort_col] = pd.to_numeric(df[sort_col], errors="coerce")
        df = df.dropna(subset=[sort_col])
        df = df.sort_values(sort_col, ascending=False).head(self._top_n.value())

        # motif_name 없으면 motif_id로 대체
        if SC.MOTIF_NAME not in df.columns:
            df[SC.MOTIF_NAME] = df.get(SC.MOTIF_ID, pd.Series("unknown", index=df.index))

        return df.reset_index(drop=True)

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        path, _ = remembered_save_path(
            self, "Export Motif Data", "motif_enrichment.xlsx",
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not path:
            return

        try:
            df_up = self._prepare(self.dataset.dataframe)
            if path.endswith(".csv"):
                if df_up is not None:
                    df_up.to_csv(path, index=False)
            else:
                with pd.ExcelWriter(path, engine="openpyxl") as writer:
                    if df_up is not None:
                        label = "UP" if self.dataset_down else "Motifs"
                        df_up.to_excel(writer, sheet_name=label[:31], index=False)
                    if self.dataset_down is not None:
                        df_dn = self._prepare(self.dataset_down.dataframe)
                        if df_dn is not None:
                            df_dn.to_excel(writer, sheet_name="DOWN", index=False)
            QMessageBox.information(self, "Export", f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
