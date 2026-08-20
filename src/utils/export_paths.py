"""Export/Save 대화상자의 '마지막 사용 폴더' 기억 유틸.

QFileDialog.getSaveFileName 을 매번 기본 경로(홈 디렉토리 등) 없이 호출하면 사용자가
매 export/bundle/save 마다 원하는 폴더까지 다시 찾아가야 한다. 이 모듈은 QSettings 에
마지막으로 저장한 폴더 하나를 기억해 두고, 다음 호출 때 그 폴더를 시작 위치로 제안한다.
"""
from __future__ import annotations

import os
from typing import Tuple

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QFileDialog, QWidget

_ORG = "RNASeqDataView"
_APP = "MainWindow"   # 앱 전역에서 이미 쓰는 QSettings 스코프와 통일
_KEY = "export/last_dir"


def get_last_export_dir() -> str:
    """마지막으로 저장한 폴더(유효하지 않으면 홈 디렉토리)."""
    d = QSettings(_ORG, _APP).value(_KEY, "")
    if d and os.path.isdir(d):
        return d
    return os.path.expanduser("~")


def remember_export_dir(file_path: str) -> None:
    """저장된 파일 경로에서 폴더를 추출해 다음 기본 위치로 기억한다."""
    if not file_path:
        return
    d = os.path.dirname(file_path)
    if d:
        QSettings(_ORG, _APP).setValue(_KEY, d)


def remembered_save_path(parent: QWidget, caption: str, default_name: str,
                         file_filter: str) -> Tuple[str, str]:
    """QFileDialog.getSaveFileName 의 대체 — 마지막 저장 폴더를 기본 위치로 제안하고,
    선택 성공 시 그 폴더를 다음 기본 위치로 기억한다. 반환 형식은 원본과 동일:
    (path, selected_filter).

    default_name 이 파일명만이면(디렉토리 없음) 기억된 폴더와 합쳐 시작 경로로 쓴다.
    default_name 에 이미 디렉토리가 포함돼 있으면(호출부가 특정 위치를 의도) 그대로 존중한다.
    """
    start = default_name if os.path.dirname(default_name) else os.path.join(
        get_last_export_dir(), default_name)
    path, selected_filter = QFileDialog.getSaveFileName(parent, caption, start, file_filter)
    if path:
        remember_export_dir(path)
    return path, selected_filter
