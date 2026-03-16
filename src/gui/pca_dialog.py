"""
PCA Plot Dialog for RNA-Seq Data

DE 데이터셋의 샘플별 abundance 컬럼을 이용한 PCA 시각화 다이얼로그.
추가 입력 없이 parquet에 저장된 샘플 컬럼을 자동 감지하여 사용합니다.
"""

import logging

import matplotlib
matplotlib.use('Qt5Agg')
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFormLayout, QGroupBox, QSpinBox, QComboBox,
    QCheckBox, QMessageBox, QFileDialog, QSizePolicy,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont

from models.standard_columns import StandardColumns


# ── 아이콘 헬퍼 (visualization_dialog 와 동일 패턴) ─────────────────────────
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


# ── 샘플 컬럼 감지 (data_loader._remove_zero_abundance_genes 와 동일 방식) ──
_DE_EXCLUDE_PATTERNS = {
    'basemean', 'base_mean', 'log2fold', 'log2fc', 'logfc', 'foldchange',
    'lfcse', 'stat', 'statistic', 'pval', 'padj', 'fdr', 'qvalue', 'adj_p',
    'gene_id', 'gene', 'symbol', 'dataset', 'description', 'name',
    'pvalue', 'p_value',
}

_STANDARD_DE_COLS = set(StandardColumns.get_de_all()) | {
    StandardColumns.GENE_ID, StandardColumns.SYMBOL,
}


def detect_sample_columns(df: pd.DataFrame) -> list[str]:
    """
    DE DataFrame 에서 샘플 abundance 컬럼 목록 반환.

    조건:
    1. 표준 DE 컬럼명이 아닐 것
    2. 컬럼명에 제외 키워드가 없을 것
    3. 숫자형(numeric) 컬럼일 것
    """
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

