#!/usr/bin/env python
"""기존 help_dialog.py의 HTML 섹션 → docs/user/help/*.md 1회성 이관 도구.

용도: F1 도움말 markdown 개편(HELP_SYSTEM_OVERHAUL_PLAN)의 1차 콘텐츠 생성.
HTML 태그를 markdown으로 변환하고, 이후 콘텐츠 수정은 docs/user/help/*.md에서 진행.
"""
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "gui" / "help_dialog.py"
OUT = ROOT / "docs" / "user" / "help"

# TOC 순서: (메서드명, 제목, 슬러그)
SECTIONS = [
    ("_get_getting_started", "1. Getting Started", "01-getting-started"),
    ("_get_loading_data", "2. Loading Data", "02-loading-data"),
    ("_get_dataset_database", "3. Dataset Database", "03-dataset-database"),
    ("_get_filtering", "4. Data Filtering", "04-data-filtering"),
    ("_get_go_kegg_analysis", "5. GO/KEGG Analysis", "05-go-kegg-analysis"),
    ("_get_go_term_comparison", "5b. GO Term Comparison", "05b-go-term-comparison"),
    ("_get_atac_seq_analysis", "5c. ATAC-seq Analysis", "05c-atac-seq-analysis"),
    ("_get_multi_omics_integration", "5d. Multi-Omics Integration", "05d-multi-omics-integration"),
    ("_get_statistical_analysis", "6. Statistical Analysis", "06-statistical-analysis"),
    ("_get_visualization", "7. Visualization", "07-visualization"),
    ("_get_project_save_load", "7b. Project Save/Load", "07b-project-save-load"),
    ("_get_igv_integration", "7c. IGV Integration", "07c-igv-integration"),
    ("_get_multi_group_heatmap", "8. Multi-Group Heatmap", "08-multi-group-heatmap"),
    ("_get_pca_plot", "9. PCA Plot", "09-pca-plot"),
    ("_get_comparison", "10. Dataset Comparison", "10-dataset-comparison"),
    ("_get_gene_annotation", "11. Gene Annotation", "11-gene-annotation"),
    ("_get_export", "12. Export & Clipboard", "12-export-clipboard"),
    ("_get_tips", "13. Tips & Shortcuts", "13-tips-shortcuts"),
]


class HtmlToMd(HTMLParser):
    """help_dialog.py의 HTML 패턴에 특화된 간단 HTML→Markdown 변환기."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.list_depth = 0
        self.li_index = {}            # depth -> 다음 번호
        self.in_table = False
        self.in_pre = False
        self.in_cell = False
        self.rows = []
        self.row = []
        self.in_head_row = True
        self.anchors = []             # (id, text) — 인라인 네비게이션 무시
        self.skip = 0
        self._pending_space = False

    # -- 헬퍼 --
    def _emit(self, s):
        self.out.append(s)

    def _newline(self):
        if self.out and not self.out[-1].endswith("\n"):
            self._emit("\n")

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        t = tag.lower()
        if self.in_pre:
            if t == "code":
                return
            if t == "pre":
                self._emit("```\n")
                self.in_pre = False
            return
        if t in ("h1", "h2", "h3", "h4"):
            self._newline(); self._emit("\n" + "#" * int(t[1]) + " ")
            if t == "h1":
                idv = a.get("id", "")
                if idv:
                    self.anchors.append(idv)
        elif t in ("p", "div", "section", "tr", "hr", "table"):
            self._newline()
            if t == "hr":
                self._emit("\n---\n")
        elif t in ("ul", "ol"):
            self.list_depth += 1
            if t == "ol":
                self.li_index[self.list_depth] = 1
        elif t == "li":
            self._newline()
            if self.li_index.get(self.list_depth):
                n = self.li_index[self.list_depth]; self.li_index[self.list_depth] = n + 1
                prefix = f"{n}. "
            else:
                prefix = "- "
            self._emit("  " * (self.list_depth - 1) + prefix)
        elif t in ("b", "strong"):
            self._emit("**")
        elif t in ("i", "em"):
            self._emit("*")
        elif t == "code":
            self._emit("`")
        elif t == "pre":
            self._newline(); self._emit("```\n"); self.in_pre = True
        elif t == "br":
            self._emit("\n")
        elif t == "table":
            self.in_table = True; self.rows = []; self.row = []
        elif t in ("thead", "tbody", "tfoot"):
            pass
        elif t == "tr":
            if self.in_table:
                self.row = []
        elif t in ("th", "td"):
            self.in_cell = True; self.in_head_row = (t == "th")
            self._emit("| ")
        elif t == "a":
            href = a.get("href", "")
            if href:
                self._emit("[")
                self._link = href
            else:
                self._link = None
        elif t == "img":
            self._emit(f"![{a.get('alt','')}]({a.get('src','')})")
        elif t == "span":
            pass
        elif t == "nav" or (t == "div" and "toc" in a.get("class", "")):
            self.skip = 1
        else:
            pass

    def handle_endtag(self, tag):
        t = tag.lower()
        if self.in_pre and t == "pre":
            return
        if t in ("h1", "h2", "h3", "h4"):
            self._emit("\n")
        elif t in ("p", "div", "section"):
            self._newline()
        elif t in ("ul", "ol"):
            if self.list_depth > 0:
                self.list_depth -= 1
            self._newline()
        elif t == "li":
            self._emit("\n")
        elif t in ("b", "strong"):
            self._emit("**")
        elif t in ("i", "em"):
            self._emit("*")
        elif t == "code":
            self._emit("`")
        elif t == "table":
            self._newline()
            for r in self.rows:
                self._emit("| " + " | ".join(r) + " |\n")
            self._emit("\n")
            self.in_table = False
        elif t == "tr":
            if self.in_table:
                self.rows.append([c.strip() for c in self.row])
        elif t in ("th", "td"):
            self.in_cell = False
        elif t == "a":
            if getattr(self, "_link", None):
                self._emit(f"]({self._link})")
            self._link = None

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_table and self.in_cell:
            self.row.append(data)
            if getattr(self, "_link", None):
                self._emit(f"[{data}]({self._link})")
            else:
                self._emit(data)
            return
        self._emit(data)


def extract_html(method: str, src: str) -> str:
    m = re.search(rf"def {re.escape(method)}\(self\):.*?return \"\"\"(.*?)\"\"\"", src, re.S)
    if not m:
        raise SystemExit(f"{method}: 삼중따옴표 HTML 추출 실패")
    return m.group(1)


def main():
    src = SRC.read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    for method, title, slug in SECTIONS:
        html_src = extract_html(method, src)
        parser = HtmlToMd()
        parser.feed(html_src)
        md = "".join(parser.out)
        md = html.unescape(md)
        md = re.sub(r"[ \t]+\n", "\n", md)
        md = re.sub(r"\n{3,}", "\n\n", md)
        md = md.strip() + "\n"
        if not md.startswith("#"):
            md = f"# {title}\n\n" + md
        (OUT / f"{slug}.md").write_text(md, encoding="utf-8")
        print(f"  {slug}.md  {len(md.splitlines())} lines")
    print(f"done -> {OUT}")


if __name__ == "__main__":
    main()