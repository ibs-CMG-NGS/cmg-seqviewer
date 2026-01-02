"""
RNA-Seq Data Analysis and Visualization Program
Main Entry Point

이 프로그램은 RNA-seq 데이터를 조회하고 추가 분석을 진행하여,
사용자가 엑셀에서 수행하는 작업을 전문적이면서도 손쉽게 대체할 수 있도록 지원합니다.

Architecture:
    - MVP (Model-View-Presenter) 패턴 사용
    - FSM (Finite State Machine) 기반 상태 관리
    - PyQt6 기반 GUI
"""

import sys
import os
import atexit
import logging

# PyInstaller 빌드 환경에서 src 경로 설정
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 경우
    application_path = sys._MEIPASS
    src_path = os.path.join(application_path, 'src')
else:
    # 일반 Python 실행
    application_path = os.path.dirname(os.path.abspath(__file__))
    src_path = application_path

# src를 Python path에 추가
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 이제 상대 import 사용 가능
from gui.main_window import MainWindow
from core.logger import setup_logger


def cleanup_qt_handlers():
    """Qt 로그 핸들러 정리 (atexit 에러 방지)"""
    try:
        root_logger = logging.getLogger()
        handlers_to_remove = []
        
        # QtLogHandler 찾기
        for handler in root_logger.handlers[:]:
            if handler.__class__.__name__ == 'QtLogHandler':
                handlers_to_remove.append(handler)
        
        # 핸들러 제거
        for handler in handlers_to_remove:
            try:
                root_logger.removeHandler(handler)
                handler.close()
            except Exception:
                pass
    except Exception:
        pass


def main():
    """프로그램 진입점"""
    # atexit 핸들러 등록 (logging shutdown보다 먼저 실행되도록)
    atexit.register(cleanup_qt_handlers)
    
    # 로거 초기화
    logger = setup_logger()
    logger.info("=" * 80)
    logger.info("RNA-Seq Data Analysis Program Starting...")
    logger.info("=" * 80)
    
    # Qt 애플리케이션 설정
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("RNA-Seq Data Analyzer")
    app.setOrganizationName("RNA-Seq Analysis Team")
    
    # 메인 윈도우 생성 및 표시
    main_window = MainWindow()
    main_window.show()
    
    logger.info("Main window initialized successfully")
    
    # 이벤트 루프 시작
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
