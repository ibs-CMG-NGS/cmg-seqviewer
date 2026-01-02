"""
Dataset Manager Widget

데이터셋 관리 위젯
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QListWidget, QListWidgetItem, QPushButton,
                            QComboBox, QGroupBox, QInputDialog)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from typing import List, Dict
from datetime import datetime
from pathlib import Path


class DatasetManagerWidget(QWidget):
    """
    데이터셋 관리 위젯
    
    여러 데이터셋을 관리하고 전환할 수 있습니다.
    """
    
    dataset_selected = pyqtSignal(str)  # dataset_name
    dataset_removed = pyqtSignal(str)   # dataset_name
    file_dropped = pyqtSignal(str)      # file_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataset_metadata: Dict[str, Dict] = {}  # dataset_name -> metadata
        self._init_ui()
        
        # 드래그 앤 드롭 활성화 - 버튼에도 적용
        self.setAcceptDrops(True)
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 현재 데이터셋 선택
        layout.addWidget(QLabel("Current Dataset:"))
        
        self.dataset_combo = QComboBox()
        self.dataset_combo.setMinimumWidth(200)
        self.dataset_combo.currentTextChanged.connect(self.dataset_selected.emit)
        layout.addWidget(self.dataset_combo)
        
        # 버튼
        self.add_dataset_btn = QPushButton("➕ Add Dataset (or drag & drop Excel file)")
        self.add_dataset_btn.setMinimumWidth(250)
        self.add_dataset_btn.setAcceptDrops(True)  # 버튼도 드롭 허용
        self.add_dataset_btn.dragEnterEvent = lambda e: self.dragEnterEvent(e)
        self.add_dataset_btn.dropEvent = lambda e: self.dropEvent(e)
        layout.addWidget(self.add_dataset_btn)
        
        self.rename_dataset_btn = QPushButton("✏️ Rename")
        self.rename_dataset_btn.setToolTip("Rename the current dataset")
        self.rename_dataset_btn.clicked.connect(self._on_rename_dataset)
        layout.addWidget(self.rename_dataset_btn)
        
        self.remove_dataset_btn = QPushButton("➖ Remove")
        self.remove_dataset_btn.clicked.connect(self._on_remove_dataset)
        layout.addWidget(self.remove_dataset_btn)
        
        # Info 라벨
        self.info_label = QLabel("No datasets loaded")
        self.info_label.setStyleSheet("color: gray;")
        layout.addWidget(self.info_label, stretch=1)
        
        layout.addStretch()
    
    def add_dataset(self, dataset_name: str, info: str = "", metadata: Dict = None):
        """
        데이터셋 추가 (중복 시 자동으로 번호 추가)
        
        Args:
            dataset_name: 데이터셋 기본 이름
            info: 추가 정보
            metadata: 메타데이터 (file_path, loaded_at 등)
        """
        # 중복 체크 및 고유 이름 생성
        unique_name = self._generate_unique_name(dataset_name)
        
        # 메타데이터 저장
        if metadata is None:
            metadata = {}
        metadata['original_name'] = dataset_name
        metadata['added_at'] = datetime.now().isoformat()
        self.dataset_metadata[unique_name] = metadata
        
        # 콤보박스에 추가 (툴팁에 상세 정보 표시)
        self.dataset_combo.addItem(unique_name)
        
        # 툴팁 설정
        index = self.dataset_combo.findText(unique_name)
        if index >= 0:
            tooltip = self._create_tooltip(unique_name, metadata)
            self.dataset_combo.setItemData(index, tooltip, Qt.ItemDataRole.ToolTipRole)
        
        self.update_info()
        return unique_name
    
    def _generate_unique_name(self, base_name: str) -> str:
        """
        중복되지 않는 고유 이름 생성
        
        Args:
            base_name: 기본 이름 (예: "DESeq2_results")
            
        Returns:
            고유 이름 (예: "DESeq2_results", "DESeq2_results (2)", "DESeq2_results (3)")
        """
        existing = self.get_all_datasets()
        
        if base_name not in existing:
            return base_name
        
        # 숫자 추가하여 고유 이름 생성
        counter = 2
        while f"{base_name} ({counter})" in existing:
            counter += 1
        
        return f"{base_name} ({counter})"
    
    def _create_tooltip(self, dataset_name: str, metadata: Dict) -> str:
        """데이터셋 툴팁 생성"""
        lines = [f"<b>{dataset_name}</b>"]
        
        if 'file_path' in metadata:
            lines.append(f"📁 File: {metadata['file_path']}")
        
        if 'row_count' in metadata:
            lines.append(f"📊 Rows: {metadata['row_count']}")
        
        if 'dataset_type' in metadata:
            lines.append(f"🔬 Type: {metadata['dataset_type']}")
        
        if 'added_at' in metadata:
            added_time = metadata['added_at'][:19]  # YYYY-MM-DDTHH:MM:SS
            lines.append(f"🕐 Added: {added_time}")
        
        return "<br>".join(lines)
    
    def remove_dataset(self, dataset_name: str):
        """데이터셋 제거"""
        index = self.dataset_combo.findText(dataset_name)
        if index >= 0:
            self.dataset_combo.removeItem(index)
            # 메타데이터도 제거
            if dataset_name in self.dataset_metadata:
                del self.dataset_metadata[dataset_name]
            self.update_info()
    
    def _on_remove_dataset(self):
        """현재 데이터셋 제거"""
        current = self.dataset_combo.currentText()
        if current:
            self.dataset_removed.emit(current)
            self.remove_dataset(current)
    
    def _on_rename_dataset(self):
        """현재 데이터셋 이름 변경"""
        current = self.dataset_combo.currentText()
        if not current:
            return
        
        # 새 이름 입력 받기
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Dataset",
            "Enter a new name for the dataset:",
            text=current
        )
        
        if ok and new_name and new_name != current:
            # 중복 확인
            if new_name in self.get_all_datasets():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Duplicate Name",
                                  f"Dataset '{new_name}' already exists.")
                return
            
            # 이름 변경
            current_index = self.dataset_combo.currentIndex()
            
            # 메타데이터 이동
            if current in self.dataset_metadata:
                self.dataset_metadata[new_name] = self.dataset_metadata.pop(current)
            
            # 콤보박스 아이템 변경
            self.dataset_combo.setItemText(current_index, new_name)
            
            # 툴팁 업데이트
            tooltip = self._create_tooltip(new_name, self.dataset_metadata.get(new_name, {}))
            self.dataset_combo.setItemData(current_index, tooltip, Qt.ItemDataRole.ToolTipRole)
            
            self.update_info()
            
            # 부모(MainWindow)에 이름 변경 알림
            if hasattr(self.parent(), '_on_dataset_renamed'):
                self.parent()._on_dataset_renamed(current, new_name)
    
    def get_current_dataset(self) -> str:
        """현재 선택된 데이터셋 이름 반환"""
        return self.dataset_combo.currentText()
    
    def get_all_datasets(self) -> List[str]:
        """모든 데이터셋 이름 반환"""
        return [self.dataset_combo.itemText(i) 
                for i in range(self.dataset_combo.count())]
    
    def get_selected_datasets(self) -> List[str]:
        """선택된 데이터셋 목록 (비교 분석용)"""
        # TODO: 다중 선택 UI 구현 시 변경
        datasets = self.get_all_datasets()
        return datasets if len(datasets) >= 2 else []
    
    def get_dataset_metadata(self, dataset_name: str) -> Dict:
        """데이터셋 메타데이터 반환"""
        return self.dataset_metadata.get(dataset_name, {})
    
    def rename_dataset(self, old_name: str, new_name: str):
        """데이터셋 이름 변경"""
        index = self.dataset_combo.findText(old_name)
        if index >= 0:
            # 고유 이름 생성
            unique_name = self._generate_unique_name(new_name)
            
            # 콤보박스 업데이트
            self.dataset_combo.setItemText(index, unique_name)
            
            # 메타데이터 이동
            if old_name in self.dataset_metadata:
                self.dataset_metadata[unique_name] = self.dataset_metadata.pop(old_name)
            
            return unique_name
        return old_name
    
    def update_info(self):
        """정보 라벨 업데이트"""
        count = self.dataset_combo.count()
        if count == 0:
            self.info_label.setText("No datasets loaded")
        elif count == 1:
            self.info_label.setText("1 dataset loaded")
        else:
            self.info_label.setText(f"{count} datasets loaded")
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """드래그 진입 이벤트"""
        if event.mimeData().hasUrls():
            # Excel 파일만 허용
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.xlsx', '.xls', '.csv', '.tsv')):
                    event.accept()
                    return
        event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """드롭 이벤트"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.xlsx', '.xls', '.csv', '.tsv')):
                    self.file_dropped.emit(file_path)
                    event.accept()
                    return
        event.ignore()
