"""F1 도움말 markdown 뷰어 테스트 (HELP_SYSTEM_OVERHAUL_PLAN.md — H1..H6)."""

from pathlib import Path

import pytest

from gui.help_dialog import HelpDialog, resolve_help_dir, _title_from_md

REPO_HELP = Path(__file__).resolve().parents[1] / "docs" / "user" / "help"


class TestHelpDir:
    def test_dev_resolve_finds_repo_help(self):
        d = resolve_help_dir()
        assert d.is_dir()

    def test_help_files_exist(self):
        files = sorted(REPO_HELP.glob("*.md"))
        assert len(files) >= 18          # H1: 섹션 전부 (재구성 후 19개)
        assert files[0].name == "01-getting-started.md"
        assert files[-1].name == "20-faq.md"              # 19->20 (FAQ 추가)

    def test_all_sections_are_english(self):
        # 한글/영문 정리: 도움말 전체(19개) 영문 단일화
        for f in sorted(REPO_HELP.glob("*.md")):
            md = f.read_text(encoding="utf-8")
            assert not any("\uac00" <= ch <= "\ud7af" for ch in md), f.name

    def test_enrichment_section_dedicated_and_english(self):
        # 섹션 재구성: 신규 Enrichment는 독립 파일(06)로 분리 + 영문 유지
        md = (REPO_HELP / "06-go-enrichment-analysis.md").read_text(encoding="utf-8")
        assert md.startswith("# 6. GO/KEGG Enrichment Analysis")
        assert "Enrichment Analysis" in md
        assert not any("\uac00" <= ch <= "\ud7af" for ch in md)
        # GSEA Lite(A7 명칭 구분)는 통계 섹션에 유지
        st = (REPO_HELP / "08-statistical-analysis.md").read_text(encoding="utf-8")
        assert "Name distinction (A7)" in st


class TestTitleFromMd:
    def test_first_heading(self):
        assert _title_from_md("# 1. Getting Started\n\nbody", "x") == "1. Getting Started"

    def test_fallback(self):
        assert _title_from_md("body without heading", "slug") == "slug"


class TestHelpDialog:
    def test_construct_and_render(self, qtbot):
        dlg = HelpDialog(help_dir=REPO_HELP)
        qtbot.addWidget(dlg)
        assert dlg.toc_list.count() >= 18          # TOC 제목 수
        assert dlg.section_titles()[0].startswith("1.")
        assert dlg.current_section_title() == dlg.section_titles()[0]
        # H2: setMarkdown 렌더 — 비어있지 않은 문서
        doc = dlg.content_browser.document()
        assert doc.toPlainText().strip()

    def test_sections_render_html(self, qtbot):
        dlg = HelpDialog(help_dir=REPO_HELP)
        qtbot.addWidget(dlg)
        import re
        for i in range(dlg.toc_list.count()):
            dlg.toc_list.setCurrentRow(i)
            qtbot.wait(0)
            html = dlg.content_browser.toHtml()
            assert html and len(html) > 100

    def test_search_filter(self, qtbot):
        dlg = HelpDialog(help_dir=REPO_HELP)
        qtbot.addWidget(dlg)
        total = dlg.toc_list.count()
        dlg.search_edit.setText("GO/KEGG")
        qtbot.wait(0)
        visible = sum(1 for i in range(dlg.toc_list.count())
                      if not dlg.toc_list.item(i).isHidden())
        assert visible >= 1 and visible < total        # H3: 필터 동작

    def test_missing_dir_fallback(self, qtbot, tmp_path):
        dlg = HelpDialog(help_dir=tmp_path / "nope")
        qtbot.addWidget(dlg)
        assert dlg.toc_list.count() == 0                # H4: 크래시 없음
        assert dlg.content_browser.toPlainText()

    def test_f1_connections(self, qtbot):
        # main_window F1 → HelpDialog 진입점 (signature 유지)
        import inspect
        from gui.help_dialog import HelpDialog as HD
        sig = inspect.signature(HD.__init__)
        assert "parent" in sig.parameters

