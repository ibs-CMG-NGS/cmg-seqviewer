"""
UpSet Plot Dialog

4개 이상 ATAC-seq DA 데이터셋의 peak_id(좌표) 기반 overlap을 UpSet plot으로 시각화.
Venn diagram은 4-way 이상에서 가독성이 떨어지므로 이 다이얼로그를 사용한다.

전제: 비교 대상 데이터셋들이 같은 peak set(consensus/union peak)에서 나와야
peak_id 기반 비교가 유효하다.
"""

import logging

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLabel, QMessageBox, QFileDialog,
)
from upsetplot import UpSet, from_contents
from upsetplot import util as _upsetplot_util

from gui.base_plot_dialog import BasePlotDialog
from utils import peak_overlap


def _patched_plot_matrix(self, ax):
    """upsetplot.UpSet.plot_matrix의 pandas 3.0 Copy-on-Write 호환 패치.

    원본 구현은 `styles[col].fillna(value, inplace=True)` (chained assignment)를 사용하는데,
    pandas>=3.0의 강제 CoW 하에서는 이 inplace 호출이 항상 no-op이 되어
    facecolor 등이 NaN으로 남고 matplotlib scatter가 'Invalid RGBA argument: nan'으로 실패한다.
    로직은 원본과 동일하게 유지하고, fillna만 non-inplace 대입으로 교체한다.
    """
    ax = self._reorient(ax)
    data = self.intersections
    n_cats = data.index.nlevels

    inclusion = data.index.to_frame().values

    styles = [
        [
            self.subset_styles[i]
            if inclusion[i, j]
            else {"facecolor": self._other_dots_color, "linewidth": 0}
            for j in range(n_cats)
        ]
        for i in range(len(data))
    ]
    styles = sum(styles, [])
    style_columns = {
        "facecolor": "facecolors",
        "edgecolor": "edgecolors",
        "linewidth": "linewidths",
        "linestyle": "linestyles",
        "hatch": "hatch",
    }
    styles = (
        pd.DataFrame(styles)
        .reindex(columns=style_columns.keys())
        .astype(
            {
                "facecolor": "O",
                "edgecolor": "O",
                "linewidth": float,
                "linestyle": "O",
                "hatch": "O",
            }
        )
    )
    styles["linewidth"] = styles["linewidth"].fillna(1)
    styles["facecolor"] = styles["facecolor"].fillna(self._facecolor)
    styles["edgecolor"] = styles["edgecolor"].fillna(styles["facecolor"])
    styles["linestyle"] = styles["linestyle"].fillna("solid")
    del styles["hatch"]

    x = np.repeat(np.arange(len(data)), n_cats)
    y = np.tile(np.arange(n_cats), len(data))

    if self._element_size is not None:
        s = (self._element_size * 0.35) ** 2
    else:
        s = 200
    ax.scatter(
        *self._swapaxes(x, y),
        s=s,
        zorder=10,
        **styles.rename(columns=style_columns),
    )

    if self._with_lines:
        idx = np.flatnonzero(inclusion)
        line_data = (
            pd.Series(y[idx], index=x[idx])
            .groupby(level=0)
            .aggregate(["min", "max"])
        )
        colors = pd.Series(
            [
                style.get("edgecolor", style.get("facecolor", self._facecolor))
                for style in self.subset_styles
            ],
            name="color",
        )
        line_data = line_data.join(colors)
        ax.vlines(
            line_data.index.values,
            line_data["min"],
            line_data["max"],
            lw=2,
            colors=line_data["color"],
            zorder=5,
        )

    tick_axis = ax.yaxis
    tick_axis.set_ticks(np.arange(n_cats))
    tick_axis.set_ticklabels(
        data.index.names, rotation=0 if self._horizontal else -90
    )
    ax.xaxis.set_visible(False)
    ax.tick_params(axis="both", which="both", length=0)
    if not self._horizontal:
        ax.yaxis.set_ticks_position("top")
    ax.set_frame_on(False)
    ax.set_xlim(-0.5, x[-1] + 0.5, auto=False)
    ax.grid(False)


