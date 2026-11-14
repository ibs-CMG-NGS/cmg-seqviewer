"""Headless GO/KEGG enrichment orchestration.

The engine itself lives in ``utils.enrichment_analyzer`` (shared with the GUI
worker). This service covers the dataset-source path needed by MCP/CLI without
importing Qt.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

from models.data_models import Dataset
from models.enrichment_models import EnrichmentRequest, EnrichmentResult, ErrorKind
from utils.deg_input import extract_deg_from_dataset
from utils.enrichment_analyzer import EnrichmentAnalyzer, EnrichmentError


class EnrichmentService:
    def __init__(
        self,
        analyzer: Optional[EnrichmentAnalyzer] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.analyzer = analyzer or EnrichmentAnalyzer(logger=self.logger)

    @staticmethod
    def _dataset_symbols(df: pd.DataFrame) -> List[str]:
        col = (
            "symbol"
            if "symbol" in df.columns
            else ("gene_id" if "gene_id" in df.columns else None)
        )
        if col is None:
            return []
        return [str(s) for s in df[col].dropna().unique() if str(s)]

    def run_dataset(
        self, dataset: Dataset, request: EnrichmentRequest
    ) -> EnrichmentResult:
        if request.source != "dataset":
            raise ValueError("EnrichmentService.run_dataset requires source='dataset'")
        problems = request.validate()
        if problems:
            raise EnrichmentError(
                ErrorKind.UNKNOWN, "Request validation failed: " + "; ".join(problems)
            )
        if dataset.dataframe is None:
            raise EnrichmentError(ErrorKind.UNKNOWN, "Dataset has no dataframe")

        deg = extract_deg_from_dataset(
            dataset.dataframe,
            request.fc_min or 0.0,
            request.fdr_max or 1.0,
            request.direction,
            request.organism,
        )
        if not deg.symbols:
            raise EnrichmentError(
                ErrorKind.NO_INPUT_GENES,
                "Extracted DEG genes: 0 (adjust thresholds/filters).",
            )

        background = request.background
        population_symbols = (
            None
            if background is not None
            else (self._dataset_symbols(dataset.dataframe) or None)
        )
        libraries = list(request.libraries or ["BP", "CC", "MF", "KEGG"])

        raw_results, warnings = self.analyzer.enrich_ora(
            deg.symbols,
            background=background,
            organism=deg.species,
            libraries=libraries,
            engine=request.engine,
            direction=deg.direction,
            population_symbols=population_symbols,
            one_sided=bool(request.extra.get("one_sided")),
        )
        df, conv_warnings = self.analyzer.to_standard(raw_results, organism=deg.species)
        warnings = warnings + conv_warnings
        metadata = self.analyzer.build_metadata(
            request,
            raw_results,
            warnings,
            n_deg=len(deg.symbols),
            n_bg=len(background) if background else None,
            organism=deg.species,
        )
        return EnrichmentResult(
            dataframe=df,
            request=request,
            metadata=metadata,
            warnings=warnings,
            engine_used=metadata.get("engine_effective") or request.engine,
            dataset_name=f"Enrichment: {dataset.name}",
        )
