"""
Expression Distribution 로더 — per-sample pseudobulk / quantile summary.

파이프라인 `expression_distribution` 번들의 주 테이블은 **long-format** 이다:

    gene_id | gene_name | cell_type | sample | dataset | condition |
    n_cells | n_expressing | pct_expressing | mean_expression | mean_counts

- `layout: "pseudobulk"`: 한 행 = gene × cell_type × sample (biological replicate)
- `layout: "quantile"`: 한 행 = gene × cell_type (+ p10/p25/median/p75/p90)

`distribution_schema`가 컬럼명/스케일/companion 파일을 지정한다. pseudobulk
테이블은 per-dataset 단위로 pandas에 로드한다. 전체 atlas 규모의 lazy query는
DuckDB/Arrow backend가 필요하며 v1 범위 밖이다 — 대신 행 수가 큰 파일은
`max_rows`로 명시적으로 거부한다.

Qt에 의존하지 않는다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from models.data_models import Dataset, DatasetType

# v1: per-dataset pseudobulk는 pandas로 로드한다. 전체 atlas를 한 파일로 export한
# 경우(수천만 행)는 메모리 폭증을 막기 위해 거부하고, dataset 단위 분할 또는
# 향후 DuckDB backend를 사용한다.
MAX_ROWS = 5_000_000

_GENE_ID_ALIASES = ('gene_id', 'gene', 'geneid', 'ensembl', 'ensembl_id',
                    'entrez', 'entrez_id', 'id', 'symbol')
_GENE_NAME_ALIASES = ('gene_name', 'gene_symbol', 'symbol', 'name')

_REQUIRED_COMMON = {'gene_id', 'cell_type', 'mean_expression'}
_REQUIRED_PSEUDOBULK = {'sample'}
_REQUIRED_QUANTILE = {'median'}

_NUMERIC_COLUMNS = (
    'n_cells', 'n_expressing', 'pct_expressing', 'mean_expression',
    'mean_counts', 'p10', 'p25', 'median', 'p75', 'p90',
)


def _key(name) -> str:
    return str(name).strip().lower().replace(' ', '_')


class ExpressionDistributionLoader:
    """Per-sample pseudobulk / quantile distribution 로더."""

    def __init__(self, distribution_schema: Optional[Dict[str, Any]] = None,
                 logger: Optional[logging.Logger] = None):
        self.schema = dict(distribution_schema or {})
        self.logger = logger or logging.getLogger(__name__)

    # ── Public interface ────────────────────────────────────────────────

    @staticmethod
    def is_distribution_dataframe(df: pd.DataFrame) -> bool:
        """long-format distribution 표인지 보수적으로 판별한다.

        `cell_type` + `mean_expression` 조합은 expression summary long과 겹치므로,
        pseudobulk의 `sample` 또는 quantile의 `median`/`p25`/`p75`가 함께 있어야
        distribution으로 인정한다.
        """
        if df is None or df.empty:
            return False
        cols = {_key(c) for c in df.columns}
        if not {'cell_type', 'mean_expression'}.issubset(cols):
            return False
        return bool(cols & {'sample', 'median', 'p25', 'p75', 'p10', 'p90'})

    def load(self, path: Path, name: Optional[str] = None,
             distribution_schema: Optional[Dict[str, Any]] = None) -> Dataset:
        path = Path(path)
        schema = dict(distribution_schema or self.schema or {})
        df = self._read_table(path)
        return self.load_from_dataframe(
            df, path=path, name=name or path.stem,
            distribution_schema=schema, base_dir=path.parent)

    def load_from_dataframe(self, df: pd.DataFrame, path: Optional[Path] = None,
                            name: Optional[str] = None,
                            distribution_schema: Optional[Dict[str, Any]] = None,
                            base_dir: Optional[Path] = None) -> Dataset:
        if len(df) > MAX_ROWS:
            raise ValueError(
                f"Expression distribution table has {len(df):,} rows; the v1 "
                f"per-dataset limit is {MAX_ROWS:,}. Split the export by dataset "
                "or use a future DuckDB-backed loader.")
        schema = dict(distribution_schema or self.schema or {})
        df, layout = self._normalize(df, schema)
        self._validate(df, layout)

        metadata: Dict[str, Any] = {
            'loaded_at': pd.Timestamp.now().isoformat(),
            'row_count': len(df),
            'column_count': len(df.columns),
            'layout': layout,
            'distribution_schema': schema,
            'gene_count': int(df['gene_id'].nunique()),
            'cell_types': self._unique(df['cell_type']),
            'samples': self._unique(df['sample']) if 'sample' in df.columns else [],
            'conditions': self._unique(df['condition']) if 'condition' in df.columns else [],
            'datasets': self._unique(df['dataset']) if 'dataset' in df.columns else [],
            'pct_scale': schema.get('pct_scale') or self._infer_pct_scale(df),
            'sample_unit': schema.get('sample_unit', ''),
            'value_column': 'mean_expression',
            'value_definition': schema.get('value_definition', ''),
            'detection': schema.get('detection', ''),
            'min_cells': schema.get('min_cells'),
        }
        metadata['cell_type_count'] = len(metadata['cell_types'])
        metadata['sample_count'] = len(metadata['samples'])

        dataset = Dataset(
            name=name or (path.stem if path else 'expression_distribution'),
            dataset_type=DatasetType.EXPRESSION_DISTRIBUTION,
            file_path=path,
            dataframe=df,
            metadata=metadata,
        )

        if base_dir is not None and schema.get('companion_files'):
            self.load_companions(dataset, Path(base_dir))

        self.logger.info(
            f"ExpressionDistributionLoader: {metadata['gene_count']} genes × "
            f"{metadata['cell_type_count']} cell types × "
            f"{metadata['sample_count'] or 1} groups ({layout})")
        return dataset

    # ── Companions ──────────────────────────────────────────────────────

    def load_companions(self, dataset: Dataset, base_dir: Path) -> None:
        """manifest의 companion_files(gene_index/cell_type_summary)를 로드한다."""
        schema = dataset.metadata.get('distribution_schema') or {}
        companions = schema.get('companion_files') or {}
        if not isinstance(companions, dict):
            return
        base_dir = Path(base_dir)
        for key in ('gene_index', 'cell_type_summary'):
            name = companions.get(key)
            if not name:
                continue
            path = base_dir / Path(str(name)).name
            if not path.exists():
                self.logger.warning(
                    f"Expression distribution companion '{key}' not found: {path}")
                continue
            try:
                dataset.metadata[key] = self._read_table(path)
            except Exception as exc:  # noqa: BLE001 — companion 실패가 메인 로드를 막지 않게
                self.logger.warning(
                    f"Failed to read expression distribution companion "
                    f"'{key}': {exc}")

    # ── Normalization / validation ──────────────────────────────────────

    def _normalize(self, df: pd.DataFrame,
                   schema: Dict[str, Any]) -> tuple[pd.DataFrame, str]:
        if df is None or df.empty:
            raise ValueError("Expression distribution table is empty")
        df = df.copy()

        # schema가 지정한 실제 컬럼명 → canonical 컬럼명
        rename = {}
        for canonical, schema_key in (
                ('gene_id', 'gene_id_column'),
                ('gene_name', 'gene_name_column'),
                ('cell_type', 'cell_type_column'),
                ('sample', 'sample_column'),
                ('dataset', 'dataset_column'),
                ('condition', 'condition_column'),
                ('n_cells', 'n_cells_column'),
                ('pct_expressing', 'pct_column'),
                ('mean_expression', 'value_column')):
            src = schema.get(schema_key)
            if src and src in df.columns and src != canonical:
                rename[src] = canonical
        if rename:
            df = df.rename(columns=rename)

        # alias fallback
        if 'gene_id' not in df.columns:
            src = next((c for c in df.columns if _key(c) in _GENE_ID_ALIASES), None)
            if src is not None:
                df = df.rename(columns={src: 'gene_id'})
        if 'gene_name' not in df.columns:
            src = next((c for c in df.columns if _key(c) in _GENE_NAME_ALIASES), None)
            if src is not None:
                df = df.rename(columns={src: 'gene_name'})
        if 'cell_type' not in df.columns:
            for alias in ('celltype', 'cell_type_level', 'cluster', 'group'):
                src = next((c for c in df.columns if _key(c) == alias), None)
                if src is not None:
                    df = df.rename(columns={src: 'cell_type'})
                    break

        for col in ('gene_id', 'cell_type', 'sample', 'dataset', 'condition'):
            if col in df.columns:
                df[col] = df[col].astype(str)
        if 'gene_name' not in df.columns:
            df['gene_name'] = df['gene_id']
        else:
            df['gene_name'] = df['gene_name'].fillna(df['gene_id']).astype(str)

        for col in _NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=['gene_id', 'cell_type', 'mean_expression']).copy()
        df = df[df['gene_id'].astype(str).str.lower() != 'nan']
        df = df[df['cell_type'].astype(str).str.lower() != 'nan']
        if df.empty:
            raise ValueError(
                "Expression distribution table has no valid gene_id/cell_type/"
                "mean_expression rows")

        layout = str(schema.get('layout') or '').strip().lower()
        if not layout:
            layout = 'pseudobulk' if 'sample' in df.columns else 'quantile'
        if layout not in ('pseudobulk', 'quantile'):
            raise ValueError(
                f"Unsupported distribution layout {layout!r}; "
                "use 'pseudobulk' or 'quantile'")
        return df, layout

    @staticmethod
    def _validate(df: pd.DataFrame, layout: str) -> None:
        cols = set(df.columns)
        missing = _REQUIRED_COMMON - cols
        if missing:
            raise ValueError(
                f"Expression distribution is missing required columns: "
                f"{sorted(missing)}. Available: {list(df.columns)}")
        if layout == 'pseudobulk':
            missing = _REQUIRED_PSEUDOBULK - cols
            if missing:
                raise ValueError(
                    "Pseudobulk layout requires a 'sample' column "
                    f"(missing: {sorted(missing)}).")
        else:
            missing = _REQUIRED_QUANTILE - cols
            if missing:
                raise ValueError(
                    "Quantile layout requires a 'median' column "
                    f"(missing: {sorted(missing)}).")

    @staticmethod
    def _infer_pct_scale(df: pd.DataFrame) -> str:
        if 'pct_expressing' not in df.columns:
            return '0-1'
        mx = pd.to_numeric(df['pct_expressing'], errors='coerce').max()
        return '0-100' if pd.notna(mx) and float(mx) > 1.5 else '0-1'

    @staticmethod
    def _unique(series: pd.Series) -> List[str]:
        seen = []
        for value in series.dropna():
            text = str(value)
            if text and text.lower() != 'nan' and text not in seen:
                seen.append(text)
        return seen

    @staticmethod
    def _read_table(path: Path) -> pd.DataFrame:
        suffix = path.suffix.lower()
        if suffix == '.parquet':
            return pd.read_parquet(path, engine='pyarrow')
        if suffix in ('.tsv', '.txt'):
            return pd.read_csv(path, sep='\t')
        if suffix == '.csv':
            return pd.read_csv(path)
        raise ValueError(
            f"Unsupported expression distribution format: {suffix!r} "
            "(use .parquet/.csv/.tsv)")
