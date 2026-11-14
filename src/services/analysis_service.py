"""Headless comparison service for CLI/MCP.

Thin, JSON-friendly facade over ``utils.statistics.StatisticalAnalyzer`` — the
same implementation the GUI's comparison workflow uses.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from models.data_models import ComparisonResult, Dataset, DatasetType
from services.dataset_service import DatasetService
from utils.statistics import StatisticalAnalyzer


class AnalysisService:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.analyzer = StatisticalAnalyzer()
        self.datasets = DatasetService(self.logger)

    def compare_datasets(
        self,
        datasets: Sequence[Dataset],
        gene_list: Optional[List[str]] = None,
        adj_pvalue_cutoff: float = 0.05,
        log2fc_cutoff: float = 1.0,
    ) -> ComparisonResult:
        return self.analyzer.compare_datasets(
            list(datasets),
            gene_list=gene_list,
            adj_pvalue_cutoff=adj_pvalue_cutoff,
            log2fc_cutoff=log2fc_cutoff,
        )

    def compare_files(
        self,
        file_paths: Sequence[str | Path],
        type_hint: Optional[DatasetType] = None,
        gene_list: Optional[List[str]] = None,
        adj_pvalue_cutoff: float = 0.05,
        log2fc_cutoff: float = 1.0,
    ) -> ComparisonResult:
        datasets = [self.datasets.load(Path(path), type_hint) for path in file_paths]
        return self.compare_datasets(
            datasets,
            gene_list=gene_list,
            adj_pvalue_cutoff=adj_pvalue_cutoff,
            log2fc_cutoff=log2fc_cutoff,
        )

    @staticmethod
    def result_to_dict(
        result: ComparisonResult,
        include_table: bool = False,
        table_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "dataset_names": list(result.dataset_names),
            "common_genes": list(result.common_genes),
            "unique_genes": {
                name: list(genes) for name, genes in result.unique_genes.items()
            },
            "overlap_stats": result.get_overlap_stats(),
            "metadata": json.loads(json.dumps(result.metadata, default=str)),
        }
        if include_table and result.comparison_table is not None:
            table = result.comparison_table
            if table_limit is not None:
                table = table.head(max(0, int(table_limit)))
            out["comparison_table"] = json.loads(table.to_json(orient="records"))
        return out

    @staticmethod
    def comparison_table(result: ComparisonResult):
        return result.comparison_table
