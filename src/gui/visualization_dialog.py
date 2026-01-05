"""
Visualization Dialog for RNA-Seq Data
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QColorDialog, QGroupBox,
    QFormLayout, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont
import matplotlib
matplotlib.use('Qt5Agg')
# matplotlib의 font_manager DEBUG 로그 억제
import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import pandas as pd
import numpy as np

from models.standard_columns import StandardColumns


def create_plot_icon(emoji: str, bg_color: QColor = None) -> QIcon:
    """플롯 다이얼로그용 아이콘 생성
    
    Args:
        emoji: 아이콘에 표시할 이모지
        bg_color: 배경 색상 (기본값: Steel Blue)
    
    Returns:
        QIcon 객체
    """
    if bg_color is None:
        bg_color = QColor(70, 130, 180)  # Steel Blue
    
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # 배경 원
    painter.setBrush(bg_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 60, 60)
    
    # 이모지/텍스트
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI Emoji", 28, QFont.Weight.Bold)
    painter.setFont(font)
    from PyQt6.QtCore import QRect
    painter.drawText(QRect(0, 0, 64, 64), Qt.AlignmentFlag.AlignCenter, emoji)
    
    painter.end()
    
    return QIcon(pixmap)


class VolcanoPlotDialog(QDialog):
    """Volcano Plot 시각화 다이얼로그"""
    
    # 클래스 변수로 설정값 저장 (세션 동안 유지)
    _saved_settings = {
        'padj_threshold': 0.05,
        'log2fc_threshold': 1.0,
        'down_color': QColor(0, 0, 255),
        'up_color': QColor(255, 0, 0),
        'ns_color': QColor(128, 128, 128),
        'dot_size': 20,
        'x_min': None,
        'x_max': None,
        'y_min': None,
        'y_max': None,
        # Plot customization
        'title': 'Volcano Plot',
        'xlabel': 'Log2 Fold Change',
        'ylabel': '-Log10(Padj)',
        'show_legend': True,
        'fig_width': 12,
        'fig_height': 8
    }
    
    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.setWindowTitle("🌋 Volcano Plot")
        self.setWindowIcon(create_plot_icon("🌋", QColor(220, 20, 60)))  # Crimson
        self.setMinimumSize(1000, 700)
        
        # 저장된 설정값 불러오기
        self.padj_threshold = self._saved_settings['padj_threshold']
        self.log2fc_threshold = self._saved_settings['log2fc_threshold']
        self.down_color = self._saved_settings['down_color']
        self.up_color = self._saved_settings['up_color']
        self.ns_color = self._saved_settings['ns_color']
        self.dot_size = self._saved_settings['dot_size']
        self.x_min = self._saved_settings['x_min']
        self.x_max = self._saved_settings['x_max']
        self.y_min = self._saved_settings['y_min']
        self.y_max = self._saved_settings['y_max']
        # Plot customization
        self.plot_title = self._saved_settings['title']
        self.plot_xlabel = self._saved_settings['xlabel']
        self.plot_ylabel = self._saved_settings['ylabel']
        self.show_legend = self._saved_settings['show_legend']
        self.fig_width = self._saved_settings['fig_width']
        self.fig_height = self._saved_settings['fig_height']
        
        self._init_ui()
        self._plot()
    
    def _init_ui(self):
        """UI 초기화"""
        main_layout = QHBoxLayout(self)  # 전체를 좌우 배열로 변경
        
        # 왼쪽: 설정 패널들
        left_panel = QVBoxLayout()
        
        # 설정 패널
        settings_group = QGroupBox("Plot Settings")
        settings_layout = QFormLayout()
        
        # Threshold 설정
        self.padj_spin = QDoubleSpinBox()
        self.padj_spin.setRange(0.0001, 1.0)
        self.padj_spin.setDecimals(4)
        self.padj_spin.setValue(self.padj_threshold)
        self.padj_spin.setSingleStep(0.01)
        self.padj_spin.valueChanged.connect(self._on_settings_changed)
        settings_layout.addRow("P-adj Threshold:", self.padj_spin)
        
        self.log2fc_spin = QDoubleSpinBox()
        self.log2fc_spin.setRange(0.0, 10.0)
        self.log2fc_spin.setDecimals(2)
        self.log2fc_spin.setValue(self.log2fc_threshold)
        self.log2fc_spin.setSingleStep(0.1)
        self.log2fc_spin.valueChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Log2FC Threshold:", self.log2fc_spin)
        
        # Color 설정
        color_layout = QHBoxLayout()
        
        self.down_btn = QPushButton("Down-regulation")
        self.down_btn.setStyleSheet(f"background-color: {self.down_color.name()};")
        self.down_btn.clicked.connect(lambda: self._choose_color('down'))
        color_layout.addWidget(self.down_btn)
        
        self.up_btn = QPushButton("Up-regulation")
        self.up_btn.setStyleSheet(f"background-color: {self.up_color.name()};")
        self.up_btn.clicked.connect(lambda: self._choose_color('up'))
        color_layout.addWidget(self.up_btn)
        
        self.ns_btn = QPushButton("Not Significant")
        self.ns_btn.setStyleSheet(f"background-color: {self.ns_color.name()};")
        self.ns_btn.clicked.connect(lambda: self._choose_color('ns'))
        color_layout.addWidget(self.ns_btn)
        
        settings_layout.addRow("Colors:", color_layout)
        
        # Dot size
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 100)
        self.size_spin.setValue(self.dot_size)
        self.size_spin.valueChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Dot Size:", self.size_spin)
        
        # X축 범위
        x_layout = QHBoxLayout()
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1000, 1000)
        self.x_min_spin.setDecimals(1)
        self.x_min_spin.setValue(self.x_min if self.x_min is not None else -10)
        self.x_min_spin.valueChanged.connect(self._on_settings_changed)
        x_layout.addWidget(QLabel("Min:"))
        x_layout.addWidget(self.x_min_spin)
        
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1000, 1000)
        self.x_max_spin.setDecimals(1)
        self.x_max_spin.setValue(self.x_max if self.x_max is not None else 10)
        self.x_max_spin.valueChanged.connect(self._on_settings_changed)
        x_layout.addWidget(QLabel("Max:"))
        x_layout.addWidget(self.x_max_spin)
        
        # X축 Auto 버튼
        self.x_auto_btn = QPushButton("Auto")
        self.x_auto_btn.setMaximumWidth(60)
        self.x_auto_btn.clicked.connect(self._auto_x_range)
        x_layout.addWidget(self.x_auto_btn)
        
        settings_layout.addRow("X-axis Range:", x_layout)
        
        # Y축 범위
        y_layout = QHBoxLayout()
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(0, 1000)
        self.y_min_spin.setDecimals(1)
        self.y_min_spin.setValue(self.y_min if self.y_min is not None else 0)
        self.y_min_spin.valueChanged.connect(self._on_settings_changed)
        y_layout.addWidget(QLabel("Min:"))
        y_layout.addWidget(self.y_min_spin)
        
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(0, 1000)
        self.y_max_spin.setDecimals(1)
        self.y_max_spin.setValue(self.y_max if self.y_max is not None else 50)
        self.y_max_spin.valueChanged.connect(self._on_settings_changed)
        y_layout.addWidget(QLabel("Max:"))
        y_layout.addWidget(self.y_max_spin)
        
        # Y축 Auto 버튼
        self.y_auto_btn = QPushButton("Auto")
        self.y_auto_btn.setMaximumWidth(60)
        self.y_auto_btn.clicked.connect(self._auto_y_range)
        y_layout.addWidget(self.y_auto_btn)
        
        settings_layout.addRow("Y-axis Range:", y_layout)
        
        settings_group.setLayout(settings_layout)
        left_panel.addWidget(settings_group)
        
        # Plot Customization 패널
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()
        
        # Title
        self.title_edit = QLineEdit(self.plot_title)
        self.title_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("Title:", self.title_edit)
        
        # X Label
        self.xlabel_edit = QLineEdit(self.plot_xlabel)
        self.xlabel_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("X Label:", self.xlabel_edit)
        
        # Y Label
        self.ylabel_edit = QLineEdit(self.plot_ylabel)
        self.ylabel_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("Y Label:", self.ylabel_edit)
        
        # Legend on/off
        self.legend_check = QCheckBox("Show Legend")
        self.legend_check.setChecked(self.show_legend)
        self.legend_check.stateChanged.connect(self._on_settings_changed)
        custom_layout.addRow("", self.legend_check)
        
        # Figure size
        size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(6, 20)
        self.width_spin.setValue(self.fig_width)
        self.width_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(4, 16)
        self.height_spin.setValue(self.fig_height)
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
        
        # Matplotlib Figure
        self.figure = Figure(figsize=(self.fig_width, self.fig_height))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        right_panel.addWidget(self.toolbar)
        right_panel.addWidget(self.canvas)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self._plot)
        button_layout.addWidget(refresh_btn)
        
        save_btn = QPushButton("Save Figure")
        save_btn.clicked.connect(self._save_figure)
        button_layout.addWidget(save_btn)
        
        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self._export_data)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        right_panel.addLayout(button_layout)
        
        # 오른쪽 패널을 메인 레이아웃에 추가
        main_layout.addLayout(right_panel, stretch=3)  # 오른쪽을 더 크게
    
    def _choose_color(self, color_type):
        """색상 선택 다이얼로그"""
        if color_type == 'down':
            color = QColorDialog.getColor(self.down_color, self, "Choose Down-regulation Color")
            if color.isValid():
                self.down_color = color
                self.down_btn.setStyleSheet(f"background-color: {color.name()};")
        elif color_type == 'up':
            color = QColorDialog.getColor(self.up_color, self, "Choose Up-regulation Color")
            if color.isValid():
                self.up_color = color
                self.up_btn.setStyleSheet(f"background-color: {color.name()};")
        elif color_type == 'ns':
            color = QColorDialog.getColor(self.ns_color, self, "Choose Not Significant Color")
            if color.isValid():
                self.ns_color = color
                self.ns_btn.setStyleSheet(f"background-color: {color.name()};")
        
        # 색상 설정값 저장
        self._saved_settings.update({
            'down_color': self.down_color,
            'up_color': self.up_color,
            'ns_color': self.ns_color
        })
        
        self._plot()
    
    def _auto_x_range(self):
        """X축 범위를 자동으로 설정"""
        # 데이터의 Log2FC 범위 계산 (대소문자 모두 지원)
        log2fc_col = None
        for col in ['log2FC', 'log2fc', StandardColumns.LOG2FC]:
            if col in self.dataframe.columns:
                log2fc_col = col
                break
        
        if log2fc_col:
            log2fc_values = self.dataframe[log2fc_col].dropna()
            if len(log2fc_values) > 0:
                x_min = float(log2fc_values.min())
                x_max = float(log2fc_values.max())
                # 약간 여유 추가
                margin = (x_max - x_min) * 0.1
                # Signal 중복 방지를 위해 blockSignals 사용
                self.x_min_spin.blockSignals(True)
                self.x_max_spin.blockSignals(True)
                self.x_min_spin.setValue(x_min - margin)
                self.x_max_spin.setValue(x_max + margin)
                self.x_min_spin.blockSignals(False)
                self.x_max_spin.blockSignals(False)
                # 수동으로 plot 업데이트
                self._on_settings_changed()
    
    def _auto_y_range(self):
        """Y축 범위를 자동으로 설정"""
        # 데이터의 -log10(padj) 범위 계산 (대소문자 모두 지원)
        padj_col = None
        for col in ['padj', 'adj_pvalue', StandardColumns.ADJ_PVALUE]:
            if col in self.dataframe.columns:
                padj_col = col
                break
        
        if padj_col:
            padj_values = self.dataframe[padj_col].dropna()
            padj_values = padj_values[padj_values > 0]  # 0 제외
            if len(padj_values) > 0:
                y_values = -np.log10(padj_values)
                y_max = float(y_values.max())
                # 약간 여유 추가
                margin = y_max * 0.1
                # Signal 중복 방지를 위해 blockSignals 사용
                self.y_min_spin.blockSignals(True)
                self.y_max_spin.blockSignals(True)
                self.y_min_spin.setValue(0)
                self.y_max_spin.setValue(y_max + margin)
                self.y_min_spin.blockSignals(False)
                self.y_max_spin.blockSignals(False)
                # 수동으로 plot 업데이트
                self._on_settings_changed()
    
    def _on_settings_changed(self):
        """설정 변경 시 자동 업데이트"""
        self.padj_threshold = self.padj_spin.value()
        self.log2fc_threshold = self.log2fc_spin.value()
        self.dot_size = self.size_spin.value()
        
        # X축, Y축 범위는 항상 사용자 설정값 사용
        self.x_min = self.x_min_spin.value()
        self.x_max = self.x_max_spin.value()
        self.y_min = self.y_min_spin.value()
        self.y_max = self.y_max_spin.value()
        
        # Plot customization
        self.plot_title = self.title_edit.text()
        self.plot_xlabel = self.xlabel_edit.text()
        self.plot_ylabel = self.ylabel_edit.text()
        self.show_legend = self.legend_check.isChecked()
        
        # 설정값을 클래스 변수에 저장 (세션 동안 유지)
        self._saved_settings.update({
            'padj_threshold': self.padj_threshold,
            'log2fc_threshold': self.log2fc_threshold,
            'down_color': self.down_color,
            'up_color': self.up_color,
            'ns_color': self.ns_color,
            'dot_size': self.dot_size,
            'x_min': self.x_min,
            'x_max': self.x_max,
            'y_min': self.y_min,
            'y_max': self.y_max,
            'title': self.plot_title,
            'xlabel': self.plot_xlabel,
            'ylabel': self.plot_ylabel,
            'show_legend': self.show_legend
        })
        
        self._plot()
    
    def _on_figure_size_changed(self):
        """Figure 크기 변경 시"""
        self.fig_width = self.width_spin.value()
        self.fig_height = self.height_spin.value()
        
        # 설정 저장
        self._saved_settings.update({
            'fig_width': self.fig_width,
            'fig_height': self.fig_height
        })
        
        # Figure 크기 변경
        self.figure.set_size_inches(self.fig_width, self.fig_height)
        self.canvas.draw()
    
    def _plot(self):
        """Volcano Plot 그리기"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 데이터 준비
        df = self.dataframe.copy()
        
        # log2FC와 padj 컬럼 확인
        if 'log2FC' not in df.columns or 'padj' not in df.columns:
            ax.text(0.5, 0.5, 'Required columns not found:\nlog2FC and padj', 
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # -log10(padj) 계산
        df['-log10(padj)'] = -np.log10(df['padj'].replace(0, 1e-300))
        
        # 분류: Up-regulated, Down-regulated, Not significant
        df['regulation'] = 'ns'
        df.loc[(df['log2FC'] >= self.log2fc_threshold) & 
               (df['padj'] <= self.padj_threshold), 'regulation'] = 'up'
        df.loc[(df['log2FC'] <= -self.log2fc_threshold) & 
               (df['padj'] <= self.padj_threshold), 'regulation'] = 'down'
        
        # DEG 데이터 저장 (hover용)
        self.deg_data = df[df['regulation'].isin(['up', 'down'])].copy()
        
        # 플롯
        scatter_collections = []
        for reg_type, color in [('ns', self.ns_color), 
                                ('down', self.down_color), 
                                ('up', self.up_color)]:
            subset = df[df['regulation'] == reg_type]
            sc = ax.scatter(subset['log2FC'], subset['-log10(padj)'], 
                      c=color.name(), s=self.dot_size, alpha=0.6,
                      label=f'{reg_type.upper()} ({len(subset)})',
                      picker=True if reg_type != 'ns' else False)  # NS는 picker 비활성화
            if reg_type != 'ns':
                scatter_collections.append((sc, subset))
        
        # Threshold 선
        ax.axhline(-np.log10(self.padj_threshold), color='black', 
                  linestyle='--', linewidth=1, alpha=0.5)
        ax.axvline(self.log2fc_threshold, color='black', 
                  linestyle='--', linewidth=1, alpha=0.5)
        ax.axvline(-self.log2fc_threshold, color='black', 
                  linestyle='--', linewidth=1, alpha=0.5)
        
        # 축 레이블 (커스터마이징)
        ax.set_xlabel(self.plot_xlabel, fontsize=12)
        ax.set_ylabel(self.plot_ylabel, fontsize=12)
        ax.set_title(self.plot_title, fontsize=14, fontweight='bold')
        
        # 축 범위 설정
        if self.x_min is not None and self.x_max is not None:
            ax.set_xlim(self.x_min, self.x_max)
        if self.y_min is not None and self.y_max is not None:
            ax.set_ylim(self.y_min, self.y_max)
        
        # 범례 (on/off)
        if self.show_legend:
            ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Annotation 텍스트 (hover용) - zorder 높게 설정하여 최상위 레이어로
        self.annot = ax.annotate("", xy=(0,0), xytext=(20,20),
                                textcoords="offset points",
                                bbox=dict(boxstyle="round", fc="w", alpha=0.9),
                                arrowprops=dict(arrowstyle="->"),
                                zorder=1000)
        self.annot.set_visible(False)
        
        # Hover 이벤트 연결 (DEG만)
        self.figure.canvas.mpl_connect("motion_notify_event", self._on_hover)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _on_hover(self, event):
        """마우스 오버 시 DEG 정보 표시"""
        if event.inaxes is None:
            self.annot.set_visible(False)
            self.canvas.draw_idle()
            return
        
        # DEG 데이터가 있는지 확인
        if not hasattr(self, 'deg_data') or len(self.deg_data) == 0:
            return
        
        # 마우스 위치에서 가장 가까운 DEG 점 찾기
        x, y = event.xdata, event.ydata
        deg_df = self.deg_data
        
        # 거리 계산 (스케일 고려)
        ax = event.inaxes
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        x_scale = xlim[1] - xlim[0]
        y_scale = ylim[1] - ylim[0]
        
        distances = np.sqrt(((deg_df['log2FC'] - x) / x_scale * 10) ** 2 + 
                           ((deg_df['-log10(padj)'] - y) / y_scale * 10) ** 2)
        
        # 가장 가까운 점 (threshold 이내)
        min_dist_idx = distances.idxmin()
        min_dist = distances[min_dist_idx]
        
        if min_dist < 0.5:  # 충분히 가까울 때만 표시
            row = deg_df.loc[min_dist_idx]
            
            # Symbol이 있으면 표시, 없으면 gene_id
            gene_name = row.get('symbol', row.get('gene_id', 'Unknown'))
            log2fc = row['log2FC']
            padj = row['padj']
            
            text = f"Gene: {gene_name}\nlog2FC: {log2fc:.3f}\nPadj: {padj:.2e}"
            
            self.annot.xy = (row['log2FC'], row['-log10(padj)'])
            self.annot.set_text(text)
            
            # Boundary 체크 및 자동 조정
            # tooltip 크기를 고려하여 더 안정적인 threshold 사용
            # 왼쪽/오른쪽: xlim의 15% 지점부터, 85% 지점까지
            # 아래/위: ylim의 15% 지점부터, 80% 지점까지
            x_pos = row['log2FC']
            y_pos = row['-log10(padj)']
            
            # X축 boundary 체크
            x_range = xlim[1] - xlim[0]
            if x_pos < xlim[0] + x_range * 0.15:
                # 왼쪽 경계 근처 - 오른쪽으로 표시
                offset_x = 20
            elif x_pos > xlim[0] + x_range * 0.80:
                # 오른쪽 경계 근처 - 왼쪽으로 표시
                offset_x = -100
            else:
                # 중앙 - 오른쪽으로 표시
                offset_x = 20
            
            # Y축 boundary 체크
            y_range = ylim[1] - ylim[0]
            if y_pos < ylim[0] + y_range * 0.15:
                # 아래 경계 근처 - 위로 표시
                offset_y = 20
            elif y_pos > ylim[0] + y_range * 0.75:
                # 위 경계 근처 - 아래로 표시
                offset_y = -70
            else:
                # 중앙 - 위로 표시
                offset_y = 20
            
            self.annot.set_position((offset_x, offset_y))
            self.annot.set_visible(True)
        else:
            self.annot.set_visible(False)
        
        self.canvas.draw_idle()
    
    def _save_figure(self):
        """Figure 저장"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Figure",
            "volcano_plot.png",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;All Files (*)"
        )
        
        if file_path:
            self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "Success", f"Figure saved to:\n{file_path}")
    
    def _export_data(self):
        """현재 표시된 데이터 내보내기"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "volcano_plot_data.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.xlsx'):
                    self.dataframe.to_excel(file_path, index=False)
                else:
                    self.dataframe.to_csv(file_path, index=False)
                QMessageBox.information(self, "Success", f"Data exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data:\n{str(e)}")


class PadjHistogramDialog(QDialog):
    """P-value Histogram 시각화 다이얼로그"""
    
    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.setWindowTitle("📊 P-value Histogram")
        self.setWindowIcon(create_plot_icon("📊", QColor(34, 139, 34)))  # Forest Green
        self.setMinimumSize(900, 700)
        
        # 기본 설정값
        self.pvalue_type = 'padj'  # 'pvalue' 또는 'padj'
        self.bin_count = 50
        
        self._init_ui()
        self._plot()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 설정 패널
        settings_group = QGroupBox("Histogram Settings")
        settings_layout = QFormLayout()
        
        # P-value 타입 선택
        self.pvalue_combo = QComboBox()
        self.pvalue_combo.addItems(["Adjusted P-value (padj)", "Original P-value (pvalue)"])
        self.pvalue_combo.currentIndexChanged.connect(self._on_settings_changed)
        settings_layout.addRow("P-value Type:", self.pvalue_combo)
        
        # Bin 개수 설정
        self.bin_spin = QSpinBox()
        self.bin_spin.setRange(10, 200)
        self.bin_spin.setValue(self.bin_count)
        self.bin_spin.setSingleStep(10)
        self.bin_spin.valueChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Number of Bins:", self.bin_spin)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Matplotlib Figure
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self._plot)
        button_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _on_settings_changed(self):
        """설정 변경 시 자동 업데이트"""
        # P-value 타입
        if self.pvalue_combo.currentIndex() == 0:
            self.pvalue_type = 'padj'
        else:
            self.pvalue_type = 'pvalue'
        
        # Bin 개수
        self.bin_count = self.bin_spin.value()
        
        self._plot()
    
    def _plot(self):
        """Histogram 그리기"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        df = self.dataframe.copy()
        
        # 컬럼 확인
        if self.pvalue_type not in df.columns:
            ax.text(0.5, 0.5, f'Required column not found: {self.pvalue_type}', 
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # Histogram
        data = df[self.pvalue_type].dropna()
        ax.hist(data, bins=self.bin_count, color='steelblue', edgecolor='black', alpha=0.7)
        
        # 축 레이블
        if self.pvalue_type == 'padj':
            xlabel = 'Adjusted P-value'
            title = 'Distribution of Adjusted P-values'
        else:
            xlabel = 'Original P-value'
            title = 'Distribution of Original P-values'
        
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 통계 정보 추가
        stats_text = f'Total: {len(data)}\nMean: {data.mean():.4f}\nMedian: {data.median():.4f}'
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
               fontsize=10)
        
        self.figure.tight_layout()
        self.canvas.draw()


class HeatmapDialog(QDialog):
    """Expression Heatmap 시각화 다이얼로그"""
    
    # 클래스 변수로 설정값 저장 (세션 동안 유지)
    _saved_settings = {
        'n_genes': 50,
        'normalization': 'z-score',
        'transpose': False,
        'sorting': 'padj',  # 'padj', 'log2fc', 'clustering'
        'colormap': 'RdBu_r',
        'colorbar_min': -3.0,
        'colorbar_max': 3.0,
        # Plot customization
        'title': 'Expression Heatmap',
        'xlabel': 'Samples',
        'ylabel': 'Genes',
        'show_legend': True,
        'fig_width': 12,
        'fig_height': 8
    }
    
    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.setWindowTitle("🔥 Expression Heatmap")
        self.setWindowIcon(create_plot_icon("🔥", QColor(255, 140, 0)))  # Dark Orange
        self.setMinimumSize(1000, 800)
        
        # 현재 표시 중인 heatmap 데이터 (export용)
        self.current_heatmap_data = None
        self.current_gene_labels = None
        
        # 저장된 설정값 불러오기
        self.n_genes = self._saved_settings['n_genes']
        self.normalization = self._saved_settings['normalization']
        self.transpose = self._saved_settings['transpose']
        self.sorting = self._saved_settings['sorting']
        self.colormap = self._saved_settings['colormap']
        self.colorbar_min = self._saved_settings['colorbar_min']
        self.colorbar_max = self._saved_settings['colorbar_max']
        # Plot customization
        self.plot_title = self._saved_settings['title']
        self.plot_xlabel = self._saved_settings['xlabel']
        self.plot_ylabel = self._saved_settings['ylabel']
        self.show_legend = self._saved_settings['show_legend']
        self.fig_width = self._saved_settings['fig_width']
        self.fig_height = self._saved_settings['fig_height']
        
        self._init_ui()
        self._plot()
    
    def _init_ui(self):
        """UI 초기화"""
        main_layout = QHBoxLayout(self)  # 전체를 좌우 배열로 변경
        
        # 왼쪽: 설정 패널들
        left_panel = QVBoxLayout()
        
        # 설정 패널
        settings_group = QGroupBox("Heatmap Settings")
        settings_layout = QFormLayout()
        
        # 유전자 개수 설정
        self.gene_spin = QSpinBox()
        self.gene_spin.setRange(10, 500)
        self.gene_spin.setValue(self.n_genes)
        self.gene_spin.setSingleStep(10)
        self.gene_spin.valueChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Number of Genes:", self.gene_spin)
        
        # Normalization 방법
        self.norm_combo = QComboBox()
        self.norm_combo.addItems([
            "Z-score (row-wise)",
            "Min-Max (0-1)",
            "Log2 Transform",
            "None (Raw values)"
        ])
        self.norm_combo.currentIndexChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Normalization:", self.norm_combo)
        
        # Sorting 방법
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Padj (ascending)",
            "Log2FC (absolute descending)",
            "Hierarchical Clustering"
        ])
        if self.sorting == 'padj':
            self.sort_combo.setCurrentIndex(0)
        elif self.sorting == 'log2fc':
            self.sort_combo.setCurrentIndex(1)
        else:
            self.sort_combo.setCurrentIndex(2)
        self.sort_combo.currentIndexChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Gene Sorting:", self.sort_combo)
        
        # Colormap 선택
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems([
            "RdBu_r (Red-Blue)",
            "viridis",
            "plasma",
            "coolwarm",
            "seismic"
        ])
        colormap_names = ['RdBu_r', 'viridis', 'plasma', 'coolwarm', 'seismic']
        if self.colormap in colormap_names:
            self.colormap_combo.setCurrentIndex(colormap_names.index(self.colormap))
        self.colormap_combo.currentIndexChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Colormap:", self.colormap_combo)
        
        # Colorbar Min/Max 설정
        colorbar_layout = QHBoxLayout()
        self.colorbar_min_spin = QDoubleSpinBox()
        self.colorbar_min_spin.setRange(-100, 100)
        self.colorbar_min_spin.setValue(self.colorbar_min)
        self.colorbar_min_spin.setDecimals(1)
        self.colorbar_min_spin.setSingleStep(0.5)
        self.colorbar_min_spin.valueChanged.connect(self._on_settings_changed)
        
        self.colorbar_max_spin = QDoubleSpinBox()
        self.colorbar_max_spin.setRange(-100, 100)
        self.colorbar_max_spin.setValue(self.colorbar_max)
        self.colorbar_max_spin.setDecimals(1)
        self.colorbar_max_spin.setSingleStep(0.5)
        self.colorbar_max_spin.valueChanged.connect(self._on_settings_changed)
        
        colorbar_layout.addWidget(QLabel("Min:"))
        colorbar_layout.addWidget(self.colorbar_min_spin)
        colorbar_layout.addWidget(QLabel("Max:"))
        colorbar_layout.addWidget(self.colorbar_max_spin)
        settings_layout.addRow("Colorbar Range:", colorbar_layout)
        
        # Transpose
        self.transpose_check = QCheckBox("Transpose (Swap Genes ↔ Samples)")
        self.transpose_check.setChecked(self.transpose)
        self.transpose_check.stateChanged.connect(self._on_settings_changed)
        settings_layout.addRow("", self.transpose_check)
        
        settings_group.setLayout(settings_layout)
        left_panel.addWidget(settings_group)
        
        # Plot Customization 패널
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()
        
        # Title
        self.title_edit = QLineEdit(self.plot_title)
        self.title_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("Title:", self.title_edit)
        
        # X Label
        self.xlabel_edit = QLineEdit(self.plot_xlabel)
        self.xlabel_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("X Label:", self.xlabel_edit)
        
        # Y Label
        self.ylabel_edit = QLineEdit(self.plot_ylabel)
        self.ylabel_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("Y Label:", self.ylabel_edit)
        
        # Legend on/off
        self.legend_check = QCheckBox("Show Colorbar")
        self.legend_check.setChecked(self.show_legend)
        self.legend_check.stateChanged.connect(self._on_settings_changed)
        custom_layout.addRow("", self.legend_check)
        
        # Figure size
        size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(8, 24)
        self.width_spin.setValue(self.fig_width)
        self.width_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(6, 20)
        self.height_spin.setValue(self.fig_height)
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
        
        # Matplotlib Figure
        self.figure = Figure(figsize=(self.fig_width, self.fig_height))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        right_panel.addWidget(self.toolbar)
        right_panel.addWidget(self.canvas)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self._plot)
        button_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self._export_heatmap_data)
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        right_panel.addLayout(button_layout)
        
        # 오른쪽 패널을 메인 레이아웃에 추가
        main_layout.addLayout(right_panel, stretch=3)  # 오른쪽을 더 크게
    
    def _on_settings_changed(self):
        """설정 변경 시 자동 업데이트"""
        self.n_genes = self.gene_spin.value()
        
        # Normalization 타입
        norm_idx = self.norm_combo.currentIndex()
        if norm_idx == 0:
            self.normalization = 'z-score'
        elif norm_idx == 1:
            self.normalization = 'minmax'
        elif norm_idx == 2:
            self.normalization = 'log2'
        else:
            self.normalization = 'none'
        
        # Sorting 타입
        sort_idx = self.sort_combo.currentIndex()
        if sort_idx == 0:
            self.sorting = 'padj'
        elif sort_idx == 1:
            self.sorting = 'log2fc'
        else:
            self.sorting = 'clustering'
        
        # Colormap
        colormap_names = ['RdBu_r', 'viridis', 'plasma', 'coolwarm', 'seismic']
        self.colormap = colormap_names[self.colormap_combo.currentIndex()]
        
        # Colorbar range
        self.colorbar_min = self.colorbar_min_spin.value()
        self.colorbar_max = self.colorbar_max_spin.value()
        
        # Transpose
        self.transpose = self.transpose_check.isChecked()
        
        # Plot customization
        self.plot_title = self.title_edit.text()
        self.plot_xlabel = self.xlabel_edit.text()
        self.plot_ylabel = self.ylabel_edit.text()
        self.show_legend = self.legend_check.isChecked()
        
        # 설정값을 클래스 변수에 저장 (세션 동안 유지)
        self._saved_settings.update({
            'n_genes': self.n_genes,
            'normalization': self.normalization,
            'transpose': self.transpose,
            'sorting': self.sorting,
            'colormap': self.colormap,
            'colorbar_min': self.colorbar_min,
            'colorbar_max': self.colorbar_max,
            'title': self.plot_title,
            'xlabel': self.plot_xlabel,
            'ylabel': self.plot_ylabel,
            'show_legend': self.show_legend
        })
        
        self._plot()
    
    def _on_figure_size_changed(self):
        """Figure 크기 변경 시"""
        self.fig_width = self.width_spin.value()
        self.fig_height = self.height_spin.value()
        
        # 설정 저장
        self._saved_settings.update({
            'fig_width': self.fig_width,
            'fig_height': self.fig_height
        })
        
        # Figure 크기 변경
        self.figure.set_size_inches(self.fig_width, self.fig_height)
        self.canvas.draw()
    
    def _plot(self):
        """Heatmap 그리기"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        df = self.dataframe.copy()
        
        # DE 분석 컬럼 제외 패턴 (대소문자 무시)
        exclude_patterns = [
            'basemean', 'base_mean', 'log2fold', 'log2fc', 'logfc', 'foldchange',
            'lfcse', 'stat', 'statistic', 'pval', 'padj', 'fdr', 'qvalue',
            'gene_id', 'gene', 'symbol', 'dataset', 'description', 'name'
        ]
        
        # 샘플 발현값 컬럼만 선택 (숫자형이면서 제외 패턴에 매칭되지 않는 컬럼)
        sample_cols = []
        for col in df.columns:
            col_lower = col.lower()
            # 제외 패턴에 매칭되는지 확인
            is_excluded = any(pattern in col_lower for pattern in exclude_patterns)
            
            if not is_excluded and pd.api.types.is_numeric_dtype(df[col]):
                sample_cols.append(col)
        
        if not sample_cols:
            ax.text(0.5, 0.5, 'No sample expression columns found.\n'
                   'Heatmap requires sample count data.', 
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # 발현값 데이터만 추출
        expr_data = df[sample_cols].copy()
        
        # NaN 제거
        expr_data = expr_data.dropna()
        
        if len(expr_data) == 0:
            ax.text(0.5, 0.5, 'No valid data after removing NaN values', 
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # 상위 N개 유전자 선택 (padj 기준 - 가장 유의미한 유전자)
        if 'padj' in df.columns:
            # padj가 있으면 가장 작은(유의미한) padj를 가진 유전자 선택
            df_with_padj = df.loc[expr_data.index].copy()
            valid_padj = df_with_padj['padj'].dropna()
            if len(valid_padj) > 0:
                top_genes_idx = valid_padj.nsmallest(min(self.n_genes, len(valid_padj))).index
            else:
                # padj가 모두 NaN이면 분산 기준으로 대체
                variances = expr_data.var(axis=1)
                top_genes_idx = variances.nlargest(min(self.n_genes, len(expr_data))).index
        else:
            # padj 컬럼이 없으면 분산 기준으로 선택
            variances = expr_data.var(axis=1)
            top_genes_idx = variances.nlargest(min(self.n_genes, len(expr_data))).index
        
        # 유전자 심볼 추출 (20개 이하일 때 Y축에 표시하기 위해)
        if 'symbol' in df.columns:
            gene_labels = df.loc[top_genes_idx, 'symbol'].tolist()
        elif 'gene_id' in df.columns:
            gene_labels = df.loc[top_genes_idx, 'gene_id'].tolist()
        else:
            gene_labels = top_genes_idx.tolist()
        
        expr_data = expr_data.loc[top_genes_idx]
        
        # Normalization 적용
        if self.normalization == 'z-score':
            # Row-wise z-score
            heatmap_data = expr_data.apply(lambda x: (x - x.mean()) / (x.std() + 1e-10), axis=1)
            cbar_label = 'Z-score'
            vmin, vmax = -3, 3
        elif self.normalization == 'minmax':
            # Row-wise min-max normalization
            heatmap_data = expr_data.apply(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-10), axis=1)
            cbar_label = 'Normalized (0-1)'
            vmin, vmax = 0, 1
        elif self.normalization == 'log2':
            # Log2 transform
            heatmap_data = np.log2(expr_data + 1)
            cbar_label = 'Log2(count + 1)'
            vmin, vmax = None, None
        else:
            # Raw values
            heatmap_data = expr_data
            cbar_label = 'Raw count'
            vmin, vmax = None, None
        
        # Sorting 적용
        if self.sorting == 'padj' and 'padj' in df.columns:
            # Padj ascending (낮은 padj 순)
            df_with_padj = df.loc[heatmap_data.index].copy()
            sort_order = df_with_padj['padj'].argsort()
            heatmap_data = heatmap_data.iloc[sort_order]
            gene_labels = [gene_labels[i] for i in sort_order]
        elif self.sorting == 'log2fc' and 'log2FC' in df.columns:
            # Log2FC absolute descending (큰 변화 순)
            df_with_log2fc = df.loc[heatmap_data.index].copy()
            sort_order = df_with_log2fc['log2FC'].abs().argsort()[::-1]
            heatmap_data = heatmap_data.iloc[sort_order]
            gene_labels = [gene_labels[i] for i in sort_order]
        elif self.sorting == 'clustering':
            # Hierarchical clustering
            try:
                from scipy.cluster.hierarchy import linkage, dendrogram
                from scipy.spatial.distance import pdist
                
                # 거리 계산 및 클러스터링
                linkage_matrix = linkage(pdist(heatmap_data, metric='euclidean'), method='average')
                dendro = dendrogram(linkage_matrix, no_plot=True)
                
                # Dendrogram 순서로 재정렬
                order = dendro['leaves']
                heatmap_data = heatmap_data.iloc[order]
                gene_labels = [gene_labels[i] for i in order]
            except ImportError:
                # scipy가 없으면 기본 순서 유지
                pass
        
        # Transpose 적용
        if self.transpose:
            heatmap_data = heatmap_data.T
            temp = self.plot_xlabel
            self.plot_xlabel = self.plot_ylabel
            self.plot_ylabel = temp
        
        # Heatmap 그리기 - colorbar range 사용
        im = ax.imshow(heatmap_data, cmap=self.colormap, aspect='auto', 
                      interpolation='nearest', vmin=self.colorbar_min, vmax=self.colorbar_max)
        
        # 현재 heatmap 데이터 저장 (export용)
        self.current_heatmap_data = heatmap_data
        self.current_gene_labels = gene_labels
        
        # 축 레이블 설정
        if self.transpose:
            # Samples on Y-axis, Genes on X-axis
            if len(heatmap_data.index) <= 50:  # 샘플이 50개 이하면 이름 표시
                ax.set_yticks(range(len(heatmap_data.index)))
                ax.set_yticklabels(heatmap_data.index, fontsize=8)
            # 유전자가 20개 이하면 X축에 유전자 심볼 표시
            if len(gene_labels) <= 20:
                ax.set_xticks(range(len(gene_labels)))
                ax.set_xticklabels(gene_labels, rotation=90, fontsize=8, ha='right')
            ax.set_xlabel(self.plot_xlabel, fontsize=12)
            ax.set_ylabel(self.plot_ylabel, fontsize=12)
        else:
            # Genes on Y-axis, Samples on X-axis
            if len(heatmap_data.columns) <= 50:  # 샘플이 50개 이하면 이름 표시
                ax.set_xticks(range(len(heatmap_data.columns)))
                ax.set_xticklabels(heatmap_data.columns, rotation=90, fontsize=8)
            # 유전자가 20개 이하면 Y축에 유전자 심볼 표시
            if len(gene_labels) <= 20:
                ax.set_yticks(range(len(gene_labels)))
                ax.set_yticklabels(gene_labels, fontsize=8)
            ax.set_xlabel(self.plot_xlabel, fontsize=12)
            ax.set_ylabel(self.plot_ylabel, fontsize=12)
        
        # Title 설정
        ax.set_title(self.plot_title, fontsize=14, fontweight='bold')
        
        # Colorbar (on/off)
        if self.show_legend:
            cbar = self.figure.colorbar(im, ax=ax)
            cbar.set_label(cbar_label, fontsize=10)
        
        # Hover 이벤트 연결 (데이터 표시)
        self.heatmap_data = heatmap_data
        self.gene_labels = gene_labels
        self.figure.canvas.mpl_connect("motion_notify_event", self._on_hover)
        
        # Annotation 텍스트 (hover용) - zorder 높게 설정하여 colorbar보다 위에 표시
        self.annot = ax.annotate("", xy=(0,0), xytext=(20,20),
                                textcoords="offset points",
                                bbox=dict(boxstyle="round", fc="w", alpha=0.9),
                                arrowprops=dict(arrowstyle="->"),
                                zorder=1000)
        self.annot.set_visible(False)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _export_heatmap_data(self):
        """현재 화면에 표시된 heatmap 데이터를 Excel로 내보내기"""
        if self.current_heatmap_data is None:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Data", "No heatmap data to export. Please generate the plot first.")
            return
        
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            # 파일 저장 대화상자
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Heatmap Data",
                "heatmap_data.xlsx",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )
            
            if not file_path:
                return
            
            # 데이터 복사 및 gene label을 인덱스로 추가
            export_df = self.current_heatmap_data.copy()
            
            # Gene labels를 첫 번째 컬럼으로 추가
            if not self.transpose:
                export_df.insert(0, 'Gene', self.current_gene_labels)
            else:
                # Transpose된 경우 columns에 gene labels
                pass  # 이미 columns가 gene labels
            
            # 파일 형식에 따라 저장
            if file_path.endswith('.csv'):
                export_df.to_csv(file_path, index=True)
            else:
                export_df.to_excel(file_path, index=True, sheet_name='Heatmap Data')
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Export Complete",
                f"Heatmap data exported successfully to:\n{file_path}"
            )
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Failed", f"Failed to export data:\n{str(e)}")
    
    def _on_hover(self, event):
        """마우스 오버 시 셀 정보 표시"""
        if event.inaxes is None:
            self.annot.set_visible(False)
            self.canvas.draw_idle()
            return
        
        # 마우스 위치의 셀 인덱스 찾기
        x, y = int(event.xdata + 0.5), int(event.ydata + 0.5)
        
        if not hasattr(self, 'heatmap_data'):
            return
        
        # Axis limits 가져오기 (boundary check용)
        ax = event.inaxes
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        # Transpose 여부에 따라 다르게 처리
        if self.transpose:
            if 0 <= y < len(self.heatmap_data.index) and 0 <= x < len(self.gene_labels):
                sample = self.heatmap_data.index[y]
                gene = self.gene_labels[x]
                value = self.heatmap_data.iloc[y, x]
                
                text = f"Sample: {sample}\nGene: {gene}\nValue: {value:.2f}"
                self.annot.xy = (x, y)
                self.annot.set_text(text)
                
                # Boundary 체크 및 tooltip 위치 조정
                x_range = xlim[1] - xlim[0]
                y_range = ylim[1] - ylim[0]
                
                # X축 boundary
                if x < x_range * 0.20:
                    offset_x = 20  # 왼쪽 - 오른쪽으로 표시
                elif x > x_range * 0.75:
                    offset_x = -100  # 오른쪽 - 왼쪽으로 표시
                else:
                    offset_x = 20
                
                # Y축 boundary
                if y < y_range * 0.20:
                    offset_y = 20  # 아래 - 위로 표시
                elif y > y_range * 0.70:
                    offset_y = -70  # 위 - 아래로 표시
                else:
                    offset_y = 20
                
                self.annot.set_position((offset_x, offset_y))
                self.annot.set_visible(True)
                self.canvas.draw_idle()
            else:
                self.annot.set_visible(False)
                self.canvas.draw_idle()
        else:
            if 0 <= y < len(self.gene_labels) and 0 <= x < len(self.heatmap_data.columns):
                gene = self.gene_labels[y]
                sample = self.heatmap_data.columns[x]
                value = self.heatmap_data.iloc[y, x]
                
                text = f"Gene: {gene}\nSample: {sample}\nValue: {value:.2f}"
                self.annot.xy = (x, y)
                self.annot.set_text(text)
                
                # Boundary 체크 및 tooltip 위치 조정
                x_range = xlim[1] - xlim[0]
                y_range = ylim[1] - ylim[0]
                
                # X축 boundary
                if x < x_range * 0.20:
                    offset_x = 20  # 왼쪽 - 오른쪽으로 표시
                elif x > x_range * 0.75:
                    offset_x = -100  # 오른쪽 - 왼쪽으로 표시
                else:
                    offset_x = 20
                
                # Y축 boundary
                if y < y_range * 0.20:
                    offset_y = 20  # 아래 - 위로 표시
                elif y > y_range * 0.70:
                    offset_y = -70  # 위 - 아래로 표시
                else:
                    offset_y = 20
                
                self.annot.set_position((offset_x, offset_y))
                self.annot.set_visible(True)
                self.canvas.draw_idle()
            else:
                self.annot.set_visible(False)
                self.canvas.draw_idle()


