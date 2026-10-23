"""Figure bundle coverage guard.

Every user-facing BasePlotDialog should either implement get_bundle_context()
or be listed as a known gap. This prevents new figure dialogs from silently
missing the external figure-atlas handoff.
"""

import ast
from pathlib import Path

GUI = Path(__file__).resolve().parents[1] / "src" / "gui"
BUNDLE_EXPORT = Path(__file__).resolve().parents[1] / "src" / "utils" / "figure_bundle_export.py"

# Remove entries as bundle support is added.
KNOWN_GAPS = set()


def _base_plot_dialogs():
    found = {}
    for path in GUI.glob("*.py"):
        if path.name.endswith("_backup.py"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {
                b.id if isinstance(b, ast.Name) else getattr(b, "attr", "")
                for b in node.bases
            }
            if "BasePlotDialog" not in bases:
                continue
            has_bundle = any(
                isinstance(n, ast.FunctionDef) and n.name == "get_bundle_context"
                for n in node.body
            )
            found[node.name] = (path.name, has_bundle)
    return found


def _bundle_plot_types():
    values = set()
    for path in GUI.glob("*.py"):
        if path.name.endswith("_backup.py"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef)
                    and node.name == "get_bundle_context"):
                continue
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Dict):
                    continue
                for key, value in zip(inner.keys, inner.values):
                    if (isinstance(key, ast.Constant) and key.value == "plot_type"
                            and isinstance(value, ast.Constant)
                            and isinstance(value.value, str)):
                        values.add(value.value)
    return values


def _builder_plot_types():
    tree = ast.parse(BUNDLE_EXPORT.read_text(encoding="utf-8"))
    names = {n.name for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name.startswith("_build_")}
    return {
        name[len("_build_"):-len("_plot_script")]
        for name in names
        if name.endswith("_plot_script")
    }


def test_base_plot_dialogs_have_bundle_or_known_gap():
    dialogs = _base_plot_dialogs()
    missing = {name for name, (_, has_bundle) in dialogs.items() if not has_bundle}
    assert missing == KNOWN_GAPS, (
        f"Unexpected bundle gaps: {sorted(missing - KNOWN_GAPS)}; "
        f"fixed known gaps should be removed from KNOWN_GAPS: "
        f"{sorted(KNOWN_GAPS - missing)}"
    )


def test_bundle_plot_types_have_dedicated_builders():
    plot_types = _bundle_plot_types()
    builders = _builder_plot_types()
    missing = plot_types - builders
    assert not missing, f"Plot types without dedicated bundle builder: {sorted(missing)}"
