"""
DataFrame-backed table model for the central data view.

QTableWidget는 셀마다 QTableWidgetItem 객체를 만들어 전체 DataFrame을 메모리에
올린다. ATAC-seq peak 파일처럼 행이 10만~18만에 달하면 데이터셋 하나당 수백만 개의
셀 객체가 상주하여 로드·탭 전환·스크롤이 느려진다.

DataFrameTableModel은 QTableView와 함께 쓰여, 화면에 보이는 셀만 data()에서 지연
포맷한다. 셀 객체를 만들지 않으므로 메모리는 DataFrame 하나 크기로 수렴하고,
로드/전환/스크롤 비용이 행 수와 무관해진다.
"""

import numpy as np
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


class DataFrameTableModel(QAbstractTableModel):
    """pandas DataFrame을 백엔드로 사용하는 읽기 전용 테이블 모델."""

    def __init__(self, df, decimal_precision: int = 2, scientific_cols=None, parent=None):
        super().__init__(parent)
        # 표시용 DataFrame (컬럼 필터링이 끝난 상태로 전달됨)
        self._df = df.reset_index(drop=True)
        self._precision = decimal_precision
        # scientific notation을 적용할 컬럼명 집합
        self._sci_cols = set(scientific_cols) if scientific_cols else set()
        # 표시 행 → 원본 DataFrame의 위치 인덱스 매핑 (정렬 후에도 원본 행 추적)
        self._source = np.arange(len(self._df))

    # ── Qt 모델 인터페이스 ────────────────────────────────────────────
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._df)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self._df.shape[1]

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < self._df.shape[1]:
                return str(self._df.columns[section])
        else:
            if 0 <= section < len(self._df):
                return str(section + 1)
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        value = self._df.iat[index.row(), index.column()]
        return self._format(value, self._df.columns[index.column()])

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if not (0 <= column < self._df.shape[1]):
            return
        self.layoutAboutToBeChanged.emit()
        col = self._df.columns[column]
        ascending = (order == Qt.SortOrder.AscendingOrder)
        # 현재 표시 순서 기준의 위치 인덱스 (mergesort로 안정 정렬, NaN은 항상 마지막)
        sorted_positions = self._df[col].sort_values(
            ascending=ascending, kind='mergesort', na_position='last'
        ).index.to_numpy()
        self._df = self._df.iloc[sorted_positions].reset_index(drop=True)
        self._source = self._source[sorted_positions]
        self.layoutChanged.emit()

    # ── 헬퍼 ─────────────────────────────────────────────────────────
    def dataframe(self):
        """현재 표시 순서의 DataFrame(컬럼 필터링·정렬 반영). export/재구성용."""
        return self._df

    def source_row(self, display_row: int) -> int:
        """표시 행 인덱스 → 원본 DataFrame의 위치 인덱스."""
        if 0 <= display_row < len(self._source):
            return int(self._source[display_row])
        return display_row

    def set_params(self, decimal_precision: int, scientific_cols=None):
        """정밀도/컬럼레벨 변경 시 포맷만 갱신 (재정렬·재구성 없음)."""
        self._precision = decimal_precision
        self._sci_cols = set(scientific_cols) if scientific_cols else set()
        if len(self._df) and self._df.shape[1]:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._df) - 1, self._df.shape[1] - 1)
            self.dataChanged.emit(top_left, bottom_right,
                                  [Qt.ItemDataRole.DisplayRole])

    def _format(self, value, col_name) -> str:
        """populate_table의 기존 포맷 규칙을 그대로 재현."""
        if isinstance(value, float):
            if col_name in self._sci_cols:
                abs_value = abs(value)
                if abs_value == 0:
                    return "0"
                elif abs_value >= 1.0:
                    return f"{value:.2f}"
                elif abs_value >= 0.01:
                    return f"{value:.3f}"
                elif abs_value >= 0.0001:
                    return f"{value:.4f}"
                else:
                    return f"{value:.2e}"
            return f"{value:.{self._precision}f}"
        return str(value)
