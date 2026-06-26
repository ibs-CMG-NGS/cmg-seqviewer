"""
Gene Expression Bar + Scatter Visualization Dialog
"""

import re
from collections import OrderedDict
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QPushButton, QCheckBox, QMessageBox,
    QFormLayout, QColorDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
import matplotlib

from models.data_models import Dataset
from models.standard_columns import StandardColumns
from gui.base_plot_dialog import BasePlotDialog

# Import QSpinBox here so _setup_controls can use it
from PyQt6.QtWidgets import QSpinBox


_NON_SAMPLE_COLS = frozenset({
    'gene_id', 'symbol', 'gene_symbol', 'gene_name', 'genesymbol',
    'base_mean', 'basemean',
    'stat', 'statistic',
    'pvalue', 'p_value', 'p.value',
    'padj', 'p_adj', 'p.adj', 'adj_pvalue', 'adj_p',
    'qvalue', 'q_value', 'fdr',
    'log2fc', 'log2foldchange', 'log2_fold_change', 'lfc',
    'lfcse', 'se',
})

_SYMBOL_ALIASES = ('symbol', 'gene_symbol', 'gene_name', 'genesymbol')


def _p_to_stars(p: float) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return ''
    if p > 0.05:
        return 'ns'
    if p <= 1e-4:
        return '****'
    if p <= 1e-3:
        return '***'
    if p <= 1e-2:
        return '**'
    return '*'


