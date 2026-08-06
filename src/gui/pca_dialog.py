"""
PCA Plot Dialog for RNA-Seq Data

DE 데이터셋의 샘플별 abundance 컬럼을 이용한 PCA 시각화 다이얼로그.
추가 입력 없이 parquet에 저장된 샘플 컬럼을 자동 감지하여 사용합니다.
"""

import logging

import numpy as np
import pandas as pd
import matplotlib

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFormLayout, QGroupBox, QSpinBox, QComboBox,
    QCheckBox, QMessageBox, QFileDialog,
)
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont
from PyQt6.QtCore import Qt

from models.standard_columns import StandardColumns
from gui.base_plot_dialog import BasePlotDialog


# ── 아이콘 헬퍼 ─────────────────────────────────────────────────────────────
def _make_icon(emoji: str, bg_color: QColor = None) -> QIcon:
    if bg_color is None:
        bg_color = QColor(60, 120, 200)
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(bg_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 60, 60)
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI Emoji", 28, QFont.Weight.Bold)
    painter.setFont(font)
    from PyQt6.QtCore import QRect
    painter.drawText(QRect(0, 0, 64, 64), Qt.AlignmentFlag.AlignCenter, emoji)
    painter.end()
    return QIcon(pixmap)


# ── 샘플 컬럼 감지 ───────────────────────────────────────────────────────────
_DE_EXCLUDE_PATTERNS = {
    'basemean', 'base_mean', 'log2fold', 'log2fc', 'logfc', 'foldchange',
    'lfcse', 'stat', 'statistic', 'pval', 'padj', 'fdr', 'qvalue', 'adj_p',
    'gene_id', 'gene', 'symbol', 'dataset', 'description', 'name',
    'pvalue', 'p_value',
}

_STANDARD_DE_COLS = set(StandardColumns.get_de_all()) | {
    StandardColumns.GENE_ID, StandardColumns.SYMBOL,
}


def auto_group_samples(sample_cols: list) -> dict:
    """샘플 컬럼명에서 조건(그룹)을 추출해 복제(replicate)를 하나로 묶는다.

    끝의 전역 인덱스(_S20 등)와 복제 번호를 제거해 조건명을 얻는다.
      JHL_Con1_S20 / JHL_Con2_S21 / JHL_Con3_S22 -> 'JHL_Con'
      JHL_1D_1_S23 / JHL_1D_2_S24 / JHL_1D_3_S25 -> 'JHL_1D'
      JHL_24h_1_S26 -> 'JHL_24h'
    """
    import re
    groups: dict = {}
    for c in sample_cols:
        g = re.sub(r'[_\-.]?[Ss]\d+$', '', str(c))   # 전역 인덱스 (_S20)
        g = re.sub(r'[_\-.]?\d+$', '', g)             # 복제 번호
        g = g.strip('_-. ') or str(c)
        groups.setdefault(g, []).append(c)
    return groups


def _useful_grouping(groups: dict, n_samples: int) -> bool:
    """복제를 실제로 묶는 유효한 그룹핑인가 (그룹 1개도, 샘플당 1개도 아님)."""
    k = len(groups)
    return bool(groups) and 1 < k < n_samples and any(len(v) > 1 for v in groups.values())


def detect_sample_columns(df: pd.DataFrame) -> list:
    result = []
    for col in df.columns:
        if col in _STANDARD_DE_COLS:
            continue
        col_lower = col.lower()
        if any(pat in col_lower for pat in _DE_EXCLUDE_PATTERNS):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            result.append(col)
    return result


# ─────────────────────────────────────────────────────────────────────────────

