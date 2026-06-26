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

    def _do_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        df = self.dataset.dataframe.copy()

        # 필수 컬럼 확인
        for col in [SC.COND1_SCORE, SC.COND2_SCORE]:
            if col not in df.columns:
                ax.text(0.5, 0.5,
                        f"Required column not found:\n{col}\n\n"
                        "Expected TOBIAS BINDetect bindetect_results.txt",
                        ha="center", va="center", fontsize=11)
                return

        # 숫자 변환
        df[SC.COND1_SCORE] = pd.to_numeric(df[SC.COND1_SCORE], errors="coerce")
        df[SC.COND2_SCORE] = pd.to_numeric(df[SC.COND2_SCORE], errors="coerce")
        df = df.dropna(subset=[SC.COND1_SCORE, SC.COND2_SCORE])

        if df.empty:
            ax.text(0.5, 0.5, "No valid data", ha="center", va="center")
            return

        pval_col = SC.FOOTPRINT_PVALUE
        change_col = SC.FOOTPRINT_CHANGE

        pval_cut = self._pval_cutoff.value()
        min_change = self._min_change.value()

        # 유의성 분류
        has_pval = pval_col in df.columns
        has_change = change_col in df.columns

        if has_pval:
            df[pval_col] = pd.to_numeric(df[pval_col], errors="coerce")
        if has_change:
            df[change_col] = pd.to_numeric(df[change_col], errors="coerce")

        def classify(row):
            sig = has_pval and pd.notna(row.get(pval_col)) and row[pval_col] <= pval_cut
            if not sig:
                return "ns"
            if has_change and pd.notna(row.get(change_col)):
                if row[change_col] >= min_change:
                    return "gain"   # cond1에서 더 활성 (위로 이동)
                elif row[change_col] <= -min_change:
                    return "loss"   # cond2에서 더 활성 (아래로 이동)
            return "ns"

        df["_cls"] = df.apply(classify, axis=1)

        colors = {"ns": "#cccccc", "gain": "#e15759", "loss": "#4e79a7"}
        alphas = {"ns": 0.3, "gain": 0.85, "loss": 0.85}
        labels_map = {"ns": "Not significant", "gain": f"{self.cond1} activated", "loss": f"{self.cond2} activated"}
        dot_size = self._dot_size.value()

        for cls in ("ns", "gain", "loss"):
            sub = df[df["_cls"] == cls]
            if sub.empty:
                continue
            ax.scatter(
                sub[SC.COND1_SCORE], sub[SC.COND2_SCORE],
                c=colors[cls], alpha=alphas[cls], s=dot_size,
                label=f"{labels_map[cls]} (n={len(sub)})",
                zorder=2 if cls != "ns" else 1,
                edgecolors="none",
            )

        # 대각선 y=x
        if self._show_diag.isChecked():
            lim_min = min(ax.get_xlim()[0], ax.get_ylim()[0])
            lim_max = max(ax.get_xlim()[1], ax.get_ylim()[1])
            ax.plot([lim_min, lim_max], [lim_min, lim_max],
                    color="gray", linestyle="--", linewidth=0.8, alpha=0.6, zorder=0)

        # 라벨링: |change| 기준 상위 N개 (유의미한 것만)
        n_label = self._top_n_label.value()
        if n_label > 0 and has_change:
            sig_df = df[df["_cls"] != "ns"].copy()
            if not sig_df.empty:
                sig_df = sig_df.dropna(subset=[change_col])
                sig_df = sig_df.reindex(
                    sig_df[change_col].abs().sort_values(ascending=False).index
                ).head(n_label)

                name_col = SC.FOOTPRINT_MOTIF_NAME if SC.FOOTPRINT_MOTIF_NAME in df.columns else None
                if name_col:
                    for _, row in sig_df.iterrows():
                        ax.annotate(
                            str(row[name_col]),
                            (row[SC.COND1_SCORE], row[SC.COND2_SCORE]),
                            fontsize=7,
                            xytext=(4, 4), textcoords="offset points",
                            color=colors.get(row["_cls"], "black"),
                        )

        ax.set_xlabel(f"{self.cond1} mean footprint score")
        ax.set_ylabel(f"{self.cond2} mean footprint score")
        ax.set_title(
            f"TF Activity  —  {self.cond1} vs {self.cond2}\n"
            f"(p ≤ {pval_cut}, |Δ| ≥ {min_change})"
        )
        ax.legend(fontsize=8, framealpha=0.7)
        self.figure.tight_layout()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        path, _ = QFileDialog.getSaveFileName(
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