class GeneExpressionBarDialog(BasePlotDialog):
    """유전자별 그룹 막대(mean) + scatter 다이얼로그."""

    def __init__(self, dataset: Dataset, parent=None, name_hint: str = None):
        self.dataset = dataset
        self.df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        self.name_hint = name_hint or dataset.name or ""

        lower_map = {str(c).lower(): c for c in self.df.columns}
        self.gene_col = None
        for alias in _SYMBOL_ALIASES:
            if alias in lower_map:
                self.gene_col = lower_map[alias]
                break
        if self.gene_col is None and 'gene_id' in lower_map:
            self.gene_col = lower_map['gene_id']

        self.sample_columns, initial_groups = self._resolve_sample_groups(
            dataset, self.df, self.name_hint)
        self.col_to_group: "OrderedDict[str, str]" = OrderedDict()
        for grp, cols in initial_groups.items():
            for c in cols:
                self.col_to_group[c] = grp
        for c in self.sample_columns:
            self.col_to_group.setdefault(c, c)

        self.sample_groups: "OrderedDict[str, List[str]]" = OrderedDict()
        self.group_colors: Dict[str, QColor] = {}
        self._rebuild_sample_groups()
        self._rebuild_group_colors()

        super().__init__("Gene Expression Bar + Scatter", parent, figsize=(10, 8))
        self._update_plot()

    # ── Sample / group resolution ─────────────────────────────────────────

    @staticmethod
    def _groups_from_name(name_hint: str, sample_columns: List[str]):
        if not name_hint or not sample_columns:
            return None
        norm = str(name_hint).replace('_', ' ')
        m = re.split(r'\bvs\b', norm, flags=re.IGNORECASE)
        if len(m) != 2:
            return None
        left = [t for t in m[0].strip().split() if t]
        right = [t for t in m[1].strip().split() if t]
        if not left or not right:
            return None
        candidates = [left[-1], right[0]]
        ranked = sorted(set(candidates), key=len, reverse=True)
        assign: "OrderedDict[str, List[str]]" = OrderedDict((c, []) for c in candidates)
        for col in sample_columns:
            cl = str(col).lower()
            chosen = next((c for c in ranked if c.lower() in cl), None)
            if chosen is None:
                return None
            assign[chosen].append(col)
        assign = OrderedDict((g, cols) for g, cols in assign.items() if cols)
        return assign if len(assign) >= 2 else None

    @staticmethod
    def _resolve_sample_groups(dataset: Dataset, df: pd.DataFrame, name_hint: str = ""):
        sample_columns: List[str] = list(dataset.metadata.get('sample_columns', []) or [])
        sample_groups: Dict[str, List[str]] = dict(dataset.metadata.get('sample_groups', {}) or {})

        if sample_columns:
            sample_columns = [c for c in sample_columns if c in df.columns]

        if not sample_columns and not df.empty:
            sample_columns = [
                c for c in df.columns
                if str(c).lower() not in _NON_SAMPLE_COLS
                and not str(c).startswith('_')
                and pd.api.types.is_numeric_dtype(df[c])
            ]

        if sample_columns and not sample_groups:
            named = GeneExpressionBarDialog._groups_from_name(name_hint, sample_columns)
            if named is not None:
                sample_groups = named

        if sample_columns and not sample_groups:
            groups: "OrderedDict[str, List[str]]" = OrderedDict()
            for col in sample_columns:
                m = re.match(r'(.+?)[._\-\s]*\d+$', str(col))
                grp = m.group(1).rstrip('._- ') if m else str(col)
                groups.setdefault(grp, []).append(col)
            sample_groups = groups

        if sample_groups:
            sample_groups = OrderedDict(
                (g, [c for c in cols if c in df.columns])
                for g, cols in sample_groups.items()
            )
            sample_groups = OrderedDict((g, cols) for g, cols in sample_groups.items() if cols)

        return sample_columns, sample_groups

    def _rebuild_sample_groups(self):
        groups: "OrderedDict[str, List[str]]" = OrderedDict()
        for col in self.sample_columns:
            grp = (self.col_to_group.get(col) or '').strip()
            if not grp:
                continue
            groups.setdefault(grp, []).append(col)
        self.sample_groups = groups

    def _default_color(self, idx: int) -> QColor:
        rgba = matplotlib.colormaps.get_cmap('tab10')(idx % 10)
        return QColor(int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255))

    def _rebuild_group_colors(self):
        new_colors: Dict[str, QColor] = {}
        for i, grp in enumerate(self.sample_groups.keys()):
            new_colors[grp] = self.group_colors.get(grp, self._default_color(i))
        self.group_colors = new_colors

    @property
    def has_data(self) -> bool:
        return bool(self.sample_groups) and self.gene_col is not None and not self.df.empty

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Chart Settings
        settings_group = QGroupBox("Chart Settings")
        settings_layout = QFormLayout()

        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(1, 60)
        self.top_n_spin.setValue(min(15, max(1, self._gene_total())))
        self.top_n_spin.valueChanged.connect(self._update_plot)
        settings_layout.addRow("Max genes:", self.top_n_spin)

        self.sort_combo = QComboBox()
        items = ["Original (input order)", "Symbol (A-Z)", "Mean expression (desc)"]
        if StandardColumns.LOG2FC in self.df.columns:
            items.append("|log2FC| (desc)")
        self.sort_combo.addItems(items)
        self.sort_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Sort genes by:", self.sort_combo)

        self.error_combo = QComboBox()
        self.error_combo.addItems(["SEM", "SD", "None"])
        self.error_combo.currentTextChanged.connect(self._update_plot)
        settings_layout.addRow("Error bars:", self.error_combo)

        self.points_check = QCheckBox("Show individual points")
        self.points_check.setChecked(True)
        self.points_check.toggled.connect(self._update_plot)
        settings_layout.addRow("", self.points_check)

        self.logy_check = QCheckBox("Log scale (Y)")
        self.logy_check.toggled.connect(self._update_plot)
        settings_layout.addRow("", self.logy_check)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Significance
        sig_group = QGroupBox("Significance")
        sig_layout = QFormLayout()

        self.sig_check = QCheckBox("Show significance stars")
        self.sig_check.toggled.connect(self._update_plot)
        sig_layout.addRow("", self.sig_check)

        self.ref_combo = QComboBox()
        self.ref_combo.currentTextChanged.connect(self._update_plot)
        sig_layout.addRow("Reference group:", self.ref_combo)

        self.test_combo = QComboBox()
        self.test_combo.addItems(["t-test (Welch)", "Mann-Whitney U"])
        self.test_combo.currentTextChanged.connect(self._update_plot)
        sig_layout.addRow("Test:", self.test_combo)

        sig_layout.addRow(QLabel("vs reference: * ≤.05  ** ≤.01\n*** ≤.001  **** ≤.0001  ns"))
        sig_group.setLayout(sig_layout)
        layout.addWidget(sig_group)
        self._rebuild_reference_combo()

        # Groups
        groups_box = QGroupBox("Sample Groups (editable)")
        groups_layout = QVBoxLayout()
        groups_layout.addWidget(QLabel("Edit group per sample, then Apply.\nEmpty group = exclude from plot."))

        self.group_table = QTableWidget()
        self.group_table.setColumnCount(2)
        self.group_table.setHorizontalHeaderLabels(["Sample", "Group"])
        self.group_table.verticalHeader().setVisible(False)
        self.group_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.group_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.group_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.group_table.setMaximumHeight(180)
        self._populate_group_table()
        groups_layout.addWidget(self.group_table)

        apply_btn = QPushButton("Apply Groups")
        apply_btn.clicked.connect(self._apply_group_table)
        groups_layout.addWidget(apply_btn)

        groups_box.setLayout(groups_layout)
        layout.addWidget(groups_box)

        # Group Colors (dynamic)
        self.colors_box = QGroupBox("Group Colors")
        self.colors_layout = QGridLayout()
        self.colors_box.setLayout(self.colors_layout)
        layout.addWidget(self.colors_box)
        self._rebuild_color_buttons()


    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    # ── Group / color / reference UI helpers ─────────────────────────────

    def _populate_group_table(self):
        self.group_table.setRowCount(len(self.sample_columns))
        for r, col in enumerate(self.sample_columns):
            sample_item = QTableWidgetItem(str(col))
            sample_item.setFlags(sample_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.group_table.setItem(r, 0, sample_item)
            self.group_table.setItem(r, 1, QTableWidgetItem(str(self.col_to_group.get(col, ''))))

    def _apply_group_table(self):
        for r, col in enumerate(self.sample_columns):
            item = self.group_table.item(r, 1)
            self.col_to_group[col] = (item.text().strip() if item else '')
        self._rebuild_sample_groups()
        if not self.sample_groups:
            QMessageBox.warning(self, "No Groups",
                                "All samples are excluded. Assign at least one group.")
        self._rebuild_group_colors()
        self._rebuild_color_buttons()
        self._rebuild_reference_combo()
        self._update_plot()

    def _rebuild_color_buttons(self):
        while self.colors_layout.count():
            item = self.colors_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for i, grp in enumerate(self.sample_groups.keys()):
            self.colors_layout.addWidget(QLabel(grp), i, 0)
            btn = QPushButton(self.group_colors[grp].name())
            btn.setStyleSheet(f"background-color: {self.group_colors[grp].name()};")
            btn.clicked.connect(lambda _checked=False, g=grp: self._choose_group_color(g))
            self.colors_layout.addWidget(btn, i, 1)

    def _choose_group_color(self, group: str):
        current = self.group_colors.get(group, QColor(70, 130, 180))
        color = QColorDialog.getColor(current, self, f"Color for '{group}'")
        if color.isValid():
            self.group_colors[group] = color
            self._rebuild_color_buttons()
            self._update_plot()

    def _rebuild_reference_combo(self):
        prev = self.ref_combo.currentText() if self.ref_combo.count() else None
        self.ref_combo.blockSignals(True)
        self.ref_combo.clear()
        self.ref_combo.addItems(list(self.sample_groups.keys()))
        if prev and prev in self.sample_groups:
            self.ref_combo.setCurrentText(prev)
        self.ref_combo.blockSignals(False)

    # ── Data helpers ──────────────────────────────────────────────────────

    def _gene_total(self) -> int:
        if self.gene_col is None or self.df.empty:
            return 1
        return int(self.df[self.gene_col].nunique())

    def _selected_genes_df(self) -> pd.DataFrame:
        df = self.df.copy()
        if self.gene_col is None:
            return df.iloc[0:0]

        df = df[df[self.gene_col].notna()]
        df = df.drop_duplicates(subset=self.gene_col, keep='first')

        all_sample_cols = [c for cols in self.sample_groups.values() for c in cols]
        df['_row_mean'] = df[all_sample_cols].mean(axis=1, numeric_only=True) if all_sample_cols else 0.0

        sort_by = self.sort_combo.currentText()
        if sort_by == "Mean expression (desc)":
            df = df.sort_values('_row_mean', ascending=False)
        elif sort_by == "|log2FC| (desc)" and StandardColumns.LOG2FC in df.columns:
            df = df.assign(_abs_fc=pd.to_numeric(df[StandardColumns.LOG2FC], errors='coerce').abs())
            df = df.sort_values('_abs_fc', ascending=False).drop(columns='_abs_fc')
        elif sort_by == "Symbol (A-Z)":
            df = df.sort_values(self.gene_col, ascending=True, key=lambda s: s.astype(str).str.lower())

        df = df.head(self.top_n_spin.value())
        return df.drop(columns='_row_mean', errors='ignore')

    @staticmethod
    def _vals(row, cols) -> np.ndarray:
        return pd.to_numeric(pd.Series([row[c] for c in cols]), errors='coerce').dropna().to_numpy()

    def _compute_pvalue(self, a: np.ndarray, b: np.ndarray) -> float:
        if a.size < 2 or b.size < 2:
            return float('nan')
        try:
            from scipy import stats
            if self.test_combo.currentText().startswith("Mann"):
                _, p = stats.mannwhitneyu(a, b, alternative='two-sided')
            else:
                _, p = stats.ttest_ind(a, b, equal_var=False)
            return float(p)
        except Exception:
            return float('nan')

    # ── Plot ──────────────────────────────────────────────────────────────

    def _message(self, text: str):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, text, ha='center', va='center', fontsize=13)
        ax.axis('off')
        self.canvas.draw()

    def _do_plot(self):
        self.figure.clear()

        if not self.has_data:
            self._message("No sample columns / groups.\n"
                          "Assign at least one group in 'Sample Groups'.")
            return

        df = self._selected_genes_df()
        if df.empty:
            self._message("No genes to display.")
            return

        genes = df[self.gene_col].astype(str).to_list()
        group_items: List[Tuple[str, List[str]]] = list(self.sample_groups.items())
        n_genes = len(genes)
        n_groups = len(group_items)

        x = np.arange(n_genes)
        total_width = 0.8
        bar_width = total_width / max(1, n_groups)
        rng = np.random.default_rng(0)

        err_mode = self.error_combo.currentText()
        show_points = self.points_check.isChecked()
        is_log = self.logy_check.isChecked()

        ax = self.figure.add_subplot(111)

        bar_center: Dict[Tuple[int, int], float] = {}
        bar_top: Dict[Tuple[int, int], float] = {}
        global_top = 0.0

        for gi, (gname, cols) in enumerate(group_items):
            offset = (gi - (n_groups - 1) / 2.0) * bar_width
            centers = x + offset
            color = self.group_colors.get(gname, self._default_color(gi)).name()

            means, errs, tops = [], [], []
            for _, row in df.iterrows():
                vals = self._vals(row, cols)
                if vals.size == 0:
                    means.append(np.nan); errs.append(0.0); tops.append(0.0)
                    continue
                m = float(np.mean(vals))
                if err_mode == "SD":
                    e = float(np.std(vals, ddof=1)) if vals.size > 1 else 0.0
                elif err_mode == "SEM":
                    e = float(np.std(vals, ddof=1) / np.sqrt(vals.size)) if vals.size > 1 else 0.0
                else:
                    e = 0.0
                means.append(m); errs.append(e)
                tops.append(max(m + e, float(np.max(vals))))

            yerr = errs if err_mode != "None" else None
            ax.bar(centers, means, width=bar_width * 0.92, color=color,
                   edgecolor='black', linewidth=0.5, label=gname,
                   yerr=yerr, capsize=3, error_kw={'elinewidth': 0.8})

            for ci in range(n_genes):
                bar_center[(gi, ci)] = centers[ci]
                bar_top[(gi, ci)] = tops[ci]
                if tops[ci] > global_top:
                    global_top = tops[ci]

            if show_points:
                for ci, (_, row) in enumerate(df.iterrows()):
                    vals = self._vals(row, cols)
                    if vals.size == 0:
                        continue
                    jitter = (rng.random(vals.size) - 0.5) * bar_width * 0.5
                    ax.scatter(np.full(vals.size, centers[ci]) + jitter, vals,
                               s=18, color='black', alpha=0.7, zorder=3,
                               edgecolors='white', linewidths=0.3)

        if self.sig_check.isChecked() and n_groups >= 2:
            ref_name = self.ref_combo.currentText()
            if ref_name in self.sample_groups:
                ref_idx = list(self.sample_groups.keys()).index(ref_name)
                ref_cols = self.sample_groups[ref_name]
                y_off = (global_top * 0.04) if global_top > 0 else 0.5
                for ci, (_, row) in enumerate(df.iterrows()):
                    ref_vals = self._vals(row, ref_cols)
                    for gi, (gname, cols) in enumerate(group_items):
                        if gi == ref_idx:
                            continue
                        p = self._compute_pvalue(self._vals(row, cols), ref_vals)
                        star = _p_to_stars(p)
                        if not star:
                            continue
                        cx = bar_center[(gi, ci)]
                        top = bar_top[(gi, ci)]
                        ty = top * 1.08 if is_log else top + y_off
                        ax.text(cx, ty, star, ha='center', va='bottom', color='black')
                if not is_log and global_top > 0:
                    ax.set_ylim(top=global_top * 1.25)

        ax.set_xticks(x)
        ax.set_xticklabels(genes, rotation=45, ha='right')
        ax.set_ylabel("Expression (raw count)", fontweight='bold')
        gene_label = genes[0] if len(genes) == 1 else self.name_hint or "Gene Expression"
        ax.set_title(f"{gene_label} — Expression by Group" if len(genes) == 1 else "Gene Expression by Group", fontweight='bold')
        if is_log:
            ax.set_yscale('log')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.legend(title="Group")

        self.figure.tight_layout()
        self.canvas.draw()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_data(self):
        from PyQt6.QtWidgets import QFileDialog

        if not self.has_data:
            QMessageBox.warning(self, "No Data", "Nothing to export.")
            return

        df = self._selected_genes_df()
        ref_name = self.ref_combo.currentText() if self.ref_combo.count() else None
        rows = []
        for _, row in df.iterrows():
            gene = row[self.gene_col]
            ref_vals = self._vals(row, self.sample_groups[ref_name]) if ref_name in self.sample_groups else np.array([])
            for gname, cols in self.sample_groups.items():
                vals = self._vals(row, cols)
                n = int(vals.size)
                mean = float(np.mean(vals)) if n else np.nan
                sd = float(np.std(vals, ddof=1)) if n > 1 else 0.0
                sem = sd / np.sqrt(n) if n > 1 else 0.0
                if ref_name and gname != ref_name and ref_vals.size:
                    p = self._compute_pvalue(vals, ref_vals)
                else:
                    p = np.nan
                rows.append({'gene': gene, 'group': gname, 'n': n,
                             'mean': mean, 'sd': sd, 'sem': sem,
                             'p_vs_ref': p, 'stars': _p_to_stars(p)})
        out = pd.DataFrame(rows)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data",
            f"gene_expression_bar_data_{self.dataset.name}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
        )
        if not file_path:
            return
        if file_path.endswith('.xlsx'):
            out.to_excel(file_path, index=False)
        else:
            out.to_csv(file_path, index=False)
        QMessageBox.information(self, "Success", f"Data exported to:\n{file_path}")
