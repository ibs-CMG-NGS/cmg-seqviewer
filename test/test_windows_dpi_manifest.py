"""Windows 빌드가 Per-Monitor V2 DPI aware인지 확인하는 회귀 테스트.

혼합 DPI(예: 120% 노트북 + 100% 외부 모니터) 환경에서 Qt 메뉴 팝업이
남는 ghosting은 프로세스가 System DPI aware일 때 발생할 수 있다.
PyInstaller spec이 PerMonitorV2 manifest를 포함해야 한다.
"""

from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "cmg-seqviewer.manifest"


def test_manifest_enables_per_monitor_v2():
    assert MANIFEST.exists()
    root = ET.fromstring(MANIFEST.read_text(encoding="utf-8"))
    text = MANIFEST.read_text(encoding="utf-8")
    assert "PerMonitorV2" in text
    # XML 자체가 유효한지 확인 (namespace 무관)
    assert root.tag.endswith("assembly")


def test_windows_specs_reference_manifest():
    for spec_name in ("rna-seq-viewer.spec", "rna-seq-viewer-onefile.spec"):
        text = (ROOT / spec_name).read_text(encoding="utf-8")
        assert "manifest='cmg-seqviewer.manifest'" in text, spec_name


def test_source_run_forces_per_monitor_dpi():
    text = (ROOT / "src" / "main.py").read_text(encoding="utf-8")
    assert "_enable_per_monitor_dpi_awareness()" in text
    assert "SetProcessDpiAwarenessContext" in text
    assert "SetProcessDpiAwareness(2)" in text
