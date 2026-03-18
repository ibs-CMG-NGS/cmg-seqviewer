"""
Column Mapper Dialog

Excel 데이터의 컬럼을 표준 컬럼명으로 매핑하는 대화상자
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                            QGroupBox, QMessageBox, QCheckBox, QLineEdit)
from PyQt6.QtCore import Qt
from typing import Dict, List, Optional
import pandas as pd
from models.data_models import DatasetType


class ColumnMapperDialog(QDialog):
    """
    컬럼 매핑 대화상자
    
    사용자가 Excel 컬럼을 표준 컬럼명으로 매핑할 수 있도록 합니다.
    """
    
    # 표준 컬럼 정의
    STANDARD_COLUMNS = {
        DatasetType.DIFFERENTIAL_EXPRESSION: {
            'gene_id': '유전자 ID (필수)',
            'log2fc': 'log2 Fold Change (필수)',
            'pvalue': 'p-value (선택)',
            'adj_pvalue': 'Adjusted p-value (필수)',
            'base_mean': 'Base Mean (선택)',
        },
        DatasetType.GO_ANALYSIS: {
            'description': 'GO Term/Description (필수)',
            'term_id': 'Term ID (선택)',
            'gene_count': 'Gene Count (필수)',
            'pvalue': 'p-value (선택)',
            'fdr': 'FDR (필수)',
            'gene_symbols': 'Gene Symbols (선택)',
        }
    }
    
    def __init__(self, dataframe: pd.DataFrame, dataset_type: DatasetType,
                 auto_mapping: Dict[str, str] = None, parent=None):
        """
        Args:
            dataframe: 로드된 데이터프레임
            dataset_type: 데이터셋 타입
            auto_mapping: 자동 감지된 매핑 (원본 컬럼 -> 표준 컬럼)
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.dataframe = dataframe
        self.dataset_type = dataset_type
        self.auto_mapping = auto_mapping or {}
        self.column_mapping: Dict[str, str] = {}  # 표준 컬럼 -> 원본 컬럼
        
        self.setWindowTitle("Column Mapping")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        self._init_ui()
        self._apply_auto_mapping()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 안내 메시지
        info_label = QLabel(
            "📋 <b>컬럼 매핑 설정</b><br>"
            "Excel 파일의 컬럼을 표준 컬럼명으로 매핑하세요.<br>"
            "자동 감지된 매핑을 확인하고 필요시 수정할 수 있습니다."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 데이터셋 타입 표시
        type_label = QLabel(f"<b>데이터셋 타입:</b> {self.dataset_type.value}")
        layout.addWidget(type_label)
        
        # 데이터 미리보기
        preview_group = QGroupBox("데이터 미리보기 (처음 5행)")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_table = QTableWidget()
        self.preview_table.setMaximumHeight(150)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._populate_preview()
        preview_layout.addWidget(self.preview_table)
        
        layout.addWidget(preview_group)
        
        # 매핑 설정
        mapping_group = QGroupBox("컬럼 매핑")
        mapping_layout = QVBoxLayout(mapping_group)
        
        # 매핑 테이블 헤더
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>표준 컬럼</b>"))
        header_layout.addWidget(QLabel("<b>Excel 컬럼</b>"))
        header_layout.addWidget(QLabel("<b>미리보기</b>"))
        mapping_layout.addLayout(header_layout)
        
        # 매핑 콤보박스들
        self.mapping_combos = {}
        standard_cols = self.STANDARD_COLUMNS[self.dataset_type]
        
        for std_col, description in standard_cols.items():
            row_layout = QHBoxLayout()
            
            # 표준 컬럼명
            label = QLabel(description)
            label.setMinimumWidth(200)
            row_layout.addWidget(label)
            
            # Excel 컬럼 선택 콤보박스
            combo = QComboBox()
            combo.addItem("-- 선택 안함 --", None)
            for col in self.dataframe.columns:
                combo.addItem(col, col)
            combo.currentIndexChanged.connect(self._on_mapping_changed)
            self.mapping_combos[std_col] = combo
            row_layout.addWidget(combo)
            
            # 데이터 미리보기 (첫 값)
            preview_label = QLabel("")
            preview_label.setMinimumWidth(150)
            preview_label.setStyleSheet("color: gray; font-size: 10px;")
            row_layout.addWidget(preview_label)
            self.mapping_combos[f"{std_col}_preview"] = preview_label
            
            mapping_layout.addLayout(row_layout)
        
        layout.addWidget(mapping_group)
        
        # 설정 저장/불러오기
        settings_layout = QHBoxLayout()
        
        self.save_mapping_check = QCheckBox("이 매핑을 기본값으로 저장")
        self.save_mapping_check.setChecked(False)
        settings_layout.addWidget(self.save_mapping_check)
        
        settings_layout.addStretch()
        
        self.reset_btn = QPushButton("🔄 초기화")
        self.reset_btn.clicked.connect(self._reset_mapping)
        settings_layout.addWidget(self.reset_btn)
        
        layout.addLayout(settings_layout)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("✅ 확인")
        self.ok_btn.clicked.connect(self._validate_and_accept)
        self.ok_btn.setDefault(True)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def _populate_preview(self):
        """데이터 미리보기 테이블 채우기"""
        preview_df = self.dataframe.head(5)
        
        self.preview_table.setRowCount(len(preview_df))
        self.preview_table.setColumnCount(len(preview_df.columns))
        self.preview_table.setHorizontalHeaderLabels(preview_df.columns.tolist())
        
        for i, row in enumerate(preview_df.values):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.preview_table.setItem(i, j, item)
        
        self.preview_table.resizeColumnsToContents()
    
    def _apply_auto_mapping(self):
        """자동 감지된 매핑 적용"""
        # auto_mapping은 {원본 컬럼: 표준 컬럼} 형식
        # 콤보박스는 표준 컬럼별로 있으므로 역매핑 필요
        reverse_mapping = {v: k for k, v in self.auto_mapping.items()}
        
        for std_col, combo in self.mapping_combos.items():
            if std_col.endswith('_preview'):
                continue
            
            if std_col in reverse_mapping:
                original_col = reverse_mapping[std_col]
                index = combo.findData(original_col)
                if index >= 0:
                    combo.setCurrentIndex(index)
    
    def _on_mapping_changed(self):
        """매핑 변경 시 미리보기 업데이트"""
        for std_col, combo in self.mapping_combos.items():
            if std_col.endswith('_preview'):
                continue
            
            original_col = combo.currentData()
            preview_label = self.mapping_combos[f"{std_col}_preview"]
            
            if original_col and original_col in self.dataframe.columns:
                # 첫 번째 non-null 값 표시
                first_value = self.dataframe[original_col].dropna().iloc[0] if len(self.dataframe[original_col].dropna()) > 0 else "N/A"
                preview_label.setText(f"예: {first_value}")
            else:
                preview_label.setText("")
    
    def _reset_mapping(self):
        """매핑 초기화 (자동 감지 상태로)"""
        for combo in self.mapping_combos.values():
            if isinstance(combo, QComboBox):
                combo.setCurrentIndex(0)
        
        self._apply_auto_mapping()
    
    def _validate_and_accept(self):
        """매핑 유효성 검사 후 확인"""
        # 필수 필드 확인
        required_fields = self._get_required_fields()
        missing_fields = []
        
        for std_col, combo in self.mapping_combos.items():
            if std_col.endswith('_preview'):
                continue
            
            original_col = combo.currentData()
            
            if original_col:
                self.column_mapping[std_col] = original_col
            elif std_col in required_fields:
                description = self.STANDARD_COLUMNS[self.dataset_type][std_col]
                missing_fields.append(description)
        
        if missing_fields:
            QMessageBox.warning(
                self,
                "필수 필드 누락",
                f"다음 필수 필드를 매핑해야 합니다:\n\n" + "\n".join(f"• {f}" for f in missing_fields)
            )
            return
        
        self.accept()
    
    def _get_required_fields(self) -> List[str]:
        """필수 필드 목록 반환"""
        if self.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            return ['gene_id', 'log2fc', 'adj_pvalue']
        elif self.dataset_type == DatasetType.GO_ANALYSIS:
            return ['term', 'gene_count', 'fdr']
        return []
    
    def get_mapping(self) -> Dict[str, str]:
        """
        확정된 매핑 반환
        
        Returns:
            {표준 컬럼: 원본 컬럼} 매핑
        """
        return self.column_mapping
    
    def should_save_mapping(self) -> bool:
        """매핑을 저장해야 하는지 여부"""
        return self.save_mapping_check.isChecked()
