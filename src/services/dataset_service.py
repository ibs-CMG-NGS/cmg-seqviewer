"""Headless dataset service — load/describe/summary/query/export.

This is the shared layer the CLI (and later MCP) should use. It deliberately
contains no Qt imports.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from models.data_models import Dataset, DatasetType
from models.standard_columns import StandardColumns
from utils.data_loader import DataLoader
from utils.dataset_detection import load_any_dataset


_REQUIRED_COLUMNS = {
    DatasetType.DIFFERENTIAL_EXPRESSION: StandardColumns.get_de_required,
    DatasetType.GO_ANALYSIS: StandardColumns.get_go_required,
    DatasetType.ATAC_SEQ: StandardColumns.get_atac_required,
    DatasetType.COMPOSITION: StandardColumns.get_composition_required,
    DatasetType.EXPRESSION_SUMMARY: StandardColumns.get_expression_summary_required,
    DatasetType.EXPRESSION_DISTRIBUTION: StandardColumns.get_expression_distribution_required,
    DatasetType.CHROMVAR_DIFF_TF: StandardColumns.get_chromvar_required,
    DatasetType.TF_FOOTPRINT: StandardColumns.get_footprint_required,
    DatasetType.MOTIF_ENRICHMENT: StandardColumns.get_motif_required,
}


def _json_safe(value: Any) -> Any:
    """Convert pandas/numpy/path values to JSON-serialisable values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, pd.DataFrame):
        return {"rows": int(len(value)), "columns": [str(c) for c in value.columns]}
    if isinstance(value, pd.Series):
        return {"length": int(len(value)), "name": str(value.name or "")}
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


class DatasetService:
    """Load and inspect one dataset without touching the GUI."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._data_loader = DataLoader()

    def load(self, file_path: str | Path, type_hint: Optional[DatasetType] = None,
             name: Optional[str] = None,
             column_mapper=None) -> Dataset:
        return load_any_dataset(
            Path(file_path), self._data_loader, name=name,
            dataset_type_hint=type_hint,
            column_mapper_callback=column_mapper,
            logger=self.logger,
        )

    def describe(self, dataset: Dataset) -> Dict[str, Any]:
        required_getter = _REQUIRED_COLUMNS.get(dataset.dataset_type)
        required = list(required_getter()) if required_getter else []
        present = [str(c) for c in (dataset.dataframe.columns
                                     if dataset.dataframe is not None else [])]
        report = {
            "dataset_type": dataset.dataset_type.value,
            "name": dataset.name,
            "rows": int(len(dataset.dataframe)) if dataset.dataframe is not None else 0,
            "columns": present,
            "valid": bool(dataset.is_valid),
            "required_columns": required,
            "missing_required_columns": [c for c in required if c not in present],
        }
        if dataset.file_path is not None:
            report["file"] = str(dataset.file_path)
        return report

    def summary(self, dataset: Dataset) -> Dict[str, Any]:
        """JSON-safe dataset summary (DataFrames become shape/column metadata)."""
        return _json_safe(dataset.get_summary())

    def query(self, dataset: Dataset, columns: Optional[List[str]] = None,
              limit: Optional[int] = None, offset: int = 0) -> pd.DataFrame:
        if dataset.dataframe is None:
            return pd.DataFrame()
        df = dataset.dataframe
        if columns:
            missing = [c for c in columns if c not in df.columns]
            if missing:
                raise ValueError(
                    f"Unknown column(s): {missing}. Available: {list(df.columns)}")
            df = df[columns]
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if limit is not None and limit < 0:
            raise ValueError("limit must be >= 0")
        end = None if limit is None else offset + limit
        return df.iloc[offset:end].copy()

    def export(self, data: Dataset | pd.DataFrame, out_path: str | Path,
               fmt: Optional[str] = None) -> Path:
        out_path = Path(out_path)
        df = data.dataframe if isinstance(data, Dataset) else data
        if df is None:
            raise ValueError("Dataset has no dataframe")
        fmt = (fmt or out_path.suffix.lstrip(".") or "csv").lower()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if fmt in ("xlsx", "xls"):
            df.to_excel(out_path, index=False)
        elif fmt == "csv":
            df.to_csv(out_path, index=False)
        elif fmt == "tsv":
            df.to_csv(out_path, index=False, sep="\t")
        elif fmt == "parquet":
            df.to_parquet(out_path, index=False)
        else:
            raise ValueError(
                f"Unsupported output format: {fmt!r} "
                "(use .xlsx/.csv/.tsv/.parquet)")
        return out_path
