"""MCP server v1: tool service, policy, resources, and registration."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

import mcp_server
from mcp_server import MCPPolicy, MCPToolService


def _de_csv(tmp_path):
    path = tmp_path / "de.csv"
    pd.DataFrame(
        {
            "gene_id": ["G1", "G2", "G3"],
            "log2fc": [2.0, -3.0, 0.1],
            "adj_pvalue": [0.01, 0.02, 0.8],
            "base_mean": [100.0, 200.0, 50.0],
        }
    ).to_csv(path, index=False)
    return path


def _de_csv_b(tmp_path):
    path = tmp_path / "de2.csv"
    pd.DataFrame(
        {
            "gene_id": ["G2", "G3", "G4"],
            "log2fc": [1.5, -2.0, 2.5],
            "adj_pvalue": [0.01, 0.02, 0.03],
        }
    ).to_csv(path, index=False)
    return path


def _service(tmp_path, **policy_kwargs):
    _de_csv(tmp_path)
    _de_csv_b(tmp_path)
    kwargs = {"workspace_root": tmp_path, "audit_log": tmp_path / "audit.jsonl"}
    kwargs.update(policy_kwargs)
    return MCPToolService(MCPPolicy(**kwargs))


def test_policy_defaults_are_schema_only(tmp_path):
    policy = MCPPolicy(workspace_root=tmp_path, audit_log=None)
    assert policy.data_policy == "schema_only"
    assert policy.allow_row_preview is False
    assert policy.allow_images is False
    assert policy.allow_write is False
    assert policy.max_preview_rows == 20


def test_preview_policy_requires_preview_level(tmp_path):
    with pytest.raises(ValueError, match="allow_row_preview"):
        MCPPolicy(workspace_root=tmp_path, allow_row_preview=True, audit_log=None)
    policy = MCPPolicy(workspace_root=tmp_path, data_policy="preview", audit_log=None)
    assert policy.allow_row_preview is True


def test_load_describe_summary_and_close(tmp_path):
    svc = _service(tmp_path)
    loaded = svc.load_dataset("de.csv", "differential_expression")
    assert loaded["dataset_type"] == "differential_expression"
    assert loaded["rows"] == 3
    assert loaded["handle"]
    assert "G1" not in json.dumps(loaded)
    assert str(tmp_path) not in json.dumps(loaded)

    described = svc.describe_dataset(loaded["handle"])
    assert described["dtypes"]["log2fc"] == "float64"
    assert "G1" not in json.dumps(described)
    assert str(tmp_path) not in json.dumps(described)

    summary = svc.summarize_dataset(loaded["handle"])
    assert summary["summary"]["row_count"] == 3
    assert str(tmp_path) not in json.dumps(summary)
    assert svc.list_datasets()["datasets"][0]["rows"] == 3

    assert svc.close_dataset(loaded["handle"])["closed"] is True
    assert svc.describe_dataset(loaded["handle"])["error_code"] == "UNKNOWN_HANDLE"


def test_default_policy_denies_rows_images_and_writes(tmp_path):
    svc = _service(tmp_path)
    handle = svc.load_dataset("de.csv", "differential_expression")["handle"]

    assert svc.query_rows(handle)["error_code"] == "ROW_PREVIEW_DENIED"
    assert (
        svc.plot(handle, "volcano", out_path="out.png")["error_code"] == "IMAGES_DENIED"
    )
    assert svc.export_table(handle, "out.csv")["error_code"] == "WRITE_DENIED"


def test_plot_also_requires_write_permission(tmp_path):
    svc = _service(tmp_path, allow_images=True)
    handle = svc.load_dataset("de.csv", "differential_expression")["handle"]
    assert (
        svc.plot(handle, "volcano", out_path="out.png")["error_code"] == "WRITE_DENIED"
    )


def test_filter_returns_child_handle_without_rows(tmp_path):
    svc = _service(tmp_path)
    handle = svc.load_dataset("de.csv", "differential_expression")["handle"]
    child = svc.filter_dataset(
        handle, "statistical", {"adj_pvalue_max": 0.05, "log2fc_min": 1.0}
    )
    assert child["parent_handle"] == handle
    assert child["handle"] != handle
    assert child["rows_before"] == 3
    assert child["rows_after"] == 2
    assert "G1" not in json.dumps(child)


def test_compare_defaults_to_counts_only(tmp_path):
    svc = _service(tmp_path)
    a = svc.load_dataset("de.csv", "differential_expression")["handle"]
    b = svc.load_dataset("de2.csv", "differential_expression")["handle"]
    out = svc.compare_datasets([a, b])
    assert out["overlap_stats"]["common_genes_count"] == 1
    assert "common_genes" not in out
    assert "unique_genes" not in out
    assert "comparison_table" not in out
    assert "G1" not in json.dumps(out)


def test_compare_gene_lists_require_aggregate(tmp_path):
    svc = _service(tmp_path)
    a = svc.load_dataset("de.csv", "differential_expression")["handle"]
    b = svc.load_dataset("de2.csv", "differential_expression")["handle"]
    denied = svc.compare_datasets([a, b], include_genes=True)
    assert denied["error_code"] == "GENE_LIST_DENIED"

    aggregate = _service(tmp_path, data_policy="aggregate")
    a = aggregate.load_dataset("de.csv", "differential_expression")["handle"]
    b = aggregate.load_dataset("de2.csv", "differential_expression")["handle"]
    out = aggregate.compare_datasets([a, b], include_genes=True)
    assert set(out["common_genes"]) == {"G2"}
    assert out["unique_genes"]["de"] == ["G1"]
    assert set(out["unique_genes"]["de2"]) == {"G3", "G4"}


def test_compare_table_requires_preview(tmp_path):
    svc = _service(tmp_path)
    a = svc.load_dataset("de.csv", "differential_expression")["handle"]
    b = svc.load_dataset("de2.csv", "differential_expression")["handle"]
    denied = svc.compare_datasets([a, b], include_table=True)
    assert denied["error_code"] == "TABLE_DENIED"

    preview = _service(tmp_path, data_policy="preview")
    a = preview.load_dataset("de.csv", "differential_expression")["handle"]
    b = preview.load_dataset("de2.csv", "differential_expression")["handle"]
    out = preview.compare_datasets(
        [a, b], include_table=True, include_genes=True, table_limit=2
    )
    assert len(out["comparison_table"]) == 2
    assert set(out["common_genes"]) == {"G2"}


def test_compare_requires_two_handles(tmp_path):
    svc = _service(tmp_path)
    a = svc.load_dataset("de.csv", "differential_expression")["handle"]
    out = svc.compare_datasets([a])
    assert out["error_code"] == "TOO_FEW_DATASETS"


def test_preview_images_write_and_audit(tmp_path):
    svc = _service(
        tmp_path,
        data_policy="preview",
        allow_images=True,
        allow_write=True,
        max_preview_rows=5,
    )
    handle = svc.load_dataset("de.csv", "differential_expression")["handle"]

    rows = svc.query_rows(handle, ["gene_id", "log2fc"], limit=1)
    assert rows["rows"] == 1
    assert rows["data"][0]["gene_id"] == "G1"

    plotted = svc.plot(handle, "volcano", out_path="out.png")
    assert plotted["artifact"] == "out.png"
    assert (tmp_path / "out.png").exists()

    exported = svc.export_table(handle, "out.csv")
    assert exported["artifact"] == "out.csv"
    assert (tmp_path / "out.csv").exists()

    audit = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert '"tool": "query_rows"' in audit
    assert "G1" not in audit


def test_path_traversal_and_absolute_outside_are_denied(tmp_path):
    svc = _service(tmp_path, allow_write=True)
    assert svc.load_dataset("../outside.csv")["error_code"] == "PATH_OUTSIDE_WORKSPACE"
    handle = svc.load_dataset("de.csv", "differential_expression")["handle"]
    assert (
        svc.export_table(handle, "../outside.csv")["error_code"]
        == "PATH_OUTSIDE_WORKSPACE"
    )


def test_help_tool_and_resources(tmp_path):
    svc = _service(tmp_path)
    hits = svc.get_help(query="command line")["sections"]
    assert any("command-line" in h["slug"] for h in hits)
    assert all("path" not in h for h in hits)
    section = svc.get_help(section="19-command-line-interface")["markdown"]
    assert "# " in section


def test_policy_file_opt_in(tmp_path):
    (tmp_path / ".cmg-mcp-policy.json").write_text(
        json.dumps(
            {
                "data_policy": "preview",
                "allow_images": True,
                "allow_write": True,
                "max_preview_rows": 5,
                "audit_log": None,
            }
        ),
        encoding="utf-8",
    )
    policy = MCPPolicy.from_file(tmp_path)
    assert policy.data_policy == "preview"
    assert policy.allow_images is True
    assert policy.allow_write is True
    assert policy.max_preview_rows == 5


def test_build_server_registers_v1_tools_resources_and_prompts(tmp_path):
    pytest.importorskip("mcp.server.mcpserver")
    server = mcp_server.build_server(MCPPolicy(workspace_root=tmp_path, audit_log=None))

    async def inspect():
        tools = await server.list_tools()
        resources = await server.list_resources()
        templates = await server.list_resource_templates()
        prompts = await server.list_prompts()
        return tools, resources, templates, prompts

    tools, resources, templates, prompts = asyncio.run(inspect())
    names = {t.name for t in tools}
    assert {
        "load_dataset",
        "describe_dataset",
        "query_rows",
        "plot",
        "export_table",
        "get_help",
    } <= names
    assert any(r.uri == "help://index" for r in resources)
    assert any(r.uri_template == "help://section/{slug}" for r in templates)
    assert any(r.uri_template == "schema://dataset/{dataset_type}" for r in templates)
    assert {"de-analysis", "expression-summary", "composition", "compare-datasets"} <= {
        p.name for p in prompts
    }


def test_call_tool_dispatch(tmp_path):
    pytest.importorskip("mcp.server.mcpserver")
    _de_csv(tmp_path)
    server = mcp_server.build_server(MCPPolicy(workspace_root=tmp_path, audit_log=None))

    async def call():
        return await server.call_tool(
            "load_dataset", {"path": "de.csv", "type_hint": "differential_expression"}
        )

    result = asyncio.run(call())
    assert result.is_error is False
    payload = json.loads(result.content[0].text)
    assert payload["dataset_type"] == "differential_expression"
    assert payload["rows"] == 3
    assert payload["handle"]


def test_stdio_end_to_end(tmp_path):
    pytest.importorskip("mcp.server.mcpserver")
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    _de_csv(tmp_path)
    repo = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo / "src"),
        "CMG_MCP_WORKSPACE": str(tmp_path),
    }
    env.pop("CMG_MCP_DISABLE", None)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server"],
        env=env,
        cwd=str(repo),
    )

    async def run():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                assert init.server_info.name == "cmg-seqviewer"
                tools = await session.list_tools()
                assert len(tools.tools) == 11
                result = await session.call_tool(
                    "load_dataset",
                    {"path": "de.csv", "type_hint": "differential_expression"},
                )
                assert result.is_error is False
                payload = json.loads(result.content[0].text)
                assert payload["rows"] == 3
                assert payload["handle"]

    asyncio.run(run())


def test_kill_switch(monkeypatch):
    monkeypatch.setenv("CMG_MCP_DISABLE", "1")
    assert mcp_server.main() == 1
