"""Expression Summary Dialog — gene × cell-type dot plot / top-N heatmap.

HypoMap 등 wide mean/pct 행렬(`gene_id`, `gene_name`, 세포타입 컬럼)과
companion(gene_index, pct, cell_type_summary)을 시각화한다.
"""
from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QCompleter, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
)

from gui.base_plot_dialog import BasePlotDialog
from plots.expression_dot import build_expression_long, render_expression_dot
from utils.export_paths import remembered_save_path


class ExpressionSummaryDialog(BasePlotDialog):
    """Gene × cell-type expression 탐색 다이얼로그."""

    def __init__(self, dataset, parent=None):
        self.logger = logging.getLogger(__name__)
        self.dataset = dataset
        self.wide_df = dataset.dataframe.copy() if dataset.dataframe is not None else pd.DataFrame()
        md = dataset.metadata or {}
        self.gene_id_col = 'gene_id' if 'gene_id' in self.wide_df.columns else self.wide_df.columns[0]
        self.gene_name_col = 'gene_name' if 'gene_name' in self.wide_df.columns else self.gene_id_col
        self.cell_types: List[str] = list(md.get('cell_types', []) or [])
        if not self.cell_types:
            from utils.expression_summary_loader import _NON_CELL_TYPE_COLUMNS
            self.cell_types = [c for c in self.wide_df.columns
                               if str(c).lower() not in _NON_CELL_TYPE_COLUMNS
                               and pd.api.types.is_numeric_dtype(self.wide_df[c])]
        self.pct_df = md.get('pct_matrix')
        self.cell_type_summary = md.get('cell_type_summary')
        self.n_cells = self._n_cells_map(self.cell_type_summary)
        self.pct_scale = md.get('pct_scale', '0-1')
        self._current_long: pd.DataFrame | None = None
        self._hover_ax = None
        self._hover_points: List[dict] = []

        self._gene_rows = self._build_gene_rows(md.get('gene_index'))
        self._gene_key_to_id: Dict[str, str] = {}
        for row in self._gene_rows:
            for key in (row.get('gene_id'), row.get('gene_name')):
                if key:
                    self._gene_key_to_id.setdefault(str(key).lower(), str(row['gene_id']))
        self._selected_genes: List[str] = []
        if self._gene_rows:
            self._selected_genes.append(str(self._gene_rows[0]['gene_id']))

        super().__init__(f"Expression Summary — {dataset.name}", parent, figsize=(13, 8))
        self.canvas.mpl_connect('motion_notify_event', self._on_hover)
        self._update_plot()

    # ── Data helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _n_cells_map(summary_df) -> Dict[str, float]:
        if not isinstance(summary_df, pd.DataFrame) or summary_df.empty:
            return {}
        ct_col = 'cell_type' if 'cell_type' in summary_df.columns else None
        n_col = 'n_cells' if 'n_cells' in summary_df.columns else None
        if not ct_col or not n_col:
            return {}
        df = summary_df.dropna(subset=[ct_col, n_col]).copy()
        df[n_col] = pd.to_numeric(df[n_col], errors='coerce')
        df = df.dropna(subset=[n_col])
        out = {}
        # wide의 cell type 컬럼이 "cell_type || dataset" 형태면 combined 키도 채운다.
        if 'dataset' in df.columns and df['dataset'].notna().any():
            combined = (df[ct_col].astype(str) + ' || ' + df['dataset'].astype(str))
            for key, val in df.assign(_label=combined).groupby('_label')[n_col].sum().items():
                out[str(key)] = float(val)
        # dataset별 행이 여러 개면 cell type 총 n_cells로 합산한다.
        for key, val in df.groupby(ct_col)[n_col].sum().items():
            out[str(key)] = float(val)
        return out

    @staticmethod
    def _cell_type_summary_map(summary_df) -> Dict[str, dict]:
        if not isinstance(summary_df, pd.DataFrame) or 'cell_type' not in summary_df.columns:
            return {}
        keys = ('n_cells', 'n_genes_detected', 'n_datasets', 'top_dataset',
                'top_dataset_n', 'top_dataset_frac', 'dataset_confined')
        out = {}
        for _, row in summary_df.iterrows():
            ct = str(row.get('cell_type'))
            if ct == 'nan':
                continue
            info = {k: row.get(k) for k in keys if k in summary_df.columns}
            out[ct] = info
            if 'dataset' in summary_df.columns and pd.notna(row.get('dataset')):
                out[f"{ct} || {row.get('dataset')}"] = info
        return out

    def _build_gene_rows(self, gene_index) -> List[dict]:
        if isinstance(gene_index, pd.DataFrame) and not gene_index.empty:
            df = gene_index.copy()
            if 'gene_id' not in df.columns:
                df = df.rename(columns={df.columns[0]: 'gene_id'})
            if 'gene_name' not in df.columns:
                df['gene_name'] = df.get('symbol', df['gene_id'])
            # HypoMap export는 max_mean_expression / max_pct_expressing 이름을 쓴다.
            if 'max_mean' not in df.columns and 'max_mean_expression' in df.columns:
                df['max_mean'] = df['max_mean_expression']
            if 'max_pct' not in df.columns and 'max_pct_expressing' in df.columns:
                df['max_pct'] = df['max_pct_expressing']
            sort_col = 'max_mean' if 'max_mean' in df.columns else 'gene_name'
            df = df.sort_values(sort_col, ascending=False, na_position='last')
            return df.to_dict('records')
        df = self.wide_df[[self.gene_id_col]]
        if self.gene_name_col in self.wide_df.columns and self.gene_name_col != self.gene_id_col:
            df = df.assign(gene_name=self.wide_df[self.gene_name_col])
        else:
            df = df.assign(gene_name=df[self.gene_id_col])
        return df.rename(columns={self.gene_id_col: 'gene_id'}).to_dict('records')

    def _n_cells_for_selected(self) -> Dict[str, float]:
        return {ct: self.n_cells.get(ct, np.nan) for ct in self.cell_types}

    # ── Controls ──────────────────────────────────────────────────────────

    def _setup_controls(self, layout: QVBoxLayout):
        # Gene search
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
        self.selected_genes.setMaximumHeight(110)
        self.selected_genes.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        gv.addWidget(self.selected_genes)

        self.gene_info_label = QLabel("")
        self.gene_info_label.setWordWrap(True)
        self.gene_info_label.setStyleSheet("color: #555555; font-size: 8pt;")
        gv.addWidget(self.gene_info_label)

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

        # Cell types
        ct_group = QGroupBox("Cell types")
        cv = QVBoxLayout()
        self.cell_type_list = QListWidget()
        self.cell_type_list.setMaximumHeight(160)
        self.cell_type_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        summary_map = self._cell_type_summary_map(self.cell_type_summary)
        for ct in self.cell_types:
            item = QListWidgetItem(str(ct))
            tip = str(ct)
            info = summary_map.get(str(ct))
            if info:
                parts = [f"{k}={v}" for k, v in info.items() if v is not None and str(v) != '']
                if parts:
                    tip += "\n" + " | ".join(parts)
            item.setToolTip(tip)
            self.cell_type_list.addItem(item)
        self.cell_type_list.selectAll()
        self.cell_type_list.itemSelectionChanged.connect(self._on_cell_type_changed)
        cv.addWidget(self.cell_type_list)

        ct_btns = QHBoxLayout()
        all_btn = QPushButton("Select all")
        all_btn.clicked.connect(self.cell_type_list.selectAll)
        none_btn = QPushButton("Clear")
        none_btn.clicked.connect(self.cell_type_list.clearSelection)
        ct_btns.addWidget(all_btn)
        ct_btns.addWidget(none_btn)
        cv.addLayout(ct_btns)
        ct_group.setLayout(cv)
        layout.addWidget(ct_group)

        # Display / filters
        disp_group = QGroupBox("Display")
        form = QFormLayout()
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Dot plot", "Top-N heatmap"])
        self.view_combo.currentIndexChanged.connect(self._on_view_changed)
        form.addRow("View:", self.view_combo)

        self.top_cell_spin = QSpinBox()
        self.top_cell_spin.setRange(1, 500)
        self.top_cell_spin.setValue(max(1, min(50, len(self.cell_types))))
        self.top_cell_spin.setToolTip("0 = all selected cell types")
        self.top_cell_spin.setSpecialValueText("All")
        self.top_cell_spin.setMinimum(0)
        form.addRow("Top cell types:", self.top_cell_spin)

        self.min_pct_spin = QDoubleSpinBox()
        self.min_pct_spin.setRange(0.0, 100.0)
        self.min_pct_spin.setDecimals(1)
        self.min_pct_spin.setValue(0.0)
        form.addRow("Min % expressing:", self.min_pct_spin)

        self.min_ncells_spin = QDoubleSpinBox()
        self.min_ncells_spin.setRange(0.0, 1e9)
        self.min_ncells_spin.setDecimals(0)
        self.min_ncells_spin.setValue(0.0)
        self.min_ncells_spin.setToolTip("cell type n_cells below this is greyed out")
        form.addRow("Min n_cells:", self.min_ncells_spin)

        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(["viridis", "plasma", "RdBu_r", "coolwarm", "magma"])
        form.addRow("Colormap:", self.cmap_combo)

        self.label_limit_spin = QSpinBox()
        self.label_limit_spin.setRange(8, 80)
        self.label_limit_spin.setValue(32)
        form.addRow("Label length:", self.label_limit_spin)

        self.norm_combo = QComboBox()
        self.norm_combo.addItems(["Z-score", "None (raw)"])
        form.addRow("Heatmap norm:", self.norm_combo)

        disp_group.setLayout(form)
        layout.addWidget(disp_group)

        for w in (self.min_pct_spin, self.min_ncells_spin, self.label_limit_spin):
            w.valueChanged.connect(self._update_plot)
        self.top_cell_spin.valueChanged.connect(self._update_plot)
        self.cmap_combo.currentIndexChanged.connect(self._update_plot)
        self.norm_combo.currentIndexChanged.connect(self._update_plot)

        self._selected_genes = getattr(self, '_selected_genes', [])
        for gid in self._selected_genes:
            self.selected_genes.addItem(str(gid))
        self._update_gene_info()
        self._on_view_changed()

    def _on_view_changed(self):
        heat = self.view_combo.currentIndex() == 1
        self.norm_combo.setEnabled(heat)
        self.top_cell_spin.setEnabled(not heat)
        self._update_plot()

    def _on_cell_type_changed(self):
        self._update_plot()

    # ── Gene selection ────────────────────────────────────────────────────

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
                    f"{len(matches)} genes match '{text}'. Refine the search "
                    f"(e.g. exact symbol).")
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
        self._update_plot()

    def _remove_selected_genes(self):
        for item in self.selected_genes.selectedItems():
            text = item.text()
            if text in self._selected_genes:
                self._selected_genes.remove(text)
            self.selected_genes.takeItem(self.selected_genes.row(item))
        self._update_gene_info()
        self._update_plot()

    def _clear_genes(self):
        self._selected_genes.clear()
        self.selected_genes.clear()
        self._update_gene_info()
        self._update_plot()

    def _selected_cell_types(self) -> List[str]:
        return [self.cell_type_list.item(i).text()
                for i in range(self.cell_type_list.count())
                if self.cell_type_list.item(i).isSelected()]

    def _update_gene_info(self) -> None:
        if not self._selected_genes:
            self.gene_info_label.setText("")
            return
        gid = self._selected_genes[0]
        row = next((r for r in self._gene_rows if str(r.get('gene_id')) == str(gid)), None)
        if row is None:
            self.gene_info_label.setText(str(gid))
            return
        parts = [f"{row.get('gene_name', gid)} ({gid})"]
        for key, label in (('max_mean', 'max mean'), ('max_pct', 'max pct'),
                           ('n_cell_types_detected', 'n cell types')):
            if key in row and pd.notna(row.get(key)):
                try:
                    parts.append(f"{label}={float(row[key]):.4g}")
                except (TypeError, ValueError):
                    parts.append(f"{label}={row[key]}")
        for key, label in (('top_cell_type', 'top'), ('top_mean_expression', 'top mean')):
            if key in row and pd.notna(row.get(key)):
                val = row[key]
                if key == 'top_mean_expression':
                    try:
                        val = f"{float(val):.4g}"
                    except (TypeError, ValueError):
                        pass
                parts.append(f"{label}={val}")
        self.gene_info_label.setText("  |  ".join(parts))

    # ── Plot ──────────────────────────────────────────────────────────────

    def _dot_params(self) -> dict:
        return {
            'top_cell_types': self.top_cell_spin.value(),
            'label_limit': self.label_limit_spin.value(),
            'cmap': self.cmap_combo.currentText(),
            'xlabel': 'Cell type',
            'ylabel': 'Gene',
        }

    def _build_long(self) -> pd.DataFrame:
        return build_expression_long(
            self.wide_df, self.pct_df, genes=self._selected_genes,
            gene_id_col=self.gene_id_col, gene_name_col=self.gene_name_col,
            cell_types=self._selected_cell_types(), n_cells=self._n_cells_for_selected(),
            pct_scale=self.pct_scale, min_pct=self.min_pct_spin.value(),
            min_n_cells=self.min_ncells_spin.value())

    def _heatmap_df(self) -> pd.DataFrame:
        long = self._build_long()
        if long.empty:
            return long
        # 선택 유전자별 top-N cell type (dot plot과 동일 기준)으로 wide 재구성
        top_n = self.top_cell_spin.value()
        if top_n > 0:
            scores = long.groupby('cell_type')['mean_expression'].mean().sort_values(ascending=False)
            keep = set(scores.index[:top_n])
            long = long[long['cell_type'].isin(keep)]
        wide = long.pivot_table(index='gene_id', columns='cell_type',
                                values='mean_expression', aggfunc='first').reset_index()
        names = long.drop_duplicates('gene_id').set_index('gene_id')['gene_name']
        wide.insert(1, 'symbol', wide['gene_id'].map(names))
        cell_cols = [c for c in wide.columns if c not in ('gene_id', 'symbol')]
        wide[cell_cols] = wide[cell_cols].fillna(0.0)
        return wide

    def _do_plot(self):
        self.figure.clear()
        self._hover_points = []
        if not self._selected_genes:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Search and add at least one gene.',
                    ha='center', va='center', transform=ax.transAxes, color='#666666')
            self._hover_ax = None
            return

        if self.view_combo.currentIndex() == 1:
            from plots.heatmap import render_heatmap
            heat_df = self._heatmap_df()
            if heat_df.empty:
                ax = self.figure.add_subplot(111)
                ax.text(0.5, 0.5, 'No data after filtering.',
                        ha='center', va='center', transform=ax.transAxes, color='#666666')
                self._hover_ax = None
                return
            params = {
                'n_genes': min(len(heat_df), 500),
                'normalization': 'z-score' if self.norm_combo.currentIndex() == 0 else 'none',
                'transpose': False,
                'sorting': 'input',
                'show_dendrogram': False,
                'colormap': 'RdBu_r',
                'colorbar_min': None,
                'colorbar_max': None,
                'show_colorbar': True,
                'labels_title': 'Expression summary',
                'labels_xlabel': 'Cell type',
                'labels_ylabel': 'Gene',
                'sample_columns': [c for c in self._selected_cell_types()
                                   if c in heat_df.columns],
            }
            render_heatmap(self.figure, heat_df, params)
            self._hover_ax = None
            return

        self._current_long = self._build_long()
        ax = self.figure.add_subplot(111)
        info = render_expression_dot(ax, self._current_long, self._dot_params())
        self._hover_ax = ax
        points = list(info.get('points', []))
        for p, x, y in zip(points, info.get('x', []), info.get('y', [])):
            p['_x'] = x
            p['_y'] = y
        self._hover_points = points

    def _on_hover(self, event):
        if self._hover_ax is None or event.inaxes is not self._hover_ax or not self._hover_points:
            return
        if event.xdata is None or event.ydata is None:
            return
        ax = self._hover_ax
        xr = ax.get_xlim()
        yr = ax.get_ylim()
        dx = max(abs(xr[1] - xr[0]), 1e-9)
        dy = max(abs(yr[1] - yr[0]), 1e-9)
        best = None
        best_dist = 1e9
        for p in self._hover_points:
            x = p.get('_x')
            y = p.get('_y')
            if x is None or y is None:
                continue
            d = ((x - event.xdata) / dx) ** 2 + ((y - event.ydata) / dy) ** 2
            if d < best_dist:
                best_dist = d
                best = p
        if best is None or best_dist > 0.0004:
            return
        text = (f"{best.get('gene_name')}\n{best.get('cell_type')}\n"
                f"mean: {best.get('mean_expression'):.4g}\n"
                f"pct: {best.get('pct_expressing')}\n"
                f"n_cells: {best.get('n_cells')}")
        try:
            from PyQt6.QtWidgets import QToolTip
            QToolTip.showText(event.guiEvent.globalPosition().toPoint(), text, self)
        except Exception:
            pass

    # ── Export ────────────────────────────────────────────────────────────

    def _extra_buttons(self) -> list:
        return [("Export Data", self._export_data)]

    def _export_data(self):
        df = self._current_long if self.view_combo.currentIndex() == 0 else self._heatmap_df()
        if not isinstance(df, pd.DataFrame) or df.empty:
            QMessageBox.information(self, "No Data", "Nothing to export with the current filters.")
            return
        path, _ = remembered_save_path(
            self, "Export Expression Data",
            f"{self.dataset.name}_expression.csv",
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
        if self.view_combo.currentIndex() == 0:
            df = self._current_long if isinstance(self._current_long, pd.DataFrame) else self._build_long()
            plot_type = 'expression_dot'
            params = self._dot_params()
            title = 'Gene × Cell-Type Expression'
        else:
            df = self._heatmap_df()
            plot_type = 'heatmap'
            params = {
                'n_genes': min(len(df), 500), 'normalization': 'z-score',
                'transpose': False, 'sorting': 'input', 'show_dendrogram': False,
                'colormap': 'RdBu_r', 'colorbar_min': None, 'colorbar_max': None,
                'show_colorbar': True, 'labels_title': 'Expression summary',
                'labels_xlabel': 'Cell type', 'labels_ylabel': 'Gene',
                'sample_columns': [c for c in df.columns
                                   if c not in ('gene_id', 'gene_name', 'symbol')],
            }
            title = 'Expression Summary Heatmap'
        slug = str(self.dataset.name).replace(' ', '_')
        return {
            'figure': self.figure,
            'dataframe': df,
            'plot_params': params,
            'dataset_name': self.dataset.name,
            'plot_type': plot_type,
            'figure_title': f"{title} — {self.dataset.name}",
            'figure_slug': f"{slug}_{plot_type}",
            'source_stem': f"{slug}_{plot_type}",
            'notes': 'Generated from cmg-seqviewer Expression Summary view.',
        }
