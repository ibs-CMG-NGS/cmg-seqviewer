"""
MA Plot Dialog

ATAC-seq DA 데이터의 MA Plot (Mean Accessibility vs Log2 Fold Change).
  X축: log₂(Mean Accessibility)  ←  base_mean 컬럼
  Y축: log₂ Fold Change          ←  log2fc 컬럼
점 색상은 adj_pvalue / log2fc 임계값으로 up / down / ns 분류.
"""
import logging

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QWidget, QPushButton, QLabel, QDoubleSpinBox, QSpinBox, QCheckBox,
    QComboBox, QColorDialog, QFileDialog, QMessageBox,
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from models.data_models import Dataset
from gui.base_plot_dialog import BasePlotDialog


class MAPlotDialog(BasePlotDialog):
    """MA Plot 다이얼로그 (Mean Accessibility vs Log₂FC)."""

    _saved_settings: dict = {
        'padj_threshold':    0.05,
        'log2fc_threshold':  1.0,
        'down_color':        QColor(0, 0, 255),
        'up_color':          QColor(255, 0, 0),
        'ns_color':          QColor(128, 128, 128),
        'dot_size':          10,
        'x_min':             None,
        'x_max':             None,
        'y_min':             None,
        'y_max':             None,
        'title':             'MA Plot',
        'xlabel':            'log₂ Mean Accessibility',
        'ylabel':            'log₂ Fold Change',
        'show_legend':       True,
        'fig_width':         12,
        'fig_height':        8,
        'annotation_mode':   'none',
        'annotation_top_n':  10,
        'annotation_label_size': 8,
        'annotation_custom_genes': [],
    }

    def __init__(self, dataset: Dataset, parent=None):
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset

        s = self._saved_settings
        self.padj_threshold       = s['padj_threshold']
        self.log2fc_threshold     = s['log2fc_threshold']
        self.down_color           = s['down_color']
        self.up_color             = s['up_color']
        self.ns_color             = s['ns_color']
        self.dot_size             = s['dot_size']
        self.x_min                = s['x_min']
        self.x_max                = s['x_max']
        self.y_min                = s['y_min']
        self.y_max                = s['y_max']
        self.plot_title           = s['title']
        self.plot_xlabel          = s['xlabel']
        self.plot_ylabel          = s['ylabel']
        self.show_legend          = s['show_legend']
        self.fig_width            = s['fig_width']
        self.fig_height           = s['fig_height']
        self.annotation_mode      = s['annotation_mode']
        self.annotation_top_n     = s['annotation_top_n']
        self.annotation_label_size = s['annotation_label_size']
        self.annotation_custom_genes = list(s['annotation_custom_genes'])

        # hover state
        self._scatter_collections = []

        super().__init__(f"MA Plot — {dataset.name}", parent, figsize=(self.fig_width, self.fig_height))
        self._update_plot()

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Plot Settings
        settings_group = QGroupBox("Plot Settings")
        settings_layout = QFormLayout()

        self.padj_spin = QDoubleSpinBox()
        self.padj_spin.setRange(0.0001, 1.0)
        self.padj_spin.setDecimals(4)
        self.padj_spin.setSingleStep(0.01)
        self.padj_spin.setValue(self.padj_threshold)
        self.padj_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("P-adj Threshold:", self.padj_spin)

        self.log2fc_spin = QDoubleSpinBox()
        self.log2fc_spin.setRange(0.0, 10.0)
        self.log2fc_spin.setDecimals(4)
        self.log2fc_spin.setSingleStep(0.1)
        self.log2fc_spin.setValue(self.log2fc_threshold)
        self.log2fc_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Log2FC Threshold:", self.log2fc_spin)

        # Colors
        self.down_btn = QPushButton("Down")
        self.down_btn.setStyleSheet(f"background-color: {self.down_color.name()};")
        self.down_btn.clicked.connect(lambda: self._choose_color('down'))
        settings_layout.addRow("Down:", self.down_btn)

        self.up_btn = QPushButton("Up")
        self.up_btn.setStyleSheet(f"background-color: {self.up_color.name()};")
        self.up_btn.clicked.connect(lambda: self._choose_color('up'))
        settings_layout.addRow("Up:", self.up_btn)

        self.ns_btn = QPushButton("NS")
        self.ns_btn.setStyleSheet(f"background-color: {self.ns_color.name()};")
        self.ns_btn.clicked.connect(lambda: self._choose_color('ns'))
        settings_layout.addRow("NS:", self.ns_btn)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 100)
        self.size_spin.setValue(self.dot_size)
        self.size_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Dot Size:", self.size_spin)

        # X-axis range
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-5, 100)
        self.x_min_spin.setDecimals(1)
        self.x_min_spin.setValue(self.x_min if self.x_min is not None else 0.0)
        self.x_min_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("X Min:", self.x_min_spin)

        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-5, 100)
        self.x_max_spin.setDecimals(1)
        self.x_max_spin.setValue(self.x_max if self.x_max is not None else 20.0)
        self.x_max_spin.valueChanged.connect(self._update_plot)
        x_auto_btn = QPushButton("Auto")
        x_auto_btn.setMaximumWidth(60)
        x_auto_btn.clicked.connect(self._auto_x_range)
        x_max_row = QWidget()
        x_max_rl = QHBoxLayout(x_max_row)
        x_max_rl.setContentsMargins(0, 0, 0, 0)
        x_max_rl.setSpacing(4)
        x_max_rl.addWidget(self.x_max_spin)
        x_max_rl.addWidget(x_auto_btn)
        settings_layout.addRow("X Max:", x_max_row)

        # Y-axis range
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-100, 0)
        self.y_min_spin.setDecimals(1)
        self.y_min_spin.setValue(self.y_min if self.y_min is not None else -6.0)
        self.y_min_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Y Min:", self.y_min_spin)

        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(0, 100)
        self.y_max_spin.setDecimals(1)
        self.y_max_spin.setValue(self.y_max if self.y_max is not None else 6.0)
        self.y_max_spin.valueChanged.connect(self._update_plot)
        y_auto_btn = QPushButton("Auto")
        y_auto_btn.setMaximumWidth(60)
        y_auto_btn.clicked.connect(self._auto_y_range)
        y_max_row = QWidget()
        y_max_rl = QHBoxLayout(y_max_row)
        y_max_rl.setContentsMargins(0, 0, 0, 0)
        y_max_rl.setSpacing(4)
        y_max_rl.addWidget(self.y_max_spin)
        y_max_rl.addWidget(y_auto_btn)
        settings_layout.addRow("Y Max:", y_max_row)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Plot Customization
        custom_group = QGroupBox("Plot Customization")
        custom_layout = QFormLayout()

        self.width_spin = QSpinBox()
        self.width_spin.setRange(6, 20)
        self.width_spin.setValue(self.fig_width)
        self.width_spin.valueChanged.connect(self._on_figure_size_changed)
        custom_layout.addRow("Width (in):", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(4, 16)
        self.height_spin.setValue(self.fig_height)
        self.height_spin.valueChanged.connect(self._on_figure_size_changed)
        custom_layout.addRow("Height (in):", self.height_spin)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # Gene Annotation
        annot_group = QGroupBox("Gene Annotation")
        annot_layout = QFormLayout()

        self.annot_mode_combo = QComboBox()
        self.annot_mode_combo.addItems(["None", "Top N (by |FC| × significance)", "Custom List"])
        mode_map = {'none': 0, 'top_n': 1, 'custom': 2}
        self.annot_mode_combo.setCurrentIndex(mode_map.get(self.annotation_mode, 0))
        self.annot_mode_combo.currentIndexChanged.connect(self._on_annot_mode_changed)
        annot_layout.addRow("Mode:", self.annot_mode_combo)

        self.annot_top_n_spin = QSpinBox()
        self.annot_top_n_spin.setRange(1, 200)
        self.annot_top_n_spin.setValue(self.annotation_top_n)
        self.annot_top_n_spin.valueChanged.connect(self._update_plot)
        annot_layout.addRow("Top N genes:", self.annot_top_n_spin)

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

        self.annot_size_spin = QSpinBox()
        self.annot_size_spin.setRange(5, 20)
        self.annot_size_spin.setValue(self.annotation_label_size)
        self.annot_size_spin.valueChanged.connect(self._update_plot)
        annot_layout.addRow("Label size:", self.annot_size_spin)

        annot_group.setLayout(annot_layout)
        layout.addWidget(annot_group)
        self._on_annot_mode_changed()

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Slots ─────────────────────────────────────────────────────────────

    def _choose_color(self, color_type: str):
        cur = getattr(self, f'{color_type}_color')
        label = {'down': 'Down-regulation', 'up': 'Up-regulation', 'ns': 'Not Significant'}[color_type]
        color = QColorDialog.getColor(cur, self, f"Choose {label} Color")
        if color.isValid():
            setattr(self, f'{color_type}_color', color)
            btn = getattr(self, f'{color_type}_btn')
            btn.setStyleSheet(f"background-color: {color.name()};")
            self._saved_settings.update({
                'down_color': self.down_color,
                'up_color':   self.up_color,
                'ns_color':   self.ns_color,
            })
            self._update_plot()

    def _auto_x_range(self):
        df = self.dataset.dataframe
        if df is None or 'base_mean' not in df.columns:
            return
        x_vals = np.log2(df['base_mean'].clip(lower=1e-6).dropna())
        if len(x_vals) == 0:
            return
        margin = (x_vals.max() - x_vals.min()) * 0.05
        self.x_min_spin.blockSignals(True)
        self.x_max_spin.blockSignals(True)
        self.x_min_spin.setValue(float(x_vals.min()) - margin)
        self.x_max_spin.setValue(float(x_vals.max()) + margin)
        self.x_min_spin.blockSignals(False)
        self.x_max_spin.blockSignals(False)
        self._update_plot()

    def _auto_y_range(self):
        df = self.dataset.dataframe
        if df is None or 'log2fc' not in df.columns:
            return
        y_vals = df['log2fc'].dropna()
        if len(y_vals) == 0:
            return
        abs_max = float(y_vals.abs().max())
        margin = abs_max * 0.1
        self.y_min_spin.blockSignals(True)
        self.y_max_spin.blockSignals(True)
        self.y_min_spin.setValue(-(abs_max + margin))
        self.y_max_spin.setValue(  abs_max + margin)
        self.y_min_spin.blockSignals(False)
        self.y_max_spin.blockSignals(False)
        self._update_plot()

    def _on_figure_size_changed(self):
        self.fig_width  = self.width_spin.value()
        self.fig_height = self.height_spin.value()
        self._saved_settings.update({'fig_width': self.fig_width, 'fig_height': self.fig_height})
        self.figure.set_size_inches(self.fig_width, self.fig_height)
        self.canvas.draw()

    def _on_annot_mode_changed(self):
        idx = self.annot_mode_combo.currentIndex()
        if hasattr(self, 'annot_top_n_spin'):
            self.annot_top_n_spin.setEnabled(idx == 1)
            self.annot_load_btn.setEnabled(idx == 2)
            self.annot_file_label.setEnabled(idx == 2)
            self.annot_size_spin.setEnabled(idx != 0)
        if hasattr(self, 'figure'):
            self._update_plot()

    def _load_annotation_gene_list(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Gene List", "",
            "Text/CSV/TSV Files (*.txt *.csv *.tsv);;All Files (*)"
        )
        if not file_path:
            return
        try:
            genes = []
            with open(file_path, encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
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
                self._update_plot()
            else:
                QMessageBox.warning(self, "Empty File", "No gene names found in the file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load gene list:\n{e}")

    # ── Plot ──────────────────────────────────────────────────────────────

    def _do_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # sync settings from UI
        self.padj_threshold    = self.padj_spin.value()
        self.log2fc_threshold  = self.log2fc_spin.value()
        self.dot_size          = self.size_spin.value()
        self.x_min             = self.x_min_spin.value()
        self.x_max             = self.x_max_spin.value()
        self.y_min             = self.y_min_spin.value()
        self.y_max             = self.y_max_spin.value()

        if hasattr(self, 'annot_mode_combo'):
            _modes = ['none', 'top_n', 'custom']
            self.annotation_mode       = _modes[self.annot_mode_combo.currentIndex()]
            self.annotation_top_n      = self.annot_top_n_spin.value()
            self.annotation_label_size = self.annot_size_spin.value()

        self._saved_settings.update({
            'padj_threshold':         self.padj_threshold,
            'log2fc_threshold':       self.log2fc_threshold,
            'dot_size':               self.dot_size,
            'x_min':                  self.x_min,
            'x_max':                  self.x_max,
            'y_min':                  self.y_min,
            'y_max':                  self.y_max,
            'title':                  self.plot_title,
            'xlabel':                 self.plot_xlabel,
            'ylabel':                 self.plot_ylabel,
            'show_legend':            self.show_legend,
            'annotation_mode':        self.annotation_mode,
            'annotation_top_n':       self.annotation_top_n,
            'annotation_label_size':  self.annotation_label_size,
            'annotation_custom_genes': list(self.annotation_custom_genes),
        })

        df = self.dataset.dataframe
        if df is None or df.empty:
            ax.text(0.5, 0.5, 'No data available.', ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

        if 'base_mean' not in df.columns or 'log2fc' not in df.columns:
            missing = [c for c in ('base_mean', 'log2fc') if c not in df.columns]
            ax.text(0.5, 0.5,
                    f'Required columns not found:\n{", ".join(missing)}',
                    ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return

        df = df.copy()
        df['_x'] = np.log2(df['base_mean'].clip(lower=1e-6))
        df['_y'] = df['log2fc']

        df['_reg'] = 'ns'
        if 'adj_pvalue' in df.columns:
            up_mask   = (df['log2fc'] >=  self.log2fc_threshold) & (df['adj_pvalue'] <= self.padj_threshold)
            down_mask = (df['log2fc'] <= -self.log2fc_threshold) & (df['adj_pvalue'] <= self.padj_threshold)
            df.loc[up_mask,   '_reg'] = 'up'
            df.loc[down_mask, '_reg'] = 'down'

        scatter_collections = []
        for reg, color, label in [
            ('ns',   self.ns_color,   f"NS ({(df['_reg']=='ns').sum():,})"),
            ('down', self.down_color, f"Down ({(df['_reg']=='down').sum():,})"),
            ('up',   self.up_color,   f"Up ({(df['_reg']=='up').sum():,})"),
        ]:
            subset = df[df['_reg'] == reg]
            sc = ax.scatter(
                subset['_x'], subset['_y'],
                c=color.name(), s=self.dot_size, alpha=0.5,
                label=label,
                picker=(reg != 'ns'),
            )
            if reg != 'ns':
                scatter_collections.append((sc, subset))

        ax.axhline(0, color='black', linewidth=0.8, alpha=0.6)
        ax.axhline( self.log2fc_threshold, color='gray', linewidth=0.8,
                   linestyle='--', alpha=0.7)
        ax.axhline(-self.log2fc_threshold, color='gray', linewidth=0.8,
                   linestyle='--', alpha=0.7)

        ax.set_xlabel(self.plot_xlabel, fontsize=12)
        ax.set_ylabel(self.plot_ylabel, fontsize=12)
        ax.set_title(self.plot_title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        if self.x_min is not None and self.x_max is not None:
            ax.set_xlim(self.x_min, self.x_max)
        if self.y_min is not None and self.y_max is not None:
            ax.set_ylim(self.y_min, self.y_max)

        if self.show_legend:
            ax.legend(loc='upper right', fontsize=10)

        self._draw_gene_labels(ax, df)

        self.annot = ax.annotate(
            "", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w", alpha=0.9),
            arrowprops=dict(arrowstyle="->"),
            zorder=1000,
        )
        self.annot.set_visible(False)
        self._scatter_collections = scatter_collections

        self.canvas.mpl_connect('motion_notify_event', self._on_hover)
        self.canvas.draw()

    def _draw_gene_labels(self, ax, df):
        if not hasattr(self, 'annot_mode_combo'):
            return
        mode_idx = self.annot_mode_combo.currentIndex()
        if mode_idx == 0:
            return

        gene_col = None
        for col in ('nearest_gene', 'symbol', 'gene_id', 'peak_id'):
            if col in df.columns:
                gene_col = col
                break
        if gene_col is None:
            return

        label_size = self.annot_size_spin.value()
        sig = df[df['_reg'].isin(['up', 'down'])].copy()
        if sig.empty:
            return

        if mode_idx == 1:
            top_n = self.annot_top_n_spin.value()
            if 'adj_pvalue' in sig.columns:
                sig['_score'] = sig['log2fc'].abs() * (-np.log10(sig['adj_pvalue'].replace(0, 1e-300)))
            else:
                sig['_score'] = sig['log2fc'].abs()
            sig = sig.nlargest(top_n, '_score')
        else:
            if not self.annotation_custom_genes:
                return
            custom_upper = {g.upper() for g in self.annotation_custom_genes}
            sig = sig[sig[gene_col].astype(str).str.upper().isin(custom_upper)]
            if sig.empty:
                return

        for _, row in sig.iterrows():
            ax.annotate(
                str(row[gene_col]),
                xy=(row['_x'], row['_y']),
                fontsize=label_size,
                ha='left', va='bottom',
                xytext=(3, 3), textcoords='offset points',
            )

    def _on_hover(self, event):
        if event.inaxes is None or not hasattr(self, '_scatter_collections'):
            if hasattr(self, 'annot'):
                self.annot.set_visible(False)
                self.canvas.draw_idle()
            return

        found = False
        for sc, subset in self._scatter_collections:
            cont, ind = sc.contains(event)
            if cont:
                idx = ind['ind'][0]
                row = subset.iloc[idx]

                gene_col = next(
                    (c for c in ('nearest_gene', 'symbol', 'gene_id', 'peak_id')
                     if c in row.index),
                    None
                )
                gene_name = str(row[gene_col]) if gene_col else 'Unknown'
                padj_val  = row.get('adj_pvalue', float('nan'))
                base_mean = row.get('base_mean', float('nan'))

                text = (
                    f"Gene: {gene_name}\n"
                    f"log₂FC: {row['log2fc']:.3f}\n"
                    f"Mean acc: {base_mean:.1f}\n"
                    f"Padj: {padj_val:.2e}"
                )
                self.annot.xy = (row['_x'], row['_y'])
                self.annot.set_text(text)
                self.annot.set_visible(True)
                found = True
                break

        if not found:
            self.annot.set_visible(False)
        self.canvas.draw_idle()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "ma_plot_data.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
        )
        if not file_path:
            return
        try:
            df = self.dataset.dataframe
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Success", f"Data exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export data:\n{e}")
