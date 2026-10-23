"""Gene Expression Distribution Dialog — violin / box / strip.

`expression_distribution` (pseudobulk 또는 quantile) long-format 데이터셋을
gene × cell type 별로 시각화한다. pseudobulk는 sample/replicate 값을 사용하고,
quantile은 p10–p90 box/range로 표시한다.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QCompleter, QDoubleSpinBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
)

from gui.base_plot_dialog import BasePlotDialog
from plots.expression_distribution import render_expression_distribution
from utils.export_paths import remembered_save_path


class ExpressionDistributionDialog(BasePlotDialog):
    """Gene expression distribution 탐색 다이얼로그."""

    def __init__(self, dataset, parent=None, initial_genes=None):
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset
        self.df = (dataset.dataframe.copy()
                   if dataset.dataframe is not None else pd.DataFrame())
        self.md = dataset.metadata or {}
        self.schema = self.md.get('distribution_schema') or {}

        self.gene_id_col = 'gene_id' if 'gene_id' in self.df.columns else self.df.columns[0]
        self.gene_name_col = 'gene_name' if 'gene_name' in self.df.columns else self.gene_id_col
        self.cell_type_col = 'cell_type'
        self.value_col = 'mean_expression'
        self.layout = str(self.md.get('layout') or self.schema.get('layout') or 'pseudobulk')
        self.pct_scale = self.md.get('pct_scale') or self.schema.get('pct_scale') or '0-1'
        self.cell_types: List[str] = list(self.md.get('cell_types', []) or [])
        if not self.cell_types:
            self.cell_types = list(dict.fromkeys(
                self.df[self.cell_type_col].dropna().astype(str))) \
                if self.cell_type_col in self.df.columns else []

        self._gene_rows = self._build_gene_rows()
        self._gene_key_to_id: Dict[str, str] = {}
        for row in self._gene_rows:
            for key in (row.get('gene_id'), row.get('gene_name')):
                if key:
                    self._gene_key_to_id.setdefault(str(key).lower(), str(row['gene_id']))
        self._initial_genes = [str(g) for g in (initial_genes or []) if str(g).strip()]
        self._selected_genes = self._seed_genes()
        self._current_plot_df: Optional[pd.DataFrame] = None

        super().__init__(f"Expression Distribution — {dataset.name}",
                         parent, figsize=(13, 8))
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._update_plot)
        self._update_plot()

    # ── Data helpers ────────────────────────────────────────────────────

    def _build_gene_rows(self) -> List[dict]:
        gene_index = self.md.get('gene_index')
        if isinstance(gene_index, pd.DataFrame) and not gene_index.empty:
            df = gene_index.copy()
            if 'gene_id' not in df.columns:
                df = df.rename(columns={df.columns[0]: 'gene_id'})
            if 'gene_name' not in df.columns:
                df['gene_name'] = df.get('symbol', df['gene_id'])
            if 'max_mean' not in df.columns and 'max_mean_expression' in df.columns:
                df['max_mean'] = df['max_mean_expression']
            if 'max_pct' not in df.columns and 'max_pct_expressing' in df.columns:
                df['max_pct'] = df['max_pct_expressing']
            sort_col = 'max_mean' if 'max_mean' in df.columns else 'gene_name'
            df = df.sort_values(sort_col, ascending=False, na_position='last')
            return df.to_dict('records')
        if self.df.empty:
            return []
        rows = (self.df.groupby(self.gene_id_col, dropna=True)
                .agg(gene_name=(self.gene_name_col, 'first'),
                     max_mean=(self.value_col, 'max'))
                .reset_index()
                .sort_values('max_mean', ascending=False))
        return rows.to_dict('records')

    def _seed_genes(self) -> List[str]:
        if self._initial_genes:
            out = []
            for gene in self._initial_genes:
                gid = self._gene_key_to_id.get(gene.lower())
                if gid and gid not in out:
                    out.append(gid)
            if out:
                return out
        return [str(self._gene_rows[0]['gene_id'])] if self._gene_rows else []

    def _selected_cell_types(self) -> List[str]:
        return [self.cell_type_list.item(i).text()
                for i in range(self.cell_type_list.count())
                if self.cell_type_list.item(i).isSelected()]

    def _rank_cell_types(self) -> List[str]:
        if not self.cell_types:
            return []
        if not self._selected_genes or self.df.empty:
            return list(self.cell_types)
        wanted = {g.lower() for g in self._selected_genes}
        ids = self.df[self.gene_id_col].astype(str).str.lower()
        names = (self.df[self.gene_name_col].astype(str).str.lower()
                 if self.gene_name_col in self.df.columns else ids)
        sub = self.df[ids.isin(wanted) | names.isin(wanted)]
        if sub.empty:
            return list(self.cell_types)
        means = (sub.groupby(self.cell_type_col)[self.value_col]
                 .mean().sort_values(ascending=False))
        ordered = [str(c) for c in means.index if str(c) in self.cell_types]
        ordered += [c for c in self.cell_types if c not in ordered]
        return ordered

    def _select_top10_cell_types(self) -> None:
        if not hasattr(self, 'cell_type_list'):
            return
        top = {str(c) for c in self._rank_cell_types()[:10]}
        self.cell_type_list.blockSignals(True)
        for i in range(self.cell_type_list.count()):
            item = self.cell_type_list.item(i)
            item.setSelected(item.text() in top)
        self.cell_type_list.blockSignals(False)
        self._update_plot()

    # ── Controls ────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        gene_group = QGroupBox("Genes")
        gv = QVBoxLayout()
        self.gene_search = QLineEdit()
        self.gene_search.setPlaceholderText("Search gene_id / gene_name and press Enter")
        completer = QCompleter(sorted(
            ({str(r.get('gene_name', '')) for r in self._gene_rows} |
             {str(r.get('gene_id', '')) for r in self._gene_rows}) - {''}))
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.gene_search.setCompleter(completer)
        self.gene_search.returnPressed.connect(self._add_gene_from_search)
        gv.addWidget(self.gene_search)

        add_btn = QPushButton("Add gene")
        add_btn.clicked.connect(self._add_gene_from_search)
        gv.addWidget(add_btn)

        self.selected_genes = QListWidget()
        self.selected_genes.setMaximumHeight(105)
        self.selected_genes.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        gv.addWidget(self.selected_genes)

        self.gene_info_label = QLabel("")
        self.gene_info_label.setWordWrap(True)
        self.gene_info_label.setStyleSheet("color: #555555; font-size: 8pt;")
        gv.addWidget(self.gene_info_label)

        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #a05a00; font-size: 8pt;")
        gv.addWidget(self.warning_label)

        row = QHBoxLayout()
        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self._remove_selected_genes)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_genes)
        row.addWidget(remove_btn)
        row.addWidget(clear_btn)
        gv.addLayout(row)
        gene_group.setLayout(gv)
        layout.addWidget(gene_group)

        ct_group = QGroupBox("Cell types")
        cv = QVBoxLayout()
        self.cell_type_list = QListWidget()
        self.cell_type_list.setMaximumHeight(165)
        self.cell_type_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        for ct in self._rank_cell_types():
            self.cell_type_list.addItem(QListWidgetItem(str(ct)))
        self.cell_type_list.itemSelectionChanged.connect(self._update_plot)
        cv.addWidget(self.cell_type_list)

        ct_btns = QHBoxLayout()
        top10_btn = QPushButton("Top 10 by mean")
        top10_btn.clicked.connect(self._select_top10_cell_types)
        all_btn = QPushButton("Select all")
        all_btn.clicked.connect(self.cell_type_list.selectAll)
        none_btn = QPushButton("Clear")
        none_btn.clicked.connect(self.cell_type_list.clearSelection)
        ct_btns.addWidget(top10_btn)
        ct_btns.addWidget(all_btn)
        ct_btns.addWidget(none_btn)
        cv.addLayout(ct_btns)
        ct_group.setLayout(cv)
        layout.addWidget(ct_group)

        disp_group = QGroupBox("Distribution")
        form = QFormLayout()

        self.group_combo = QComboBox()
        for label, col in (("Condition", "condition"), ("Dataset", "dataset"),
                           ("Sample", "sample")):
            if col in self.df.columns and self.df[col].notna().any():
                self.group_combo.addItem(label, col)
        if self.group_combo.count() == 0:
            self.group_combo.addItem("All", "")
        form.addRow("Group by:", self.group_combo)

        self.plot_combo = QComboBox()
        self.plot_combo.addItems(["Violin", "Box", "Strip", "Box + points"])
        if self.layout == 'quantile':
            self.plot_combo.setCurrentText("Box")
            self.plot_combo.setToolTip(
                "Quantile layout has no cell-level values; violin is disabled.")
        form.addRow("Plot type:", self.plot_combo)
        self.plot_combo.currentIndexChanged.connect(self._on_plot_type_changed)

        self.min_ncells_spin = QDoubleSpinBox()
        self.min_ncells_spin.setRange(0.0, 1e9)
        self.min_ncells_spin.setDecimals(0)
        self.min_ncells_spin.setValue(0.0)
        form.addRow("Min n_cells:", self.min_ncells_spin)

        self.min_pct_spin = QDoubleSpinBox()
        self.min_pct_spin.setRange(0.0, 100.0)
        self.min_pct_spin.setDecimals(1)
        self.min_pct_spin.setValue(0.0)
        form.addRow("Min % expressing:", self.min_pct_spin)

        self.label_limit_spin = QSpinBox()
        self.label_limit_spin.setRange(8, 120)
        self.label_limit_spin.setValue(40)
        form.addRow("Label length:", self.label_limit_spin)

        self.log_check = QCheckBox("Log scale (y)")
        form.addRow("", self.log_check)

        disp_group.setLayout(form)
        layout.addWidget(disp_group)

        for w in (self.min_ncells_spin, self.min_pct_spin, self.label_limit_spin):
            w.valueChanged.connect(self._update_plot)
        self.log_check.toggled.connect(self._update_plot)
        self.group_combo.currentIndexChanged.connect(self._update_plot)

        self._selected_genes = getattr(self, '_selected_genes', [])
        for gid in self._selected_genes:
            self.selected_genes.addItem(str(gid))
        self._update_gene_info()
        self._select_top10_cell_types()

    def _on_plot_type_changed(self):
        if self.layout == 'quantile' and self.plot_combo.currentText() == 'Violin':
            self.plot_combo.setCurrentText('Box')
        self._update_plot()

    # ── Gene selection ──────────────────────────────────────────────────

    def _add_gene_from_search(self):
        text = self.gene_search.text().strip()
        if not text:
            return
        key = text.lower()
        gid = self._gene_key_to_id.get(key)
        if gid is None:
            matches = [r['gene_id'] for r in self._gene_rows
                       if key in str(r.get('gene_id', '')).lower()
                       or key in str(r.get('gene_name', '')).lower()]
            if len(matches) == 1:
                gid = matches[0]
            elif len(matches) > 1:
                QMessageBox.information(
                    self, "Multiple matches",
                    f"{len(matches)} genes match '{text}'. Refine the search.")
                return
        if gid is None:
            QMessageBox.warning(self, "Not found", f"No gene matches '{text}'.")
            return
        gid = str(gid)
        if gid not in self._selected_genes:
            self._selected_genes.append(gid)
            self.selected_genes.addItem(gid)
        self.gene_search.clear()
        self._update_gene_info()
        self._refresh_cell_type_order()
        self._update_plot()

    def _remove_selected_genes(self):
        for item in self.selected_genes.selectedItems():
            text = item.text()
            if text in self._selected_genes:
                self._selected_genes.remove(text)
            self.selected_genes.takeItem(self.selected_genes.row(item))
        self._update_gene_info()
        self._refresh_cell_type_order()
        self._update_plot()

    def _clear_genes(self):
        self._selected_genes.clear()
        self.selected_genes.clear()
        self._update_gene_info()
        self._refresh_cell_type_order()
        self._update_plot()

    def _refresh_cell_type_order(self):
        """선택 gene 기준으로 cell type 목록 순서를 갱신하되 선택 상태는 유지."""
        if not hasattr(self, 'cell_type_list'):
            return
        selected = set(self._selected_cell_types())
        ranked = self._rank_cell_types()
        self.cell_type_list.blockSignals(True)
        self.cell_type_list.clear()
        for ct in ranked:
            item = QListWidgetItem(str(ct))
            self.cell_type_list.addItem(item)
            item.setSelected(str(ct) in selected)
        self.cell_type_list.blockSignals(False)

    def _update_gene_info(self) -> None:
        if not self._selected_genes:
            self.gene_info_label.setText("")
            return
        gid = str(self._selected_genes[0])
        row = next((r for r in self._gene_rows
                    if str(r.get('gene_id')) == gid), None)
        if row is None:
            self.gene_info_label.setText(gid)
            return
        parts = [f"{row.get('gene_name', gid)} ({gid})"]
        for key, label in (('max_mean', 'max mean'), ('max_pct', 'max pct'),
                           ('n_cell_types_detected', 'n cell types')):
            if key in row and pd.notna(row.get(key)):
                try:
                    parts.append(f"{label}={float(row[key]):.4g}")
                except (TypeError, ValueError):
                    parts.append(f"{label}={row[key]}")
        self.gene_info_label.setText("  |  ".join(parts))

    # ── Plot ────────────────────────────────────────────────────────────

    def _fit_figure_to_canvas(self, n_genes: int = 1) -> None:
        try:
            w = self.canvas.width() / max(self.figure.dpi, 1)
            h = self.canvas.height() / max(self.figure.dpi, 1)
            if w > 2 and h > 2:
                self.figure.set_size_inches(w, max(h, 2.6 * max(n_genes, 1)))
        except Exception:
            pass

    def _filtered_df(self) -> pd.DataFrame:
        if self.df.empty:
            return self.df
        out = self.df
        if self._selected_genes:
            wanted = {g.lower() for g in self._selected_genes}
            ids = out[self.gene_id_col].astype(str).str.lower()
            names = (out[self.gene_name_col].astype(str).str.lower()
                     if self.gene_name_col in out.columns else ids)
            out = out[ids.isin(wanted) | names.isin(wanted)]
        selected_ct = self._selected_cell_types()
        if selected_ct:
            out = out[out[self.cell_type_col].astype(str).isin(set(selected_ct))]
        if self.min_ncells_spin.value() > 0 and 'n_cells' in out.columns:
            out = out[pd.to_numeric(out['n_cells'], errors='coerce').fillna(0)
                      >= self.min_ncells_spin.value()]
        if self.min_pct_spin.value() > 0 and 'pct_expressing' in out.columns:
            from plots.expression_distribution import _pct_factor
            pct = (pd.to_numeric(out['pct_expressing'], errors='coerce').fillna(0)
                   * _pct_factor(self.pct_scale))
            out = out[pct >= self.min_pct_spin.value()]
        return out

    def _plot_params(self) -> dict:
        plot_type = self.plot_combo.currentText().lower()
        plot_type = {
            'violin': 'violin', 'box': 'box', 'strip': 'strip',
            'box + points': 'box+points',
        }.get(plot_type, 'violin')
        return {
            'genes': list(self._selected_genes),
            'cell_types': self._selected_cell_types(),
            'group_by': self.group_combo.currentData() or '',
            'plot_type': plot_type,
            'layout': self.layout,
            'value_column': self.value_col,
            'pct_scale': self.pct_scale,
            'min_n_cells': self.min_ncells_spin.value(),
            'min_pct': self.min_pct_spin.value(),
            'label_limit': self.label_limit_spin.value(),
            'log_scale': self.log_check.isChecked(),
            'xlabel': 'Cell type',
            'ylabel': 'Expression',
        }

    def _do_plot(self):
        self.figure.clear()
        if not self._selected_genes:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Search and add at least one gene.',
                    ha='center', va='center', transform=ax.transAxes,
                    color='#666666')
            self._current_plot_df = self.df.iloc[0:0]
            self.warning_label.setText("")
            return
        if not self._selected_cell_types():
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Select at least one cell type.',
                    ha='center', va='center', transform=ax.transAxes,
                    color='#666666')
            self._current_plot_df = self.df.iloc[0:0]
            self.warning_label.setText("")
            return
        self._current_plot_df = self._filtered_df()
        n_genes = max(len(self._selected_genes), 1)
        self._fit_figure_to_canvas(n_genes)
        params = self._plot_params()
        info = render_expression_distribution(
            self.figure, self._current_plot_df, params)
        try:
            self.figure.tight_layout()
        except Exception:
            pass
        self.warning_label.setText(" ".join(info.get('warnings') or []))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_resize_timer'):
            self._resize_timer.start(120)

    # ── Export / bundle ─────────────────────────────────────────────────

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    def _export_data(self):
        df = self._current_plot_df
        if not isinstance(df, pd.DataFrame) or df.empty:
            QMessageBox.information(
                self, "No Data", "Nothing to export with the current filters.")
            return
        path, _ = remembered_save_path(
            self, "Export Expression Distribution",
            f"{self.dataset.name}_distribution.csv",
            "CSV (*.csv);;TSV (*.tsv);;Excel (*.xlsx)")
        if not path:
            return
        try:
            if path.lower().endswith('.xlsx'):
                df.to_excel(path, index=False)
            elif path.lower().endswith('.tsv'):
                df.to_csv(path, index=False, sep='\t')
            else:
                df.to_csv(path, index=False)
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export failed", str(exc))

    def get_bundle_context(self) -> dict:
        df = self._current_plot_df if isinstance(self._current_plot_df, pd.DataFrame) \
            else self._filtered_df()
        slug = str(self.dataset.name).replace(' ', '_')
        return {
            'figure': self.figure,
            'dataframe': df,
            'plot_params': self._plot_params(),
            'dataset_name': self.dataset.name,
            'plot_type': 'expression_distribution',
            'figure_title': f"Expression Distribution — {self.dataset.name}",
            'figure_slug': f"{slug}_expression_distribution",
            'source_stem': f"{slug}_expression_distribution",
            'notes': 'Generated from cmg-seqviewer Expression Distribution view.',
        }
