"""
UpSet Plot Dialog

4개 이상 ATAC-seq DA 데이터셋의 peak_id(좌표) 기반 overlap을 UpSet plot으로 시각화.
Venn diagram은 4-way 이상에서 가독성이 떨어지므로 이 다이얼로그를 사용한다.

전제: 비교 대상 데이터셋들이 같은 peak set(consensus/union peak)에서 나와야
peak_id 기반 비교가 유효하다.
"""

import logging

import pandas as pd
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLabel, QMessageBox, QFileDialog,
)

from gui.base_plot_dialog import BasePlotDialog
from utils import peak_overlap
from utils.export_paths import remembered_save_path


class UpsetPlotDialog(BasePlotDialog):
    """ATAC DA 데이터셋(4개 이상)의 peak_id 기반 overlap을 UpSet plot으로 표시."""

    def __init__(self, datasets, parent=None):
        if len(datasets) < 2:
            raise ValueError("UpSet plot requires at least 2 datasets")

        self.datasets = datasets
        self.logger = logging.getLogger(__name__)
        self._upset_data = None

        super().__init__(f"DA Peak Overlap — {len(datasets)} Datasets", parent, figsize=(11, 7))

        warning = peak_overlap.check_consensus(datasets)
        if warning:
            QMessageBox.warning(self, "Peak Set 불일치 가능성", warning)

        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        settings_group = QGroupBox("Filter & Display")
        settings_layout = QFormLayout()

        self.use_sig_only = QCheckBox("Significant peaks only")
        self.use_sig_only.setChecked(True)
        self.use_sig_only.stateChanged.connect(self._update_plot)
        settings_layout.addRow(self.use_sig_only)

        self.padj_spin = QDoubleSpinBox()
        self.padj_spin.setRange(0.0001, 1.0)
        self.padj_spin.setDecimals(4)
        self.padj_spin.setValue(0.05)
        self.padj_spin.setSingleStep(0.01)
        self.padj_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Adj. p-value ≤", self.padj_spin)

        self.log2fc_spin = QDoubleSpinBox()
        self.log2fc_spin.setRange(0.0, 10.0)
        self.log2fc_spin.setDecimals(4)
        self.log2fc_spin.setValue(1.0)
        self.log2fc_spin.setSingleStep(0.1)
        self.log2fc_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("|log2FC| ≥", self.log2fc_spin)

        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(3, 50)
        self.top_n_spin.setValue(15)
        self.top_n_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Max intersections shown:", self.top_n_spin)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        self._count_label = QLabel("")
        self._count_label.setWordWrap(True)
        layout.addWidget(self._count_label)

    def _extra_buttons(self):
        return [("Export Data", self._export_data)]

    # ── Data helpers ──────────────────────────────────────────────────────

    def _get_peak_sets(self) -> dict:
        padj = self.padj_spin.value() if self.use_sig_only.isChecked() else None
        lfc = self.log2fc_spin.value() if self.use_sig_only.isChecked() else None

        peak_sets = {}
        for ds in self.datasets:
            peak_sets[ds.name] = peak_overlap.get_peak_set(ds, padj, lfc)
        return peak_sets

    def _build_membership_df(self, peak_sets):
        """peak_sets(dict) → long-format(dataset/item) 멤버십 테이블. (df, order) 반환."""
        order = list(peak_sets.keys())
        frames = [pd.DataFrame({'dataset': name, 'item': list(s)})
                  for name, s in peak_sets.items()]
        df = pd.concat(frames, ignore_index=True) if frames else \
            pd.DataFrame(columns=['dataset', 'item'])
        return df, order

    def _plot_params(self, order=None) -> dict:
        if order is None:
            order = [ds.name for ds in self.datasets]
        return {
            'top_n': self.top_n_spin.value(),
            'order': order,
            'title': 'DA Peak Overlap Across Comparisons',
        }

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/upset.py 에 있으며 번들과 공유한다."""
        from plots.upset import render_upset

        self.figure.clear()
        peak_sets = self._get_peak_sets()
        self._count_label.setText(
            "Set sizes — " + ", ".join(f"{name}: {len(s)}" for name, s in peak_sets.items())
        )
        df, order = self._build_membership_df(peak_sets)
        self._upset_data = render_upset(self.figure, df, self._plot_params(order))
        self.canvas.draw()

    # ── Bundle export ─────────────────────────────────────────────────────

    def get_bundle_context(self) -> dict:
        peak_sets = self._get_peak_sets()
        df, order = self._build_membership_df(peak_sets)
        return {
            'figure': self.figure,
            'dataframe': df,
            'plot_params': self._plot_params(order),
            'dataset_name': 'da_peak_overlap',
            'plot_type': 'upset',
            'figure_title': f'DA Peak Overlap — {len(self.datasets)} Datasets',
            'figure_slug': 'upset_plot',
            'source_stem': 'upset_plot',
            'notes': 'Generated from cmg-seqviewer UpSet plot (long-format membership input)',
        }

    def _apply_labels(self):
        """UpSet은 다중 axes 구조라 단일 axes 가정의 기본 구현을 쓰지 않고
        제목만 figure suptitle로 덮어쓴다."""
        title = self._labels.get_params().get('labels_title', '')
        if title:
            self.figure.suptitle(title, fontsize=13, fontweight='bold')

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        if self._upset_data is None:
            QMessageBox.warning(self, "No Data", "내보낼 데이터가 없습니다.")
            return

        path, _ = remembered_save_path(
            self, "Export Peak Overlap Data", "da_peak_overlap.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            df = self._upset_data.reset_index().rename(columns={'id': 'peak_id'})
            if path.lower().endswith('.csv'):
                df.to_csv(path, index=False)
            else:
                df.to_excel(path, index=False, sheet_name="Peak_Overlap")
            QMessageBox.information(self, "Exported", f"저장 완료:\n{path}")
        except Exception as e:
            self.logger.error(f"Failed to export peak overlap data: {e}")
            QMessageBox.critical(self, "Export Error", f"내보내기 실패:\n{e}")
