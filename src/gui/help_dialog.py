"""
Help dialog — Markdown 기반 F1 도움말 뷰어 (docs/user/help/*.md — wiki 운영).

개편 (HELP_SYSTEM_OVERHAUL_PLAN.md):
- 콘텐츠 1원본: `docs/user/help/NN-slug.md` (섹션별 markdown, 파일명 번호 정렬).
- 뷰어: TOC(파일 `#` 제목) + 검색 필터 + `QTextBrowser.setMarkdown()` (PyQt6 네이티브 md/GFM 표 렌더).
- 경로 해석: 개발 = repo `docs/user/help/`; frozen = 번들 datas 후보; 부재 시 안내 문구.
"""

from pathlib import Path
import re
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLineEdit, QListWidget, QPushButton, QSplitter,
    QTextBrowser, QVBoxLayout,
)

HELP_DIR_NAME = "help"


def create_help_icon() -> QIcon:
    """help 아이콘 (기존과 동일)."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(30, 144, 255))  # Dodger Blue
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 60, 60)
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Arial", 36, QFont.Weight.Bold)
    painter.setFont(font)
    from PyQt6.QtCore import QRect
    painter.drawText(QRect(0, 0, 64, 64), Qt.AlignmentFlag.AlignCenter, "?")
    painter.end()
    return QIcon(pixmap)


def resolve_help_dir() -> Path:
    """docs/user/help 디렉토리 해석 (개발 repo → frozen 번들 후보)."""
    candidates = [
        Path(__file__).resolve().parents[2] / "docs" / "user" / HELP_DIR_NAME,
    ]
    if getattr(sys, "frozen", False):
        from pathlib import Path as _P
        base = _P(sys.executable).resolve().parent
        candidates += [
            base / "docs" / "user" / HELP_DIR_NAME,
            base / "_internal" / "docs" / "user" / HELP_DIR_NAME,
        ]
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(_P(meipass) / "docs" / "user" / HELP_DIR_NAME)
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


def _title_from_md(text: str, fallback: str) -> str:
    """첫 `# ` 헤딩을 TOC 제목으로 사용 (없으면 파일명)."""
    m = re.match(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else fallback


class HelpDialog(QDialog):
    """Markdown 기반 도움말 (TOC + 검색 + QTextBrowser.setMarkdown)."""

    def __init__(self, parent=None, help_dir: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle("Help — CMG-SeqViewer")
        self.resize(900, 640)
        self.help_dir = help_dir or resolve_help_dir()
        self._files: list[Path] = []       # 파일명 오름차순
        self._titles: list[str] = []
        self._contents: list[str] = []
        self._init_ui()
        self._load_content()

    # ------------------------------------------------------------------ UI

    def _init_ui(self):
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search help sections...")
        self.search_edit.textChanged.connect(self._apply_filter)
        left.addWidget(self.search_edit)

        self.toc_list = QListWidget()
        self.toc_list.setMaximumWidth(280)
        self.toc_list.currentRowChanged.connect(self._on_toc_selection_changed)
        left.addWidget(self.toc_list)

        left_widget = self._wrap(left)
        splitter.addWidget(left_widget)

        self.content_browser = QTextBrowser()
        # HTML 인라인 링크를 직접 처리: http(s)는 외부 브라우저, 로컬 .md는 인앱 렌더 + 앵커 이동
        self.content_browser.setOpenLinks(False)
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.anchorClicked.connect(self._on_anchor_clicked)
        # 로컬 이미지(assets/*.png) 렌더: markdown 이미지 상대경로의 기준 URL 설정
        if self.help_dir.is_dir():
            self.content_browser.document().setBaseUrl(
                __import__("PyQt6.QtCore", fromlist=["QUrl"]).QUrl.fromLocalFile(
                    str(self.help_dir) + "/"))
        splitter.addWidget(self.content_browser)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    @staticmethod
    def _wrap(layout) -> "QWidget":
        from PyQt6.QtWidgets import QWidget
        w = QWidget()
        w.setLayout(layout)
        return w

    # ---------------------------------------------------------- navigation

    @staticmethod
    def _slug_of(text: str) -> str:
        """헤딩 텍스트 → 앵커 슬러그 (예: '5.1 Overview' → '5-1-overview')."""
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
        return "-".join(p for p in slug.split("-") if p)

    def _on_anchor_clicked(self, url):
        """링크 처리: http(s)는 외부 브라우저; 로컬 .md는 인앱 렌더(+앵커 스크롤)."""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        scheme = url.scheme().lower()
        if scheme in ("http", "https"):
            QDesktopServices.openUrl(url)
            return
        assert self.help_dir.is_dir(), "help dir unavailable for anchor navigation"
        raw = url.path() if not url.isRelative() else url.toString()
        candidate = self.help_dir / raw
        if not candidate.exists():
            candidate = (self.help_dir.parent / raw)   # ../user-guide.md 등 docs 루트
        if not candidate.is_file() or candidate.suffix != ".md":
            return
        text = candidate.read_text(encoding="utf-8")
        self.content_browser.setMarkdown(text)
        # TOC에서 해당 섹션 선택 (도움말 파일일 때만)
        for i, f in enumerate(self._files):
            if f.resolve() == candidate.resolve():
                self.toc_list.setCurrentRow(i)
                break
        fragment = url.fragment()
        if fragment:
            self._scroll_to_heading(fragment)

    def _scroll_to_heading(self, fragment: str):
        """슬러그 프래그먼트(#5-1-overview)로 헤딩 찾아 스크롤."""
        target = self._slug_of(fragment.replace("-", " "))
        doc = self.content_browser.document()
        blk = doc.begin()
        while blk.isValid():
            if blk.blockFormat().headingLevel() > 0:
                if self._slug_of(blk.text()) == target:
                    cursor = self.content_browser.textCursor()
                    cursor.setPosition(blk.position())
                    self.content_browser.setTextCursor(cursor)
                    self.content_browser.ensureCursorVisible()
                    return
            blk = blk.next()

    # ---------------------------------------------------------------- content

    def _load_content(self):
        self._files, self._titles, self._contents = [], [], []
        if not self.help_dir.is_dir():
            self._show_notice(
                f"Help content not found at:\n{self.help_dir}\n\n"
                "In packaged builds make sure docs/user/help is bundled; "
                "in development run from the repository root.")
            return
        for f in sorted(self.help_dir.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                continue
            self._files.append(f)
            self._titles.append(_title_from_md(text, f.stem))
            self._contents.append(text)
        if not self._files:
            self._show_notice(f"No markdown help files in {self.help_dir}")
            return
        for t in self._titles:
            self.toc_list.addItem(t)
        self.toc_list.setCurrentRow(0)

    def _show_notice(self, message: str):
        self.content_browser.setPlainText(message)

    def _apply_filter(self, query: str):
        q = query.strip().lower()
        for i, title in enumerate(self._titles):
            item = self.toc_list.item(i)
            item.setHidden(bool(q) and q not in title.lower())
        # 항상 하나의 가시 아이템 선택 보장
        for i in range(self.toc_list.count()):
            if not self.toc_list.item(i).isHidden():
                self.toc_list.setCurrentRow(i)
                break

    def _on_toc_selection_changed(self, index: int):
        if 0 <= index < len(self._contents):
            self.content_browser.setMarkdown(self._contents[index])

    # ----------------------------------------------------------------- misc

    def current_section_title(self) -> str | None:
        """현재 섹션 제목 (테스트/진단용)."""
        row = self.toc_list.currentRow()
        return self._titles[row] if 0 <= row < len(self._titles) else None

    def section_titles(self) -> list[str]:
        return list(self._titles)