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


_DPI_AWARENESS_STATUS = "unknown"


def _is_wsl() -> bool:
    """WSL/WSLg 환경인지 감지한다."""
    try:
        import platform
        return ('microsoft' in platform.uname().release.lower()
                or bool(os.environ.get('WSL_DISTRO_NAME')))
    except Exception:
        return False


def _enable_per_monitor_dpi_awareness() -> None:
    """Windows에서 Per-Monitor V2 DPI awareness를 가능한 한 일찍 켠다.

    혼합 DPI(예: 120% 노트북 + 100% 외부 모니터)에서 Qt 메뉴/팝업이 닫힌 뒤
    이전 프레임이 남는 ghosting은 프로세스가 System DPI aware일 때 발생할 수
    있다. PyInstaller 빌드는 `cmg-seqviewer.manifest`로 동일 설정을 넣지만,
    소스 실행(`python src/main.py`)에서는 이 호출이 그 역할을 한다.
    이미 DPI awareness가 설정된 경우(예: python.exe manifest) 호출은 실패할
    수 있으며, 그 경우 조용히 무시한다.
    """
    global _DPI_AWARENESS_STATUS
    if sys.platform != 'win32':
        _DPI_AWARENESS_STATUS = "not_windows"
        return
    try:
        import ctypes
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            _DPI_AWARENESS_STATUS = "per_monitor_v2"
            return
    except Exception:
        pass
    try:
        import ctypes
        # PROCESS_PER_MONITOR_DPI_AWARE = 2 (Windows 8.1+ fallback)
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            _DPI_AWARENESS_STATUS = "per_monitor"
            return
    except Exception:
        pass
    _DPI_AWARENESS_STATUS = "unchanged"




def _xcb_plugin_deps_available() -> tuple[bool, list[str]]:
    """Qt xcb 플랫폼 플러그인이 요구하는 시스템 라이브러리 존재 여부.

    Qt 6.5+ xcb 플러그인은 libxcb-cursor0 외에도 icccm/keysyms/shape 등
    여러 xcb 라이브러리를 필요로 한다. 일부만 설치된 상태에서 xcb를
    강제하면 앱이 Aborted로 죽으므로, 전부 있을 때만 xcb를 선택한다.
    """
    libs = [
        'xcb-cursor', 'xcb-icccm', 'xcb-image', 'xcb-keysyms',
        'xcb-randr', 'xcb-render-util', 'xcb-shape', 'xcb-sync',
        'xcb-xfixes', 'xcb-xinerama', 'xcb-xkb', 'xkbcommon-x11',
    ]
    missing = []
    try:
        import ctypes.util
        import glob
        for name in libs:
            if ctypes.util.find_library(name):
                continue
            pattern = f'/usr/lib/*/lib{name}.so*'
            alt = f'/lib/*/lib{name}.so*'
            if glob.glob(pattern) or glob.glob(alt):
                continue
            missing.append(name)
    except Exception:
        return False, libs
    return (not missing), missing



def _pick_cursor_theme() -> str | None:
    """설치된 X11 커서 테마 중 하나를 고른다 (WSLg xcb 커서 표시용)."""
    try:
        from pathlib import Path as _Path
        for name in ('Adwaita', 'Yaru', 'Humanity', 'hicolor', 'default'):
            if (_Path('/usr/share/icons') / name).is_dir():
                return name
    except Exception:
        pass
    return None

_enable_per_monitor_dpi_awareness()

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

