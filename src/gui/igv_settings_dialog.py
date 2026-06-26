import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QSpinBox, QCheckBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QDialogButtonBox, QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class IGVSettingsDialog(QDialog):

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("IGV Integration Settings")
        self.setMinimumWidth(620)
        self.setMinimumHeight(460)
        self._build_ui()
        self._load_settings()

    # ──────────────────────────── UI build ────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(self._build_connection_group())
        layout.addWidget(self._build_navigation_group())
        layout.addWidget(self._build_tracks_group())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_connection_group(self):
        group = QGroupBox("Connection")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(60151)
        self.port_spin.setFixedWidth(80)
        layout.addWidget(self.port_spin)

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._on_test_connection)
        layout.addWidget(self.test_btn)

        self.status_label = QLabel("—")
        layout.addWidget(self.status_label)
        layout.addStretch()
        return group

    def _build_navigation_group(self):
        group = QGroupBox("Navigation")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("Context padding:"))
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 100000)
        self.padding_spin.setValue(500)
        self.padding_spin.setFixedWidth(80)
        layout.addWidget(self.padding_spin)
        layout.addWidget(QLabel("bp"))

        layout.addSpacing(20)
        self.auto_genome_check = QCheckBox("Auto-set genome on send")
        self.auto_genome_check.setChecked(True)
        layout.addWidget(self.auto_genome_check)
        layout.addStretch()
        return group

    def _build_tracks_group(self):
        group = QGroupBox("Signal Tracks")
        layout = QVBoxLayout(group)

        self.track_table = QTableWidget(0, 3)
        self.track_table.setHorizontalHeaderLabels(["Display Name", "File Path", "Genome"])
        self.track_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.track_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.track_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.track_table.setMinimumHeight(140)
        layout.addWidget(self.track_table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Add Track")
        add_btn.clicked.connect(self._on_add_track)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._on_remove_track)
        btn_layout.addWidget(remove_btn)

        btn_layout.addStretch()

        self.load_tracks_btn = QPushButton("Load All Tracks in IGV Now")
        self.load_tracks_btn.clicked.connect(self._on_load_tracks_in_igv)
        btn_layout.addWidget(self.load_tracks_btn)

        layout.addLayout(btn_layout)

        self.track_status_label = QLabel("")
        layout.addWidget(self.track_status_label)
        return group

    # ──────────────────────────── Load / Save ────────────────────────────

    def _load_settings(self):
        self.port_spin.setValue(self.settings.value("igv/port", 60151, type=int))
        self.padding_spin.setValue(self.settings.value("igv/padding", 500, type=int))
        self.auto_genome_check.setChecked(
            self.settings.value("igv/auto_genome", True, type=bool))

        tracks_json = self.settings.value("igv/tracks", "[]")
        try:
            tracks = json.loads(tracks_json)
        except Exception:
            tracks = []
        for t in tracks:
            self._add_track_row(t.get("name", ""), t.get("path", ""), t.get("genome", ""))

    def _save_settings(self):
        self.settings.setValue("igv/port", self.port_spin.value())
        self.settings.setValue("igv/padding", self.padding_spin.value())
        self.settings.setValue("igv/auto_genome", self.auto_genome_check.isChecked())

        tracks = []
        for row in range(self.track_table.rowCount()):
            name = self._cell_text(row, 0)
            path = self._cell_text(row, 1)
            genome = self._cell_text(row, 2)
            if path:
                tracks.append({"name": name, "path": path, "genome": genome, "color": ""})
        self.settings.setValue("igv/tracks", json.dumps(tracks))

    def _cell_text(self, row: int, col: int) -> str:
        item = self.track_table.item(row, col)
        return item.text().strip() if item else ""

    # ──────────────────────────── Helpers ────────────────────────────

    def _add_track_row(self, name: str = "", path: str = "", genome: str = ""):
        row = self.track_table.rowCount()
        self.track_table.insertRow(row)
        self.track_table.setItem(row, 0, QTableWidgetItem(name))
        self.track_table.setItem(row, 1, QTableWidgetItem(path))
        self.track_table.setItem(row, 2, QTableWidgetItem(genome))

    def _make_connector(self):
        from utils.igv_connector import IGVConnector
        return IGVConnector(port=self.port_spin.value())

    # ──────────────────────────── Slots ────────────────────────────

    def _on_test_connection(self):
        connector = self._make_connector()
        if connector.is_running():
            self.status_label.setText("● Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("✗ Not running")
            self.status_label.setStyleSheet("color: red;")

    def _on_add_track(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select BigWig / BAM files", "",
            "Track files (*.bw *.bigwig *.bam);;All files (*.*)"
        )
        for path in paths:
            import os
            name = os.path.splitext(os.path.basename(path))[0]
            self._add_track_row(name, path, "")

    def _on_remove_track(self):
        rows = sorted({idx.row() for idx in self.track_table.selectedIndexes()},
                      reverse=True)
        for row in rows:
            self.track_table.removeRow(row)

    def _on_load_tracks_in_igv(self):
        from utils.igv_connector import IGVConnector, IGVTrack
        connector = IGVConnector(port=self.port_spin.value())
        if not connector.is_running():
            QMessageBox.warning(self, "IGV Not Running",
                                "IGV에 연결할 수 없습니다.\n포트 설정과 IGV 실행 여부를 확인하세요.")
            return

        ok = fail = 0
        for row in range(self.track_table.rowCount()):
            name = self._cell_text(row, 0)
            path = self._cell_text(row, 1)
            if not path:
                continue
            track = IGVTrack(path=path, name=name or path,
                             genome=self._cell_text(row, 2))
            if connector.load_track(track):
                ok += 1
            else:
                fail += 1

        if fail == 0:
            self.track_status_label.setText(f"Loaded {ok} track(s) successfully.")
            self.track_status_label.setStyleSheet("color: green;")
        else:
            self.track_status_label.setText(f"Loaded {ok}, failed {fail} track(s).")
            self.track_status_label.setStyleSheet("color: orange;")

    def _on_ok(self):
        self._save_settings()
        self.accept()
