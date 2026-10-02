"""
GO/KEGG Enrichment Analysis dialog (plan §10-2, G3/G8/G12/G14/F1/F3/F10).

- 입력 소스 3종: ① 현재 DE 데이터셋 ② 붙여넣기 gene list ③ Comparison: Statistics (meta)
- 종 Human/Mouse (mouse=로컬 우선 배너 A3), 라이브러리 GO BP/CC/MF + KEGG (F10: ontology당 1개)
- 모드 Auto/Online/Local/Offline (+Auto 라우팅 표, 오프라인 KEGG 배너 F3, QSettings 토글 F1)
- custom background → 로컬 강제 안내 (ADR-2 2A), 진행/취소/요약 (G14)
- 결과: EnrichmentWorker → EnrichmentResult → presenter.register_enrichment_result (G11)
"""

from pathlib import Path
from typing import List, Optional

import logging

import pandas as pd
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QProgressBar, QTabWidget, QVBoxLayout,
    QWidget,
)

from models.data_models import Dataset, DatasetType
from models.enrichment_models import DIRECTION_ALL, EnrichmentRequest, VALID_ENGINES
from workers.go_workers import EnrichmentWorker, ErrorPayload

logger = logging.getLogger(__name__)

_LIB_LABELS = [("BP", "GO Biological Process"), ("CC", "GO Cellular Component"),
               ("MF", "GO Molecular Function"), ("KEGG", "KEGG Pathway")]
# F3/ADR-1: v1 오프라인 = GO 전용 (KEGG 비활성) — Option 2 채택 시 재결정
_OFFLINE_BANNER = "Offline/Local mode = GO only (KEGG is analyzed online only, v1 — ADR-1 Option 1)"
_AUTO_ROUTING = ("Auto: no background + online → Enrichr (online) / background set or offline → "
                 "local (GOATOOLS); mouse GO is always local (A3)")