# If running from a PyInstaller bundle, ensure working directory and
# environment are set correctly for Finder launches
if getattr(sys, 'frozen', False):
    try:
        # Set working directory to bundle location
        os.chdir(application_path)
        # Also set environment variable for resource lookup
        os.environ['RESOURCEPATH'] = application_path
    except Exception:
        # Silent fail - frozen apps don't have terminal output
        pass

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
    logger.info(f"DPI awareness: {_DPI_AWARENESS_STATUS}")
    
    # WSLg의 Wayland 백엔드는 클라이언트가 팝업의 전역 위치를 지정하지 못해
    # 메뉴가 화면 왼쪽 위에 뜨는 문제가 있다. xcb(XWayland)에서는 QMenu.move()가
    # 동작하므로, libxcb-cursor0가 설치되어 있으면 xcb를 우선 사용한다.
    # 없으면 Qt xcb 플러그인이 로드되지 않으므로 Wayland로 fallback 한다.
    # 사용자가 QT_QPA_PLATFORM을 지정하면 그 값을 존중한다.
    if _is_wsl():
        logger.warning(
            "WSLg detected: mixed-DPI monitor popup coordinates can be "
            "unreliable. Wayland is used by default (cursor is visible); "
            "a native Windows build is recommended for multi-monitor use.")
        _requested = os.environ.get('QT_QPA_PLATFORM', '')
        if not _requested:
            # Wayland: WSLg compositor가 커서를 그려 주므로 커서가 보인다.
            os.environ['QT_QPA_PLATFORM'] = 'wayland'
        elif _requested.startswith('xcb'):
            # xcb는 QMenu.move()가 동작하지만 WSLg에서 커서가 안 보일 수 있다.
            # 의존 라이브러리가 없으면 크래시하므로 Wayland로 fallback.
            _xcb_ok, _xcb_missing = _xcb_plugin_deps_available()
            if not _xcb_ok:
                logger.warning(
                    "xcb 의존 라이브러리 누락: %s — Wayland로 fallback.",
                    ', '.join(_xcb_missing))
                os.environ['QT_QPA_PLATFORM'] = 'wayland'
            else:
                _theme = _pick_cursor_theme()
                if _theme:
                    os.environ.setdefault('XCURSOR_THEME', _theme)
                os.environ.setdefault('XCURSOR_SIZE', '24')
                logger.info(
                    "xcb requested: XCURSOR_THEME=%s XCURSOR_SIZE=%s",
                    os.environ.get('XCURSOR_THEME', '(unset)'),
                    os.environ.get('XCURSOR_SIZE', '(unset)'))
    logger.info(f"Qt platform: {os.environ.get('QT_QPA_PLATFORM', '(default)')}")
    logger.info(
        "Cursor env: XCURSOR_THEME=%s XCURSOR_SIZE=%s WAYLAND_DISPLAY=%s",
        os.environ.get('XCURSOR_THEME', '(unset)'),
        os.environ.get('XCURSOR_SIZE', '(unset)'),
        os.environ.get('WAYLAND_DISPLAY', '(unset)'))

    # Qt 애플리케이션 설정
    # 혼합 DPI(예: 120% 노트북 + 100% 외부 모니터)에서 PassThrough(1.2배)는
    # Windows에서 메뉴 팝업이 엉뚱한 모니터 좌표에 뜨거나 이전 프레임이 남는
    # 문제를 일으킬 수 있다. 기본은 Round(정수 배율)로 두고, 필요하면
    # CMG_DPI_ROUNDING_POLICY=PassThrough|RoundPreferFloor|Floor|Ceil 로 바꿀 수 있다.
    _policy_name = os.environ.get("CMG_DPI_ROUNDING_POLICY", "Round")
    _policy = getattr(
        Qt.HighDpiScaleFactorRoundingPolicy,
        _policy_name,
        Qt.HighDpiScaleFactorRoundingPolicy.Round,
    )
    QApplication.setHighDpiScaleFactorRoundingPolicy(_policy)
    logger.info(f"High-DPI rounding policy: {_policy_name}")
    
    app = QApplication(sys.argv)
    logger.info(f"Qt platform plugin: {app.platformName()}")
    app.setApplicationName("RNA-Seq Data Analyzer")
    app.setOrganizationName("RNA-Seq Analysis Team")

    # 작업표시줄 및 전체 앱 아이콘 설정 (QApplication 레벨)
    # setWindowIcon을 MainWindow에서만 하면 타이틀바에만 적용되고
    # Windows 작업표시줄에는 표시되지 않으므로 app에도 동일하게 설정
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont as QFontIcon
    from PyQt6.QtCore import QRect   # Qt는 파일 상단에서 이미 import됨
    _pixmap = QPixmap(64, 64)
    _pixmap.fill(Qt.GlobalColor.transparent)
    _painter = QPainter(_pixmap)
    _painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _painter.setBrush(QColor(70, 130, 180))
    _painter.setPen(Qt.PenStyle.NoPen)
    _painter.drawEllipse(2, 2, 60, 60)
    _painter.setPen(QColor(255, 255, 255))
    _painter.setFont(QFontIcon("Arial", 28, QFontIcon.Weight.Bold))
    _painter.drawText(QRect(0, 0, 64, 64), Qt.AlignmentFlag.AlignCenter, "🧬")
    _painter.end()
    app.setWindowIcon(QIcon(_pixmap))
    
    # Force light theme for consistent UI across platforms
    # macOS dark mode causes text visibility issues.
    # CMG_UI_STYLE=windowsvista 로 바꾸면 Windows 네이티브 메뉴 렌더링을 테스트할 수 있다.
    _ui_style = os.environ.get('CMG_UI_STYLE', 'Fusion')
    app.setStyle(_ui_style)
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    # 메인 윈도우 생성 및 표시
    main_window = MainWindow()
    main_window.show()
    
    logger.info("Main window initialized successfully")
    
    # 이벤트 루프 시작
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
