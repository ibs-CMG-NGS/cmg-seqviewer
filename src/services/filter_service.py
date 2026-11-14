"""Headless filter service.

v1 wraps the existing ``MainPresenter.compute_filtered_df`` so the CLI and MCP
share the exact same filtering behaviour as the GUI. A later phase can move the
pure filter helpers out of the presenter without changing this API.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Optional

import pandas as pd

from models.data_models import Dataset, FilterCriteria


class FilterService:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._presenter = None

    def _get_presenter(self):
        if self._presenter is None:
            from presenters.main_presenter import MainPresenter
            self._presenter = MainPresenter(SimpleNamespace())
        return self._presenter

    def filter(self, dataset: Dataset, criteria: FilterCriteria) -> Optional[pd.DataFrame]:
        presenter = self._get_presenter()
        presenter.current_dataset = dataset
        return presenter.compute_filtered_df(criteria)
