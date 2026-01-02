"""
GO/KEGG Bar Chart Visualization Dialog
"""

from typing import Optional
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSpinBox, QComboBox, QPushButton,
    QCheckBox, QDoubleSpinBox, QMessageBox, QFormLayout, QLineEdit,
    QColorDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar  # type: ignore
from matplotlib.figure import Figure

from models.data_models import Dataset
from models.standard_columns import StandardColumns


class GOBarChartDialog(QDialog):
    """GO/KEGG Bar Chart 다이얼로그"""
    
    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        
        self.setWindowTitle("GO/KEGG Bar Chart")
        self.setMinimumSize(1000, 800)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        
        self._init_ui()
        
        # 초기 플롯 생성
        self._update_plot()
    
    def _init_ui(self):
        """UI 초기화"""
        main_layout = QHBoxLayout(self)  # 전체를 좌우 배열로 변경
        
        # 왼쪽: 설정 패널들
        left_panel = QVBoxLayout()
        
        # 설정 패널
        settings_group = QGroupBox("Chart Settings")
        settings_layout = QFormLayout()  # HBoxLayout에서 FormLayout으로 변경
        
        # Top N terms
        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(5, 50)
        self.top_n_spin.setValue(15)
        self.top_n_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Top N terms:", self.top_n_spin)
        
        # X-axis 선택
        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItems(["-log10(FDR)", "Gene Count", "Fold Enrichment"])
        self.x_axis_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("X-axis:", self.x_axis_combo)
        
        # Sort by 선택
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["FDR (ascending)", "Gene Count (descending)", "Alphabetical"])
        self.sort_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Sort by:", self.sort_combo)
        
        # Bar color (단일 색상 선택)
        color_layout = QHBoxLayout()
        self.bar_color = QColor(70, 130, 180)  # 기본 steelblue
        self.bar_color_btn = QPushButton("Choose Bar Color")
        self.bar_color_btn.setStyleSheet(f"background-color: {self.bar_color.name()};")
        self.bar_color_btn.clicked.connect(self._choose_bar_color)
        color_layout.addWidget(self.bar_color_btn)
        settings_layout.addRow("Bar Color:", color_layout)
        
        # Horizontal
        self.horizontal_check = QCheckBox("Horizontal bars")
        self.horizontal_check.setChecked(True)
        self.horizontal_check.toggled.connect(self._update_plot)
        settings_layout.addRow("", self.horizontal_check)
        
        settings_group.setLayout(settings_layout)
        left_panel.addWidget(settings_group)
        
        # Plot Customization 패널
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()
        
        # Title
        self.title_edit = QLineEdit("GO/KEGG Enrichment Bar Chart")
        self.title_edit.textChanged.connect(self._update_plot)
        custom_layout.addRow("Title:", self.title_edit)
        
        # X Label
        self.xlabel_edit = QLineEdit("-log10(FDR)")
        self.xlabel_edit.textChanged.connect(self._update_plot)
        custom_layout.addRow("X Label:", self.xlabel_edit)
        
        # Y Label
        self.ylabel_edit = QLineEdit("GO/KEGG Terms")
        self.ylabel_edit.textChanged.connect(self._update_plot)
        custom_layout.addRow("Y Label:", self.ylabel_edit)
        
        # Figure size
        size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(6, 20)
        self.width_spin.setValue(12)
        self.width_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(4, 16)
        self.height_spin.setValue(8)
        self.height_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.height_spin)
        custom_layout.addRow("Figure Size (inches):", size_layout)
        
        custom_group.setLayout(custom_layout)
        left_panel.addWidget(custom_group)
        
        left_panel.addStretch()  # 아래 여백
        
        # 왼쪽 패널을 메인 레이아웃에 추가
        main_layout.addLayout(left_panel)
        
        # 오른쪽: Plot 영역
        right_panel = QVBoxLayout()
        
        # Matplotlib canvas
        right_panel.addWidget(self.canvas)
        
        # Navigation toolbar
        toolbar = NavigationToolbar(self.canvas, self)
        right_panel.addWidget(toolbar)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self._update_plot)
        button_layout.addWidget(refresh_btn)
        
        save_btn = QPushButton("Save Figure")
        save_btn.clicked.connect(self._save_figure)
        button_layout.addWidget(save_btn)
        
        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self._export_data)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        right_panel.addLayout(button_layout)
        
        # 오른쪽 패널을 메인 레이아웃에 추가
        main_layout.addLayout(right_panel, stretch=3)  # 오른쪽을 더 크게
    
    def _on_figure_size_changed(self):
        """Figure 크기 변경 시 처리"""
        width = self.width_spin.value()
        height = self.height_spin.value()
        self.figure.set_size_inches(width, height)
        self.canvas.draw()
    
    def _choose_bar_color(self):
        """Bar 색상 선택"""
        color = QColorDialog.getColor(self.bar_color, self, "Choose Bar Color")
        if color.isValid():
            self.bar_color = color
            self.bar_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self._update_plot()
    
    def _get_filtered_data(self) -> pd.DataFrame:
        """데이터 반환 (필터링 제거 - filtered by statistics 결과만 사용)"""
        return self.df.copy()
    
    def _update_plot(self):
        """플롯 업데이트"""
        self.figure.clear()
        
        # 필터링된 데이터
        df = self._get_filtered_data()
        
        if len(df) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data to display\nAdjust filters',
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # NaN 값이 있는 행 제거 (Description 등 필수 컬럼)
        required_cols = [StandardColumns.DESCRIPTION]
        if StandardColumns.FDR in df.columns:
            required_cols.append(StandardColumns.FDR)
        if StandardColumns.GENE_COUNT in df.columns:
            required_cols.append(StandardColumns.GENE_COUNT)
        
        df = df.dropna(subset=required_cols)
        
        if len(df) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No valid data to display\n(NaN values removed)',
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # Sorting (Top N 선택 전에 정렬)
        sort_by = self.sort_combo.currentText()
        if sort_by == "FDR (ascending)" and StandardColumns.FDR in df.columns:
            df = df.sort_values(StandardColumns.FDR, ascending=True)
        elif sort_by == "Gene Count (descending)" and StandardColumns.GENE_COUNT in df.columns:
            df = df.sort_values(StandardColumns.GENE_COUNT, ascending=False)
        elif sort_by == "Alphabetical" and StandardColumns.DESCRIPTION in df.columns:
            df = df.sort_values(StandardColumns.DESCRIPTION, ascending=True)
        
        # Top N terms
        top_n = self.top_n_spin.value()
        df = df.head(top_n)
        
        # X-axis 데이터
        x_axis_type = self.x_axis_combo.currentText()
        if x_axis_type == "-log10(FDR)":
            if StandardColumns.FDR in df.columns:
                x_data = -np.log10(df[StandardColumns.FDR].replace(0, 1e-300))
                x_label = "-log10(FDR)"
            else:
                x_data = pd.Series(1, index=df.index)
                x_label = "Value"
        elif x_axis_type == "Gene Count":
            if StandardColumns.GENE_COUNT in df.columns:
                x_data = df[StandardColumns.GENE_COUNT]
                x_label = "Gene Count"
            else:
                x_data = pd.Series(1, index=df.index)
                x_label = "Value"
        else:  # Fold Enrichment
            if StandardColumns.FOLD_ENRICHMENT in df.columns:
                x_data = df[StandardColumns.FOLD_ENRICHMENT]
                x_label = "Fold Enrichment"
            else:
                x_data = pd.Series(1, index=df.index)
                x_label = "Value"
        
        # Y-axis (Term descriptions)
        if StandardColumns.DESCRIPTION in df.columns:
            y_labels = df[StandardColumns.DESCRIPTION].to_list()
        else:
            y_labels = [f"Term {i+1}" for i in range(len(df))]
        
        # Truncate long descriptions (convert to string to handle NaN/float)
        y_labels = [str(label)[:70] + '...' if len(str(label)) > 70 else str(label) 
                   for label in y_labels]
        
        y_positions = np.arange(len(y_labels))
        
        # 단일 색상 사용
        bar_color = self.bar_color.name()
        horizontal = self.horizontal_check.isChecked()
        
        ax = self.figure.add_subplot(111)
        
        # 단순 바 차트
        if horizontal:
            ax.barh(y_positions, x_data, color=bar_color, edgecolor='black', linewidth=0.5)
            ax.set_yticks(y_positions)
            ax.set_yticklabels(y_labels, fontsize=9)
            ax.set_xlabel(self.xlabel_edit.text(), fontsize=11, fontweight='bold')
            ax.set_ylabel(self.ylabel_edit.text(), fontsize=11, fontweight='bold')
            ax.invert_yaxis()  # 큰 값이 위로
        else:
            ax.bar(y_positions, x_data, color=bar_color, edgecolor='black', linewidth=0.5)
            ax.set_xticks(y_positions)
            ax.set_xticklabels(y_labels, rotation=45, ha='right', fontsize=8)
            ax.set_ylabel(self.xlabel_edit.text(), fontsize=11, fontweight='bold')
            ax.set_xlabel(self.ylabel_edit.text(), fontsize=11, fontweight='bold')
        
        # Title (사용자 입력 값만 사용)
        ax.set_title(self.title_edit.text(), fontsize=13, fontweight='bold')
        
        # Grid
        if horizontal:
            ax.grid(axis='x', alpha=0.3, linestyle='--')
        else:
            ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Layout 조정
        self.figure.tight_layout()
        
        self.canvas.draw()
    
    def _save_figure(self):
        """Figure 저장"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Figure",
            f"go_bar_chart_{self.dataset.name}.png",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;All Files (*)"
        )
        
        if file_path:
            self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "Success", f"Figure saved to:\n{file_path}")
    
    def _export_data(self):
        """데이터 내보내기"""
        from PyQt6.QtWidgets import QFileDialog
        
        df = self._get_filtered_data()
        
        # Sorting 적용 (plot과 동일)
        sort_by = self.sort_combo.currentText()
        if sort_by == "FDR (ascending)" and StandardColumns.FDR in df.columns:
            df = df.sort_values(StandardColumns.FDR, ascending=True)
        elif sort_by == "Gene Count (descending)" and StandardColumns.GENE_COUNT in df.columns:
            df = df.sort_values(StandardColumns.GENE_COUNT, ascending=False)
        elif sort_by == "Alphabetical" and StandardColumns.DESCRIPTION in df.columns:
            df = df.sort_values(StandardColumns.DESCRIPTION, ascending=True)
        
        top_n = self.top_n_spin.value()
        df = df.head(top_n)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            f"go_bar_chart_data_{self.dataset.name}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
        )
        
        if file_path:
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            
            QMessageBox.information(self, "Success", f"Data exported to:\n{file_path}")
