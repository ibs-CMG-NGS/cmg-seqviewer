"""HelpService unit tests."""

from services.help_service import HelpService


def test_sections_and_get():
    svc = HelpService()
    sections = svc.sections()
    assert sections
    assert sections[0]["title"].startswith("1.")
    md = svc.get(sections[0]["slug"])
    assert md.startswith("# ")


def test_search_returns_matches():
    svc = HelpService()
    hits = svc.search("filter")
    assert hits


def test_missing_section_raises():
    svc = HelpService()
    try:
        svc.get("definitely-not-a-section")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")
