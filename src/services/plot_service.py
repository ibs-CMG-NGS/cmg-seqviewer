"""Headless plot service — render a registered plot type to an image file."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping, Optional

import matplotlib
matplotlib.use("Agg")
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from models.data_models import Dataset
from plots.registry import is_supported, render_to_figure, supported_plot_types
from utils.figure_export import save_figure


class PlotService:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def list_plot_types(self) -> list[str]:
        return supported_plot_types()

    def _dataframe(self, data: Dataset | pd.DataFrame) -> pd.DataFrame:
        if isinstance(data, Dataset):
            if data.dataframe is None:
                raise ValueError("Dataset has no dataframe")
            return data.dataframe.copy()
        return data.copy()

    @staticmethod
    def _prepare_for_plot(df: pd.DataFrame, plot_type: str) -> pd.DataFrame:
        """Add the alias columns some renderers use for standard dataset columns."""
        if plot_type == "volcano":
            if "log2FC" not in df.columns and "log2fc" in df.columns:
                df["log2FC"] = df["log2fc"]
            if "padj" not in df.columns and "adj_pvalue" in df.columns:
                df["padj"] = df["adj_pvalue"]
        return df

    def render_figure(self, data: Dataset | pd.DataFrame, plot_type: str,
                      params: Optional[Mapping[str, Any]] = None,
                      figsize: tuple[float, float] = (10.0, 7.0)) -> Figure:
        plot_type = (plot_type or "").lower()
        if not is_supported(plot_type):
            raise ValueError(
                f"Unsupported plot_type {plot_type!r}. "
                f"Available: {', '.join(supported_plot_types())}")
        df = self._prepare_for_plot(self._dataframe(data), plot_type)
        fig = Figure(figsize=figsize)
        FigureCanvasAgg(fig)
        ok = render_to_figure(fig, plot_type, df, dict(params or {}))
        if not ok:
            raise ValueError(f"Could not render plot_type {plot_type!r}")
        return fig

    def render(self, data: Dataset | pd.DataFrame, plot_type: str,
               out_path: str | Path, params: Optional[Mapping[str, Any]] = None,
               fmt: Optional[str] = None, dpi: int = 300,
               figsize: tuple[float, float] = (10.0, 7.0)) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig = self.render_figure(data, plot_type, params=params, figsize=figsize)
        return save_figure(fig, out_path, fmt=fmt, dpi=dpi)