class PCADialog(BasePlotDialog):
    """
    샘플 PCA Plot 다이얼로그

    DE 테이블의 샘플 abundance 컬럼을 자동 감지하여 PCA를 수행합니다.
    """

    # 세션 동안 설정 유지
    _saved_settings: dict = {
        'n_genes': 500,
        'transform': 'log2',
        'scaling': 'standard',
        'x_pc': 1,
        'y_pc': 2,
        'point_size': 80,
        'show_labels': True,
        'title': 'PCA — Sample Expression',
        'fig_width': 8,
        'fig_height': 6,
    }

    def __init__(self, dataframe: pd.DataFrame, dataset_name: str = "", parent=None,
                 sample_columns: list = None, sample_groups: dict = None):
        self.logger = logging.getLogger(__name__)
        self.dataframe = dataframe
        self.dataset_name = dataset_name

        # 샘플 컬럼: 명시(metadata) 우선, 없으면 자동 감지
        explicit = [c for c in (sample_columns or []) if c in dataframe.columns]
        self.sample_cols = explicit if explicit else detect_sample_columns(dataframe)

        # 그룹핑: metadata 의 그룹이 복제를 제대로 묶으면 사용, 아니면(예: 샘플당 1개로
        # 쪼개진 경우) 샘플명에서 조건을 추출해 자동 그룹핑. 둘 다 안 되면 그룹 없음.
        n = len(self.sample_cols)
        meta_groups = sample_groups or {}
        if _useful_grouping(meta_groups, n):
            self.sample_groups = meta_groups
        else:
            auto = auto_group_samples(self.sample_cols)
            self.sample_groups = auto if _useful_grouping(auto, n) else {}

        # 설정 복원
        s = self._saved_settings
        self.n_genes    = s['n_genes']
        self.transform  = s['transform']
        self.scaling    = s['scaling']
        self.x_pc       = s['x_pc']
        self.y_pc       = s['y_pc']
        self.point_size = s['point_size']
        self.show_labels = s['show_labels']
        self.plot_title  = s['title'] if not dataset_name else f"PCA — {dataset_name}"
        self.fig_width   = s['fig_width']
        self.fig_height  = s['fig_height']

        # PCA 결과 캐시 (export 용)
        self._pca_result = None
        self._explained_var = []

        super().__init__("PCA Plot", parent, figsize=(self.fig_width, self.fig_height))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Dataset Info
        info_group = QGroupBox("Dataset Info")
        info_layout = QFormLayout(info_group)
        n_samples = len(self.sample_cols)
        n_genes_total = len(self.dataframe)
        info_layout.addRow("Samples detected:", QLabel(str(n_samples)))
        info_layout.addRow("Total genes:", QLabel(str(n_genes_total)))
        if self.sample_cols:
            sample_preview = ', '.join(self.sample_cols[:4])
            if len(self.sample_cols) > 4:
                sample_preview += f', … (+{len(self.sample_cols)-4})'
            lbl = QLabel(sample_preview)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #555; font-size: 10px;")
            info_layout.addRow("Columns:", lbl)
        layout.addWidget(info_group)

        # PCA Settings
        pca_group = QGroupBox("PCA Settings")
        pca_layout = QFormLayout(pca_group)

        self.gene_spin = QSpinBox()
        self.gene_spin.setRange(10, 10000)
        self.gene_spin.setValue(self.n_genes_clamped())
        self.gene_spin.setSingleStep(100)
        pca_layout.addRow("Top genes (variance):", self.gene_spin)

        self.transform_combo = QComboBox()
        self.transform_combo.addItems(["log2(x+1)", "log1p", "None"])
        self.transform_combo.setItemData(0, "log2(x + 1)", 3)      # tooltip
        self.transform_combo.setItemData(1, "log1p (natural log)", 3)
        self.transform_combo.setItemData(2, "None (raw values)", 3)
        transform_map = {'log2': 0, 'log1p': 1, 'none': 2}
        self.transform_combo.setCurrentIndex(transform_map.get(self.transform, 0))
        pca_layout.addRow("Transformation:", self.transform_combo)

        self.scaling_combo = QComboBox()
        self.scaling_combo.addItems(["StandardScaler", "None"])
        self.scaling_combo.setItemData(0, "StandardScaler (mean=0, std=1)", 3)
        self.scaling_combo.setItemData(1, "None (no scaling)", 3)
        self.scaling_combo.setCurrentIndex(0 if self.scaling == 'standard' else 1)
        pca_layout.addRow("Feature scaling:", self.scaling_combo)

        self.x_pc_spin = QSpinBox()
        self.x_pc_spin.setRange(1, 10)
        self.x_pc_spin.setValue(self.x_pc)
        pca_layout.addRow("X axis PC:", self.x_pc_spin)

        self.y_pc_spin = QSpinBox()
        self.y_pc_spin.setRange(1, 10)
        self.y_pc_spin.setValue(self.y_pc)
        pca_layout.addRow("Y axis PC:", self.y_pc_spin)

        layout.addWidget(pca_group)

        # Display Settings
        disp_group = QGroupBox("Display Settings")
        disp_layout = QFormLayout(disp_group)

        self.point_spin = QSpinBox()
        self.point_spin.setRange(10, 500)
        self.point_spin.setValue(self.point_size)
        self.point_spin.setSingleStep(10)
        disp_layout.addRow("Point size:", self.point_spin)

        # 색상 기준: 그룹(복제를 조건으로 묶어 색칠 + 범례) vs 샘플(각 샘플 개별 색)
        self.color_by_combo = QComboBox()
        if self.sample_groups:
            n_grp = len(self.sample_groups)
            self.color_by_combo.addItem(f"Group ({n_grp})", "group")
            self.color_by_combo.addItem("Sample", "sample")
        else:
            # 유효 그룹이 없으면 그룹 옵션 비활성(샘플만)
            self.color_by_combo.addItem("Sample", "sample")
            self.color_by_combo.setToolTip(
                "샘플명에서 조건 그룹을 찾지 못했습니다. 각 샘플을 개별 색으로 표시합니다.")
        self.color_by_combo.currentIndexChanged.connect(self._update_plot)
        disp_layout.addRow("Color by:", self.color_by_combo)

        self.label_check = QCheckBox("Show sample labels")
        self.label_check.setChecked(self.show_labels)
        disp_layout.addRow("", self.label_check)

        layout.addWidget(disp_group)

    def _extra_buttons(self) -> list:
        return [("Export PCA Scores (CSV)", self._export_csv)]

    # ── Bundle / params ────────────────────────────────────────────────────

    def _plot_params(self) -> dict:
        return {
            'n_genes': self.n_genes,
            'transform': self.transform,
            'scaling': self.scaling,
            'x_pc': self.x_pc,
            'y_pc': self.y_pc,
            'point_size': self.point_size,
            'show_labels': self.show_labels,
            'title': self.plot_title,
            'sample_columns': list(self.sample_cols),
            'sample_groups': (
                {g: list(cols) for g, cols in self.sample_groups.items()}
                if self._color_mode() == 'group' else {}
            ),
        }

    def _color_mode(self) -> str:
        cb = getattr(self, 'color_by_combo', None)
        return cb.currentData() if cb is not None and cb.currentData() else (
            'group' if self.sample_groups else 'sample')

    def get_bundle_context(self) -> dict:
        return {
            'figure': self.figure,
            'dataframe': self.dataframe,
            'plot_params': self._plot_params(),
            'dataset_name': getattr(self, 'dataset_name', 'unknown'),
            'plot_type': 'pca',
            'figure_title': self.plot_title or 'PCA Plot',
            'figure_slug': 'pca_plot',
            'source_stem': 'pca_plot',
            'notes': 'Generated from cmg-seqviewer PCA plot',
        }

    # ── Settings helpers ──────────────────────────────────────────────────

    def n_genes_clamped(self) -> int:
        return min(self.n_genes, max(10, len(self.dataframe)))

    def _sync_settings_from_ui(self):
        self.n_genes     = self.gene_spin.value()
        self.transform   = ['log2', 'log1p', 'none'][self.transform_combo.currentIndex()]
        self.scaling     = 'standard' if self.scaling_combo.currentIndex() == 0 else 'none'
        self.x_pc        = self.x_pc_spin.value()
        self.y_pc        = self.y_pc_spin.value()
        self.point_size  = self.point_spin.value()
        self.show_labels = self.label_check.isChecked()

    def _save_settings(self):
        PCADialog._saved_settings.update({
            'n_genes':     self.n_genes,
            'transform':   self.transform,
            'scaling':     self.scaling,
            'x_pc':        self.x_pc,
            'y_pc':        self.y_pc,
            'point_size':  self.point_size,
            'show_labels': self.show_labels,
            'title':       self.plot_title,
            'fig_width':   self.fig_width,
            'fig_height':  self.fig_height,
        })

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        """렌더는 순수 함수 src/plots/pca.py::render_pca 에 있으며 재현 번들과 공유한다."""
        from plots.pca import render_pca

        self._sync_settings_from_ui()
        self._save_settings()
        self.figure.clear()

        try:
            result = render_pca(self.figure, self.dataframe, self._plot_params())
        except Exception as e:
            self.logger.error(f"PCA failed: {e}", exc_info=True)
            ax = self.figure.axes[0] if self.figure.axes else self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f"PCA failed:\n{e}", ha='center', va='center',
                    transform=ax.transAxes, fontsize=11, color='red')
            self.canvas.draw()
            return

        # export 캐시 (scores / explained variance)
        if result is not None:
            self._pca_result, self._explained_var = result

        self.figure.tight_layout()
        self.canvas.draw()

    def _run_pca(self):
        df = self.dataframe.copy()
        expr = df[self.sample_cols].copy()
        expr = expr.fillna(0)

        n = min(self.n_genes, len(expr))
        variances = expr.var(axis=1)
        top_idx = variances.nlargest(n).index
        expr = expr.loc[top_idx]

        mat = expr.values.astype(float)
        if self.transform == 'log2':
            mat = np.log2(mat + 1.0)
        elif self.transform == 'log1p':
            mat = np.log1p(mat)

        X = mat.T

        if self.scaling == 'standard':
            mean = X.mean(axis=0)
            std  = X.std(axis=0, ddof=0)
            std[std == 0] = 1.0
            X = (X - mean) / std

        X_centered = X - X.mean(axis=0)
        U, s, Vt = np.linalg.svd(X_centered, full_matrices=False)
        explained_variance = (s ** 2) / (X_centered.shape[0] - 1)
        total_variance = explained_variance.sum()
        explained_variance_ratio = (explained_variance / total_variance).tolist()
        n_components = min(len(self.sample_cols), X_centered.shape[1], 10)
        scores = U[:, :n_components] * s[:n_components]

        self._pca_result = pd.DataFrame(
            scores,
            index=self.sample_cols,
            columns=[f"PC{i+1}" for i in range(scores.shape[1])],
        )
        self._explained_var = explained_variance_ratio[:n_components]

        return scores, self._explained_var

    # ── Warning ───────────────────────────────────────────────────────────

    def _show_no_sample_warning(self, ax=None):
        msg = (
            "No sample abundance columns detected.\n\n"
            "PCA requires per-sample normalized count columns.\n"
            "Make sure your DE result file includes sample columns\n"
            "(e.g. sample_ctrl1, sample_trt1, …) alongside\n"
            "the standard DE statistics."
        )
        if ax is not None:
            ax.text(0.5, 0.5, msg, ha='center', va='center',
                    transform=ax.transAxes, fontsize=11,
                    bbox=dict(boxstyle='round', fc='#fff3cd', ec='#ffc107'))
        else:
            QMessageBox.warning(self, "No Sample Columns", msg)

    # ── Export ────────────────────────────────────────────────────────────

    def _export_csv(self):
        if self._pca_result is None:
            QMessageBox.information(self, "No Data", "Run the PCA first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PCA Scores", "pca_scores.csv", "CSV Files (*.csv)"
        )
        if path:
            out = self._pca_result.copy()
            if self._explained_var:
                pct = [f"{v*100:.2f}%" for v in self._explained_var]
                header_row = pd.DataFrame(
                    [pct[:out.shape[1]]],
                    columns=out.columns,
                    index=["explained_var"],
                )
                out = pd.concat([header_row, out])
            out.to_csv(path)
            QMessageBox.information(self, "Saved", f"PCA scores saved to:\n{path}")
