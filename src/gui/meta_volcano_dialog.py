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

_C_UP = '#c0392b'
_C_DOWN = '#2c6fbb'
_C_DISCORD = '#e08a1e'
_C_NS = '#c8c8c8'

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
_X_LABELS = {
    "meta_effect_log2fc": "Pooled log2 fold change (random-effects)",
    "meta_log2fc_mean": "Mean log2 fold change",
    "meta_log2fe_mean": "Mean log2 fold enrichment",
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

    @staticmethod
    def _found_in_num(v) -> int:
        try:
            return int(str(v).split('/')[0])
        except (ValueError, TypeError):
            return 0

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

    def _prepare(self) -> pd.DataFrame:
        pcol = _P_SOURCES[self._psrc_combo.currentText()]
        xcol = self._xcol()
        if not xcol or pcol not in self.df.columns:
            return pd.DataFrame()
        d = self.df.copy()
        d['_x'] = pd.to_numeric(d[xcol], errors='coerce')
        d['_p'] = pd.to_numeric(d[pcol], errors='coerce')
        d = d[d['_x'].notna() & d['_p'].notna()].copy()
        if 'meta_found_in' in d.columns:
            d['_k'] = d['meta_found_in'].map(self._found_in_num)
            d = d[d['_k'] >= self._mink_spin.value()]
        d['_p'] = d['_p'].clip(lower=1e-300, upper=1.0)
        d['_y'] = -np.log10(d['_p'])
        return d

    def _do_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        d = self._prepare()
        if d.empty:
            ax.text(0.5, 0.5,
                    "No meta-analysis columns found.\n"
                    "Run Compare → Statistics Filtering on 2+ datasets first.",
                    ha='center', va='center', transform=ax.transAxes, color='#888888')
            self._plot_df = None
            self.canvas.draw()
            return

        p_thr = self._p_spin.value()
        lfc_thr = self._lfc_spin.value()
        sig = (d['_p'] <= p_thr) & (d['_x'].abs() >= lfc_thr)
        direction = d.get('meta_direction', pd.Series('', index=d.index)).astype(str)
        concord = direction.eq('concordant')

        cat_up = sig & concord & (d['_x'] > 0)
        cat_down = sig & concord & (d['_x'] < 0)
        cat_disc = sig & ~concord
        cat_ns = ~sig

        for mask, color, label in (
            (cat_ns, _C_NS, 'n.s.'),
            (cat_disc, _C_DISCORD, 'Sig. discordant'),
            (cat_up, _C_UP, 'Sig. up (concordant)'),
            (cat_down, _C_DOWN, 'Sig. down (concordant)'),
        ):
            if mask.any():
                ax.scatter(d.loc[mask, '_x'], d.loc[mask, '_y'], s=16,
                           c=color, label=label, edgecolors='none', alpha=0.8)

        # 임계값 가이드 라인
        ax.axhline(-np.log10(p_thr), color='#888888', ls='--', lw=0.7)
        if lfc_thr > 0:
            ax.axvline(lfc_thr, color='#888888', ls='--', lw=0.7)
            ax.axvline(-lfc_thr, color='#888888', ls='--', lw=0.7)
        ax.axvline(0, color='#cccccc', lw=0.6)

        # 라벨/hover에 쓸 식별자 컬럼 (유전자 또는 term)
        self._label_col = next((c for c in ('symbol', 'gene_id', 'description', 'term_id')
                                if c in d.columns), None)

        # 상위 N개 라벨 (유의 유전자 중 p-value 작은 순) — adjustText로 겹침 방지
        topn = self._topn_spin.value()
        lbl_size = self._labelsize_spin.value()
        if topn > 0 and self._label_col:
            top = d[sig].nsmallest(topn, '_p')
            texts = []
            for _, r in top.iterrows():
                name = str(r[self._label_col])
                if name and name != 'nan':
                    texts.append(ax.text(r['_x'], r['_y'], name, fontsize=lbl_size,
                                         ha='center', va='center',
                                         bbox=dict(boxstyle='round,pad=0.15', fc='white',
                                                   ec='none', alpha=0.7), zorder=500))
            if texts:
                try:
                    from adjustText import adjust_text
                    adjust_text(texts, ax=ax,
                                arrowprops=dict(arrowstyle='-', color='grey', lw=0.5),
                                expand=(1.15, 1.4), force_text=(0.4, 0.6),
                                only_move={'text': 'xy'})
                except ImportError:
                    pass

        src = self._psrc_combo.currentText()
        xcol = self._xcol()
        is_term = xcol == 'meta_log2fe_mean'
        ax.set_xlabel(_X_LABELS.get(xcol, "Mean log2 fold change"))
        ax.set_ylabel(f"-log10(meta p-value, {src})")
        unit = "term" if is_term else "gene"
        ax.set_title(f"Meta Volcano — cross-dataset {unit} consistency",
                     fontsize=12, fontweight='bold')
        ax.legend(fontsize=7, loc='upper right', framealpha=0.9)

        # hover용 주석 (숨김 상태로 생성, 최상위 레이어)
        self.annot = ax.annotate(
            "", xy=(0, 0), xytext=(16, 16), textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w", alpha=0.92),
            arrowprops=dict(arrowstyle="->"), zorder=1000, fontsize=lbl_size)
        self.annot.set_visible(False)
        self._hover_df = d   # _x/_y/_p/라벨/meta_found_in 포함

        self._plot_df = d.rename(columns={'_x': 'mean_log2fc', '_p': 'meta_p', '_y': 'neg_log10_p'})
        self.figure.tight_layout()
        self.canvas.draw()

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
        path, _ = QFileDialog.getSaveFileName(
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