class EnrichmentAnalysisDialog(QDialog):
    """enrichment 분석 다이얼로그.

    main_window가 필요한 최소 인터페이스 (테스트 스텁 대체 가능):
      - .presenter: MainPresenter (datasets 딕셔너리, register_enrichment_result, dataset_loaded)
      - .data_tabs.currentWidget()/model(): Comparison: Statistics 시트 df 접근 (meta volcano 패턴)
      - .settings: QSettings("RNASeqDataView")
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.presenter = getattr(main_window, "presenter", None)
        self._worker: Optional[EnrichmentWorker] = None
        self._result_summary: Optional[str] = None
        self.setWindowTitle("GO/KEGG Enrichment Analysis")
        self.setMinimumWidth(680)

        self._build_ui()
        self._load_settings()
        self._refresh_dataset_list()
        self._update_mode_ui()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        root = QVBoxLayout(self)

        # ---- 입력 소스 탭 ----
        self.source_tabs = QTabWidget()
        self.source_tabs.addTab(self._build_dataset_tab(), "Current DE Dataset")
        self.source_tabs.addTab(self._build_paste_tab(), "Paste Gene List")
        self.source_tabs.addTab(self._build_meta_tab(), "Comparison: Statistics")
        root.addWidget(self.source_tabs)

        # ---- 공통 옵션 ----
        opts = QGroupBox("Common Options")
        form = QFormLayout(opts)
        self.species_combo = QComboBox()
        self.species_combo.addItem("Human", "human")
        self.species_combo.addItem("Mouse (local-first — A3)", "mouse")
        self.species_combo.currentIndexChanged.connect(self._update_mode_ui)
        form.addRow("Species", self.species_combo)

        lib_box = QWidget()
        lib_row = QHBoxLayout(lib_box)
        lib_row.setContentsMargins(0, 0, 0, 0)
        self.lib_checks = {}
        for key, label in _LIB_LABELS:
            cb = QCheckBox(label)
            cb.setChecked(True)
            # F10: v1은 (direction×ontology)당 라이브러리 1개 — 다중 라이브러리 노출 없음
            cb.setToolTip("v1: one library per ontology (F10)")
            self.lib_checks[key] = cb
            lib_row.addWidget(cb)
        form.addRow("Libraries", lib_box)

        self.engine_combo = QComboBox()
        for eng in VALID_ENGINES:
            self.engine_combo.addItem({"auto": "Auto (auto routing)",
                                       "online": "Online (Enrichr)",
                                       "local": "Local (GOATOOLS)",
                                       "offline": "Offline (local only, no downloads)"}[eng], eng)
        self.engine_combo.currentIndexChanged.connect(self._update_mode_ui)
        self.engine_combo.currentIndexChanged.connect(self._persist_engine_setting)
        form.addRow("Engine Mode", self.engine_combo)
        self.one_sided_check = QCheckBox(
            "One-sided Fisher (enrichment, matches pipeline statistics — local GO)")
        self.one_sided_check.setToolTip(
            "Local GOATOOLS uses two-sided Fisher by default (more conservative). "
            "Check to reproduce the pipeline/clusterProfiler one-sided (enrichment) p-values.")
        form.addRow("", self.one_sided_check)
        self.routing_label = QLabel(_AUTO_ROUTING)
        self.routing_label.setWordWrap(True)
        font = self.routing_label.font()
        font.setPointSize(font.pointSize() - 1)
        self.routing_label.setFont(font)
        form.addRow("", self.routing_label)
        self.offline_banner = QLabel(_OFFLINE_BANNER)
        self.offline_banner.setStyleSheet("color: #b06000;")
        self.offline_banner.setWordWrap(True)
        form.addRow("", self.offline_banner)

        # background
        bg_box = QWidget()
        bg_row = QHBoxLayout(bg_box)
        bg_row.setContentsMargins(0, 0, 0, 0)
        self.bg_count_label = QLabel("Not set (online = Enrichr universe / local = full DE table)")
        self.bg_file_btn = self._mk_button("Background file...", self._load_background_file)
        bg_row.addWidget(self.bg_count_label, 1)
        bg_row.addWidget(self.bg_file_btn)
        form.addRow("Background", bg_box)
        self._custom_background: Optional[List[str]] = None

        root.addWidget(opts)

        # ---- 실행/진행 ----
        action_row = QHBoxLayout()
        self.run_btn = self._mk_button("Run Analysis", self._on_run_clicked)
        self.cancel_btn = self._mk_button("Cancel", self._on_cancel_clicked)
        self.cancel_btn.setEnabled(False)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        action_row.addWidget(self.run_btn)
        action_row.addWidget(self.cancel_btn)
        action_row.addWidget(self.progress, 1)
        root.addLayout(action_row)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        root.addWidget(self.summary_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        root.addWidget(self.button_box)

    def _build_dataset_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.dataset_combo = QComboBox()
        form.addRow("DE Dataset", self.dataset_combo)
        self.fc_min_spin = QDoubleSpinBox()
        self.fc_min_spin.setRange(0.0, 100.0)
        self.fc_min_spin.setDecimals(2)
        self.fc_min_spin.setValue(1.0)
        form.addRow("|log2FC| ≥", self.fc_min_spin)
        self.fdr_max_spin = QDoubleSpinBox()
        self.fdr_max_spin.setRange(0.0, 1.0)
        self.fdr_max_spin.setDecimals(4)
        self.fdr_max_spin.setValue(0.05)
        form.addRow("adj_pvalue ≤", self.fdr_max_spin)
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("TOTAL only", "TOTAL")
        self.direction_combo.addItem("UP", "UP")
        self.direction_combo.addItem("DOWN", "DOWN")
        self.direction_combo.addItem("UP + DOWN + TOTAL", DIRECTION_ALL)
        self.direction_combo.setToolTip(
            "UP + DOWN + TOTAL runs all three and merges them into one dataset "
            "(matches the pipeline-import Excel format — one dataset with UP/DOWN/TOTAL rows).")
        form.addRow("Direction", self.direction_combo)
        return w

    def _build_paste_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("One per line / comma / tab / semicolon separated (human=UPPER, mouse=Title applied automatically — A6)"))
        self.paste_edit = QPlainTextEdit()
        self.paste_edit.setPlaceholderText("e.g. TP53, JUN, FOS, BRCA1, MYC ...")
        v.addWidget(self.paste_edit)
        self.paste_count_label = QLabel("")
        v.addWidget(self.paste_count_label)
        self.paste_edit.textChanged.connect(self._update_paste_count)
        return w

    def _build_meta_tab(self) -> QWidget:
        from utils.deg_input import parse_gene_list  # noqa: F401 (로컬 사용)
        w = QWidget()
        form = QFormLayout(w)
        self.meta_available_label = QLabel("")
        form.addRow("Comparison: Statistics", self.meta_available_label)
        self.meta_cutoff_spin = QDoubleSpinBox()
        self.meta_cutoff_spin.setRange(0.0, 1.0)
        self.meta_cutoff_spin.setDecimals(4)
        self.meta_cutoff_spin.setValue(0.05)
        form.addRow("meta FDR ≤", self.meta_cutoff_spin)
        self.meta_concordant_check = QCheckBox("Only meta_direction concordant rows (recommended)")
        form.addRow("", self.meta_concordant_check)
        # Phase 4 M4b: ORA vs GSEA prerank (A7 명칭 구분)
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        self.meta_method_group = QButtonGroup(self)
        self.meta_ora_radio = QRadioButton("ORA (over-representation)")
        self.meta_prerank_radio = QRadioButton("GSEA prerank (gseapy, international gene sets — cached GMT)")
        self.meta_ora_radio.setChecked(True)
        self.meta_method_group.addButton(self.meta_ora_radio)
        self.meta_method_group.addButton(self.meta_prerank_radio)
        meth_row = QHBoxLayout()
        meth_row.addWidget(self.meta_ora_radio)
        meth_row.addWidget(self.meta_prerank_radio)
        form.addRow("Analysis Method", meth_row)
        return w

    # ----------------------------------------------------------------- util

    @staticmethod
    def _mk_button(text: str, slot) -> "object":
        from PyQt6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.clicked.connect(slot)
        return btn

    def _settings(self) -> QSettings:
        s = getattr(self.main_window, "settings", None)
        return s if isinstance(s, QSettings) else QSettings("RNASeqDataView")

    def _load_settings(self):
        self._setting_restore = True
        try:
            offline = self._settings().value("enrichment/offline", False, bool)
            if offline:
                idx = self.engine_combo.findData("offline")
                if idx >= 0:
                    self.engine_combo.setCurrentIndex(idx)
        finally:
            self._setting_restore = False

    def _persist_engine_setting(self):
        """F1: 사용자 엔진 선택을 QSettings에 기록 (offline 토글 포함)."""
        if getattr(self, "_setting_restore", False):
            return
        settings = self._settings()
        settings.setValue("enrichment/engine", self._engine())
        settings.setValue("enrichment/offline", self._engine() == "offline")

    def _refresh_dataset_list(self):
        self.dataset_combo.clear()
        datasets = self._de_datasets()
        for ds in datasets:
            self.dataset_combo.addItem(ds.name, ds.name)
        self.dataset_combo.setEnabled(len(datasets) > 0)

    def _de_datasets(self) -> List[Dataset]:
        if self.presenter is None:
            return []
        return [d for d in self.presenter.datasets.values()
                if getattr(d, "dataset_type", None) == DatasetType.DIFFERENTIAL_EXPRESSION
                and d.dataframe is not None]

    def _current_meta_df(self) -> Optional[pd.DataFrame]:
        """현재 Comparison: Statistics 시트 df (meta volcano 패턴)."""
        tabs = getattr(self.main_window, "data_tabs", None)
        if tabs is None:
            return None
        w = tabs.currentWidget()
        model = getattr(w, "model", lambda: None)()
        df = getattr(model, "dataframe", None)  # DataFrameTableModel 표시용 df
        if df is None and hasattr(model, "_df"):
            df = model._df
        return df if isinstance(df, pd.DataFrame) else None

    def _update_paste_count(self):
        from utils.deg_input import parse_gene_list
        text = self.paste_edit.toPlainText()
        symbols, warnings = parse_gene_list(text, species=self._species())
        self.paste_count_label.setText(
            f"Parsed: {len(symbols)} symbols" + (f" (warnings: {len(warnings)})" if warnings else ""))

    def _species(self) -> str:
        return self.species_combo.currentData()

    def _selected_libraries(self) -> List[str]:
        return [key for key, cb in self.lib_checks.items() if cb.isChecked()]

    def _engine(self) -> str:
        return self.engine_combo.currentData()

    def _update_mode_ui(self):
        eng = self._engine()
        offline = eng in ("offline", "local")
        self.offline_banner.setVisible(offline)
        # mouse GO 로컬 우선 안내 (A3)
        if self._species() == "mouse":
            self.routing_label.setText(
                _AUTO_ROUTING + "  |  mouse: GO local only (no online mouse GO library — P0-7)")
        else:
            self.routing_label.setText(_AUTO_ROUTING)
        if eng == "offline":
            self.offline_banner.setText("Offline mode — no internet. First run needs cached files (obo/gene2go); see the download guide. KEGG inactive.")
        else:
            self.offline_banner.setText(_OFFLINE_BANNER)

    def _load_background_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Background gene list", "",
                                              "Text/TSV (*.txt *.tsv *.csv);;All files (*)")
        if not path:
            return
        try:
            from utils.deg_input import parse_gene_list
            symbols, _w = parse_gene_list(Path(path).read_text(encoding="utf-8"),
                                          species=self._species())
            if not symbols:
                QMessageBox.warning(self, "Background", "No genes found in the background file.")
                return
            self._custom_background = symbols
            self.bg_count_label.setText(f"Custom {len(symbols)} genes — local engine forced (2A)")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Background", f"Failed to read background file:\n{exc}")

    # ----------------------------------------------------------------- run

    def _build_request(self) -> Optional[EnrichmentRequest]:
        species = self._species()
        libs = self._selected_libraries()
        if not libs:
            QMessageBox.warning(self, "Enrichment", "Select at least one library.")
            return None
        engine = self._engine()
        common = {
            "organism": species, "libraries": libs, "engine": engine,
            "background": self._custom_background,
        }
        src = self.source_tabs.currentIndex()
        if src == 0:  # dataset
            name = self.dataset_combo.currentData()
            ds = self.presenter.datasets.get(name) if name else None
            if ds is None or ds.dataframe is None:
                QMessageBox.warning(self, "Enrichment", "Select a DE dataset.")
                return None
            req = EnrichmentRequest(source="dataset", dataset_name=name,
                                    fc_min=self.fc_min_spin.value(),
                                    fdr_max=self.fdr_max_spin.value(),
                                    direction=self.direction_combo.currentData(),
                                    **common)
            self._pending_df = ds.dataframe
            return req
        if src == 1:  # paste
            from utils.deg_input import parse_gene_list
            symbols, _w = parse_gene_list(self.paste_edit.toPlainText(), species=species)
            if not symbols:
                QMessageBox.warning(self, "Enrichment", "The pasted gene list is empty.")
                return None
            req = EnrichmentRequest(source="paste", gene_list=symbols,
                                    direction="TOTAL", **common)
            self._pending_df = None
            return req
        # meta
        meta_df = self._current_meta_df()
        if meta_df is None:
            QMessageBox.warning(self, "Enrichment",
                                "The current sheet is not 'Comparison: Statistics' (meta columns required).")
            return None
        req = EnrichmentRequest(source="meta",
                                meta_cutoff=self.meta_cutoff_spin.value(),
                                meta_direction_required=self.meta_concordant_check.isChecked(),
                                direction="TOTAL", **common)
        req.extra["prerank"] = self.meta_prerank_radio.isChecked()
        # meta provenance (M4b/§6.9)
        meta_src = getattr(self, "_current_meta_df", None)
        if meta_src is not None and hasattr(self.main_window, "dataset_manager"):
            try:
                req.extra["combined_datasets"] = list(self.presenter.datasets.keys())
            except Exception:
                pass
        self._pending_df = meta_df
        return req

    def _on_run_clicked(self):
        if self._worker is not None and self._worker.isRunning():
            return
        req = self._build_request()
        if req is None:
            return
        req.extra["one_sided"] = self.one_sided_check.isChecked()
        self._result_summary = None
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setValue(0)
        self.summary_label.setText("Analyzing...")
        self._worker = EnrichmentWorker(req, dataframe=getattr(self, "_pending_df", None))
        self._worker.progress.connect(self.progress.setValue)
        self._worker.result_ready.connect(self._on_result)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_cancel_clicked(self):
        if self._worker is not None:
            self._worker.cancel()
            self.summary_label.setText("Cancel requested... (partial results discarded, P2-4)")

    def _on_result(self, result):
        self.progress.setValue(100)
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        name = None
        if self.presenter is not None:
            name = self.presenter.register_enrichment_result(result)
        n = len(result.dataframe)
        w = len(result.warnings)
        self._result_summary = (f"Done: {n} terms (engine={result.engine_used})"
                                + (f" ({w} warnings)" if w else ""))
        if name:
            self._result_summary += f"\nDataset '{name}' registered — open in the existing GO visualizations (§6.3)"
        self.summary_label.setText(self._result_summary)
        self._warn_if_kegg_offline(result)

    def _warn_if_kegg_offline(self, result):
        kegg_req = "KEGG" in (result.request.libraries or [])
        kegg_present = (result.dataframe["ontology"] == "KEGG").any() \
            if "ontology" in result.dataframe.columns else False
        if kegg_req and not kegg_present:
            QMessageBox.information(
                self, "GO/KEGG Enrichment",
                "KEGG is inactive in offline/local mode (v1, ADR-1 Option 1).\n"
                "Running online mode includes KEGG analysis. (F3)")

    def _on_failed(self, payload: ErrorPayload):
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setValue(0)
        base = f"Analysis failed ({payload.kind.value}):\n{payload.message}"
        if payload.warnings:
            base += "\nWarnings:\n  " + "\n  ".join(payload.warnings[:5])
        self.summary_label.setText(base)
        QMessageBox.warning(self, "GO/KEGG Enrichment", base)

    # ----------------------------------------------------------------- misc

    def current_summary(self) -> Optional[str]:
        return self._result_summary

    def closeEvent(self, event):  # noqa: N802 (Qt)
        w = self._worker
        if w is not None and w.isRunning():
            # P2-4/architect P2-2: cancel 후 완료 대기 — 그래도 남으면 terminate (부분 결과 폐기)
            w.cancel()
            w.wait(15000)
            if w.isRunning():
                w.terminate()
                w.wait(2000)
        super().closeEvent(event)