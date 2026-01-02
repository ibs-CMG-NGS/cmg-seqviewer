"""
Scientific Notation Delegate for QTableView

FDR, adj-pvalue 등 매우 작은 값을 과학적 표기법으로 표시하는 커스텀 delegate입니다.
"""

from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtCore import Qt


class ScientificDelegate(QStyledItemDelegate):
    """과학적 표기법으로 숫자를 표시하는 Delegate"""
    
    def __init__(self, threshold=0.01, precision=2, parent=None):
        """
        Args:
            threshold: 이 값보다 작으면 scientific notation 사용
            precision: 유효숫자 자릿수
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.threshold = threshold
        self.precision = precision
    
    def displayText(self, value, locale):
        """
        값을 표시할 텍스트로 변환
        
        Args:
            value: 원본 값
            locale: 로케일 (사용 안 함)
            
        Returns:
            표시할 텍스트
        """
        try:
            # 숫자로 변환 시도
            num_value = float(value)
            
            # 0이거나 매우 작은 값
            if num_value == 0:
                return "0"
            
            # 음수 처리
            is_negative = num_value < 0
            abs_value = abs(num_value)
            
            # Threshold보다 작거나 매우 큰 값은 scientific notation
            if abs_value < self.threshold or abs_value >= 1000:
                # Scientific notation with precision
                text = f"{num_value:.{self.precision}e}"
                return text
            else:
                # 일반 소수점 표기 (최대 4자리)
                text = f"{num_value:.4f}".rstrip('0').rstrip('.')
                return text
                
        except (ValueError, TypeError):
            # 숫자가 아닌 경우 원본 그대로 반환
            return str(value)


class HighPrecisionDelegate(QStyledItemDelegate):
    """
    더 높은 정밀도로 숫자를 표시하는 Delegate
    
    - 0.001 이상: 소수점 4자리
    - 0.001 미만: 과학적 표기법 (3자리 유효숫자)
    """
    
    def displayText(self, value, locale):
        try:
            num_value = float(value)
            
            if num_value == 0:
                return "0"
            
            abs_value = abs(num_value)
            
            if abs_value >= 0.001:
                # 소수점 4자리까지 표시
                text = f"{num_value:.4f}".rstrip('0').rstrip('.')
                return text
            else:
                # 과학적 표기법 (3자리 유효숫자)
                return f"{num_value:.3e}"
                
        except (ValueError, TypeError):
            return str(value)


class AdaptiveScientificDelegate(QStyledItemDelegate):
    """
    값의 크기에 따라 자동으로 표기법을 선택하는 Delegate
    
    권장 사용:
    - FDR, adj-pvalue 컬럼
    - p-value 컬럼
    """
    
    def displayText(self, value, locale):
        try:
            num_value = float(value)
            
            if num_value == 0:
                return "0"
            
            abs_value = abs(num_value)
            
            # 범위별로 다른 표기법 사용
            if abs_value >= 1.0:
                # 1 이상: 소수점 2자리
                return f"{num_value:.2f}"
            elif abs_value >= 0.01:
                # 0.01 ~ 1: 소수점 3자리
                return f"{num_value:.3f}"
            elif abs_value >= 0.0001:
                # 0.0001 ~ 0.01: 소수점 4자리
                return f"{num_value:.4f}"
            else:
                # 0.0001 미만: 과학적 표기법 (2자리 유효숫자)
                return f"{num_value:.2e}"
                
        except (ValueError, TypeError):
            return str(value)
