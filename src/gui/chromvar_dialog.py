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
from utils.export_paths import remembered_save_path

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

    def get_plot_params(self) -> dict:
        mode = self._mode.currentText()
        if 'Heatmap' in mode:
            mode_key = 'heatmap'
        elif 'Scatter' in mode:
            mode_key = 'scatter'
        else:
            mode_key = 'volcano'
        return {
            'mode': mode_key,
            'padj_cutoff': self._padj_cut.value(),
            'delta_cutoff': self._delta_cut.value(),
            'top_n': self._top_n.value(),
            'dot_size': self._dot_size.value(),
            'heatmap_top_n': self._heatmap_top_n.value(),
            'title': f'TF Activity — {self.dataset.name}',
        }

    def _bundle_df(self) -> pd.DataFrame:
        if 'Heatmap' in self._mode.currentText() and len(self.all_datasets) > 1:
            frames = []
            for ds in self.all_datasets:
                df = ds.dataframe.copy()
                df['dataset'] = ds.name
                frames.append(df)
            return pd.concat(frames, ignore_index=True)
        return self.dataset.dataframe.copy()

    def _do_plot(self):
        from plots.chromvar import render_chromvar
        self.figure.clear()
        self._annot = None
        self._hover_pairs = []
        info = render_chromvar(self.figure, self._bundle_df(), self.get_plot_params())
        self.figure.tight_layout()
        self._hover_pairs = info.get('hover_pairs') or []
        self._hover_x_col = info.get('hover_x') or ''
        self._hover_y_col = info.get('hover_y') or ''
        self._annot = self._make_annot(self.figure.axes[0]) if self._hover_pairs else None

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self._bundle_df(),
            'plot_params': self.get_plot_params(),
            'dataset_name': self.dataset.name,
            'plot_type': 'chromvar',
            'figure_title': f'chromVAR TF Activity — {self.dataset.name}',
            'figure_slug': 'chromvar',
            'source_stem': 'chromvar',
            'notes': 'Generated from cmg-seqviewer chromVAR differential TF activity',
        }

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
        path, _ = remembered_save_path(
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