UpSet.plot_matrix = _patched_plot_matrix


def _patched_label_sizes(self, ax, rects, where):
    """upsetplot.UpSet._label_sizes의 numpy>=2.0 호환 패치.

    원본은 `0.01 * abs(np.diff(ax.get_xlim()))`로 margin을 계산하는데, 이 결과는
    길이 1짜리 ndarray이다. numpy>=2.0에서는 matplotlib의 Text 좌표 변환이
    이런 1-요소 배열을 암묵적으로 스칼라로 변환하지 못해
    'only 0-dimensional arrays can be converted to Python scalars' 오류가 난다.
    로직은 원본과 동일하게 유지하고 margin만 float 스칼라로 변환한다.
    """
    if not self._show_counts and not self._show_percentages:
        return
    if self._show_counts is True:
        count_fmt = "{:.0f}"
    else:
        count_fmt = self._show_counts
        if "{" not in count_fmt:
            count_fmt = _upsetplot_util.to_new_pos_format(count_fmt)

    pct_fmt = "{:.1%}" if self._show_percentages is True else self._show_percentages

    if count_fmt and pct_fmt:
        if where == "top":
            fmt = f"{count_fmt}\n({pct_fmt})"
        else:
            fmt = f"{count_fmt} ({pct_fmt})"

        def make_args(val):
            return val, val / self.total
    elif count_fmt:
        fmt = count_fmt

        def make_args(val):
            return (val,)
    else:
        fmt = pct_fmt

        def make_args(val):
            return (val / self.total,)

    if where == "right":
        margin = float(0.01 * abs(np.diff(ax.get_xlim()))[0])
        for rect in rects:
            width = rect.get_width() + rect.get_x()
            ax.text(
                width + margin,
                rect.get_y() + rect.get_height() * 0.5,
                fmt.format(*make_args(width)),
                ha="left",
                va="center",
            )
    elif where == "left":
        margin = float(0.01 * abs(np.diff(ax.get_xlim()))[0])
        for rect in rects:
            width = rect.get_width() + rect.get_x()
            ax.text(
                width + margin,
                rect.get_y() + rect.get_height() * 0.5,
                fmt.format(*make_args(width)),
                ha="right",
                va="center",
            )
    elif where == "top":
        margin = float(0.01 * abs(np.diff(ax.get_ylim()))[0])
        for rect in rects:
            height = rect.get_height() + rect.get_y()
            ax.text(
                rect.get_x() + rect.get_width() * 0.5,
                height + margin,
                fmt.format(*make_args(height)),
                ha="center",
                va="bottom",
            )
    else:
        raise NotImplementedError("unhandled where: %r" % where)


UpSet._label_sizes = _patched_label_sizes


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
        self.log2fc_spin.setDecimals(2)
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

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()

        peak_sets = self._get_peak_sets()
        self._count_label.setText(
            "Set sizes — " + ", ".join(f"{name}: {len(s)}" for name, s in peak_sets.items())
        )

        non_empty = {k: v for k, v in peak_sets.items() if v}
        if len(non_empty) < 2:
            ax = self.figure.add_subplot(111)
            ax.text(
                0.5, 0.5,
                "표시할 peak이 충분하지 않습니다.\n필터 조건을 조정하세요.",
                ha='center', va='center', fontsize=12,
            )
            self.canvas.draw()
            return

        self._upset_data = from_contents(non_empty)

        upset = UpSet(
            self._upset_data,
            subset_size='count',
            sort_by='cardinality',
            max_subset_rank=self.top_n_spin.value(),
            show_counts=True,
        )
        upset.plot(fig=self.figure)
        self.figure.suptitle(
            "DA Peak Overlap Across Comparisons", fontsize=13, fontweight='bold'
        )

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

        path, _ = QFileDialog.getSaveFileName(
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