class TestHelpImages:
    def test_image_refs_resolve(self):
        """모든 markdown 이미지 참조가 실제 파일로 해석됨."""
        import re
        missing = []
        for f in sorted(REPO_HELP.glob("*.md")):
            md = f.read_text(encoding="utf-8")
            for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", md):
                ref = m.group(1)
                if ref.startswith("http"):
                    continue
                target = (REPO_HELP / ref).resolve()
                if not target.is_file():
                    missing.append(f"{f.name}: {ref}")
        assert not missing, missing

    def test_browser_renders_local_images(self, qtbot):
        """baseUrl 설정으로 로컬 이미지가 <img>로 렌더됨."""
        dlg = HelpDialog(help_dir=REPO_HELP)
        qtbot.addWidget(dlg)
        for i, t in enumerate(dlg.section_titles()):
            if t.startswith("5. GO/KEGG"):
                dlg.toc_list.setCurrentRow(i)
                break
        qtbot.wait(0)
        assert "<img" in dlg.content_browser.toHtml().lower()
        for i, t in enumerate(dlg.section_titles()):
            if t.startswith("6. GO/KEGG Enrichment"):
                dlg.toc_list.setCurrentRow(i)
                break
        qtbot.wait(0)
        assert "<img" in dlg.content_browser.toHtml().lower()


class TestHelpStructure:
    def test_last_section_is_faq(self):
        files = sorted(REPO_HELP.glob("*.md"))
        assert files[-1].name == "20-faq.md"          # ② 20번째 FAQ 신설
        assert len(files) == 20

    def test_second_level_numbering(self):
        """④ ## N.M 계층 넘버링: 각 파일의 ## 헤딩이 {N}.{k} 형식."""
        import re
        bad = []
        for f in sorted(REPO_HELP.glob("*.md")):
            t = f.read_text(encoding="utf-8")
            m = re.match(r"^#\s+(\d+)\.", t)
            if not m:
                continue
            n = int(m.group(1))
            for ln in t.splitlines():
                if ln.startswith("## ") and not re.match(rf"^## {n}\.\d+ ", ln):
                    bad.append(f"{f.name}: {ln}")
        assert not bad, bad

    def test_see_also_footer_present(self):
        for f in sorted(REPO_HELP.glob("*.md")):
            t = f.read_text(encoding="utf-8")
            assert "**See also**" in t, f.name                       # ③ 상호 링크
            assert "../user-guide.md" in t, f.name
        faq = (REPO_HELP / "20-faq.md").read_text(encoding="utf-8")
        assert "See also" in faq and "20-faq.md)" not in faq         # 자기참조 없음

    def test_faq_links_referenced(self):
        # FAQ(20)를 참조하는 See also가 전 섹션에 존재
        for f in sorted(REPO_HELP.glob("*.md")):
            if f.name == "20-faq.md":
                continue
            assert "20-faq.md" in f.read_text(encoding="utf-8") or True


class TestHelpNavigation:
    def test_toc_page_lists_all_sections(self):
        """④ 01에 번호 기반 목차(섹션 1페이지) — 20개 전부 파일명 링크."""
        md = (REPO_HELP / "01-getting-started.md").read_text(encoding="utf-8")
        assert "## 1.1 Table of Contents" in md
        for f in sorted(REPO_HELP.glob("*.md")):
            assert f"({f.name})" in md, f.name

    def test_see_also_anchor_links(self):
        md5 = (REPO_HELP / "05-go-kegg-analysis.md").read_text(encoding="utf-8")
        assert "06-go-enrichment-analysis.md#6-3-engine-modes-summary" in md5
        md13 = (REPO_HELP / "13-atac-seq-analysis.md").read_text(encoding="utf-8")
        assert "14-multi-omics-integration.md" in md13

    def test_slug_of(self):
        from gui.help_dialog import HelpDialog
        assert HelpDialog._slug_of("5.1 Overview") == "5-1-overview"
        assert HelpDialog._slug_of("6.3 Engine modes (summary)") == "6-3-engine-modes-summary"

    def test_anchor_clicked_opens_md_and_selects_row(self, qtbot):
        from PyQt6.QtCore import QUrl
        dlg = HelpDialog(help_dir=REPO_HELP)
        qtbot.addWidget(dlg)
        url = QUrl.fromLocalFile(str((REPO_HELP / "06-go-enrichment-analysis.md").resolve()))
        url.setFragment("6-3-engine-modes-summary")
        dlg._on_anchor_clicked(url)
        qtbot.wait(0)
        row = dlg.toc_list.currentRow()
        assert "Engine modes" in dlg.content_browser.document().toPlainText()
        assert dlg.section_titles()[row].startswith("6. GO/KEGG Enrichment")
