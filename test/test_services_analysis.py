"""AnalysisService: shared headless dataset comparison."""

import json

import pandas as pd

from services.analysis_service import AnalysisService


def _write_de(path, genes):
    pd.DataFrame(
        {
            "gene_id": genes,
            "log2fc": [2.0, -2.5, 1.5][: len(genes)],
            "adj_pvalue": [0.01, 0.02, 0.03][: len(genes)],
        }
    ).to_csv(path, index=False)
    return path


def test_compare_files_and_json(tmp_path):
    a = _write_de(tmp_path / "a.csv", ["G1", "G2", "G3"])
    b = _write_de(tmp_path / "b.csv", ["G2", "G3", "G4"])
    svc = AnalysisService()
    result = svc.compare_files([a, b])

    assert result.dataset_names == ["a", "b"]
    assert set(result.common_genes) == {"G2", "G3"}
    assert result.unique_genes["a"] == ["G1"]
    assert result.unique_genes["b"] == ["G4"]
    assert result.metadata["total_genes"] == 4

    payload = svc.result_to_dict(result, include_table=True, table_limit=2)
    json.dumps(payload)
    assert payload["overlap_stats"]["common_genes_count"] == 2
    assert len(payload["comparison_table"]) == 2


def test_result_to_dict_can_omit_gene_lists(tmp_path):
    a = _write_de(tmp_path / "a.csv", ["G1", "G2", "G3"])
    b = _write_de(tmp_path / "b.csv", ["G2", "G3", "G4"])
    result = AnalysisService().compare_files([a, b])
    payload = AnalysisService.result_to_dict(result, include_genes=False)
    assert payload["overlap_stats"]["common_genes_count"] == 2
    assert "common_genes" not in payload
    assert "unique_genes" not in payload


def test_compare_gene_list(tmp_path):
    a = _write_de(tmp_path / "a.csv", ["G1", "G2", "G3"])
    b = _write_de(tmp_path / "b.csv", ["G2", "G3", "G4"])
    result = AnalysisService().compare_files([a, b], gene_list=["G2"])
    assert result.dataset_names == ["a", "b"]
    assert result.common_genes == ["G2"]
    assert result.metadata["total_genes"] == 1
