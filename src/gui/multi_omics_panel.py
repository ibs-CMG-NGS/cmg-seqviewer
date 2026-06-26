"""
Multi-Omics Panel Widget

좌측 패널에 추가되는 Multi-Omics 탭입니다.
RNA-seq Dataset과 ATAC-seq Dataset을 선택하고 통합 분석을 실행합니다.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QPushButton, QDoubleSpinBox, QSpinBox,
    QFormLayout, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal
from models.data_models import DatasetType


class MultiOmicsPanel(QWidget):
    """
    Multi-Omics 통합 분석 설정 패널

    Signals:
        integrate_requested(str rna_name, str atac_name,
                            str method, int tss_window,
                            float rna_padj, float rna_lfc,
                            float atac_padj, float atac_lfc)
    """

    integrate_requested = pyqtSignal(str, str, str, int, float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI 초기화
    # ------------------------------------------------------------------ #

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Dataset 선택 그룹 ──────────────────────────────────────────
        dataset_group = QGroupBox("Dataset Selection")
        dataset_form = QFormLayout(dataset_group)
        dataset_form.setSpacing(6)

        self.rna_combo = QComboBox()
        self.rna_combo.setPlaceholderText("Select RNA-seq dataset...")
        self.rna_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        dataset_form.addRow("RNA-seq:", self.rna_combo)

        self.atac_combo = QComboBox()
        self.atac_combo.setPlaceholderText("Select ATAC-seq dataset...")
        self.atac_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        dataset_form.addRow("ATAC-seq:", self.atac_combo)

        layout.addWidget(dataset_group)

        # ── Integration Method 그룹 ────────────────────────────────────
        method_group = QGroupBox("Integration Method")
        method_form = QFormLayout(method_group)
        method_form.setSpacing(6)

        self.method_combo = QComboBox()
        self.method_combo.addItem("Nearest Gene", "nearest_gene")
        self.method_combo.addItem("Promoter Only (TSS window)", "promoter_only")
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        method_form.addRow("Method:", self.method_combo)

        self.tss_spin = QSpinBox()
        self.tss_spin.setRange(100, 100_000)
        self.tss_spin.setValue(2000)
        self.tss_spin.setSuffix(" bp")
        self.tss_spin.setEnabled(False)
        method_form.addRow("TSS window (±):", self.tss_spin)

        layout.addWidget(method_group)

        # ── Significance Threshold 그룹 ────────────────────────────────
        thresh_group = QGroupBox("Significance Thresholds")
        thresh_form = QFormLayout(thresh_group)
        thresh_form.setSpacing(6)

        self.rna_padj_spin = QDoubleSpinBox()
        self._setup_padj_spin(self.rna_padj_spin, 0.05)
        thresh_form.addRow("RNA padj ≤", self.rna_padj_spin)

        self.rna_lfc_spin = QDoubleSpinBox()
        self._setup_lfc_spin(self.rna_lfc_spin, 1.0)
        thresh_form.addRow("RNA |log2FC| ≥", self.rna_lfc_spin)

        self.atac_padj_spin = QDoubleSpinBox()
        self._setup_padj_spin(self.atac_padj_spin, 0.05)
        thresh_form.addRow("ATAC padj ≤", self.atac_padj_spin)

        self.atac_lfc_spin = QDoubleSpinBox()
        self._setup_lfc_spin(self.atac_lfc_spin, 1.0)
        thresh_form.addRow("ATAC |log2FC| ≥", self.atac_lfc_spin)

        layout.addWidget(thresh_group)

        # ── 실행 버튼 ─────────────────────────────────────────────────
        self.integrate_btn = QPushButton("🔗 Integrate RNA + ATAC")
        self.integrate_btn.setMinimumHeight(32)
        self.integrate_btn.setStyleSheet("""
            QPushButton {
                background-color: #5C85D6;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #4A72C4; }
            QPushButton:disabled { background-color: #AAAAAA; }
        """)
        self.integrate_btn.clicked.connect(self._on_integrate_clicked)
        layout.addWidget(self.integrate_btn)

        layout.addStretch()

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _setup_padj_spin(spin: QDoubleSpinBox, default: float):
        spin.setRange(0.0001, 1.0)
        spin.setDecimals(4)
        spin.setSingleStep(0.01)
        spin.setValue(default)

    @staticmethod
    def _setup_lfc_spin(spin: QDoubleSpinBox, default: float):
        spin.setRange(0.0, 10.0)
        spin.setDecimals(4)
        spin.setSingleStep(0.5)
        spin.setValue(default)

    def _on_method_changed(self, index: int):
        method = self.method_combo.currentData()
        self.tss_spin.setEnabled(method == "promoter_only")

    def _on_integrate_clicked(self):
        rna_name  = self.rna_combo.currentText()
        atac_name = self.atac_combo.currentText()

        if not rna_name or not atac_name:
            return
        if rna_name == atac_name:
            return

        self.integrate_requested.emit(
            rna_name,
            atac_name,
            self.method_combo.currentData(),
            self.tss_spin.value(),
            self.rna_padj_spin.value(),
            self.rna_lfc_spin.value(),
            self.atac_padj_spin.value(),
            self.atac_lfc_spin.value(),
        )

    # ------------------------------------------------------------------ #
    #  Public API (main_window에서 호출)
    # ------------------------------------------------------------------ #

    def refresh_dataset_list(self, datasets: dict):
        """
        DatasetManager의 datasets dict를 받아 콤보박스를 갱신합니다.

        Args:
            datasets: {name: Dataset} dict
        """
        rna_current  = self.rna_combo.currentText()
        atac_current = self.atac_combo.currentText()

        rna_names  = [
            n for n, d in datasets.items()
            if d.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION
        ]
        atac_names = [
            n for n, d in datasets.items()
            if d.dataset_type == DatasetType.ATAC_SEQ
        ]
        # ATAC 데이터셋이 없으면 전체 목록을 fallback으로 표시
        if not atac_names:
            atac_names = list(datasets.keys())

        self.rna_combo.clear()
        self.rna_combo.addItems(rna_names)
        if rna_current in rna_names:
            self.rna_combo.setCurrentText(rna_current)

        self.atac_combo.clear()
        self.atac_combo.addItems(atac_names)
        if atac_current in atac_names:
            self.atac_combo.setCurrentText(atac_current)