class PCADialog(QDialog):
    """
    샘플 PCA Plot 다이얼로그

    DE 테이블의 샘플 abundance 컬럼을 자동 감지하여 PCA를 수행합니다.
    - 입력: gene × sample 행렬 (log2 변환 + StandardScaler 선택 가능)
    - 출력: PC1/PC2 scatter plot (샘플 이름 레이블 포함)
    """

    # 세션 동안 설정 유지
    _saved_settings: dict = {
        'n_genes': 500,
        'transform': 'log2',        # 'none' | 'log2' | 'log1p'
        'scaling': 'standard',       # 'none' | 'standard'
        'x_pc': 1,
        'y_pc': 2,
        'point_size': 80,
        'show_labels': True,
        'title': 'PCA — Sample Expression',
        'fig_width': 8,
        'fig_height': 6,
    }

    def __init__(self, dataframe: pd.DataFrame, dataset_name: str = "", parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.dataframe = dataframe
        self.dataset_name = dataset_name

        # 샘플 컬럼 감지
        self.sample_cols = detect_sample_columns(dataframe)

        self.setWindowTitle("🔵 PCA Plot")
        self.setWindowIcon(_make_icon("🔵", QColor(60, 120, 200)))
        self.setMinimumSize(1100, 750)

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
        self._pca_result: pd.DataFrame | None = None
        self._explained_var: list[float] = []

        self._init_ui()

        if not self.sample_cols:
            self._show_no_sample_warning()
        else:
            self._plot()

    # ── UI ────────────────────────────────────────────────────────────────

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # ── 왼쪽: 설정 패널 ──────────────────────────────────────────────
        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 데이터 정보
        info_group = QGroupBox("Dataset Info")
        info_layout = QFormLayout(info_group)
        n_samples = len(self.sample_cols)
        n_genes   = len(self.dataframe)
        info_layout.addRow("Samples detected:", QLabel(str(n_samples)))
        info_layout.addRow("Total genes:", QLabel(str(n_genes)))
        if self.sample_cols:
            sample_preview = ', '.join(self.sample_cols[:4])
            if len(self.sample_cols) > 4:
                sample_preview += f', … (+{len(self.sample_cols)-4})'
            lbl = QLabel(sample_preview)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #555; font-size: 10px;")
            info_layout.addRow("Columns:", lbl)
        left.addWidget(info_group)

        # PCA 설정
        pca_group = QGroupBox("PCA Settings")
        pca_layout = QFormLayout(pca_group)

        self.gene_spin = QSpinBox()
        self.gene_spin.setRange(10, 10000)
        self.gene_spin.setValue(self.n_genes_clamped())
        self.gene_spin.setSingleStep(100)
        self.gene_spin.valueChanged.connect(self._on_settings_changed)
        pca_layout.addRow("Top genes (variance):", self.gene_spin)

        self.transform_combo = QComboBox()
        self.transform_combo.addItems([
            "log2(x + 1)",
            "log1p  (natural log)",
            "None (raw values)",
        ])
        transform_map = {'log2': 0, 'log1p': 1, 'none': 2}
        self.transform_combo.setCurrentIndex(transform_map.get(self.transform, 0))
        self.transform_combo.currentIndexChanged.connect(self._on_settings_changed)
        pca_layout.addRow("Transformation:", self.transform_combo)

        self.scaling_combo = QComboBox()
        self.scaling_combo.addItems([
            "StandardScaler  (mean=0, std=1)",
            "None (no scaling)",
        ])
        self.scaling_combo.setCurrentIndex(0 if self.scaling == 'standard' else 1)
        self.scaling_combo.currentIndexChanged.connect(self._on_settings_changed)
        pca_layout.addRow("Feature scaling:", self.scaling_combo)

        self.x_pc_spin = QSpinBox()
        self.x_pc_spin.setRange(1, 10)
        self.x_pc_spin.setValue(self.x_pc)
        self.x_pc_spin.valueChanged.connect(self._on_settings_changed)
        pca_layout.addRow("X axis PC:", self.x_pc_spin)

        self.y_pc_spin = QSpinBox()
        self.y_pc_spin.setRange(1, 10)
        self.y_pc_spin.setValue(self.y_pc)
        self.y_pc_spin.valueChanged.connect(self._on_settings_changed)
        pca_layout.addRow("Y axis PC:", self.y_pc_spin)

        left.addWidget(pca_group)

        # 표시 설정
        disp_group = QGroupBox("Display Settings")
        disp_layout = QFormLayout(disp_group)

        self.point_spin = QSpinBox()
        self.point_spin.setRange(10, 500)
        self.point_spin.setValue(self.point_size)
        self.point_spin.setSingleStep(10)
        self.point_spin.valueChanged.connect(self._on_settings_changed)
        disp_layout.addRow("Point size:", self.point_spin)

        self.label_check = QCheckBox("Show sample labels")
        self.label_check.setChecked(self.show_labels)
        self.label_check.stateChanged.connect(self._on_settings_changed)
        disp_layout.addRow("", self.label_check)

        left.addWidget(disp_group)

        # 버튼
        btn_layout = QVBoxLayout()
        self.update_btn = QPushButton("🔄 Update Plot")
        self.update_btn.clicked.connect(self._plot)
        btn_layout.addWidget(self.update_btn)

        export_csv_btn = QPushButton("💾 Export PCA Scores (CSV)")
        export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(export_csv_btn)

        export_img_btn = QPushButton("🖼 Export Image (PNG/SVG)")
        export_img_btn.clicked.connect(self._export_image)
        btn_layout.addWidget(export_img_btn)

        close_btn = QPushButton("✖ Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        left.addLayout(btn_layout)
        left.addStretch()

        left_widget_container = QGroupBox()
        left_widget_container.setFlat(True)
        left_widget_container.setLayout(left)
        left_widget_container.setFixedWidth(310)
        main_layout.addWidget(left_widget_container)

        # ── 오른쪽: 플롯 영역 ────────────────────────────────────────────
        right = QVBoxLayout()

        self.figure = Figure(figsize=(self.fig_width, self.fig_height), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.toolbar = NavigationToolbar(self.canvas, self)

        right.addWidget(self.toolbar)
        right.addWidget(self.canvas)

        main_layout.addLayout(right, stretch=1)

    # ── 설정 동기화 ───────────────────────────────────────────────────────

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

    def _on_settings_changed(self):
        pass  # 자동 업데이트 없음 — Update Plot 버튼으로만 갱신

    # ── PCA 계산 + 플롯 ───────────────────────────────────────────────────

    def _plot(self):
        self._sync_settings_from_ui()
        self._save_settings()
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not self.sample_cols:
            self._show_no_sample_warning(ax)
            self.canvas.draw()
            return

        try:
            scores, explained = self._run_pca()
        except Exception as e:
            self.logger.error(f"PCA failed: {e}", exc_info=True)
            ax.text(0.5, 0.5, f"PCA failed:\n{e}",
                    ha='center', va='center', transform=ax.transAxes, fontsize=11,
                    color='red')
            self.canvas.draw()
            return

        n_pcs = scores.shape[1]
        xi = self.x_pc - 1
        yi = self.y_pc - 1

        if xi >= n_pcs or yi >= n_pcs:
            ax.text(0.5, 0.5,
                    f"Only {n_pcs} PCs available.\nReduce X/Y axis PC numbers.",
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            self.canvas.draw()
            return

        xs = scores[:, xi]
        ys = scores[:, yi]
        labels = self.sample_cols

        # 색상 팔레트 (샘플 수에 맞게 자동)
        cmap = matplotlib.colormaps.get_cmap('tab10')
        colors = [cmap(i % 10) for i in range(len(labels))]

        scatter = ax.scatter(xs, ys, s=self.point_size, c=colors, alpha=0.85,
                             edgecolors='white', linewidths=0.8, zorder=3)

        if self.show_labels:
            for x, y, lbl in zip(xs, ys, labels):
                ax.annotate(
                    lbl, (x, y),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=8, color='#222',
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6, ec='none'),
                )

        pct_x = explained[xi] * 100 if xi < len(explained) else 0
        pct_y = explained[yi] * 100 if yi < len(explained) else 0

        ax.set_xlabel(f"PC{self.x_pc}  ({pct_x:.1f}% variance)", fontsize=12)
        ax.set_ylabel(f"PC{self.y_pc}  ({pct_y:.1f}% variance)", fontsize=12)
        ax.set_title(self.plot_title, fontsize=13, fontweight='bold')
        ax.axhline(0, color='#bbb', linewidth=0.8, linestyle='--', zorder=1)
        ax.axvline(0, color='#bbb', linewidth=0.8, linestyle='--', zorder=1)
        ax.grid(True, alpha=0.3, zorder=0)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # scree 정보 (오른쪽 아래 작게)
        scree_lines = [f"PC{i+1}: {v*100:.1f}%" for i, v in enumerate(explained[:5])]
        scree_text  = "Explained variance:\n" + "  ".join(scree_lines)
        ax.text(0.99, 0.01, scree_text,
                transform=ax.transAxes, fontsize=7.5,
                ha='right', va='bottom', color='#666',
                bbox=dict(boxstyle='round', fc='white', alpha=0.7, ec='#ccc'))

        self.figure.tight_layout()
        self.canvas.draw()

    def _run_pca(self) -> tuple[np.ndarray, list[float]]:
        """
        PCA 수행 (numpy SVD 기반 — sklearn 의존성 없음).

        행 = 유전자, 열 = 샘플 → PCA는 (샘플 × 특성) 을 원하므로 전치.

        Returns:
            scores: ndarray (n_samples, n_pcs)
            explained_variance_ratio: list[float]
        """
        df = self.dataframe.copy()
        expr = df[self.sample_cols].copy()

        # NaN → 0
        expr = expr.fillna(0)

        # ── 분산 기준 상위 N개 유전자 선택 ──────────────────────────────
        n = min(self.n_genes, len(expr))
        variances = expr.var(axis=1)
        top_idx = variances.nlargest(n).index
        expr = expr.loc[top_idx]

        # ── 변환 ────────────────────────────────────────────────────────
        mat = expr.values.astype(float)   # shape: (genes, samples)
        if self.transform == 'log2':
            mat = np.log2(mat + 1.0)
        elif self.transform == 'log1p':
            mat = np.log1p(mat)

        # ── PCA 입력: (samples × genes) ─────────────────────────────────
        X = mat.T  # (n_samples, n_genes)

        # ── StandardScaler (numpy 구현) ───────────────────────────────────
        if self.scaling == 'standard':
            mean = X.mean(axis=0)
            std  = X.std(axis=0, ddof=0)
            std[std == 0] = 1.0          # 분산 0인 컬럼 보호
            X = (X - mean) / std

        # ── PCA via SVD (numpy 구현) ──────────────────────────────────────
        # 1) 평균 중심화
        X_centered = X - X.mean(axis=0)
        # 2) SVD: X_centered = U @ diag(s) @ Vt
        U, s, Vt = np.linalg.svd(X_centered, full_matrices=False)
        # 3) 설명 분산 비율
        explained_variance = (s ** 2) / (X_centered.shape[0] - 1)
        total_variance = explained_variance.sum()
        explained_variance_ratio = (explained_variance / total_variance).tolist()
        # 4) 스코어 (n_samples × n_components)
        n_components = min(len(self.sample_cols), X_centered.shape[1], 10)
        scores = U[:, :n_components] * s[:n_components]

        # PCA scores DataFrame 캐시 (export 용)
        self._pca_result = pd.DataFrame(
            scores,
            index=self.sample_cols,
            columns=[f"PC{i+1}" for i in range(scores.shape[1])],
        )
        self._explained_var = explained_variance_ratio[:n_components]

        return scores, self._explained_var

    # ── 경고 메시지 ───────────────────────────────────────────────────────

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

    def _export_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "pca_plot.png",
            "PNG Image (*.png);;SVG Vector (*.svg);;PDF (*.pdf)"
        )
        if path:
            self.figure.savefig(path, dpi=150, bbox_inches='tight')
            QMessageBox.information(self, "Saved", f"Plot saved to:\n{path}")
