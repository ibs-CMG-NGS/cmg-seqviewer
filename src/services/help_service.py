"""Help service — list/read/search the Markdown F1 help sections."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _help_dirs() -> list[Path]:
    candidates = [Path(__file__).resolve().parents[2] / "docs" / "user" / "help"]
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidates.append(Path(base) / "docs" / "user" / "help")
        candidates.append(Path(base) / "user" / "help")
    return candidates


def resolve_help_dir() -> Path:
    for path in _help_dirs():
        if path.is_dir():
            return path
    return _help_dirs()[0]


def _title(md: str, fallback: str) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


class HelpService:
    def __init__(self, help_dir: Optional[Path] = None):
        self.help_dir = Path(help_dir) if help_dir else resolve_help_dir()

    def sections(self) -> List[Dict[str, Any]]:
        if not self.help_dir.is_dir():
            return []
        out = []
        for path in sorted(self.help_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            out.append({"slug": path.stem, "title": _title(text, path.stem),
                        "path": str(path)})
        return out

    def get(self, slug: str) -> str:
        path = self.help_dir / f"{Path(slug).stem}.md"
        if not path.exists():
            raise FileNotFoundError(f"Help section not found: {slug}")
        return path.read_text(encoding="utf-8")

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        q = (query or "").strip().lower()
        if not q:
            return []
        hits = []
        for section in self.sections():
            text = Path(section["path"]).read_text(encoding="utf-8")
            if q in section["title"].lower() or q in text.lower():
                hits.append(section)
            if len(hits) >= limit:
                break
        return hits
