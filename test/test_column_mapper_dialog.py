"""
ColumnMapperDialog 필수 필드 테스트 (반입 일반성 감사 후속).

_get_required_fields()가 STANDARD_COLUMNS의 실제 키와 일치하는지 (예전엔 GO의
'term'이 'description'과 안 맞아 필수 체크가 무력화돼 있었음), 그리고 ATAC_SEQ가
DE/GO처럼 수동 매핑 UI를 지원하는지 확인한다.
"""

from PyQt6.QtWidgets import QApplication

from models.data_models import DatasetType
from gui.column_mapper_dialog import ColumnMapperDialog

_QAPP = QApplication.instance() or QApplication([])


def test_required_fields_match_standard_columns_keys():
    for dataset_type in (DatasetType.DIFFERENTIAL_EXPRESSION, DatasetType.GO_ANALYSIS,
                         DatasetType.ATAC_SEQ):
        dlg = ColumnMapperDialog.__new__(ColumnMapperDialog)
        dlg.dataset_type = dataset_type
        required = dlg._get_required_fields()
        available_keys = set(ColumnMapperDialog.STANDARD_COLUMNS[dataset_type].keys())
        assert required, f"{dataset_type} has no required fields"
        for field in required:
            assert field in available_keys, (
                f"{dataset_type}: required field {field!r} is not a mapping-combo key "
                f"({available_keys}) — the required-field check would be silently inert")


def test_atac_seq_has_standard_columns_entry():
    assert DatasetType.ATAC_SEQ in ColumnMapperDialog.STANDARD_COLUMNS
    cols = ColumnMapperDialog.STANDARD_COLUMNS[DatasetType.ATAC_SEQ]
    assert {'peak_id', 'log2fc', 'adj_pvalue'}.issubset(cols.keys())


def test_go_required_fields_no_longer_include_nonexistent_term_key():
    dlg = ColumnMapperDialog.__new__(ColumnMapperDialog)
    dlg.dataset_type = DatasetType.GO_ANALYSIS
    assert 'term' not in dlg._get_required_fields()
    assert 'description' in dlg._get_required_fields()
