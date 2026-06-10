"""
chromVAR Differential TF Activity Dialog

세 가지 시각화 모드:
  Volcano  — X: delta z-score,  Y: -log10(padj)
  Scatter  — X: base(Control) z-score,  Y: compare z-score
  Heatmap  — 여러 조건의 delta z-score를 TF × condition matrix로 시각화

Hover:
  Volcano / Scatter 모드에서 마우스 오버 시 TF 이름, Motif ID, delta, padj 툴팁 표시.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSpinBox, QLabel, QComboBox,
    QFileDialog, QMessageBox,
)

from gui.base_plot_dialog import BasePlotDialog
from models.data_models import Dataset
from models.standard_columns import StandardColumns as SC

# hover 감지 반경 (데이터 단위 아닌 픽셀)
_HOVER_RADIUS = 8


class ChromVARDialog(BasePlotDialog):
    """
    chromVAR Differential TF Activity 시각화 다이얼로그.

    단일 데이터셋: Volcano 또는 Scatter
    복수 데이터셋: Multi-condition Heatmap
    """

    def __init__(
        self,
        dataset: Dataset,
        extra_datasets: Optional[list[Dataset]] = None,
        parent=None,
    ):
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset
        self.all_datasets: list[Dataset] = [dataset] + (extra_datasets or [])

        # hover 상태 — _do_plot() 에서 갱신
        self._annot = None                  # 현재 axes의 annotation 객체
        self._hover_pairs: list = []        # [(PathCollection, df_subset), ...]
        self._hover_x_col: str = ""         # hover 시 X 좌표 컬럼명
        self._hover_y_col: str = ""         # hover 시 Y 좌표 컬럼명

        title = f"chromVAR TF Activity — {dataset.name}"
        super().__init__(title, parent, figsize=(9, 7))

        # canvas에 한 번만 연결 (figure.clear() 후에도 canvas는 유지됨)
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)

        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        mode_grp = QGroupBox("View")
        mode_lay = QVBoxLayout()
        self._mode = QComboBox()
        modes = ["Volcano", "Scatter (base vs compare)"]
        if len(self.all_datasets) > 1:
            modes.append("Multi-condition Heatmap")
        self._mode.addItems(modes)
        self._mode.currentIndexChanged.connect(self._on_mode_changed)
        mode_lay.addWidget(self._mode)
        mode_grp.setLayout(mode_lay)
        layout.addWidget(mode_grp)

        grp = QGroupBox("Thresholds & Labels")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._padj_cut = QDoubleSpinBox()
        self._padj_cut.setRange(0.0, 1.0)
        self._padj_cut.setSingleStep(0.01)
        self._padj_cut.setDecimals(3)
        self._padj_cut.setValue(0.05)
        form.addRow("padj cutoff:", self._padj_cut)

        self._delta_cut = QDoubleSpinBox()
        self._delta_cut.setRange(0.0, 10.0)
        self._delta_cut.setSingleStep(0.1)
        self._delta_cut.setDecimals(2)
        self._delta_cut.setValue(0.5)
        self._delta_cut.setToolTip("|delta z-score| 최솟값")
        form.addRow("|delta| ≥:", self._delta_cut)

        self._top_n = QSpinBox()
        self._top_n.setRange(0, 50)
        self._top_n.setValue(10)
        form.addRow("Label top N:", self._top_n)

        self._dot_size = QSpinBox()
        self._dot_size.setRange(5, 200)
        self._dot_size.setValue(30)
        form.addRow("Dot size:", self._dot_size)

        self._heatmap_top_n = QSpinBox()
        self._heatmap_top_n.setRange(5, 100)
        self._heatmap_top_n.setValue(30)
        self._heatmap_top_n.setToolTip("Heatmap에 표시할 상위 TF 수 (|delta| 최대값 기준)")
        self._heatmap_top_n_label = QLabel("Heatmap top N TFs:")
        form.addRow(self._heatmap_top_n_label, self._heatmap_top_n)

        grp.setLayout(form)
        layout.addWidget(grp)

        for w in [self._padj_cut, self._delta_cut, self._top_n,
                  self._dot_size, self._heatmap_top_n]:
            w.valueChanged.connect(self._update_plot)

        self._on_mode_changed()

    def _on_mode_changed(self):
        is_heatmap = "Heatmap" in self._mode.currentText()
        self._heatmap_top_n.setVisible(is_heatmap)
        self._heatmap_top_n_label.setVisible(is_heatmap)
        self._top_n.setVisible(not is_heatmap)
        self._dot_size.setVisible(not is_heatmap)
        self._update_plot()

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Plot dispatcher ───────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()
        # hover 상태 초기화 (이전 axes 참조 무효화)
        self._annot = None
        self._hover_pairs = []

        mode = self._mode.currentText()
        if "Heatmap" in mode:
            self._plot_heatmap()
        elif "Scatter" in mode:
            self._plot_scatter()
        else:
            self._plot_volcano()

    # ── Volcano ───────────────────────────────────────────────────────────

    def _plot_volcano(self):
        df = self._prepare(self.dataset.dataframe)
        ax = self.figure.add_subplot(111)

        if df is None or df.empty:
            ax.text(0.5, 0.5, "No data available", ha="center", va="center")
            return

        padj_cut = self._padj_cut.value()
        delta_cut = self._delta_cut.value()
        neg_log = df["chromvar_neg_log_padj"]
        delta = df[SC.CHROMVAR_DELTA]

        sig_up   = (df[SC.CHROMVAR_PADJ] <= padj_cut) & (delta >= delta_cut)
        sig_down = (df[SC.CHROMVAR_PADJ] <= padj_cut) & (delta <= -delta_cut)
        ns = ~(sig_up | sig_down)

        sc_ns = ax.scatter(
            delta[ns], neg_log[ns],
            c="#cccccc", s=self._dot_size.value(), alpha=0.5,
            label=f"NS (n={ns.sum()})", zorder=1, edgecolors="none",
        )
        sc_up = ax.scatter(
            delta[sig_up], neg_log[sig_up],
            c="#e15759", s=self._dot_size.value(), alpha=0.85,
            label=f"Increased (n={sig_up.sum()})", zorder=2, edgecolors="none",
        )
        sc_dn = ax.scatter(
            delta[sig_down], neg_log[sig_down],
            c="#4e79a7", s=self._dot_size.value(), alpha=0.85,
            label=f"Decreased (n={sig_down.sum()})", zorder=2, edgecolors="none",
        )

        ax.axhline(-np.log10(padj_cut), color="gray", linestyle="--",
                   linewidth=0.8, alpha=0.7)
        ax.axvline(delta_cut, color="gray", linestyle="--",
                   linewidth=0.8, alpha=0.7)
        ax.axvline(-delta_cut, color="gray", linestyle="--",
                   linewidth=0.8, alpha=0.7)

        self._label_top(ax, df, sig_up | sig_down, delta, neg_log)

        ax.set_xlabel("delta z-score  (compare − base)")
        ax.set_ylabel("-log₁₀(padj)")
        ax.set_title(f"TF Activity Volcano — {self.dataset.name}")
        ax.legend(fontsize=8, framealpha=0.7)
        self.figure.tight_layout()

        # hover 설정
        self._annot = self._make_annot(ax)
        self._hover_pairs = [
            (sc_ns,  df[ns].reset_index(drop=True)),
            (sc_up,  df[sig_up].reset_index(drop=True)),
            (sc_dn,  df[sig_down].reset_index(drop=True)),
        ]
        self._hover_x_col = SC.CHROMVAR_DELTA
        self._hover_y_col = "chromvar_neg_log_padj"

    # ── Scatter ───────────────────────────────────────────────────────────

    def _plot_scatter(self):
        df = self._prepare(self.dataset.dataframe)
        ax = self.figure.add_subplot(111)

        if df is None or df.empty:
            ax.text(0.5, 0.5, "No data available", ha="center", va="center")
            return

        for col in [SC.CHROMVAR_MEAN_BASE, SC.CHROMVAR_MEAN_COMPARE]:
            if col not in df.columns:
                ax.text(0.5, 0.5, f"Column not found:\n{col}", ha="center", va="center")
                return

        padj_cut = self._padj_cut.value()
        delta_cut = self._delta_cut.value()
        delta = df[SC.CHROMVAR_DELTA]
        x = df[SC.CHROMVAR_MEAN_BASE]
        y = df[SC.CHROMVAR_MEAN_COMPARE]

        sig_up   = (df[SC.CHROMVAR_PADJ] <= padj_cut) & (delta >= delta_cut)
        sig_down = (df[SC.CHROMVAR_PADJ] <= padj_cut) & (delta <= -delta_cut)
        ns = ~(sig_up | sig_down)

        sc_ns = ax.scatter(
            x[ns], y[ns], c="#cccccc", s=self._dot_size.value(),
            alpha=0.4, label=f"NS (n={ns.sum()})", zorder=1, edgecolors="none",
        )
        sc_up = ax.scatter(
            x[sig_up], y[sig_up], c="#e15759", s=self._dot_size.value(),
            alpha=0.85, label=f"Increased (n={sig_up.sum()})", zorder=2, edgecolors="none",
        )
        sc_dn = ax.scatter(
            x[sig_down], y[sig_down], c="#4e79a7", s=self._dot_size.value(),
            alpha=0.85, label=f"Decreased (n={sig_down.sum()})", zorder=2, edgecolors="none",
        )

        lim = [min(x.min(), y.min()) - 0.2, max(x.max(), y.max()) + 0.2]
        ax.plot(lim, lim, color="gray", linestyle="--", linewidth=0.8, alpha=0.6, zorder=0)
        ax.set_xlim(lim)
        ax.set_ylim(lim)

        self._label_top(ax, df, sig_up | sig_down, delta, y, x_vals=x)

        ax.set_xlabel("base (Control) mean z-score")
        ax.set_ylabel("compare mean z-score")
        ax.set_title(f"TF Activity Scatter — {self.dataset.name}")
        ax.legend(fontsize=8, framealpha=0.7)
        self.figure.tight_layout()

        # hover 설정
        self._annot = self._make_annot(ax)
        self._hover_pairs = [
            (sc_ns,  df[ns].reset_index(drop=True)),
            (sc_up,  df[sig_up].reset_index(drop=True)),
            (sc_dn,  df[sig_down].reset_index(drop=True)),
        ]
        self._hover_x_col = SC.CHROMVAR_MEAN_BASE
        self._hover_y_col = SC.CHROMVAR_MEAN_COMPARE

    # ── Multi-condition Heatmap ───────────────────────────────────────────

    def _plot_heatmap(self):
        from matplotlib.colors import TwoSlopeNorm

        ax = self.figure.add_subplot(111)

        frames = {}
        for ds in self.all_datasets:
            df = self._prepare(ds.dataframe)
            if df is None or df.empty:
                continue
            key_col = SC.CHROMVAR_TF_NAME if SC.CHROMVAR_TF_NAME in df.columns else SC.CHROMVAR_MOTIF_ID
            frames[ds.name] = df.set_index(key_col)[SC.CHROMVAR_DELTA]

        if not frames:
            ax.text(0.5, 0.5, "No data available", ha="center", va="center")
            return

        mat = pd.DataFrame(frames).dropna(how="all")
        top_n = self._heatmap_top_n.value()
        mat["_max_abs"] = mat.abs().max(axis=1)
        mat = mat.nlargest(top_n, "_max_abs").drop(columns="_max_abs")
        mat = mat.sort_values(mat.columns[0], ascending=False)

        if mat.empty:
            ax.text(0.5, 0.5, "No significant TFs", ha="center", va="center")
            return

        vmax = max(mat.abs().max().max(), 0.01)
        norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
        im = ax.imshow(mat.values, aspect="auto", cmap="RdBu_r", norm=norm)
        self.figure.colorbar(im, ax=ax, label="delta z-score", shrink=0.8)

        ax.set_xticks(range(len(mat.columns)))
        ax.set_xticklabels(mat.columns, rotation=30, ha="right", fontsize=8)
        ax.set_yticks(range(len(mat.index)))
        ax.set_yticklabels(mat.index, fontsize=7)
        ax.set_title(f"TF Activity Heatmap  (top {top_n} by |delta|)", fontsize=10)
        self.figure.tight_layout()

        # hover 없음 (heatmap 모드)
        self._annot = None
        self._hover_pairs = []

    # ── Hover ─────────────────────────────────────────────────────────────

    def _make_annot(self, ax):
        """tooltip annotation 객체 생성."""
        annot = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#888888",
                      alpha=0.92, linewidth=0.8),
            arrowprops=dict(arrowstyle="-", color="#888888", lw=0.8),
            fontsize=8,
            zorder=1000,
        )
        annot.set_visible(False)
        return annot

    def _on_hover(self, event):
        """motion_notify_event 핸들러 — Volcano/Scatter 모드에서만 동작."""
        if self._annot is None or not self._hover_pairs:
            return
        if event.inaxes is None:
            if self._annot.get_visible():
                self._annot.set_visible(False)
                self.canvas.draw_idle()
            return

        ax = event.inaxes
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        # 각 scatter collection을 순회하며 가장 가까운 점 탐색
        hit_row = None
        hit_x = hit_y = 0.0
        min_dist = float("inf")

        for sc, sub_df in self._hover_pairs:
            if sub_df.empty:
                continue
            # contains() 로 픽셀 반경 내 점 확인
            cont, ind = sc.contains(event)
            if not cont:
                continue
            # 여러 점이 잡히면 마우스와 가장 가까운 것 선택
            offsets = sc.get_offsets()
            for i in ind["ind"]:
                if i >= len(offsets):
                    continue
                px, py = offsets[i]
                d = (px - event.xdata) ** 2 + (py - event.ydata) ** 2
                if d < min_dist:
                    min_dist = d
                    hit_x, hit_y = px, py
                    if i < len(sub_df):
                        hit_row = sub_df.iloc[i]

        if hit_row is None:
            if self._annot.get_visible():
                self._annot.set_visible(False)
                self.canvas.draw_idle()
            return

        # 툴팁 텍스트 구성
        name_col = SC.CHROMVAR_TF_NAME if SC.CHROMVAR_TF_NAME in hit_row.index else SC.CHROMVAR_MOTIF_ID
        tf_name  = str(hit_row.get(SC.CHROMVAR_TF_NAME, ""))
        motif_id = str(hit_row.get(SC.CHROMVAR_MOTIF_ID, ""))
        delta    = hit_row.get(SC.CHROMVAR_DELTA, float("nan"))
        padj     = hit_row.get(SC.CHROMVAR_PADJ,  float("nan"))
        pval     = hit_row.get(SC.CHROMVAR_PVALUE, float("nan"))

        lines = [f"TF: {tf_name}"]
        if motif_id and motif_id != tf_name:
            lines.append(f"Motif: {motif_id}")
        lines.append(f"Δ z-score: {delta:.3f}")
        if not np.isnan(padj):
            lines.append(f"padj: {padj:.3e}")
        if not np.isnan(pval):
            lines.append(f"p-value: {pval:.3e}")

        # Scatter 모드에서는 base/compare 점수 추가
        if self._hover_x_col == SC.CHROMVAR_MEAN_BASE:
            base = hit_row.get(SC.CHROMVAR_MEAN_BASE, float("nan"))
            comp = hit_row.get(SC.CHROMVAR_MEAN_COMPARE, float("nan"))
            if not np.isnan(base):
                lines.append(f"Base: {base:.3f}")
            if not np.isnan(comp):
                lines.append(f"Compare: {comp:.3f}")

        self._annot.xy = (hit_x, hit_y)
        self._annot.set_text("\n".join(lines))

        # 화면 경계에 따라 툴팁 방향 조정
        x_ratio = (hit_x - xlim[0]) / max(xlim[1] - xlim[0], 1e-9)
        y_ratio = (hit_y - ylim[0]) / max(ylim[1] - ylim[0], 1e-9)
        ox = -110 if x_ratio > 0.75 else 15
        oy = -90  if y_ratio > 0.75 else 15
        self._annot.set_position((ox, oy))
        self._annot.set_visible(True)
        self.canvas.draw_idle()

    # ── 공용 헬퍼 ────────────────────────────────────────────────────────

    def _prepare(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        df = df.copy()
        for col in [SC.CHROMVAR_DELTA, SC.CHROMVAR_PADJ,
                    SC.CHROMVAR_MEAN_BASE, SC.CHROMVAR_MEAN_COMPARE]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if SC.CHROMVAR_DELTA not in df.columns or SC.CHROMVAR_PADJ not in df.columns:
            return None
        df = df.dropna(subset=[SC.CHROMVAR_DELTA, SC.CHROMVAR_PADJ])
        pv = df[SC.CHROMVAR_PADJ].clip(lower=1e-300)
        df["chromvar_neg_log_padj"] = -np.log10(pv)
        return df.reset_index(drop=True)

    def _label_top(self, ax, df, sig_mask, sort_series, y_vals, x_vals=None):
        n = self._top_n.value()
        if n == 0:
            return
        name_col = SC.CHROMVAR_TF_NAME if SC.CHROMVAR_TF_NAME in df.columns else SC.CHROMVAR_MOTIF_ID
        sig_df = df[sig_mask].copy()
        if sig_df.empty:
            return
        sig_df = sig_df.reindex(
            sort_series[sig_mask].abs().sort_values(ascending=False).index
        ).head(n)
        for _, row in sig_df.iterrows():
            x_val = row[x_vals.name] if x_vals is not None else row[SC.CHROMVAR_DELTA]
            y_val = row[y_vals.name]
            color = "#e15759" if row[SC.CHROMVAR_DELTA] > 0 else "#4e79a7"
            ax.annotate(
                str(row[name_col]),
                (x_val, y_val),
                fontsize=7,
                xytext=(4, 4), textcoords="offset points",
                color=color,
            )

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export chromVAR Data", "chromvar_diff_tf.xlsx",
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not path:
            return
        try:
            if path.endswith(".csv"):
                df = self._prepare(self.dataset.dataframe)
                if df is not None:
                    df.drop(columns=["chromvar_neg_log_padj"], errors="ignore").to_csv(path, index=False)
            else:
                with pd.ExcelWriter(path, engine="openpyxl") as writer:
                    for ds in self.all_datasets:
                        df = self._prepare(ds.dataframe)
                        if df is not None:
                            out = df.drop(columns=["chromvar_neg_log_padj"], errors="ignore")
                            out.to_excel(writer, sheet_name=ds.name[:31], index=False)
            QMessageBox.information(self, "Export", f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
