"""
Meta Volcano Plot

Compare > Statistics Filtering 결과의 메타 통계 컬럼(meta_pvalue_fisher/stouffer,
meta_log2fc_mean, meta_direction, meta_found_in)을 이용해, 여러 실험에서 재현성 높은
공통 시그널을 volcano 형태로 시각화한다.

X = meta_log2fc_mean, Y = -log10(meta p-value). 임계값을 넘고 방향이 일관된(concordant)
유전자를 up(빨강)/down(파랑)으로, 방향이 엇갈리는(discordant) 유전자는 회색조로 구분한다.
"""
import logging
from typing import List

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QVBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox, QSpinBox, QComboBox,
    QFileDialog, QMessageBox,
)

from gui.base_plot_dialog import BasePlotDialog
from utils.export_paths import remembered_save_path

_P_SOURCES = {
    "Fisher": "meta_pvalue_fisher",
    "Fisher FDR": "meta_fdr_fisher",
    "Stouffer": "meta_pvalue_stouffer",
    "Random-effects": "meta_pvalue_re",
}

# X축 소스 (있는 것만 노출). 통합 추정치(RE)를 우선.
_X_SOURCES = {
    "Pooled log2FC (RE)": "meta_effect_log2fc",
    "Mean log2FC": "meta_log2fc_mean",
    "Mean log2FE": "meta_log2fe_mean",
}


