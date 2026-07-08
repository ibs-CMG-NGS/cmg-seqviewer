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
}


class MetaVolcanoDialog(BasePlotDialog):
    """메타 통계 기반 volcano plot."""

    def __init__(self, df: pd.DataFrame, parent=None):
        self.logger = logging.getLogger(__name__)
        self.df = df.copy()
        self._plot_df = None  # 마지막 렌더 데이터 (Export용)
        super().__init__("Meta Volcano Plot", parent, figsize=(8, 7))
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

    def _prepare(self) -> pd.DataFrame:
        pcol = _P_SOURCES[self._psrc_combo.currentText()]
        need = {pcol, 'meta_log2fc_mean'}
        if not need.issubset(self.df.columns):
            return pd.DataFrame()
        d = self.df.copy()
        d['_x'] = pd.to_numeric(d['meta_log2fc_mean'], errors='coerce')
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

        # 상위 N개 라벨 (유의 유전자 중 p-value 작은 순)
        topn = self._topn_spin.value()
        if topn > 0:
            label_col = 'symbol' if 'symbol' in d.columns else ('gene_id' if 'gene_id' in d.columns else None)
            if label_col:
                top = d[sig].nsmallest(topn, '_p')
                for _, r in top.iterrows():
                    name = str(r[label_col])
                    if name and name != 'nan':
                        ax.annotate(name, (r['_x'], r['_y']), fontsize=7,
                                    xytext=(3, 3), textcoords='offset points')

        src = self._psrc_combo.currentText()
        ax.set_xlabel("Mean log2 fold change")
        ax.set_ylabel(f"-log10(meta p-value, {src})")
        ax.set_title("Meta Volcano — cross-dataset consistency",
                     fontsize=12, fontweight='bold')
        ax.legend(fontsize=7, loc='upper right', framealpha=0.9)

        self._plot_df = d.rename(columns={'_x': 'mean_log2fc', '_p': 'meta_p', '_y': 'neg_log10_p'})
        self.figure.tight_layout()
        self.canvas.draw()

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
        keep = [c for c in ('gene_id', 'symbol', 'mean_log2fc', 'meta_p', 'neg_log10_p',
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
