"""버전 문자열이 여러 파일에서 어긋나지 않는지 검사한다.

`src/version.py` 가 단일 소스이고, 빌드/설치/문서 쪽 사본은 여기서 검증한다.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _version() -> str:
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']',
                      _read("src/version.py"), re.MULTILINE)
    assert match, "src/version.py 에 __version__ 이 없습니다"
    return match.group(1)


VERSION = _version()


def test_setup_py_reads_version_file():
    setup_py = _read("setup.py")
    assert "src/version.py" in setup_py, "setup.py 는 버전을 하드코딩하지 말고 src/version.py 를 읽어야 합니다"
    assert "version=VERSION" in setup_py


def test_installer_iss_matches():
    assert f'#define MyAppVersion "{VERSION}"' in _read("installer.iss")


def test_macos_spec_matches():
    spec = _read("cmg-seqviewer-macos.spec")
    assert "APP_VERSION" in spec, "macOS spec 은 src/version.py 의 APP_VERSION 을 사용해야 합니다"
    assert f"'{VERSION}'" not in spec, "macOS spec 에 하드코딩된 버전이 남아 있습니다"


def test_project_io_uses_version_module():
    project_io = _read("src/utils/project_io.py")
    assert "from version import __version__ as APP_VERSION" in project_io
    assert '"app_version": APP_VERSION' in project_io


def test_readme_badge_and_citation_match():
    readme = _read("README.md")
    assert f"release-v{VERSION}-" in readme, "README 배지 버전이 다릅니다"
    assert f"version = {{{VERSION}}}" in readme, "README 인용 버전이 다릅니다"