class DotPlotDialog(QDialog):
    """Dot Plot for Comparison Data Visualization
    
    Displays genes from comparison sheet with:
    - Dot size: based on -log10(Padj) thresholds (0.05, 0.01, 0.001, <0.001)
    - Dot color: based on log2FoldChange (colormap)
    - Supports multiple datasets in one plot
    """
    
    # 클래스 변수로 설정값 저장
    _saved_settings = {
        'colormap': 'RdBu_r',
        'transpose': False,
        'colorbar_min': -3.0,
        'colorbar_max': 3.0,
        'title': 'Dot Plot - Comparison Data',
        'xlabel': 'Datasets',
        'ylabel': 'Genes',
        'show_legend': True,
        'fig_width': 12,
        'fig_height': 10
    }
    
    def __init__(self, comparison_df, parent=None):
        super().__init__(parent)
        self.comparison_df = comparison_df
        self.setWindowTitle("⚫ Dot Plot - Comparison Data")
        self.setWindowIcon(create_plot_icon("⚫", QColor(138, 43, 226)))  # Blue Violet
        self.setMinimumSize(1000, 800)
        
        # 설정값 불러오기
        self.colormap = self._saved_settings['colormap']
        self.transpose = self._saved_settings['transpose']
        self.colorbar_min = self._saved_settings['colorbar_min']
        self.colorbar_max = self._saved_settings['colorbar_max']
        self.plot_title = self._saved_settings['title']
        self.plot_xlabel = self._saved_settings['xlabel']
        self.plot_ylabel = self._saved_settings['ylabel']
        self.show_legend = self._saved_settings['show_legend']
        
        # Dataset 이름 추출
        self.dataset_names = self._extract_dataset_names()
        
        if not self.dataset_names:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Data", 
                              "No valid dataset columns found in comparison sheet.")
            self.reject()
            return
        
        self._init_ui()
        self._plot()
    
    def _extract_dataset_names(self):
        """컬럼명에서 데이터셋 이름 추출"""
        dataset_names = []
        for col in self.comparison_df.columns:
            if '_log2FC' in col or '_log2fc' in col:
                # Dataset name 추출
                dataset_name = col.replace('_log2FC', '').replace('_log2fc', '')
                if dataset_name and dataset_name not in dataset_names:
                    dataset_names.append(dataset_name)
        return dataset_names
    
    def _init_ui(self):
        """UI 초기화 - 좌우 분할"""
        layout = QHBoxLayout(self)
        
        # 좌측 패널: 설정
        left_panel = QVBoxLayout()
        
        # === Settings 그룹 ===
        settings_group = QGroupBox("Dot Plot Settings")
        settings_layout = QFormLayout()
        
        # Colormap 선택
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems([
            "RdBu_r (Red-Blue)",
            "viridis",
            "plasma",
            "coolwarm",
            "seismic"
        ])
        colormap_names = ['RdBu_r', 'viridis', 'plasma', 'coolwarm', 'seismic']
        if self.colormap in colormap_names:
            self.colormap_combo.setCurrentIndex(colormap_names.index(self.colormap))
        self.colormap_combo.currentIndexChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Colormap:", self.colormap_combo)
        
        # Colorbar Min/Max
        colorbar_layout = QHBoxLayout()
        self.colorbar_min_spin = QDoubleSpinBox()
        self.colorbar_min_spin.setRange(-100, 100)
        self.colorbar_min_spin.setValue(self.colorbar_min)
        self.colorbar_min_spin.setDecimals(1)
        self.colorbar_min_spin.setSingleStep(0.5)
        self.colorbar_min_spin.valueChanged.connect(self._on_settings_changed)
        
        self.colorbar_max_spin = QDoubleSpinBox()
        self.colorbar_max_spin.setRange(-100, 100)
        self.colorbar_max_spin.setValue(self.colorbar_max)
        self.colorbar_max_spin.setDecimals(1)
        self.colorbar_max_spin.setSingleStep(0.5)
        self.colorbar_max_spin.valueChanged.connect(self._on_settings_changed)
        
        colorbar_layout.addWidget(QLabel("Min:"))
        colorbar_layout.addWidget(self.colorbar_min_spin)
        colorbar_layout.addWidget(QLabel("Max:"))
        colorbar_layout.addWidget(self.colorbar_max_spin)
        settings_layout.addRow("Colorbar Range:", colorbar_layout)
        
        # Transpose
        self.transpose_check = QCheckBox("Transpose (Swap Datasets ↔ Genes)")
        self.transpose_check.setChecked(self.transpose)
        self.transpose_check.stateChanged.connect(self._on_settings_changed)
        settings_layout.addRow("", self.transpose_check)
        
        # Gene Clustering
        self.cluster_genes_check = QCheckBox("Cluster Genes (Reorder by similarity)")
        self.cluster_genes_check.setChecked(False)
        self.cluster_genes_check.setToolTip("Reorder genes based on hierarchical clustering")
        self.cluster_genes_check.stateChanged.connect(self._on_settings_changed)
        settings_layout.addRow("", self.cluster_genes_check)
        
        settings_group.setLayout(settings_layout)
        left_panel.addWidget(settings_group)
        
        # === Plot Customization 그룹 ===
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()
        
        # Title
        self.title_edit = QLineEdit(self.plot_title)
        self.title_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("Title:", self.title_edit)
        
        # X Label
        self.xlabel_edit = QLineEdit(self.plot_xlabel)
        self.xlabel_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("X Label:", self.xlabel_edit)
        
        # Y Label
        self.ylabel_edit = QLineEdit(self.plot_ylabel)
        self.ylabel_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("Y Label:", self.ylabel_edit)
        
        # Legend
        self.legend_check = QCheckBox("Show Legend")
        self.legend_check.setChecked(self.show_legend)
        self.legend_check.stateChanged.connect(self._on_settings_changed)
        custom_layout.addRow("", self.legend_check)
        
        custom_group.setLayout(custom_layout)
        left_panel.addWidget(custom_group)
        
        # Figure Size
        size_group = QGroupBox("Figure Size")
        size_layout = QFormLayout()
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(6, 20)
        self.width_spin.setValue(self._saved_settings['fig_width'])
        self.width_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addRow("Width:", self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(6, 20)
        self.height_spin.setValue(self._saved_settings['fig_height'])
        self.height_spin.valueChanged.connect(self._on_figure_size_changed)
        size_layout.addRow("Height:", self.height_spin)
        
        size_group.setLayout(size_layout)
        left_panel.addWidget(size_group)
        
        left_panel.addStretch()
        
        # 우측 패널: Plot
        right_panel = QVBoxLayout()
        
        # Matplotlib Figure
        fig_width = self._saved_settings['fig_width']
        fig_height = self._saved_settings['fig_height']
        self.figure = Figure(figsize=(fig_width, fig_height))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        right_panel.addWidget(self.toolbar)
        right_panel.addWidget(self.canvas, stretch=3)
        
        # 하단 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setToolTip("Refresh the plot with current settings")
        refresh_btn.clicked.connect(self._plot)
        button_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        right_panel.addLayout(button_layout)
        
        # Layout 구성
        layout.addLayout(left_panel, stretch=1)
        layout.addLayout(right_panel, stretch=3)
    
    def _on_settings_changed(self):
        """설정 변경 시 자동 업데이트"""
        colormap_names = ['RdBu_r', 'viridis', 'plasma', 'coolwarm', 'seismic']
        self.colormap = colormap_names[self.colormap_combo.currentIndex()]
        self.colorbar_min = self.colorbar_min_spin.value()
        self.colorbar_max = self.colorbar_max_spin.value()
        self.transpose = self.transpose_check.isChecked()
        self.plot_title = self.title_edit.text()
        self.plot_xlabel = self.xlabel_edit.text()
        self.plot_ylabel = self.ylabel_edit.text()
        self.show_legend = self.legend_check.isChecked()
        
        # 설정값 저장
        self._saved_settings.update({
            'colormap': self.colormap,
            'colorbar_min': self.colorbar_min,
            'colorbar_max': self.colorbar_max,
            'transpose': self.transpose,
            'title': self.plot_title,
            'xlabel': self.plot_xlabel,
            'ylabel': self.plot_ylabel,
            'show_legend': self.show_legend
        })
        
        self._plot()
    
    def _on_figure_size_changed(self):
        """Figure 크기 변경"""
        width = self.width_spin.value()
        height = self.height_spin.value()
        
        self._saved_settings['fig_width'] = width
        self._saved_settings['fig_height'] = height
        
        self.figure.set_size_inches(width, height)
        self.canvas.draw()
    
    def _plot(self):
        """Dot Plot 그리기"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 데이터 준비
        genes = []
        dataset_data = {name: {'log2fc': [], 'padj': []} for name in self.dataset_names}
        
        # 각 유전자에 대해 데이터 수집
        for idx, row in self.comparison_df.iterrows():
            gene_symbol = row.get('symbol', row.get('gene_id', f'Gene_{idx}'))
            genes.append(gene_symbol)
            
            for dataset_name in self.dataset_names:
                log2fc_col = f"{dataset_name}_log2FC"
                padj_col = f"{dataset_name}_padj"
                
                # 대소문자 변형 확인
                if log2fc_col not in self.comparison_df.columns:
                    log2fc_col = f"{dataset_name}_log2fc"
                if padj_col not in self.comparison_df.columns:
                    padj_col = f"{dataset_name}_Padj"
                
                log2fc = row.get(log2fc_col, np.nan)
                padj = row.get(padj_col, np.nan)
                
                dataset_data[dataset_name]['log2fc'].append(log2fc)
                dataset_data[dataset_name]['padj'].append(padj)
        
        # Gene Clustering (선택 시)
        gene_order = list(range(len(genes)))
        if self.cluster_genes_check.isChecked() and len(genes) > 1:
            try:
                # log2fc 데이터를 행렬로 변환
                log2fc_matrix = np.array([dataset_data[name]['log2fc'] for name in self.dataset_names]).T
                
                # NaN 값을 0으로 대체 (클러스터링을 위해)
                log2fc_matrix_clean = np.nan_to_num(log2fc_matrix, nan=0.0)
                
                # 최소 2개 이상의 유전자와 유효한 데이터가 있을 때만 클러스터링
                if log2fc_matrix_clean.shape[0] >= 2 and not np.all(log2fc_matrix_clean == 0):
                    from scipy.cluster.hierarchy import linkage, dendrogram
                    from scipy.spatial.distance import pdist
                    
                    # 계층적 클러스터링
                    linkage_matrix = linkage(log2fc_matrix_clean, method='average', metric='euclidean')
                    dendro = dendrogram(linkage_matrix, no_plot=True)
                    gene_order = dendro['leaves']
            except Exception:
                # 클러스터링 실패 시 원래 순서 유지 (사용자에게 알리지 않음)
                gene_order = list(range(len(genes)))
        
        # 순서에 따라 genes 재정렬
        genes_ordered = [genes[i] for i in gene_order]
        
        # 전체 dot 개수를 고려하여 크기 조정
        total_dots = len(genes) * len(self.dataset_names)
        base_size = 200 if total_dots < 100 else 100 if total_dots < 500 else 50
        
        # Padj threshold별 크기 정의
        def get_dot_size(padj):
            """Padj 값에 따라 dot 크기 반환"""
            if pd.isna(padj):
                return base_size * 0.1
            elif padj < 0.001:
                return base_size * 1.5
            elif padj < 0.01:
                return base_size * 1.2
            elif padj < 0.05:
                return base_size * 0.8
            else:
                return base_size * 0.4
        
        # Plot 데이터 생성
        if not self.transpose:
            # Genes on Y-axis, Datasets on X-axis
            for dataset_idx, dataset_name in enumerate(self.dataset_names):
                log2fcs = dataset_data[dataset_name]['log2fc']
                padjs = dataset_data[dataset_name]['padj']
                
                for display_idx, original_gene_idx in enumerate(gene_order):
                    log2fc = log2fcs[original_gene_idx]
                    padj = padjs[original_gene_idx]
                    
                    if not pd.isna(log2fc):
                        size = get_dot_size(padj)
                        scatter = ax.scatter(dataset_idx, display_idx, 
                                           s=size, c=[log2fc], 
                                           cmap=self.colormap, 
                                           vmin=self.colorbar_min, 
                                           vmax=self.colorbar_max,
                                           alpha=0.7, edgecolors='black', linewidths=0.5)
            
            # 축 설정
            ax.set_xticks(range(len(self.dataset_names)))
            ax.set_xticklabels(self.dataset_names, rotation=45, ha='right')
            
            if len(genes) <= 50:
                ax.set_yticks(range(len(genes)))
                ax.set_yticklabels(genes_ordered, fontsize=8)
            
            ax.set_xlabel(self.plot_xlabel, fontsize=12)
            ax.set_ylabel(self.plot_ylabel, fontsize=12)
            
        else:
            # Datasets on Y-axis, Genes on X-axis (Transposed)
            for display_idx, original_gene_idx in enumerate(gene_order):
                for dataset_idx, dataset_name in enumerate(self.dataset_names):
                    log2fc = dataset_data[dataset_name]['log2fc'][original_gene_idx]
                    padj = dataset_data[dataset_name]['padj'][original_gene_idx]
                    
                    if not pd.isna(log2fc):
                        size = get_dot_size(padj)
                        scatter = ax.scatter(display_idx, dataset_idx, 
                                           s=size, c=[log2fc], 
                                           cmap=self.colormap, 
                                           vmin=self.colorbar_min, 
                                           vmax=self.colorbar_max,
                                           alpha=0.7, edgecolors='black', linewidths=0.5)
            
            # 축 설정
            if len(genes) <= 50:
                ax.set_xticks(range(len(genes)))
                ax.set_xticklabels(genes_ordered, rotation=90, ha='right', fontsize=8)
            
            ax.set_yticks(range(len(self.dataset_names)))
            ax.set_yticklabels(self.dataset_names, fontsize=10)
            
            ax.set_xlabel(self.plot_ylabel, fontsize=12)  # Swapped
            ax.set_ylabel(self.plot_xlabel, fontsize=12)  # Swapped
        
        # 축 범위 조정 (간격 좁히기)
        if not self.transpose:
            # X축(Datasets) 범위를 좁게 설정
            num_datasets = len(self.dataset_names)
            margin = 0.3  # 양쪽 여백
            ax.set_xlim(-margin, num_datasets - 1 + margin)
            
            # Y축(Genes) 범위
            num_genes = len(genes)
            ax.set_ylim(-0.5, num_genes - 0.5)
        else:
            # Transpose: X축(Genes), Y축(Datasets)
            num_genes = len(genes)
            margin = 0.3
            ax.set_xlim(-margin, num_genes - 1 + margin)
            
            num_datasets = len(self.dataset_names)
            ax.set_ylim(-0.5, num_datasets - 0.5)
        
        # Title
        ax.set_title(self.plot_title, fontsize=14, fontweight='bold')
        
        # Colorbar
        if hasattr(self, 'scatter') or 'scatter' in locals():
            cbar = self.figure.colorbar(scatter, ax=ax)
            cbar.set_label('Log2 Fold Change', fontsize=10)
        
        # Legend for dot sizes
        if self.show_legend:
            from matplotlib.lines import Line2D
            legend_elements = [
                Line2D([0], [0], marker='o', color='w', label='Padj < 0.001',
                      markerfacecolor='gray', markersize=12, markeredgecolor='black'),
                Line2D([0], [0], marker='o', color='w', label='0.001 ≤ Padj < 0.01',
                      markerfacecolor='gray', markersize=10, markeredgecolor='black'),
                Line2D([0], [0], marker='o', color='w', label='0.01 ≤ Padj < 0.05',
                      markerfacecolor='gray', markersize=8, markeredgecolor='black'),
                Line2D([0], [0], marker='o', color='w', label='Padj ≥ 0.05',
                      markerfacecolor='gray', markersize=5, markeredgecolor='black')
            ]
            ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.15, 1), 
                     fontsize=9, title='Significance')
        
        self.figure.tight_layout()
        self.canvas.draw()

