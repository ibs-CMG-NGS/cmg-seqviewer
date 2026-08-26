"""
Dataset Bulk Edit Dialog

여러 개의 Pre-loaded 데이터셋을 선택하여 공통 메타데이터를 한 번에 편집하는 다이얼로그
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QPushButton, QLineEdit, QTextEdit, QLabel,
                            QComboBox, QMessageBox, QGroupBox, QCheckBox,
                            QListWidget, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List
import logging

from models.data_models import PreloadedDatasetMetadata
from utils.database_manager import DatabaseManager


class BulkEditDialog(QDialog):
    """
    여러 데이터셋의 공통 메타데이터를 한 번에 편집하는 다이얼로그

    각 필드는 체크박스로 "적용 여부"를 선택하며, 체크된 필드만 선택된
    모든 데이터셋에 일괄 적용된다. Alias는 데이터셋마다 고유해야 하므로
    일괄 편집 대상에서 제외한다.
    """

    # Signal
    edit_completed = pyqtSignal(list)  # 변경된 dataset_id 리스트

    LIST_FIELD_MODES = ["Replace", "Add"]

    def __init__(self, metadata_list: List[PreloadedDatasetMetadata],
                 database_manager: DatabaseManager, parent=None):
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.metadata_list = metadata_list
        self.db_manager = database_manager

        self._init_ui()

    def _init_ui(self):
        """UI 초기화"""
        count = len(self.metadata_list)
        self.setWindowTitle(f"Bulk Edit - {count} Datasets Selected")
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setGeometry(150, 150, 620, 700)

        layout = QVBoxLayout(self)

        # 선택된 데이터셋 목록 (읽기 전용)
        selected_group = QGroupBox(f"Selected Datasets ({count})")
        selected_layout = QVBoxLayout(selected_group)
        selected_list = QListWidget()
        selected_list.addItems([m.alias for m in self.metadata_list])
        selected_list.setMaximumHeight(120)
        selected_layout.addWidget(selected_list)
        layout.addWidget(selected_group)

        hint = QLabel(
            "Check a field to overwrite it on every selected dataset. "
            "Unchecked fields are left unchanged."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        layout.addWidget(hint)

        # 편집 가능한 공통 메타데이터
        meta_group = QGroupBox("Common Metadata")
        meta_layout = QFormLayout(meta_group)

        # Condition
        self.condition_check, self.condition_input = self._add_text_row(
            meta_layout, "Condition:", "e.g., Drug treatment vs Control"
        )

        # Cell Type
        self.cell_type_check, self.cell_type_input = self._add_text_row(
            meta_layout, "Cell Type:", "e.g., MCF7, HeLa, HEK293"
        )

        # Organism
        self.organism_check = QCheckBox()
        self.organism_combo = QComboBox()
        self.organism_combo.setEditable(True)
        self.organism_combo.addItems([
            "Homo sapiens",
            "Mus musculus",
            "Rattus norvegicus",
            "Drosophila melanogaster",
            "Caenorhabditis elegans",
            "Danio rerio"
        ])
        self.organism_combo.setEnabled(False)
        self.organism_check.toggled.connect(self.organism_combo.setEnabled)
        meta_layout.addRow(self._checked_row("Organism:", self.organism_check), self.organism_combo)

        # Tissue
        self.tissue_check, self.tissue_input = self._add_text_row(
            meta_layout, "Tissue:", "e.g., Liver, Brain, Muscle"
        )

        # Timepoint
        self.timepoint_check, self.timepoint_input = self._add_text_row(
            meta_layout, "Timepoint:", "e.g., 24h, 48h, Day 3"
        )

        # Researcher (list 필드 - Replace/Add 모드)
        self.researcher_check, self.researcher_input, self.researcher_mode = self._add_list_row(
            meta_layout, "Researcher:", "Comma-separated initials (e.g., ljh, hiy)"
        )

        # Tags (list 필드 - Replace/Add 모드)
        self.tags_check, self.tags_input, self.tags_mode = self._add_list_row(
            meta_layout, "Tags:", "Comma-separated tags"
        )

        # Notes
        self.notes_check = QCheckBox()
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes or description...")
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setEnabled(False)
        self.notes_check.toggled.connect(self.notes_input.setEnabled)
        meta_layout.addRow(self._checked_row("Notes:", self.notes_check), self.notes_input)

        layout.addWidget(meta_group)

        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        apply_btn = QPushButton(f"💾 Apply to {count} Dataset(s)")
        apply_btn.clicked.connect(self._on_apply)
        button_layout.addWidget(apply_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _checked_row(self, label_text: str, checkbox: QCheckBox) -> QWidget:
        """체크박스 + 레이블을 한 줄로 묶은 위젯 (FormLayout의 label 자리에 사용)"""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(checkbox)
        row_layout.addWidget(QLabel(label_text))
        return row

    def _add_text_row(self, form_layout: QFormLayout, label: str, placeholder: str):
        """체크박스 + QLineEdit 한 행을 추가하고 (checkbox, input)을 반환"""
        checkbox = QCheckBox()
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setEnabled(False)
        checkbox.toggled.connect(line_edit.setEnabled)
        form_layout.addRow(self._checked_row(label, checkbox), line_edit)
        return checkbox, line_edit

    def _add_list_row(self, form_layout: QFormLayout, label: str, placeholder: str):
        """체크박스 + QLineEdit + Replace/Add 모드 콤보를 한 행에 추가"""
        checkbox = QCheckBox()
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setEnabled(False)

        mode_combo = QComboBox()
        mode_combo.addItems(self.LIST_FIELD_MODES)
        mode_combo.setToolTip(
            "Replace: overwrite existing values.\n"
            "Add: append to existing values (duplicates skipped)."
        )
        mode_combo.setEnabled(False)
        mode_combo.setMaximumWidth(80)

        checkbox.toggled.connect(line_edit.setEnabled)
        checkbox.toggled.connect(mode_combo.setEnabled)

        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.addWidget(line_edit, stretch=1)
        field_layout.addWidget(mode_combo)

        form_layout.addRow(self._checked_row(label, checkbox), field_container)
        return checkbox, line_edit, mode_combo

    def _on_apply(self):
        """체크된 필드를 선택된 모든 데이터셋에 일괄 적용"""
        # 적용할 필드가 하나도 없으면 안내
        any_checked = any([
            self.condition_check.isChecked(),
            self.cell_type_check.isChecked(),
            self.organism_check.isChecked(),
            self.tissue_check.isChecked(),
            self.timepoint_check.isChecked(),
            self.researcher_check.isChecked(),
            self.tags_check.isChecked(),
            self.notes_check.isChecked(),
        ])
        if not any_checked:
            QMessageBox.warning(
                self, "No Fields Selected",
                "Please check at least one field to apply."
            )
            return

        count = len(self.metadata_list)
        reply = QMessageBox.question(
            self,
            "Confirm Bulk Edit",
            f"Apply the checked field(s) to {count} dataset(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            changed_ids = []
            for metadata in self.metadata_list:
                self._apply_fields(metadata)
                changed_ids.append(metadata.dataset_id)

            # DatabaseManager의 메타데이터 리스트에 반영
            by_id = {m.dataset_id: m for m in self.metadata_list}
            for idx, meta in enumerate(self.db_manager.metadata_list):
                if meta.dataset_id in by_id:
                    self.db_manager.metadata_list[idx] = by_id[meta.dataset_id]

            self.db_manager._save_metadata()

            QMessageBox.information(
                self,
                "Bulk Edit Complete",
                f"Successfully updated {count} dataset(s)."
            )

            self.edit_completed.emit(changed_ids)
            self.accept()

        except Exception as e:
            self.logger.error(f"Failed to apply bulk edit: {e}")
            QMessageBox.critical(
                self,
                "Bulk Edit Failed",
                f"An error occurred while saving:\n\n{str(e)}"
            )

    def _apply_fields(self, metadata: PreloadedDatasetMetadata):
        """체크된 필드 값을 개별 metadata 객체에 적용"""
        if self.condition_check.isChecked():
            metadata.experiment_condition = self.condition_input.text().strip()

        if self.cell_type_check.isChecked():
            metadata.cell_type = self.cell_type_input.text().strip()

        if self.organism_check.isChecked():
            metadata.organism = self.organism_combo.currentText().strip()

        if self.tissue_check.isChecked():
            metadata.tissue = self.tissue_input.text().strip()

        if self.timepoint_check.isChecked():
            metadata.timepoint = self.timepoint_input.text().strip()

        if self.researcher_check.isChecked():
            metadata.researcher = self._merge_list(
                metadata.researcher, self.researcher_input.text(), self.researcher_mode.currentText()
            )

        if self.tags_check.isChecked():
            metadata.tags = self._merge_list(
                metadata.tags, self.tags_input.text(), self.tags_mode.currentText()
            )

        if self.notes_check.isChecked():
            metadata.notes = self.notes_input.toPlainText().strip()

    @staticmethod
    def _merge_list(existing: List[str], text: str, mode: str) -> List[str]:
        """콤마 구분 텍스트를 파싱하여 Replace 또는 Add 모드로 리스트 필드를 갱신"""
        new_values = [v.strip() for v in text.split(',') if v.strip()]

        if mode == "Add":
            merged = list(existing)
            for v in new_values:
                if v not in merged:
                    merged.append(v)
            return merged

        return new_values
