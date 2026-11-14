"""CMG-SeqViewer MCP server (v1, stdio) — read-only tool layer.

The `mcp` SDK is an optional extra; the tool service itself can be imported and
tested without it. Run with::

    cmg-seqviewer-mcp

Privacy defaults: schema_only, no row values, no images, no writes. A workspace
`.cmg-mcp-policy.json` can opt into aggregate/preview/images/write.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from models.data_models import Dataset, DatasetType, FilterCriteria, FilterMode
from services.analysis_service import AnalysisService
from services.dataset_service import DatasetService
from services.filter_service import FilterService
from services.help_service import HelpService
from services.plot_service import PlotService

SCHEMA_VERSION = "1.0"
_TYPE_HINTS = {
    "atac": DatasetType.ATAC_SEQ,
    "atac_seq": DatasetType.ATAC_SEQ,
    "differential_expression": DatasetType.DIFFERENTIAL_EXPRESSION,
    "go_analysis": DatasetType.GO_ANALYSIS,
    "multi_group": DatasetType.MULTI_GROUP,
    "multi_omics": DatasetType.MULTI_OMICS,
    "composition": DatasetType.COMPOSITION,
    "expression_summary": DatasetType.EXPRESSION_SUMMARY,
    "expression_distribution": DatasetType.EXPRESSION_DISTRIBUTION,
    "chromvar": DatasetType.CHROMVAR_DIFF_TF,
    "chromvar_diff_tf": DatasetType.CHROMVAR_DIFF_TF,
    "motif": DatasetType.MOTIF_ENRICHMENT,
    "motif_enrichment": DatasetType.MOTIF_ENRICHMENT,
    "footprint": DatasetType.TF_FOOTPRINT,
    "tf_footprint": DatasetType.TF_FOOTPRINT,
}
_POLICIES = ("schema_only", "aggregate", "preview")


class ToolError(Exception):
    def __init__(self, code: str, message: str, hint: str = ""):
        super().__init__(message)
        self.code, self.message, self.hint = code, message, hint

    def to_dict(self) -> dict:
        return {"error_code": self.code, "message": self.message, "hint": self.hint}


def _tool_error(fn: Callable):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError as exc:
            return exc.to_dict()
        except FileNotFoundError as exc:
            return {"error_code": "FILE_NOT_FOUND", "message": str(exc), "hint": ""}
        except ValueError as exc:
            return {"error_code": "BAD_ARGUMENT", "message": str(exc), "hint": ""}
        except Exception as exc:  # noqa: BLE001 — MCP boundary: structured error
            return {"error_code": "INTERNAL_ERROR", "message": str(exc), "hint": ""}

    return wrapper


@dataclass
class MCPPolicy:
    data_policy: str = "schema_only"
    allow_row_preview: bool = False
    allow_images: bool = False
    allow_write: bool = False
    max_preview_rows: int = 20
    workspace_root: Path = field(default_factory=Path.cwd)
    audit_log: Optional[Path] = field(
        default_factory=lambda: Path.home() / ".cmg-seqviewer" / "mcp_audit.jsonl"
    )
    enabled: bool = True

    def __post_init__(self):
        self.workspace_root = Path(self.workspace_root).resolve()
        if self.data_policy not in _POLICIES:
            raise ValueError(
                f"data_policy must be one of {_POLICIES}, got {self.data_policy!r}"
            )
        if self.data_policy == "preview":
            self.allow_row_preview = True
        if self.allow_row_preview and self.data_policy != "preview":
            raise ValueError("allow_row_preview requires data_policy='preview'")
        self.max_preview_rows = max(0, min(int(self.max_preview_rows), 100))

    @classmethod
    def from_file(
        cls, workspace_root: str | Path, path: Optional[str | Path] = None
    ) -> "MCPPolicy":
        root = Path(workspace_root).resolve()
        policy_path = Path(path) if path else root / ".cmg-mcp-policy.json"
        data: Dict[str, Any] = {}
        if policy_path.exists():
            data = json.loads(policy_path.read_text(encoding="utf-8"))
        data["workspace_root"] = root
        return cls(**data)

    def resolve_path(self, value: str | Path, *, write: bool = False) -> Path:
        if not self.enabled:
            raise ToolError("MCP_DISABLED", "MCP is disabled by policy.")
        if write and not self.allow_write:
            raise ToolError(
                "WRITE_DENIED",
                "Writing is disabled by policy.",
                "Set allow_write=true in .cmg-mcp-policy.json.",
            )
        path = Path(value)
        resolved = (
            (self.workspace_root / path).resolve()
            if not path.is_absolute()
            else path.resolve()
        )
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise ToolError(
                "PATH_OUTSIDE_WORKSPACE",
                "Path is outside the configured workspace.",
                f"Workspace root: {self.workspace_root}",
            ) from None
        return resolved


class DatasetRegistry:
    def __init__(self):
        self._items: Dict[str, Dataset] = {}
        self._sources: Dict[str, str] = {}

    def add(self, dataset: Dataset, source: str) -> str:
        handle = str(uuid.uuid4())
        self._items[handle] = dataset
        self._sources[handle] = source
        return handle

    def get(self, handle: str) -> Dataset:
        dataset = self._items.get(handle)
        if dataset is None:
            raise ToolError("UNKNOWN_HANDLE", f"Unknown dataset handle: {handle}")
        return dataset

    def source(self, handle: str) -> str:
        return self._sources.get(handle, "")

    def list(self) -> list[dict]:
        return [
            {
                "handle": handle,
                "name": ds.name,
                "dataset_type": ds.dataset_type.value,
                "rows": int(len(ds.dataframe)) if ds.dataframe is not None else 0,
            }
            for handle, ds in self._items.items()
        ]

    def close(self, handle: str) -> None:
        self._items.pop(handle, None)
        self._sources.pop(handle, None)


class MCPToolService:
    def __init__(
        self,
        policy: Optional[MCPPolicy] = None,
        registry: Optional[DatasetRegistry] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.policy = policy or MCPPolicy()
        self.registry = registry or DatasetRegistry()
        self.logger = logger or logging.getLogger(__name__)
        self.datasets = DatasetService(self.logger)
        self.filters = FilterService(self.logger)
        self.analysis = AnalysisService(self.logger)
        self.plots = PlotService(self.logger)
        self.help = HelpService()

    # ── Helpers ──────────────────────────────────────────────────────────
    def _base(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "data_policy": self.policy.data_policy,
        }

    def _audit(self, tool: str, handle: str = "", response: Any = None) -> None:
        if not self.policy.audit_log:
            return
        try:
            path = Path(self.policy.audit_log)
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": tool,
                "dataset_hash": (
                    hashlib.sha256(handle.encode()).hexdigest()[:16] if handle else ""
                ),
                "data_policy": self.policy.data_policy,
                "response_bytes": len(
                    json.dumps(response, default=str).encode("utf-8")
                ),
            }
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            self.logger.debug("MCP audit log write failed", exc_info=True)

    def _relative_path(self, value: str) -> Optional[str]:
        try:
            return str(Path(value).resolve().relative_to(self.policy.workspace_root))
        except (ValueError, OSError):
            return None

    def _redact_paths(self, value: Any) -> Any:
        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                if key in ("file", "file_path") and isinstance(item, str):
                    relative = self._relative_path(item)
                    if relative is not None:
                        out[key] = relative
                elif key == "path":
                    continue
                else:
                    out[key] = self._redact_paths(item)
            return out
        if isinstance(value, list):
            return [self._redact_paths(item) for item in value]
        return value

    def _describe(self, dataset: Dataset, handle: str) -> dict:
        info = self.datasets.describe(dataset)
        info.pop("file", None)
        df = dataset.dataframe
        info["dtypes"] = (
            {str(c): str(dtype) for c, dtype in df.dtypes.items()}
            if df is not None
            else {}
        )
        info["metadata"] = self._redact_paths(self.datasets.summary(dataset))
        info.update(self._base())
        info["handle"] = handle
        return info

    # ── Tools ────────────────────────────────────────────────────────────
    @_tool_error
    def list_datasets(self) -> dict:
        out = self._base()
        out["datasets"] = self.registry.list()
        self._audit("list_datasets", response=out)
        return out

    @_tool_error
    def load_dataset(
        self, path: str, type_hint: Optional[str] = None, name: Optional[str] = None
    ) -> dict:
        resolved = self.policy.resolve_path(path)
        hint = _TYPE_HINTS.get(type_hint) if type_hint else None
        if type_hint and hint is None:
            raise ToolError("BAD_TYPE", f"Unknown type_hint: {type_hint}")
        dataset = self.datasets.load(resolved, hint, name=name)
        handle = self.registry.add(dataset, str(resolved))
        out = self._describe(dataset, handle)
        self._audit("load_dataset", handle, out)
        return out

    @_tool_error
    def describe_dataset(self, handle: str) -> dict:
        dataset = self.registry.get(handle)
        out = self._describe(dataset, handle)
        self._audit("describe_dataset", handle, out)
        return out

    @_tool_error
    def summarize_dataset(self, handle: str) -> dict:
        dataset = self.registry.get(handle)
        out = self._base()
        out["handle"] = handle
        out["summary"] = self._redact_paths(self.datasets.summary(dataset))
        self._audit("summarize_dataset", handle, out)
        return out

    @_tool_error
    def filter_dataset(
        self, handle: str, mode: str = "statistical", criteria: Optional[dict] = None
    ) -> dict:
        dataset = self.registry.get(handle)
        raw = dict(criteria or {})
        try:
            filter_mode = FilterMode(mode)
        except ValueError:
            raise ToolError("BAD_FILTER_MODE", f"Unknown filter mode: {mode}") from None
        if "mode" in raw:
            raw.pop("mode")
        allowed = {f.name for f in FilterCriteria.__dataclass_fields__.values()} - {
            "mode"
        }
        unknown = set(raw) - allowed
        if unknown:
            raise ToolError("BAD_FILTER_KEY", f"Unknown filter keys: {sorted(unknown)}")
        filtered = self.filters.filter(dataset, FilterCriteria(mode=filter_mode, **raw))
        if filtered is None:
            raise ToolError("FILTER_EMPTY", "Filter produced no result.")
        child = Dataset(
            f"{dataset.name} [filtered]",
            dataset.dataset_type,
            file_path=dataset.file_path,
            dataframe=filtered,
            metadata=dict(dataset.metadata),
        )
        child_handle = self.registry.add(child, self.registry.source(handle))
        out = self._describe(child, child_handle)
        out["parent_handle"] = handle
        out["rows_before"] = (
            int(len(dataset.dataframe)) if dataset.dataframe is not None else 0
        )
        out["rows_after"] = int(len(filtered))
        self._audit("filter_dataset", handle, out)
        return out

    @_tool_error
    def compare_datasets(
        self,
        handles: list[str],
        gene_list: Optional[list[str]] = None,
        adj_pvalue_cutoff: float = 0.05,
        log2fc_cutoff: float = 1.0,
        include_genes: bool = False,
        include_table: bool = False,
        table_limit: int = 50,
    ) -> dict:
        if len(handles) < 2:
            raise ToolError(
                "TOO_FEW_DATASETS", "At least 2 dataset handles are required."
            )
        datasets = [self.registry.get(handle) for handle in handles]
        if include_genes and self.policy.data_policy not in ("aggregate", "preview"):
            raise ToolError(
                "GENE_LIST_DENIED",
                "Gene lists require aggregate or preview data policy.",
                "Set data_policy=aggregate (or preview) in .cmg-mcp-policy.json.",
            )
        if include_table and self.policy.data_policy != "preview":
            raise ToolError(
                "TABLE_DENIED",
                "Comparison tables require preview data policy.",
                "Set data_policy=preview in .cmg-mcp-policy.json.",
            )
        result = self.analysis.compare_datasets(
            datasets,
            gene_list=gene_list,
            adj_pvalue_cutoff=adj_pvalue_cutoff,
            log2fc_cutoff=log2fc_cutoff,
        )
        out = self._base()
        out["handles"] = list(handles)
        out.update(
            self.analysis.result_to_dict(
                result,
                include_table=include_table,
                table_limit=max(0, min(int(table_limit), 100)),
                include_genes=include_genes,
            )
        )
        self._audit("compare_datasets", handles[0], out)
        return out

    @_tool_error
    def query_rows(
        self,
        handle: str,
        columns: Optional[list[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        if self.policy.data_policy != "preview" or not self.policy.allow_row_preview:
            raise ToolError(
                "ROW_PREVIEW_DENIED",
                "Row preview is disabled by policy.",
                "Set allow_row_preview=true and data_policy=preview.",
            )
        dataset = self.registry.get(handle)
        limit = max(0, min(int(limit), self.policy.max_preview_rows))
        df = self.datasets.query(dataset, columns=columns, limit=limit, offset=offset)
        out = self._base()
        out.update(
            {
                "handle": handle,
                "rows": len(df),
                "columns": list(df.columns),
                "data": json.loads(df.to_json(orient="records")),
            }
        )
        self._audit("query_rows", handle, out)
        return out

    @_tool_error
    def plot(
        self,
        handle: str,
        plot_type: str,
        params: Optional[dict] = None,
        out_path: str = "figure.png",
    ) -> dict:
        if not self.policy.allow_images:
            raise ToolError(
                "IMAGES_DENIED",
                "Image export is disabled by policy.",
                "Set allow_images=true in .cmg-mcp-policy.json.",
            )
        dataset = self.registry.get(handle)
        resolved = self.policy.resolve_path(out_path, write=True)
        path = self.plots.render(dataset, plot_type, resolved, params=params or {})
        out = self._base()
        out.update(
            {
                "handle": handle,
                "plot_type": plot_type,
                "artifact": str(path.relative_to(self.policy.workspace_root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
        self._audit("plot", handle, out)
        return out

    @_tool_error
    def export_table(
        self, handle: str, out_path: str, format: Optional[str] = None
    ) -> dict:
        dataset = self.registry.get(handle)
        resolved = self.policy.resolve_path(out_path, write=True)
        path = self.datasets.export(dataset, resolved, fmt=format)
        out = self._base()
        out.update(
            {
                "handle": handle,
                "artifact": str(path.relative_to(self.policy.workspace_root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
        self._audit("export_table", handle, out)
        return out

    @_tool_error
    def close_dataset(self, handle: str) -> dict:
        self.registry.close(handle)
        out = self._base()
        out.update({"handle": handle, "closed": True})
        self._audit("close_dataset", handle, out)
        return out

    @_tool_error
    def get_help(
        self, query: Optional[str] = None, section: Optional[str] = None
    ) -> dict:
        out = self._base()
        if section:
            out["section"] = section
            out["markdown"] = self.help.get(section)
        else:
            found = self.help.search(query) if query else self.help.sections()
            out["sections"] = [
                {k: v for k, v in item.items() if k != "path"} for item in found
            ]
        self._audit("get_help", response=out)
        return out


_WORKFLOWS = {
    "de-analysis": '# DE analysis\n\n1. `load_dataset(path, type_hint="differential_expression")`\n2. `filter_dataset(handle, mode="statistical", criteria={...})`\n3. `plot(handle, plot_type="volcano")`\n4. `summarize_dataset(handle)`\n',
    "expression-summary": '# Expression summary\n\n1. `load_dataset(path, type_hint="expression_summary")`\n2. `describe_dataset(handle)`\n3. `plot(handle, plot_type="expression_dot")`\n',
    "composition": '# Composition\n\n1. `load_dataset(path, type_hint="composition")`\n2. `summarize_dataset(handle)`\n3. `plot(handle, plot_type="composition")`\n',
    "compare-datasets": "# Compare datasets\n\n1. `load_dataset` for each DE file\n2. `compare_datasets(handles=[...])` for overlap counts\n3. Add `include_genes=true` only with aggregate/preview policy\n",
}

TOOL_DESCRIPTIONS = {
    "list_datasets": "List datasets loaded in this MCP session.",
    "load_dataset": "Load a workspace file and return a dataset handle plus schema.",
    "describe_dataset": "Describe a handle: type, rows, columns, dtypes, metadata.",
    "summarize_dataset": "Return a JSON-safe summary for a handle.",
    "filter_dataset": "Apply a filter and return a new child handle (counts only).",
    "compare_datasets": "Compare >=2 DE handles; counts by default, gene lists opt-in.",
    "query_rows": "Preview rows; requires preview policy opt-in.",
    "plot": "Render a registered plot type to a workspace image; requires image opt-in.",
    "export_table": "Export a handle to a workspace file; requires write opt-in.",
    "close_dataset": "Release a dataset handle.",
    "get_help": "Search/list F1 help sections or return one section as Markdown.",
}


def build_server(policy: Optional[MCPPolicy] = None):
    """Build the MCP server. Requires the optional `mcp` package."""
    try:
        from mcp.server.mcpserver import MCPServer
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "The MCP SDK is not installed. Install with: "
            "pip install 'cmg-seqviewer[mcp]'"
        ) from exc
    from version import __version__

    service = MCPToolService(policy)
    server = MCPServer(
        name="cmg-seqviewer",
        title="CMG-SeqViewer",
        description="Headless dataset inspection, filtering, plotting, and help.",
        version=__version__,
    )
    for name, description in TOOL_DESCRIPTIONS.items():
        server.add_tool(getattr(service, name), name=name, description=description)

    @server.resource("help://index", mime_type="application/json")
    def help_index() -> str:
        sections = [
            {k: v for k, v in item.items() if k != "path"}
            for item in service.help.sections()
        ]
        return json.dumps(sections, ensure_ascii=False)

    @server.resource("help://section/{slug}", mime_type="text/markdown")
    def help_section(slug: str) -> str:
        return service.help.get(slug)

    @server.resource("schema://dataset/{dataset_type}", mime_type="application/json")
    def dataset_schema(dataset_type: str) -> str:
        try:
            dtype = DatasetType(dataset_type)
        except ValueError:
            return json.dumps(
                {
                    "error_code": "BAD_TYPE",
                    "message": f"Unknown dataset_type: {dataset_type}",
                }
            )
        return json.dumps(
            {
                "dataset_type": dtype.value,
                "required_columns": service.datasets.required_columns(dtype),
            },
            ensure_ascii=False,
        )

    @server.resource("docs://pipeline-integration", mime_type="text/markdown")
    def pipeline_integration_doc() -> str:
        path = (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "developer"
            / "pipeline-integration.md"
        )
        if not path.exists():
            return (
                "# Pipeline integration\n\n"
                "The full specification is shipped in the source repository at "
                "`docs/developer/pipeline-integration.md`."
            )
        return path.read_text(encoding="utf-8")

    for workflow_name, workflow_text in _WORKFLOWS.items():

        def _make_workflow(text: str):
            def _workflow() -> str:
                return text

            return _workflow

        server.resource(
            f"workflow://{workflow_name}", name=workflow_name, mime_type="text/markdown"
        )(_make_workflow(workflow_text))

    @server.prompt(
        name="de-analysis", description="DE: load → filter → volcano → summary"
    )
    def de_analysis_prompt() -> str:
        return (
            "Use load_dataset, filter_dataset (mode=statistical), plot "
            "(plot_type=volcano), and summarize_dataset. Keep data_policy at "
            "schema_only unless the user explicitly opted in."
        )

    @server.prompt(
        name="expression-summary",
        description="Expression Summary: inspect schema → dot plot",
    )
    def expression_summary_prompt() -> str:
        return (
            "Use load_dataset with type_hint=expression_summary, describe_dataset, "
            "then plot with plot_type=expression_dot. Prefer aggregate/schema-only "
            "outputs; ask before enabling row preview or images."
        )

    @server.prompt(
        name="composition", description="Composition: inspect groups → composition plot"
    )
    def composition_prompt() -> str:
        return (
            "Use load_dataset with type_hint=composition, summarize_dataset for group "
            "counts, and plot with plot_type=composition. Report FDR/PropRatio "
            "interpretation without exposing raw rows by default."
        )

    @server.prompt(
        name="compare-datasets",
        description="Compare DE datasets: overlap counts, opt-in gene lists",
    )
    def compare_datasets_prompt() -> str:
        return (
            "Load each DE file, call compare_datasets with their handles, and report "
            "overlap counts. Ask before enabling include_genes or include_table; "
            "gene lists need aggregate/preview and tables need preview policy."
        )

    return server


def main() -> int:
    if os.environ.get("CMG_MCP_DISABLE") == "1":
        print("CMG-SeqViewer MCP is disabled by CMG_MCP_DISABLE=1")
        return 1
    workspace = Path(os.environ.get("CMG_MCP_WORKSPACE", Path.cwd()))
    policy = MCPPolicy.from_file(workspace, os.environ.get("CMG_MCP_POLICY"))
    if not policy.enabled:
        print("CMG-SeqViewer MCP is disabled by .cmg-mcp-policy.json")
        return 1
    server = build_server(policy)
    server.run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
