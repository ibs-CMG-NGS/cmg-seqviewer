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

    def _do_plot(self):
        self.figure.clear()

        if self.dataset_down is not None:
            self._plot_comparison()
        else:
            self._plot_single()

    def _plot_single(self):
        """단일 결과 — 가로 막대 그래프."""
        df = self._prepare(self.dataset.dataframe)
        if df is None or df.empty:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, "No significant motifs found\n(check q-value cutoff)",
                    ha="center", va="center", fontsize=12)
            return

        ax = self.figure.add_subplot(111)
        y = np.arange(len(df))
        bars = ax.barh(y, df[SC.MOTIF_LOG_PVALUE], color="#4e79a7", alpha=0.85, height=0.7)

        ax.set_yticks(y)
        ax.set_yticklabels(df[SC.MOTIF_NAME], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("-log₁₀(p-value)")
        ax.set_title(self.dataset.name)

        # % 오버레이
        if self._show_pct.isChecked() and SC.TARGET_PCT in df.columns:
            ax2 = ax.twiny()
            ax2.barh(y, df[SC.TARGET_PCT], color="#e15759", alpha=0.3, height=0.7)
            ax2.set_xlabel("% of target peaks", color="#e15759")
            ax2.tick_params(axis="x", colors="#e15759")

        # 유의성 표시 (q-value 컷오프 통과 개수)
        n_sig = (df[SC.MOTIF_QVALUE] <= self._qval_cutoff.value()).sum() if SC.MOTIF_QVALUE in df.columns else len(df)
        ax.set_title(f"{self.dataset.name}  (n={len(df)}, q≤{self._qval_cutoff.value():.3f}: {n_sig})")

        self.figure.tight_layout()

    def _plot_comparison(self):
        """UP / DOWN 나란히 비교."""
        df_up = self._prepare(self.dataset.dataframe)
        df_dn = self._prepare(self.dataset_down.dataframe)

        axes = self.figure.subplots(1, 2, sharey=False)

        for ax, df, label, color in [
            (axes[0], df_up, self.dataset.name, "#e15759"),
            (axes[1], df_dn, self.dataset_down.name, "#4e79a7"),
        ]:
            if df is None or df.empty:
                ax.text(0.5, 0.5, "No significant motifs",
                        ha="center", va="center", fontsize=10)
                ax.set_title(label)
                continue

            y = np.arange(len(df))
            ax.barh(y, df[SC.MOTIF_LOG_PVALUE], color=color, alpha=0.85, height=0.7)
            ax.set_yticks(y)
            ax.set_yticklabels(df[SC.MOTIF_NAME], fontsize=7)
            ax.invert_yaxis()
            ax.set_xlabel("-log₁₀(p-value)")
            ax.set_title(label)

        self.figure.tight_layout()

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
        path, _ = QFileDialog.getSaveFileName(
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
