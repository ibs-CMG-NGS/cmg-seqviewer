"""
다이얼로그 위치/크기 기억

QDialog는 기본적으로 열릴 때마다 코드에 지정된 초기 크기로 리셋된다.
이 모듈은 메인 윈도우가 이미 쓰고 있는 것과 동일한 QSettings 스토어
("RNASeqDataView", "MainWindow")에 다이얼로그별 geometry를 저장/복원해서,
다음에 열 때 마지막으로 두었던 위치/크기 그대로 뜨도록 해준다.

사용법:
    class MyDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("...")
            self.resize(600, 400)          # 최초 실행 시(저장된 값 없을 때)의 기본 크기
            remember_geometry(self)        # __init__ 마지막에 한 줄만 추가
            ...

key를 생략하면 클래스명을 사용한다. main_window.py 안에서 만드는 이름 없는
QDialog(self)처럼 클래스가 전부 "QDialog"로 겹치는 경우에는 명시적으로
구분되는 key를 넘긴다 (예: remember_geometry(dlg, "AboutDialog")).
"""

from typing import Optional

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QDialog

_ORG = "RNASeqDataView"
_APP = "MainWindow"


def remember_geometry(dialog: QDialog, key: Optional[str] = None) -> None:
    """다이얼로그의 위치/크기를 저장된 값으로 복원하고, 닫힐 때 다시 저장하도록 연결한다.

    Args:
        dialog: 대상 QDialog (이미 기본 크기가 설정된 상태여야 함 —
                저장된 값이 없을 때는 그 기본 크기가 그대로 쓰인다)
        key: QSettings에 저장할 때 쓸 식별자. 생략 시 dialog의 클래스명 사용.
    """
    if key is None:
        key = type(dialog).__name__

    settings = QSettings(_ORG, _APP)
    settings_key = f"dialogGeometry/{key}"

    saved = settings.value(settings_key)
    if saved:
        try:
            dialog.restoreGeometry(saved)
        except Exception:
            pass

    def _save(*_args) -> None:
        try:
            settings.setValue(settings_key, dialog.saveGeometry())
        except Exception:
            pass

    dialog.finished.connect(_save)
