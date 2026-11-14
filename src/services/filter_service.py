"""Headless filter service.

The pure filtering logic lives in ``services.filter_engine.FilterEngine``; the
GUI presenter delegates to the same engine. This service keeps the CLI/MCP API
stable without importing Qt or constructing a MainPresenter.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.data_models import Dataset, FilterCriteria
from services.filter_engine import FilterEngine


class FilterService:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.engine = FilterEngine(self.logger)

    def filter(
        self, dataset: Dataset, criteria: FilterCriteria
    ) -> Optional[pd.DataFrame]:
        return self.engine.filter(dataset, criteria)
