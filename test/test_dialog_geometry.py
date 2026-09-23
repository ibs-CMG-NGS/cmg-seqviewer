"""
utils.dialog_geometry 테스트.

- remember_geometry: 저장된 값 복원 + 닫힐 때 재저장
- clamp_to_current_screen: 다른 화면(해상도/DPI)에서 저장된 geometry가 지금
  화면보다 크거나 화면 밖으로 나가면 안으로 보정 (본문 docstring 참고)
"""

from PyQt6.QtCore import QRect, QSettings
from PyQt6.QtWidgets import QApplication, QDialog, QWidget

from utils.dialog_geometry import clamp_to_current_screen, remember_geometry


# 모듈 전역에서 참조를 붙잡아둔다 — QApplication.instance() or QApplication([])를
# 반환값을 저장하지 않고 호출하면, 새로 만든 QApplication의 유일한 파이썬 참조가
# 함수 반환 직후 GC되어 이후 위젯 생성이 "Must construct a QApplication before a
# QWidget"로 죽는다(실측: pytest 하에서 재현, 순수 스크립트 top-level 변수 보관 시엔 정상).
_QAPP = QApplication.instance() or QApplication([])


def _app():
    return _QAPP


def _clear_settings(key: str):
    settings = QSettings("RNASeqDataView", "MainWindow")
    settings.remove(f"dialogGeometry/{key}")


def test_remember_geometry_restores_saved_value_and_resaves_on_close():
    _app()
    key = "TestDialogRestoreRoundtrip"
    _clear_settings(key)
    try:
        d1 = QDialog()
        d1.resize(600, 400)
        remember_geometry(d1, key)
        d1.move(50, 60)
        d1.resize(700, 500)
        d1.show()   # close()가 finished를 내보내려면 먼저 보여야 함 (실제 사용과 동일)
        d1.close()  # QDialog.close() emits finished -> _save()

        d2 = QDialog()
        d2.resize(600, 400)  # 기본값 (저장된 값이 있으면 무시돼야 함)
        remember_geometry(d2, key)
        assert d2.width() == 700
        assert d2.height() == 500
    finally:
        _clear_settings(key)


def test_remember_geometry_first_run_keeps_default_size():
    _app()
    key = "TestDialogNoSavedValue"
    _clear_settings(key)
    d = QDialog()
    d.resize(321, 234)
    remember_geometry(d, key)
    assert d.width() == 321
    assert d.height() == 234


def test_clamp_shrinks_geometry_larger_than_available_screen(monkeypatch):
    app = _app()
    screen = app.primaryScreen()
    avail = screen.availableGeometry()

    w = QWidget()
    # 다른(더 큰) 화면에서 저장된 것처럼 현재 화면보다 훨씬 큰 geometry를 강제 지정.
    oversized = QRect(avail.x(), avail.y(), avail.width() + 2000, avail.height() + 2000)
    monkeypatch.setattr(type(w), "screen", lambda self: screen)
    w.setGeometry(oversized)

    clamp_to_current_screen(w)

    geo = w.geometry()
    assert geo.width() <= avail.width()
    assert geo.height() <= avail.height()


def test_clamp_moves_geometry_back_onto_screen(monkeypatch):
    app = _app()
    screen = app.primaryScreen()
    avail = screen.availableGeometry()

    w = QWidget()
    w.resize(400, 300)
    monkeypatch.setattr(type(w), "screen", lambda self: screen)
    # 화면 오른쪽/아래로 한참 벗어난 위치 (다른 모니터 좌표계에서 저장된 상황 시뮬레이션).
    w.move(avail.x() + avail.width() + 5000, avail.y() + avail.height() + 5000)

    clamp_to_current_screen(w)

    geo = w.geometry()
    assert geo.x() + geo.width() <= avail.x() + avail.width()
    assert geo.y() + geo.height() <= avail.y() + avail.height()
    assert geo.x() >= avail.x()
    assert geo.y() >= avail.y()


def test_clamp_leaves_geometry_that_already_fits_untouched(monkeypatch):
    app = _app()
    screen = app.primaryScreen()
    avail = screen.availableGeometry()

    w = QWidget()
    monkeypatch.setattr(type(w), "screen", lambda self: screen)
    fits = QRect(avail.x() + 10, avail.y() + 10, min(400, avail.width() - 20),
                 min(300, avail.height() - 20))
    w.setGeometry(fits)

    clamp_to_current_screen(w)

    assert w.geometry() == fits


def test_clamp_never_shrinks_below_widgets_own_minimum_size(monkeypatch):
    app = _app()
    screen = app.primaryScreen()
    avail = screen.availableGeometry()

    w = QWidget()
    monkeypatch.setattr(type(w), "screen", lambda self: screen)
    min_w = avail.width() + 100   # 화면보다 큰 최소 크기 (극단 케이스)
    min_h = avail.height() + 100
    w.setMinimumSize(min_w, min_h)
    w.setGeometry(avail.x(), avail.y(), min_w, min_h)

    clamp_to_current_screen(w)

    # Qt의 setGeometry는 위젯 자신의 최소 크기보다 작게 만들 수 없다 —
    # 화면보다 최소 크기가 커도 화면 크기로 억지로 줄이지 않는다.
    assert w.width() >= min_w
    assert w.height() >= min_h


def test_clamp_returns_early_without_screen(monkeypatch):
    w = QWidget()
    monkeypatch.setattr(type(w), "screen", lambda self: None)
    monkeypatch.setattr(QApplication, "primaryScreen", staticmethod(lambda: None))
    geo_before = w.geometry()
    clamp_to_current_screen(w)  # should not raise
    assert w.geometry() == geo_before
