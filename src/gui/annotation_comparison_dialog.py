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

    def _build_long_df(self):
        """데이터셋들을 long-format(dataset/annotation/log2fc/adj_pvalue)으로 병합.
        (df, order) 반환."""
        ann_col = StandardColumns.ANNOTATION
        lfc_col, padj_col = StandardColumns.LOG2FC, StandardColumns.ADJ_PVALUE
        frames, order = [], []
        for ds in self.datasets:
            label = ds.metadata.get('experiment_condition') or ds.name
            order.append(label)
            df = ds.dataframe
            if df is None or ann_col not in df.columns:
                continue
            n = len(df)
            frames.append(pd.DataFrame({
                'dataset': label,
                'annotation': df[ann_col].values,
                'log2fc': (pd.to_numeric(df[lfc_col], errors='coerce').values
                           if lfc_col in df.columns else np.full(n, np.nan)),
                'adj_pvalue': (pd.to_numeric(df[padj_col], errors='coerce').values
                               if padj_col in df.columns else np.full(n, np.nan)),
            }))
        long_df = pd.concat(frames, ignore_index=True) if frames else \
            pd.DataFrame(columns=['dataset', 'annotation', 'log2fc', 'adj_pvalue'])
        return long_df, order

    def _plot_params(self, order=None) -> dict:
        if order is None:
            order = [ds.metadata.get('experiment_condition') or ds.name for ds in self.datasets]
        if self._enr_radio.isChecked():
            display = 'enrichment'
        elif self._prop_radio.isChecked():
            display = 'proportion'
        else:
            display = 'counts'
        return {
            'peak_set': 'significant' if self._sig_radio.isChecked() else 'all',
            'display': display,
            'fdr_max': self._fdr_spin.value(),
            'lfc_min': self._lfc_spin.value(),
            'order': order,
        }

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/annotation_comparison.py 에 있으며 번들과 공유한다."""
        from plots.annotation_comparison import render_annotation_comparison

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        long_df, order = self._build_long_df()
        self._matrix_df = render_annotation_comparison(ax, long_df, self._plot_params(order))
        self.figure.tight_layout()
        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        long_df, order = self._build_long_df()
        return {
            'figure': self.figure,
            'dataframe': long_df,
            'plot_params': self._plot_params(order),
            'dataset_name': 'annotation_comparison',
            'plot_type': 'annotation_comparison',
            'figure_title': 'Genomic Annotation Comparison',
            'figure_slug': 'annotation_comparison',
            'source_stem': 'annotation_comparison',
            'notes': 'Generated from cmg-seqviewer Genomic Annotation Comparison (long-format input)',
        }

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
