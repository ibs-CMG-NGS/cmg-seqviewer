"""Headless access to the pre-loaded dataset database.

The GUI's DatabaseManager already owns import/search/load/export. This service
adds a JSON-friendly, Qt-free facade for the CLI (and later MCP) without
duplicating database logic.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.data_models import Dataset, PreloadedDatasetMetadata
from utils.database_manager import DatabaseManager


class DatabaseService:
    def __init__(
        self,
        database_dir: Optional[str | Path] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.db = DatabaseManager(
            database_dir=Path(database_dir) if database_dir else None
        )

    @staticmethod
    def metadata_dict(meta: PreloadedDatasetMetadata) -> Dict[str, Any]:
        return meta.to_dict()

    def list(
        self,
        query: str = "",
        cell_type: str = "",
        organism: str = "",
        dataset_type: str = "",
        researcher: str = "",
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        metas = self.db.search_datasets(
            query=query,
            cell_type=cell_type,
            organism=organism,
            dataset_type=dataset_type,
            researcher=researcher,
            tags=tags,
        )
        return [self.metadata_dict(meta) for meta in metas]

    def get_metadata(self, dataset_id: str) -> Dict[str, Any]:
        meta = self.db.get_metadata(dataset_id)
        if meta is None:
            raise ValueError(f"Dataset not found: {dataset_id}")
        return self.metadata_dict(meta)

    def load(self, dataset_id: str) -> Dataset:
        dataset = self.db.load_dataset(dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset could not be loaded: {dataset_id}")
        return dataset

    def describe(self, dataset_id: str, include_schema: bool = True) -> Dict[str, Any]:
        from services.dataset_service import DatasetService

        out = self.get_metadata(dataset_id)
        if include_schema:
            try:
                dataset = self.load(dataset_id)
                schema = DatasetService(self.logger).describe(dataset)
                schema.pop("file", None)
                out["schema"] = schema
            except Exception as exc:  # noqa: BLE001 — metadata remains useful
                out["load_error"] = str(exc)
        return out