class MetaVolcanoDialog(BasePlotDialog):
    """메타 통계 기반 volcano plot."""

    def __init__(self, df: pd.DataFrame, parent=None):
        self.logger = logging.getLogger(__name__)
        self.df = df.copy()
        self._plot_df = None    # 마지막 렌더 데이터 (Export용)
        self._hover_df = None   # hover 조회용 (_x/_y/라벨/통계)
        self._label_col = None
        self.annot = None
        super().__init__("Meta Volcano Plot", parent, figsize=(8, 7))
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        group = QGroupBox("Meta thresholds")
        form = QFormLayout()

        self._psrc_combo = QComboBox()
        # 시트에 실제로 존재하는 컬럼만 선택지로
        avail = [name for name, col in _P_SOURCES.items() if col in self.df.columns]
        self._psrc_combo.addItems(avail or list(_P_SOURCES.keys()))
        self._psrc_combo.currentTextChanged.connect(self._update_plot)
        form.addRow("Meta p-value", self._psrc_combo)

        self._xsrc_combo = QComboBox()
        xavail = [name for name, col in _X_SOURCES.items() if col in self.df.columns]
        self._xsrc_combo.addItems(xavail or list(_X_SOURCES.keys()))
        self._xsrc_combo.currentTextChanged.connect(self._update_plot)
        form.addRow("X axis", self._xsrc_combo)

        self._p_spin = QDoubleSpinBox()
        self._p_spin.setDecimals(4)
        self._p_spin.setRange(0.0, 1.0)
        self._p_spin.setSingleStep(0.01)
        self._p_spin.setValue(0.05)
        self._p_spin.valueChanged.connect(self._update_plot)
        form.addRow("meta p ≤", self._p_spin)

        self._lfc_spin = QDoubleSpinBox()
        self._lfc_spin.setDecimals(3)
        self._lfc_spin.setRange(0.0, 20.0)
        self._lfc_spin.setSingleStep(0.1)
        self._lfc_spin.setValue(1.0)
        self._lfc_spin.valueChanged.connect(self._update_plot)
        form.addRow("|mean log2FC| ≥", self._lfc_spin)

        self._mink_spin = QSpinBox()
        self._mink_spin.setRange(2, 99)
        self._mink_spin.setValue(2)
        self._mink_spin.valueChanged.connect(self._update_plot)
        form.addRow("found in ≥ (datasets)", self._mink_spin)

        self._topn_spin = QSpinBox()
        self._topn_spin.setRange(0, 100)
        self._topn_spin.setValue(10)
        self._topn_spin.valueChanged.connect(self._update_plot)
        form.addRow("label top N", self._topn_spin)

        self._labelsize_spin = QSpinBox()
        self._labelsize_spin.setRange(6, 24)
        self._labelsize_spin.setValue(9)
        self._labelsize_spin.valueChanged.connect(self._update_plot)
        form.addRow("label font size", self._labelsize_spin)

        group.setLayout(form)
        layout.addWidget(group)

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Plot ──────────────────────────────────────────────────────────────

    def _xcol(self) -> str:
        """선택된 X축 컬럼 (통합 log2FC / 단순 평균 / term FE)."""
        if getattr(self, '_xsrc_combo', None) is not None and self._xsrc_combo.count():
            col = _X_SOURCES.get(self._xsrc_combo.currentText(), '')
            if col in self.df.columns:
                return col
        for c in ('meta_effect_log2fc', 'meta_log2fc_mean', 'meta_log2fe_mean'):
            if c in self.df.columns:
                return c
        return ''

    def _plot_params(self) -> dict:
        return {
            'p_col': _P_SOURCES.get(self._psrc_combo.currentText(), ''),
            'p_source_name': self._psrc_combo.currentText(),
            'x_col': self._xcol(),
            'p_threshold': self._p_spin.value(),
            'lfc_threshold': self._lfc_spin.value(),
            'min_k': self._mink_spin.value(),
            'top_n': self._topn_spin.value(),
            'label_size': self._labelsize_spin.value(),
        }

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/meta_volcano.py 에 있으며 번들과 공유한다.
        hover 툴팁(Qt 전용)은 render 반환 (d, label_col) 을 재사용한다."""
        from plots.meta_volcano import render_meta_volcano

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        d, label_col = render_meta_volcano(ax, self.df, self._plot_params())
        self._label_col = label_col
        if d is None or d.empty:
            self._plot_df = None
            self._hover_df = None
            self.canvas.draw()
            return

        # hover용 주석 (숨김 상태로 생성, 최상위 레이어)
        lbl_size = self._labelsize_spin.value()
        self.annot = ax.annotate(
            "", xy=(0, 0), xytext=(16, 16), textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w", alpha=0.92),
            arrowprops=dict(arrowstyle="->"), zorder=1000, fontsize=lbl_size)
        self.annot.set_visible(False)
        self._hover_df = d   # _x/_y/_p/라벨/meta_found_in 포함

        self._plot_df = d.rename(columns={'_x': 'mean_log2fc', '_p': 'meta_p', '_y': 'neg_log10_p'})
        self.figure.tight_layout()
        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.df,
            'plot_params': self._plot_params(),
            'dataset_name': 'meta_volcano',
            'plot_type': 'meta_volcano',
            'figure_title': 'Meta Volcano Plot',
            'figure_slug': 'meta_volcano',
            'source_stem': 'meta_volcano',
            'notes': 'Generated from cmg-seqviewer Meta Volcano plot',
        }

    def _on_hover(self, event):
        """마우스 오버 시 가장 가까운 점의 gene/term 정보 표시."""
        if self.annot is None or self._hover_df is None:
            return
        if event.inaxes is None:
            if self.annot.get_visible():
                self.annot.set_visible(False)
                self.canvas.draw_idle()
            return
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        d = self._hover_df
        ax = event.inaxes
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        xs = (xlim[1] - xlim[0]) or 1.0
        ys = (ylim[1] - ylim[0]) or 1.0
        dist = np.sqrt(((d['_x'] - x) / xs * 10) ** 2 + ((d['_y'] - y) / ys * 10) ** 2)
        if dist.empty:
            return
        idx = dist.idxmin()
        if dist[idx] >= 0.5:
            if self.annot.get_visible():
                self.annot.set_visible(False)
                self.canvas.draw_idle()
            return
        r = d.loc[idx]
        name = (str(r[self._label_col]) if self._label_col and pd.notna(r.get(self._label_col))
                else 'Unknown')
        text = (f"{name}\nmeta p: {r['_p']:.2e}"
                f"\nmean log2{'FE' if self._xcol() == 'meta_log2fe_mean' else 'FC'}: {r['_x']:.2f}"
                f"\nfound in: {r.get('meta_found_in', '')}")
        self.annot.xy = (r['_x'], r['_y'])
        self.annot.set_text(text)
        self.annot.set_fontsize(self._labelsize_spin.value())
        ox = -120 if r['_x'] > xlim[0] + (xlim[1] - xlim[0]) * 0.80 else 16
        oy = -70 if r['_y'] > ylim[0] + (ylim[1] - ylim[0]) * 0.75 else 16
        self.annot.set_position((ox, oy))
        self.annot.set_visible(True)
        self.canvas.draw_idle()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        if self._plot_df is None or self._plot_df.empty:
            QMessageBox.warning(self, "No Data", "There is no plotted data to export.")
            return
        path, _ = remembered_save_path(
            self, "Export Meta Volcano Data", "meta_volcano.csv",
            "CSV (*.csv);;TSV (*.tsv);;Excel (*.xlsx)",
        )
        if not path:
            return
        keep = [c for c in ('gene_id', 'symbol', 'term_id', 'description',
                            'mean_log2fc', 'meta_p', 'neg_log10_p',
                            'meta_direction', 'meta_found_in') if c in self._plot_df.columns]
        out = self._plot_df[keep] if keep else self._plot_df
        try:
            if path.endswith('.xlsx'):
                out.to_excel(path, index=False)
            elif path.endswith('.tsv'):
                out.to_csv(path, sep='\t', index=False)
            else:
                out.to_csv(path, index=False)
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")
