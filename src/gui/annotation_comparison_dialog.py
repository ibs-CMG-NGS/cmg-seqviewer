"""
Genomic Annotation Comparison Dialog

여러 ATAC 데이터셋의 peak annotation 카테고리 분포를 비교한다.

- Peak set: 전체(All) 또는 유의(Significant) peak
- Display:
    * Counts / Proportion(%) → 데이터셋당 누적 막대
    * Enrichment (log2 sig/all) → 배경(전체) 대비 유의 peak의 feature별 log2 enrichment
      를 데이터셋별 그룹 막대로. 0 = 배경과 동일, + = 유의 peak이 그 feature에 쏠림.
"""
import logging
from typing import List

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QVBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox, QRadioButton,
    QButtonGroup, QFileDialog, QMessageBox,
)

from models.data_models import Dataset
from models.standard_columns import StandardColumns
from gui.base_plot_dialog import BasePlotDialog
from utils.annotation_categories import (
    normalize_annotation, order_categories, color_for_category,
)

# 데이터셋 구분용 팔레트 (enrichment 그룹 막대에서 데이터셋별 색)
_DATASET_COLORS = [
    '#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
    '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac',
]


class AnnotationComparisonDialog(BasePlotDialog):
    """선택한 ATAC 데이터셋들의 annotation 분포/enrichment 비교 차트."""

    def __init__(self, datasets: List[Dataset], parent=None):
        self.logger = logging.getLogger(__name__)
        self.datasets = datasets
        self._matrix_df = None  # 마지막 집계 (카테고리 × 데이터셋), Export용
        super().__init__("Genomic Annotation Comparison", parent, figsize=(9, 6))
        # 카테고리가 많아 그림 안 범례는 막대를 가림 → 기본을 플롯 밖 우측으로
        self._labels.legend_pos_combo.blockSignals(True)
        self._labels.legend_pos_combo.setCurrentText('outside right')
        self._labels.legend_pos_combo.blockSignals(False)
        self._sync_enabled()
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Peak 집합 모드
        mode_group = QGroupBox("Peak set")
        mv = QVBoxLayout()
        self._all_radio = QRadioButton("All peaks")
        self._sig_radio = QRadioButton("Significant only")
        # 기본을 Significant only로 — All peaks는 공통 consensus peak set이면
        # 데이터셋 간 분포가 거의 동일해 비교 정보량이 낮다(배경 분포 참고용).
        self._sig_radio.setChecked(True)
        self._mode_grp = QButtonGroup(self)
        self._mode_grp.addButton(self._all_radio)
        self._mode_grp.addButton(self._sig_radio)
        mv.addWidget(self._all_radio)
        mv.addWidget(self._sig_radio)

        thr_form = QFormLayout()
        self._fdr_spin = QDoubleSpinBox()
        self._fdr_spin.setDecimals(4)
        self._fdr_spin.setRange(0.0, 1.0)
        self._fdr_spin.setSingleStep(0.01)
        self._fdr_spin.setValue(0.05)
        thr_form.addRow("FDR ≤", self._fdr_spin)

        self._lfc_spin = QDoubleSpinBox()
        self._lfc_spin.setDecimals(3)
        self._lfc_spin.setRange(0.0, 20.0)
        self._lfc_spin.setSingleStep(0.1)
        self._lfc_spin.setValue(1.0)
        thr_form.addRow("|log2FC| ≥", self._lfc_spin)
        mv.addLayout(thr_form)
        mode_group.setLayout(mv)
        layout.addWidget(mode_group)

        # 표시 형식
        disp_group = QGroupBox("Display")
        dv = QVBoxLayout()
        self._count_radio = QRadioButton("Counts")
        self._prop_radio = QRadioButton("Proportion (%)")
        self._enr_radio = QRadioButton("Enrichment (log2 sig/all)")
        self._count_radio.setChecked(True)
        self._disp_grp = QButtonGroup(self)
        self._disp_grp.addButton(self._count_radio)
        self._disp_grp.addButton(self._prop_radio)
        self._disp_grp.addButton(self._enr_radio)
        dv.addWidget(self._count_radio)
        dv.addWidget(self._prop_radio)
        dv.addWidget(self._enr_radio)
        disp_group.setLayout(dv)
        layout.addWidget(disp_group)

        # 시그널
        for w in (self._all_radio, self._sig_radio,
                  self._count_radio, self._prop_radio, self._enr_radio):
            w.toggled.connect(self._on_controls_changed)
        self._fdr_spin.valueChanged.connect(self._update_plot)
        self._lfc_spin.valueChanged.connect(self._update_plot)

    def _on_controls_changed(self, checked: bool):
        # toggled는 해제/선택 두 번 발생 → 선택된 경우에만 처리
        if not checked:
            return
        self._sync_enabled()
        self._update_plot()

    def _sync_enabled(self):
        """Enrichment 모드에선 Peak set 선택이 무의미(항상 sig vs all).
        임계값은 Significant 또는 Enrichment 모드에서만 활성."""
        enr = self._enr_radio.isChecked()
        self._all_radio.setEnabled(not enr)
        self._sig_radio.setEnabled(not enr)
        need_thr = enr or self._sig_radio.isChecked()
        self._fdr_spin.setEnabled(need_thr)
        self._lfc_spin.setEnabled(need_thr)

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── 집계 ────────────────────────────────────────────────────────────────

    def _annotation_counts(self, ds: Dataset, significant: bool) -> pd.Series:
        """데이터셋의 annotation 카테고리 개수. significant=True면 유의 peak만."""
        df = ds.dataframe
        ann_col = StandardColumns.ANNOTATION
        if df is None or ann_col not in df.columns:
            return pd.Series(dtype=float)
        sub = df
        if significant:
            lfc_col, padj_col = StandardColumns.LOG2FC, StandardColumns.ADJ_PVALUE
            if lfc_col not in df.columns or padj_col not in df.columns:
                return pd.Series(dtype=float)
            sub = df[(df[padj_col] <= self._fdr_spin.value())
                     & (df[lfc_col].abs() >= self._lfc_spin.value())]
        return sub[ann_col].dropna().map(normalize_annotation).value_counts()

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if self._enr_radio.isChecked():
            self._plot_enrichment(ax)
        else:
            self._plot_stacked(ax)
        self.figure.tight_layout()
        self.canvas.draw()

    def _plot_stacked(self, ax):
        labels = [ds.metadata.get('experiment_condition') or ds.name for ds in self.datasets]
        significant = self._sig_radio.isChecked()
        per_ds = [self._annotation_counts(ds, significant) for ds in self.datasets]

        all_cats = set()
        for s in per_ds:
            all_cats.update(s.index.tolist())
        ordered = order_categories(all_cats)
        if not ordered:
            self._empty(ax)
            return

        matrix = pd.DataFrame(
            {lbl: {cat: float(s.get(cat, 0)) for cat in ordered}
             for lbl, s in zip(labels, per_ds)}
        ).reindex(ordered)
        self._matrix_df = matrix

        plot_mat = matrix.copy()
        as_prop = self._prop_radio.isChecked()
        if as_prop:
            col_sums = plot_mat.sum(axis=0).replace(0, np.nan)
            plot_mat = plot_mat.divide(col_sums, axis=1).fillna(0.0) * 100.0

        x = list(range(len(labels)))
        bottom = np.zeros(len(labels))
        for i, cat in enumerate(ordered):
            vals = plot_mat.loc[cat].to_numpy()
            ax.bar(x, vals, bottom=bottom, color=color_for_category(cat, i),
                   label=cat, edgecolor='white', linewidth=0.4)
            bottom += vals

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
        ax.set_ylabel("Proportion (%)" if as_prop else "Peak number")
        mode_txt = "significant peaks" if significant else "all peaks"
        ax.set_title(f"Genomic annotation distribution ({mode_txt})",
                     fontsize=12, fontweight='bold')
        ax.legend(title="Annotation")

    def _plot_enrichment(self, ax):
        """배경(전체 peak) 대비 유의 peak의 feature별 log2 enrichment.

        pseudocount 0.5로 0-division/log(0)을 피한다:
            prop = (count + 0.5) / (total + 0.5*K)
            enr  = log2(sig_prop / all_prop)
        """
        labels = [ds.metadata.get('experiment_condition') or ds.name for ds in self.datasets]
        all_series = [self._annotation_counts(ds, False) for ds in self.datasets]
        sig_series = [self._annotation_counts(ds, True) for ds in self.datasets]

        # 카테고리 축 = 배경(전체) 카테고리 합집합
        all_cats = set()
        for s in all_series:
            all_cats.update(s.index.tolist())
        ordered = order_categories(all_cats)
        if not ordered:
            self._empty(ax)
            return

        K = len(ordered)
        enr = {}  # label -> [log2 enrichment per category]
        for lbl, allc, sigc in zip(labels, all_series, sig_series):
            all_tot = float(allc.sum())
            sig_tot = float(sigc.sum())
            if sig_tot == 0 or all_tot == 0:
                enr[lbl] = [np.nan] * K  # 유의 peak 없음 → 그리지 않음
                continue
            row = []
            for cat in ordered:
                all_p = (float(allc.get(cat, 0)) + 0.5) / (all_tot + 0.5 * K)
                sig_p = (float(sigc.get(cat, 0)) + 0.5) / (sig_tot + 0.5 * K)
                row.append(float(np.log2(sig_p / all_p)))
            enr[lbl] = row

        self._matrix_df = pd.DataFrame(enr, index=ordered)

        n = len(labels)
        width = 0.8 / max(n, 1)
        xbase = np.arange(K)
        for j, lbl in enumerate(labels):
            offset = (j - (n - 1) / 2) * width
            vals = np.array(enr[lbl], dtype=float)
            ax.bar(xbase + offset, vals, width=width,
                   color=_DATASET_COLORS[j % len(_DATASET_COLORS)],
                   label=lbl, edgecolor='white', linewidth=0.3)

        ax.axhline(0, color='#333333', linewidth=0.8)
        ax.set_xticks(xbase)
        ax.set_xticklabels(ordered, rotation=30, ha='right', fontsize=8)
        ax.set_ylabel("log2( significant / all )")
        ax.set_title("Genomic annotation enrichment (significant vs background)",
                     fontsize=12, fontweight='bold')
        ax.legend(title="Dataset")

    def _empty(self, ax):
        ax.text(0.5, 0.5, "No annotation data in the selected datasets.",
                ha='center', va='center', transform=ax.transAxes, color='#888888')
        self._matrix_df = None

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        if self._matrix_df is None or self._matrix_df.empty:
            QMessageBox.warning(self, "No Data", "There is no aggregated data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Annotation Comparison", "annotation_comparison.csv",
            "CSV (*.csv);;TSV (*.tsv);;Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            out = self._matrix_df.copy()
            out.index.name = 'annotation'
            if path.endswith('.xlsx'):
                out.to_excel(path)
            elif path.endswith('.tsv'):
                out.to_csv(path, sep='\t')
            else:
                out.to_csv(path)
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")
