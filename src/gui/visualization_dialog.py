"""
Visualization Dialog for RNA-Seq Data
"""
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QColorDialog, QGroupBox,
    QFormLayout, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox,
    QScrollArea, QFileDialog, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont
import matplotlib
matplotlib.use('QtAgg')
# matplotlib의 font_manager DEBUG 로그 억제
import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar  # type: ignore
from matplotlib.figure import Figure
import pandas as pd
import numpy as np

from models.standard_columns import StandardColumns
from utils import figure_theme, figure_export
from gui.widgets.figure_style_panel import FigureStylePanel
from gui.widgets.plot_labels_panel import PlotLabelsPanel
from gui.base_plot_dialog import BasePlotDialog


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


class VolcanoPlotWidget(QWidget):
    """Standalone Volcano Plot widget — embeddable in dialogs or tabs."""

    pin_requested = pyqtSignal(str, dict)  # (label, plot_params)

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
        'fig_height': 8,
        # Gene annotation
        'annotation_mode': 'none',   # 'none' | 'top_n' | 'custom'
        'annotation_top_n': 10,
        'annotation_label_size': 8,
        'annotation_custom_genes': [],  # list[str]
    }

    def __init__(self, dataframe, plot_params=None, parent=None, show_pin_button=True, embed_settings=True):
        super().__init__(parent)
        self.dataframe = dataframe
        self._show_pin_button = show_pin_button
        self._embed_settings = embed_settings
        self._settings_panel: 'QWidget | None' = None  # set in _init_ui when embed_settings=False

        # Merge class defaults with any provided plot_params override
        settings = dict(self.__class__._saved_settings)
        if plot_params:
            settings.update(plot_params)

        self.padj_threshold = settings['padj_threshold']
        self.log2fc_threshold = settings['log2fc_threshold']
        # Colors may arrive as hex strings (from JSON) or QColor objects
        def _to_qcolor(v):
            return QColor(v) if isinstance(v, str) else v
        self.down_color = _to_qcolor(settings['down_color'])
        self.up_color = _to_qcolor(settings['up_color'])
        self.ns_color = _to_qcolor(settings['ns_color'])
        self.dot_size = settings['dot_size']
        self.x_min = settings['x_min']
        self.x_max = settings['x_max']
        self.y_min = settings['y_min']
        self.y_max = settings['y_max']
        # Plot customization (compat: used for _labels defaults in _init_ui)
        self.plot_title = settings.get('title', 'Volcano Plot')
        self.plot_xlabel = settings.get('xlabel', 'Log2 Fold Change')
        self.plot_ylabel = settings.get('ylabel', '-Log10(Padj)')
        self.show_legend = settings.get('show_legend', True)
        self.fig_width = settings.get('fig_width', 12)
        self.fig_height = settings.get('fig_height', 8)
        # Gene annotation
        self.annotation_mode = settings['annotation_mode']
        self.annotation_top_n = settings['annotation_top_n']
        self.annotation_label_size = settings['annotation_label_size']
        self.annotation_custom_genes = list(settings['annotation_custom_genes'])

        # 저장된 label params (Pin to Tab 복원 시)
        self._pending_label_params = {k: v for k, v in settings.items()
                                      if k.startswith('labels_') or k in
                                      ('show_xticklabels', 'show_yticklabels', 'legend_position')}

        self._init_ui()
        # _init_ui 이후에 저장된 label params 복원
        if self._pending_label_params:
            self._labels.load_params(self._pending_label_params)
        self._plot()

    def get_plot_params(self) -> dict:
        """현재 설정을 직렬화 가능한 dict로 반환 (프로젝트 저장 / 탭 고정에 사용)."""
        params = {
            'padj_threshold': self.padj_threshold,
            'log2fc_threshold': self.log2fc_threshold,
            'down_color': self.down_color.name(),
            'up_color': self.up_color.name(),
            'ns_color': self.ns_color.name(),
            'dot_size': self.dot_size,
            'x_min': self.x_min,
            'x_max': self.x_max,
            'y_min': self.y_min,
            'y_max': self.y_max,
            'annotation_mode': self.annotation_mode,
            'annotation_top_n': self.annotation_top_n,
            'annotation_label_size': self.annotation_label_size,
            'annotation_custom_genes': list(self.annotation_custom_genes),
        }
        if hasattr(self, '_labels'):
            params.update(self._labels.get_params())
        return params

    def get_settings_panel(self) -> 'QWidget | None':
        """설정 패널 반환 (embed_settings=False일 때 외부 배치용)."""
        return self._settings_panel

    def _on_pin_to_tab(self):
        """탭으로 고정 버튼 클릭 → pin_requested 시그널 발생."""
        params = self.get_plot_params()
        padj = params['padj_threshold']
        lfc = params['log2fc_threshold']
        label = f"Volcano (p≤{padj}, FC≥{lfc})"
        self.pin_requested.emit(label, params)

    def _init_ui(self):
        """UI 초기화"""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 메인 스플리터 (좌: 설정, 우: 플롯)
        main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        outer_layout.addWidget(main_splitter)

        # 설정 패널 컨테이너
        settings_container = QWidget()
        left_panel = QVBoxLayout(settings_container)

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

        # Color 설정 (3행 세로)
        self.down_btn = QPushButton("Down-regulation")
        self.down_btn.setStyleSheet(f"background-color: {self.down_color.name()};")
        self.down_btn.clicked.connect(lambda: self._choose_color('down'))
        settings_layout.addRow("Down:", self.down_btn)

        self.up_btn = QPushButton("Up-regulation")
        self.up_btn.setStyleSheet(f"background-color: {self.up_color.name()};")
        self.up_btn.clicked.connect(lambda: self._choose_color('up'))
        settings_layout.addRow("Up:", self.up_btn)

        self.ns_btn = QPushButton("Not Significant")
        self.ns_btn.setStyleSheet(f"background-color: {self.ns_color.name()};")
        self.ns_btn.clicked.connect(lambda: self._choose_color('ns'))
        settings_layout.addRow("NS:", self.ns_btn)

        # Dot size
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 100)
        self.size_spin.setValue(self.dot_size)
        self.size_spin.valueChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Dot Size:", self.size_spin)

        # X축 범위 (Min/Max 세로 2행 + Auto)
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1000, 1000)
        self.x_min_spin.setDecimals(1)
        self.x_min_spin.setValue(self.x_min if self.x_min is not None else -10)
        self.x_min_spin.valueChanged.connect(self._on_settings_changed)
        settings_layout.addRow("X Min:", self.x_min_spin)

        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1000, 1000)
        self.x_max_spin.setDecimals(1)
        self.x_max_spin.setValue(self.x_max if self.x_max is not None else 10)
        self.x_max_spin.valueChanged.connect(self._on_settings_changed)
        self.x_auto_btn = QPushButton("Auto")
        self.x_auto_btn.setMaximumWidth(48)
        self.x_auto_btn.clicked.connect(self._auto_x_range)
        x_max_row = QWidget()
        xm = QHBoxLayout(x_max_row)
        xm.setContentsMargins(0, 0, 0, 0)
        xm.setSpacing(4)
        xm.addWidget(self.x_max_spin)
        xm.addWidget(self.x_auto_btn)
        settings_layout.addRow("X Max:", x_max_row)

        # Y축 범위 (Min/Max 세로 2행 + Auto)
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(0, 1000)
        self.y_min_spin.setDecimals(1)
        self.y_min_spin.setValue(self.y_min if self.y_min is not None else 0)
        self.y_min_spin.valueChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Y Min:", self.y_min_spin)

        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(0, 1000)
        self.y_max_spin.setDecimals(1)
        self.y_max_spin.setValue(self.y_max if self.y_max is not None else 50)
        self.y_max_spin.valueChanged.connect(self._on_settings_changed)
        self.y_auto_btn = QPushButton("Auto")
        self.y_auto_btn.setMaximumWidth(48)
        self.y_auto_btn.clicked.connect(self._auto_y_range)
        y_max_row = QWidget()
        ym = QHBoxLayout(y_max_row)
        ym.setContentsMargins(0, 0, 0, 0)
        ym.setSpacing(4)
        ym.addWidget(self.y_max_spin)
        ym.addWidget(self.y_auto_btn)
        settings_layout.addRow("Y Max:", y_max_row)

        settings_group.setLayout(settings_layout)
        left_panel.addWidget(settings_group)

        # ── Gene Annotation 패널 ──────────────────────────────────────
        annot_group = QGroupBox("Gene Annotation")
        annot_layout = QFormLayout()

        # Mode 선택: None / Top N / Custom List
        self.annot_mode_combo = QComboBox()
        self.annot_mode_combo.addItems(["None", "Top N (by significance)", "Custom List"])
        mode_map = {'none': 0, 'top_n': 1, 'custom': 2}
        self.annot_mode_combo.setCurrentIndex(mode_map.get(self.annotation_mode, 0))
        self.annot_mode_combo.currentIndexChanged.connect(self._on_annot_mode_changed)
        annot_layout.addRow("Mode:", self.annot_mode_combo)

        # Top N spinbox
        self.annot_top_n_spin = QSpinBox()
        self.annot_top_n_spin.setRange(1, 200)
        self.annot_top_n_spin.setValue(self.annotation_top_n)
        self.annot_top_n_spin.valueChanged.connect(self._on_settings_changed)
        annot_layout.addRow("Top N genes:", self.annot_top_n_spin)

        # Custom list: 파일 로드 버튼 + 상태 레이블
        custom_list_layout = QHBoxLayout()
        self.annot_load_btn = QPushButton("Load File…")
        self.annot_load_btn.setMaximumWidth(90)
        self.annot_load_btn.clicked.connect(self._load_annotation_gene_list)
        custom_list_layout.addWidget(self.annot_load_btn)
        self.annot_file_label = QLabel(
            f"{len(self.annotation_custom_genes)} genes loaded"
            if self.annotation_custom_genes else "No file loaded"
        )
        self.annot_file_label.setStyleSheet("color: grey; font-size: 10px;")
        custom_list_layout.addWidget(self.annot_file_label)
        annot_layout.addRow("Gene list:", custom_list_layout)

        # Label font size
        self.annot_size_spin = QSpinBox()
        self.annot_size_spin.setRange(5, 20)
        self.annot_size_spin.setValue(self.annotation_label_size)
        self.annot_size_spin.valueChanged.connect(self._on_settings_changed)
        annot_layout.addRow("Label size:", self.annot_size_spin)

        annot_group.setLayout(annot_layout)
        left_panel.addWidget(annot_group)
        self._on_annot_mode_changed()   # 초기 위젯 표시 상태 반영

        # ── Plot Labels & Legend ─────────────────────────────────────
        self._labels = PlotLabelsPanel()
        self._labels.set_defaults(
            title=self.plot_title,
            xlabel=self.plot_xlabel,
            ylabel=self.plot_ylabel,
        )
        self._labels.legend_check.setChecked(self.show_legend)
        self._labels.changed.connect(self._plot)
        labels_group = QGroupBox("Plot Labels & Legend")
        lv = QVBoxLayout(labels_group)
        lv.addWidget(self._labels)
        left_panel.addWidget(labels_group)

        # ── Figure Style & Export ────────────────────────────────────
        self._style = FigureStylePanel()
        self._style.changed.connect(self._plot)
        style_group = QGroupBox("Figure Style & Export")
        sv = QVBoxLayout(style_group)
        sv.addWidget(self._style)
        left_panel.addWidget(style_group)

        left_panel.addStretch()  # 아래 여백

        # embed_settings에 따라 설정 패널을 레이아웃에 추가하거나 외부 접근용으로 보관
        scroll = QScrollArea()
        scroll.setWidget(settings_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMinimumWidth(220)
        scroll.setMaximumWidth(300)

        if self._embed_settings:
            main_splitter.addWidget(scroll)
        else:
            # 외부(MainWindow 도크)에 배치될 설정 패널 보존
            self._settings_panel = scroll

        # 오른쪽: Plot 영역
        right_widget = QWidget()
        right_panel = QVBoxLayout(right_widget)
        right_panel.setContentsMargins(0, 0, 0, 0)

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

        if self._show_pin_button:
            pin_btn = QPushButton("📌 Pin to Tab")
            pin_btn.setToolTip("Pin this plot as a new tab")
            pin_btn.clicked.connect(self._on_pin_to_tab)
            button_layout.addWidget(pin_btn)

        right_panel.addLayout(button_layout)

        main_splitter.addWidget(right_widget)
        # 초기 스플리터 비율: 설정 300px, 나머지 플롯
        main_splitter.setSizes([300, 9999])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)

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
        self.__class__._saved_settings.update({
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

        # Gene annotation (위젯이 아직 없을 수 있으므로 guard)
        if hasattr(self, 'annot_mode_combo'):
            _mode_names = ['none', 'top_n', 'custom']
            self.annotation_mode = _mode_names[self.annot_mode_combo.currentIndex()]
            self.annotation_top_n = self.annot_top_n_spin.value()
            self.annotation_label_size = self.annot_size_spin.value()

        # 설정값을 클래스 변수에 저장 (세션 동안 유지)
        self.__class__._saved_settings.update({
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
            'annotation_mode': self.annotation_mode,
            'annotation_top_n': self.annotation_top_n,
            'annotation_label_size': self.annotation_label_size,
            'annotation_custom_genes': list(self.annotation_custom_genes),
        })

        self._plot()

    def _plot(self):
        """Volcano Plot 그리기"""
        # _init_ui 완료 전 호출 방지
        if not hasattr(self, 'figure'):
            return
        theme = self._style.theme_name() if hasattr(self, '_style') else 'Journal (sans-serif)'
        with figure_theme.theme_context(theme):
            self._draw_plot()

    def _draw_plot(self):
        """실제 matplotlib 그리기 (theme_context 안에서 호출)."""
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

        # 축 범위 설정
        if self.x_min is not None and self.x_max is not None:
            ax.set_xlim(self.x_min, self.x_max)
        if self.y_min is not None and self.y_max is not None:
            ax.set_ylim(self.y_min, self.y_max)

        ax.grid(True, alpha=0.3)

        # Annotation 텍스트 (hover용) - zorder 높게 설정하여 최상위 레이어로
        self.annot = ax.annotate("", xy=(0, 0), xytext=(20, 20),
                                textcoords="offset points",
                                bbox=dict(boxstyle="round", fc="w", alpha=0.9),
                                arrowprops=dict(arrowstyle="->"),
                                zorder=1000)
        self.annot.set_visible(False)

        # ── Gene Name Annotation (label) ─────────────────────────────
        self._draw_gene_labels(ax, df)

        # Hover 이벤트 연결 (DEG만)
        self.figure.canvas.mpl_connect("motion_notify_event", self._on_hover)

        # PlotLabelsPanel 적용 (title/xlabel/ylabel/ticks/legend)
        if hasattr(self, '_labels'):
            self._labels.apply_to_axes(ax)

        self.figure.tight_layout()
        self.canvas.draw()

    # ── Gene Annotation 관련 메서드 ───────────────────────────────────────────

    def _on_annot_mode_changed(self):
        """Annotation mode 콤보박스 변경 시 관련 위젯 활성/비활성"""
        idx = self.annot_mode_combo.currentIndex()
        # 0=None, 1=Top N, 2=Custom List
        self.annot_top_n_spin.setEnabled(idx == 1)
        self.annot_load_btn.setEnabled(idx == 2)
        self.annot_file_label.setEnabled(idx == 2)
        self.annot_size_spin.setEnabled(idx != 0)
        # figure가 이미 생성된 경우에만 replot (init 중 호출 시 스킵)
        if hasattr(self, 'figure'):
            self._on_settings_changed()

    def _load_annotation_gene_list(self):
        """txt/csv/tsv 파일에서 gene list 로드"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Gene List",
            "",
            "Text/CSV/TSV Files (*.txt *.csv *.tsv);;All Files (*)"
        )
        if not file_path:
            return
        try:
            genes: list[str] = []
            with open(file_path, encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # csv/tsv → 첫 번째 컬럼만 사용
                    for sep in ('\t', ','):
                        if sep in line:
                            line = line.split(sep)[0].strip()
                            break
                    if line:
                        genes.append(line)
            if genes:
                self.annotation_custom_genes = genes
                self.annot_file_label.setText(f"{len(genes)} genes loaded")
                self.annot_file_label.setStyleSheet("color: green; font-size: 10px;")
                self._on_settings_changed()
            else:
                QMessageBox.warning(self, "Empty File", "No gene names found in the file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load gene list:\n{e}")

    def _draw_gene_labels(self, ax, df):
        """Volcano plot 위에 gene name 레이블 그리기"""
        mode_idx = self.annot_mode_combo.currentIndex()
        if mode_idx == 0:   # None
            return

        # gene name 컬럼 결정 (symbol 우선)
        gene_col = None
        for c in ('symbol', 'gene_id'):
            if c in df.columns:
                gene_col = c
                break
        if gene_col is None:
            return

        label_size = self.annot_size_spin.value()

        if mode_idx == 1:   # Top N by significance score
            top_n = self.annot_top_n_spin.value()
            # significant genes만 대상 (up + down)
            sig = df[df['regulation'].isin(['up', 'down'])].copy()
            if sig.empty:
                return
            # score = |log2FC| * -log10(padj) 로 순위 결정
            sig['_score'] = sig['log2FC'].abs() * sig['-log10(padj)']
            sig = sig.nlargest(top_n, '_score')
            genes_to_label = sig
        else:               # Custom List
            if not self.annotation_custom_genes:
                return
            custom_upper = {g.upper() for g in self.annotation_custom_genes}
            genes_to_label = df[df[gene_col].astype(str).str.upper().isin(custom_upper)]
            if genes_to_label.empty:
                return

        # 각 gene에 레이블 annotate
        for _, row in genes_to_label.iterrows():
            x = row['log2FC']
            y = row['-log10(padj)']
            name = str(row[gene_col])
            ax.annotate(
                name,
                xy=(x, y),
                xytext=(4, 4),
                textcoords='offset points',
                fontsize=label_size,
                fontweight='bold',
                color='black',
                arrowprops=dict(arrowstyle='-', color='grey',
                                lw=0.5, shrinkA=0, shrinkB=2),
                bbox=dict(boxstyle='round,pad=0.15', fc='white',
                          ec='none', alpha=0.6),
                zorder=500,
            )

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

            x_pos = row['log2FC']
            y_pos = row['-log10(padj)']

            # X축 boundary 체크
            x_range = xlim[1] - xlim[0]
            if x_pos < xlim[0] + x_range * 0.15:
                offset_x = 20
            elif x_pos > xlim[0] + x_range * 0.80:
                offset_x = -100
            else:
                offset_x = 20

            # Y축 boundary 체크
            y_range = ylim[1] - ylim[0]
            if y_pos < ylim[0] + y_range * 0.15:
                offset_y = 20
            elif y_pos > ylim[0] + y_range * 0.75:
                offset_y = -70
            else:
                offset_y = 20

            self.annot.set_position((offset_x, offset_y))
            self.annot.set_visible(True)
        else:
            self.annot.set_visible(False)

        self.canvas.draw_idle()

    def _save_figure(self):
        """Figure 저장"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        opts = self._style.export_opts()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure",
            f"volcano_plot.{opts['fmt']}",
            figure_export.filter_string(),
        )
        if not path:
            return
        try:
            saved = figure_export.save_figure(self.figure, path, **opts)
            QMessageBox.information(self, "Saved", f"Figure saved to:\n{saved}")
        except ValueError as e:
            QMessageBox.warning(self, "Unsupported Format", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

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


class VolcanoPlotDialog(QDialog):
    """Thin dialog wrapper around VolcanoPlotWidget."""

    # Emitted when the user requests to pin the plot to a main-window tab.
    # Signature: (widget: QWidget, label: str, plot_type: str, plot_params: dict)
    plot_pinned = pyqtSignal(object, str, str, dict)

    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.setWindowTitle("🌋 Volcano Plot")
        self.setWindowIcon(create_plot_icon("🌋", QColor(220, 20, 60)))  # Crimson
        self.setMinimumSize(1000, 700)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self._widget = VolcanoPlotWidget(dataframe, parent=self, show_pin_button=True)
        self._widget.pin_requested.connect(self._on_pin_requested)
        layout.addWidget(self._widget)

    def _on_pin_requested(self, label: str, params: dict):
        """Pin button inside widget → create a fresh widget for the tab, emit signal."""
        tab_widget = VolcanoPlotWidget(self.dataframe, plot_params=params, show_pin_button=False, embed_settings=False)
        self.plot_pinned.emit(tab_widget, label, 'volcano', params)
        self.close()


class PadjHistogramDialog(BasePlotDialog):
    """P-value Histogram 시각화 다이얼로그 — inherits BasePlotDialog."""

    def __init__(self, dataframe, parent=None):
        # Domain state must be set before super().__init__() calls _setup_controls()
        self.dataframe = dataframe
        self.pvalue_type = 'padj'
        self.bin_count = 50

        super().__init__("P-value Histogram", parent, figsize=(10, 6))
        self.setWindowIcon(create_plot_icon("📊", QColor(34, 139, 34)))  # Forest Green
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
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

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_settings_changed(self):
        """설정 변경 시 자동 업데이트"""
        if self.pvalue_combo.currentIndex() == 0:
            self.pvalue_type = 'padj'
        else:
            self.pvalue_type = 'pvalue'
        self.bin_count = self.bin_spin.value()
        self._update_plot()

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
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


class HeatmapWidget(QWidget):
    """Standalone Expression Heatmap widget — embeddable in dialogs or tabs."""
    pin_requested = pyqtSignal(str, dict)  # (label, plot_params)

    # 클래스 변수로 설정값 저장 (세션 동안 유지)
    _saved_settings = {
        'n_genes': 50,
        'normalization': 'z-score',
        'transpose': False,
        'sorting': 'padj',
        'colormap': 'RdBu_r',
        'colorbar_min': -3.0,
        'colorbar_max': 3.0,
        'show_legend': True,
        'fig_width': 12,
        'fig_height': 8
    }

    # PlotLabelsPanel 기본값 (set_defaults에 사용)
    _default_title = 'Expression Heatmap'
    _default_xlabel = 'Samples'
    _default_ylabel = 'Genes'

    def __init__(self, dataframe, plot_params=None, parent=None, show_pin_button=True, embed_settings=True):
        super().__init__(parent)
        self.dataframe = dataframe
        self._show_pin_button = show_pin_button
        self._embed_settings = embed_settings
        self._settings_panel: QWidget | None = None  # set in _init_ui when embed_settings=False

        # 현재 표시 중인 heatmap 데이터 (export용)
        self.current_heatmap_data = None
        self.current_gene_labels = None

        # 클래스 기본값을 기준으로 plot_params 오버라이드 적용
        merged = dict(self._saved_settings)
        if plot_params:
            merged.update(plot_params)

        self.n_genes = merged['n_genes']
        self.normalization = merged['normalization']
        self.transpose = merged['transpose']
        self.sorting = merged['sorting']
        self.colormap = merged['colormap']
        self.colorbar_min = merged['colorbar_min']
        self.colorbar_max = merged['colorbar_max']
        self.show_legend = merged['show_legend']
        self.fig_width = merged['fig_width']
        self.fig_height = merged['fig_height']

        self._init_ui()

        # PlotLabelsPanel 기본값 설정 (plot_params 복원 포함)
        self._labels.set_defaults(
            merged.get('labels_title', self._default_title),
            merged.get('labels_xlabel', self._default_xlabel),
            merged.get('labels_ylabel', self._default_ylabel),
        )
        if plot_params:
            self._labels.load_params(plot_params)

        self._plot()

    def get_plot_params(self) -> dict:
        """현재 설정값을 JSON 직렬화 가능한 dict로 반환"""
        params = {
            'n_genes': self.n_genes,
            'normalization': self.normalization,
            'transpose': self.transpose,
            'sorting': self.sorting,
            'colormap': self.colormap,
            'colorbar_min': self.colorbar_min,
            'colorbar_max': self.colorbar_max,
            'show_legend': self.show_legend,
            'fig_width': self.fig_width,
            'fig_height': self.fig_height,
        }
        params.update(self._labels.get_params())
        return params

    def get_settings_panel(self) -> 'QWidget | None':
        """설정 패널 반환 (embed_settings=False일 때 외부 배치용)."""
        return self._settings_panel

    def _on_pin_to_tab(self):
        """현재 플롯을 탭으로 고정 요청"""
        n = self.n_genes
        norm = self.normalization
        label = f"Heatmap (top {n}, {norm})"
        self.pin_requested.emit(label, self.get_plot_params())

    def _init_ui(self):
        """UI 초기화"""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 메인 스플리터 (좌: 설정, 우: 플롯)
        main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        outer_layout.addWidget(main_splitter)

        # 설정 패널 컨테이너
        settings_container = QWidget()
        left_panel = QVBoxLayout(settings_container)

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
        norm_map = {'z-score': 0, 'minmax': 1, 'log2': 2, 'none': 3}
        self.norm_combo.setCurrentIndex(norm_map.get(self.normalization, 0))
        self.norm_combo.currentIndexChanged.connect(self._on_settings_changed)
        settings_layout.addRow("Normalization:", self.norm_combo)

        # Sorting 방법
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Padj (ascending)",
            "Log2FC (absolute descending)",
            "Hierarchical Clustering"
        ])
        sort_map = {'padj': 0, 'log2fc': 1, 'clustering': 2}
        self.sort_combo.setCurrentIndex(sort_map.get(self.sorting, 0))
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

        # Colorbar 표시 옵션
        custom_group = QGroupBox("Plot Options")
        custom_layout = QFormLayout()

        self.legend_check = QCheckBox("Show Colorbar")
        self.legend_check.setChecked(self.show_legend)
        self.legend_check.stateChanged.connect(self._on_settings_changed)
        custom_layout.addRow("", self.legend_check)

        custom_group.setLayout(custom_layout)
        left_panel.addWidget(custom_group)

        # --- Plot Labels & Legend ---
        labels_group = QGroupBox("Plot Labels & Legend")
        labels_vbox = QVBoxLayout()
        self._labels = PlotLabelsPanel()
        self._labels.changed.connect(self._plot)
        labels_vbox.addWidget(self._labels)
        labels_group.setLayout(labels_vbox)
        left_panel.addWidget(labels_group)

        # --- Figure Style & Export ---
        style_group = QGroupBox("Figure Style & Export")
        style_vbox = QVBoxLayout()
        self._style = FigureStylePanel()
        self._style.changed.connect(self._plot)
        style_vbox.addWidget(self._style)
        style_group.setLayout(style_vbox)
        left_panel.addWidget(style_group)

        left_panel.addStretch()

        # embed_settings에 따라 설정 패널을 레이아웃에 추가하거나 외부 접근용으로 보관
        scroll = QScrollArea()
        scroll.setWidget(settings_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMinimumWidth(220)
        scroll.setMaximumWidth(300)

        if self._embed_settings:
            main_splitter.addWidget(scroll)
        else:
            self._settings_panel = scroll

        # 오른쪽: Plot 영역
        right_widget = QWidget()
        right_panel = QVBoxLayout(right_widget)
        right_panel.setContentsMargins(0, 0, 0, 0)

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
        export_btn.clicked.connect(self._export_heatmap_data)
        button_layout.addWidget(export_btn)

        if self._show_pin_button:
            pin_btn = QPushButton("📌 Pin to Tab")
            pin_btn.setToolTip("Pin this plot as a new tab")
            pin_btn.clicked.connect(self._on_pin_to_tab)
            button_layout.addWidget(pin_btn)

        right_panel.addLayout(button_layout)

        main_splitter.addWidget(right_widget)
        # 초기 스플리터 비율: 설정 300px, 나머지 플롯
        main_splitter.setSizes([300, 9999])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)

    def _on_settings_changed(self):
        """설정 변경 시 자동 업데이트"""
        self.n_genes = self.gene_spin.value()

        norm_idx = self.norm_combo.currentIndex()
        if norm_idx == 0:
            self.normalization = 'z-score'
        elif norm_idx == 1:
            self.normalization = 'minmax'
        elif norm_idx == 2:
            self.normalization = 'log2'
        else:
            self.normalization = 'none'

        sort_idx = self.sort_combo.currentIndex()
        if sort_idx == 0:
            self.sorting = 'padj'
        elif sort_idx == 1:
            self.sorting = 'log2fc'
        else:
            self.sorting = 'clustering'

        colormap_names = ['RdBu_r', 'viridis', 'plasma', 'coolwarm', 'seismic']
        self.colormap = colormap_names[self.colormap_combo.currentIndex()]

        self.colorbar_min = self.colorbar_min_spin.value()
        self.colorbar_max = self.colorbar_max_spin.value()
        self.transpose = self.transpose_check.isChecked()
        self.show_legend = self.legend_check.isChecked()

        self.__class__._saved_settings.update({
            'n_genes': self.n_genes,
            'normalization': self.normalization,
            'transpose': self.transpose,
            'sorting': self.sorting,
            'colormap': self.colormap,
            'colorbar_min': self.colorbar_min,
            'colorbar_max': self.colorbar_max,
            'show_legend': self.show_legend
        })

        self._plot()

    def _plot(self):
        with figure_theme.theme_context(self._style.theme_name()):
            self._draw_heatmap()

    def _draw_heatmap(self):
        """Heatmap 그리기"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        df = self.dataframe.copy()

        exclude_patterns = [
            'basemean', 'base_mean', 'log2fold', 'log2fc', 'logfc', 'foldchange',
            'lfcse', 'stat', 'statistic', 'pval', 'padj', 'fdr', 'qvalue',
            'gene_id', 'gene', 'symbol', 'dataset', 'description', 'name'
        ]

        sample_cols = []
        for col in df.columns:
            col_lower = col.lower()
            is_excluded = any(pattern in col_lower for pattern in exclude_patterns)
            if not is_excluded and pd.api.types.is_numeric_dtype(df[col]):
                sample_cols.append(col)

        if not sample_cols:
            ax.text(0.5, 0.5, 'No sample expression columns found.\n'
                   'Heatmap requires sample count data.',
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

        expr_data = df[sample_cols].copy()
        expr_data = expr_data.dropna()

        if len(expr_data) == 0:
            ax.text(0.5, 0.5, 'No valid data after removing NaN values',
                   ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

        if 'padj' in df.columns:
            df_with_padj = df.loc[expr_data.index].copy()
            valid_padj = df_with_padj['padj'].dropna()
            if len(valid_padj) > 0:
                top_genes_idx = valid_padj.nsmallest(min(self.n_genes, len(valid_padj))).index
            else:
                variances = expr_data.var(axis=1)
                top_genes_idx = variances.nlargest(min(self.n_genes, len(expr_data))).index
        else:
            variances = expr_data.var(axis=1)
            top_genes_idx = variances.nlargest(min(self.n_genes, len(expr_data))).index

        if 'symbol' in df.columns:
            gene_labels = df.loc[top_genes_idx, 'symbol'].tolist()
        elif 'gene_id' in df.columns:
            gene_labels = df.loc[top_genes_idx, 'gene_id'].tolist()
        else:
            gene_labels = top_genes_idx.tolist()

        expr_data = expr_data.loc[top_genes_idx]

        if self.normalization == 'z-score':
            heatmap_data = expr_data.apply(lambda x: (x - x.mean()) / (x.std() + 1e-10), axis=1)
            cbar_label = 'Z-score'
        elif self.normalization == 'minmax':
            heatmap_data = expr_data.apply(lambda x: (x - x.min()) / (x.max() - x.min() + 1e-10), axis=1)
            cbar_label = 'Normalized (0-1)'
        elif self.normalization == 'log2':
            heatmap_data = np.log2(expr_data + 1)
            cbar_label = 'Log2(count + 1)'
        else:
            heatmap_data = expr_data
            cbar_label = 'Raw count'

        if self.sorting == 'padj' and 'padj' in df.columns:
            df_with_padj = df.loc[heatmap_data.index].copy()
            sort_order = df_with_padj['padj'].argsort()
            heatmap_data = heatmap_data.iloc[sort_order]
            gene_labels = [gene_labels[i] for i in sort_order]
        elif self.sorting == 'log2fc' and 'log2FC' in df.columns:
            df_with_log2fc = df.loc[heatmap_data.index].copy()
            sort_order = df_with_log2fc['log2FC'].abs().argsort()[::-1]
            heatmap_data = heatmap_data.iloc[sort_order]
            gene_labels = [gene_labels[i] for i in sort_order]
        elif self.sorting == 'clustering':
            try:
                from scipy.cluster.hierarchy import linkage, dendrogram
                from scipy.spatial.distance import pdist
                linkage_matrix = linkage(pdist(heatmap_data, metric='euclidean'), method='average')
                dendro = dendrogram(linkage_matrix, no_plot=True)
                order = dendro['leaves']
                heatmap_data = heatmap_data.iloc[order]
                gene_labels = [gene_labels[i] for i in order]
            except ImportError:
                pass

        if self.transpose:
            heatmap_data = heatmap_data.T

        im = ax.imshow(heatmap_data, cmap=self.colormap, aspect='auto',
                      interpolation='nearest', vmin=self.colorbar_min, vmax=self.colorbar_max)

        self.current_heatmap_data = heatmap_data
        self.current_gene_labels = gene_labels

        if self.transpose:
            if len(heatmap_data.index) <= 50:
                ax.set_yticks(range(len(heatmap_data.index)))
                ax.set_yticklabels(heatmap_data.index, fontsize=8)
            if len(gene_labels) <= 20:
                ax.set_xticks(range(len(gene_labels)))
                ax.set_xticklabels(gene_labels, rotation=90, fontsize=8, ha='right')
        else:
            if len(heatmap_data.columns) <= 50:
                ax.set_xticks(range(len(heatmap_data.columns)))
                ax.set_xticklabels(heatmap_data.columns, rotation=90, fontsize=8)
            if len(gene_labels) <= 20:
                ax.set_yticks(range(len(gene_labels)))
                ax.set_yticklabels(gene_labels, fontsize=8)

        self._labels.apply_to_axes(ax)

        if self.show_legend:
            cbar = self.figure.colorbar(im, ax=ax)
            cbar.set_label(cbar_label, fontsize=10)

        self.heatmap_data = heatmap_data
        self.gene_labels = gene_labels
        self.figure.canvas.mpl_connect("motion_notify_event", self._on_hover)

        self.annot = ax.annotate("", xy=(0, 0), xytext=(20, 20),
                                textcoords="offset points",
                                bbox=dict(boxstyle="round", fc="w", alpha=0.9),
                                arrowprops=dict(arrowstyle="->"),
                                zorder=1000)
        self.annot.set_visible(False)

        self.figure.tight_layout()
        self.canvas.draw()

    def _save_figure(self):
        opts = self._style.export_opts()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure",
            f"heatmap.{opts['fmt']}",
            figure_export.filter_string()
        )
        if not path:
            return
        try:
            saved = figure_export.save_figure(self.figure, path, **opts)
            QMessageBox.information(self, "Saved", f"Figure saved to:\n{saved}")
        except ValueError as e:
            QMessageBox.warning(self, "Unsupported Format", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save figure:\n{e}")

    def _export_heatmap_data(self):
        """현재 화면에 표시된 heatmap 데이터를 Excel로 내보내기"""
        if self.current_heatmap_data is None:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Data", "No heatmap data to export. Please generate the plot first.")
            return

        try:
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Heatmap Data",
                "heatmap_data.xlsx",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )

            if not file_path:
                return

            export_df = self.current_heatmap_data.copy()

            if not self.transpose:
                export_df.insert(0, 'Gene', self.current_gene_labels)

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

        x, y = int(event.xdata + 0.5), int(event.ydata + 0.5)

        if not hasattr(self, 'heatmap_data'):
            return

        ax = event.inaxes
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        if self.transpose:
            if 0 <= y < len(self.heatmap_data.index) and 0 <= x < len(self.gene_labels):
                sample = self.heatmap_data.index[y]
                gene = self.gene_labels[x]
                value = self.heatmap_data.iloc[y, x]

                text = f"Sample: {sample}\nGene: {gene}\nValue: {value:.2f}"
                self.annot.xy = (x, y)
                self.annot.set_text(text)

                x_range = xlim[1] - xlim[0]
                y_range = ylim[1] - ylim[0]
                offset_x = -100 if x > x_range * 0.75 else 20
                offset_y = -70 if y > y_range * 0.70 else 20

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

                x_range = xlim[1] - xlim[0]
                y_range = ylim[1] - ylim[0]
                offset_x = -100 if x > x_range * 0.75 else 20
                offset_y = -70 if y > y_range * 0.70 else 20

                self.annot.set_position((offset_x, offset_y))
                self.annot.set_visible(True)
                self.canvas.draw_idle()
            else:
                self.annot.set_visible(False)
                self.canvas.draw_idle()


class HeatmapDialog(QDialog):
    """Thin dialog wrapper around HeatmapWidget."""
    plot_pinned = pyqtSignal(object, str, str, dict)  # widget, label, plot_type, params

    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.setWindowTitle("🔥 Expression Heatmap")
        self.setWindowIcon(create_plot_icon("🔥", QColor(255, 140, 0)))
        self.setMinimumSize(1000, 800)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self._widget = HeatmapWidget(dataframe, parent=self, show_pin_button=True)
        self._widget.pin_requested.connect(self._on_pin_requested)
        layout.addWidget(self._widget)

        # Close 버튼 추가
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _on_pin_requested(self, label: str, params: dict):
        """pin_requested 시그널 수신 → 탭 위젯 생성 후 plot_pinned 방출"""
        tab_widget = HeatmapWidget(self.dataframe, plot_params=params, show_pin_button=False, embed_settings=False)
        self.plot_pinned.emit(tab_widget, label, 'heatmap', params)
        self.close()


class DotPlotDialog(BasePlotDialog):
    """Dot Plot for Comparison Data Visualization — inherits BasePlotDialog.

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
        # Domain state must be set before super().__init__() calls _setup_controls()
        self.comparison_df = comparison_df
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
            # Defer warning — cannot show QMessageBox before QApplication is ready
            # The dialog will show an empty plot with an error message
            pass

        fig_width = self._saved_settings['fig_width']
        fig_height = self._saved_settings['fig_height']

        super().__init__("Dot Plot - Comparison Data", parent, figsize=(fig_width, fig_height))
        self.setWindowIcon(create_plot_icon("⚫", QColor(138, 43, 226)))  # Blue Violet
        self._update_plot()

    def _extract_dataset_names(self):
        """컬럼명에서 데이터셋 이름 추출"""
        dataset_names = []
        for col in self.comparison_df.columns:
            if '_log2FC' in col or '_log2fc' in col:
                dataset_name = col.replace('_log2FC', '').replace('_log2fc', '')
                if dataset_name and dataset_name not in dataset_names:
                    dataset_names.append(dataset_name)
        return dataset_names

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
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
        layout.addWidget(settings_group)

        # === Plot Customization 그룹 ===
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()

        self.title_edit = QLineEdit(self.plot_title)
        self.title_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("Title:", self.title_edit)

        self.xlabel_edit = QLineEdit(self.plot_xlabel)
        self.xlabel_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("X Label:", self.xlabel_edit)

        self.ylabel_edit = QLineEdit(self.plot_ylabel)
        self.ylabel_edit.textChanged.connect(self._on_settings_changed)
        custom_layout.addRow("Y Label:", self.ylabel_edit)

        self.legend_check = QCheckBox("Show Legend")
        self.legend_check.setChecked(self.show_legend)
        self.legend_check.stateChanged.connect(self._on_settings_changed)
        custom_layout.addRow("", self.legend_check)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

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
        layout.addWidget(size_group)

    # ── Slots ─────────────────────────────────────────────────────────────

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

        self._update_plot()

    def _on_figure_size_changed(self):
        """Figure 크기 변경"""
        width = self.width_spin.value()
        height = self.height_spin.value()

        self._saved_settings['fig_width'] = width
        self._saved_settings['fig_height'] = height

        self.figure.set_size_inches(width, height)
        self.canvas.draw()

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        """Dot Plot 그리기"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not self.dataset_names:
            ax.text(0.5, 0.5, 'No valid dataset columns found in comparison sheet.',
                    ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

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

        scatter = None

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
            num_datasets = len(self.dataset_names)
            margin = 0.3
            ax.set_xlim(-margin, num_datasets - 1 + margin)
            num_genes = len(genes)
            ax.set_ylim(-0.5, num_genes - 0.5)
        else:
            num_genes = len(genes)
            margin = 0.3
            ax.set_xlim(-margin, num_genes - 1 + margin)
            num_datasets = len(self.dataset_names)
            ax.set_ylim(-0.5, num_datasets - 0.5)

        # Title
        ax.set_title(self.plot_title, fontsize=14, fontweight='bold')

        # Colorbar
        if scatter is not None:
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
