"""
Expression Summary 로더 (HypoMap 등 gene × cell-type 발현 요약).

v1은 **wide layout**만 지원한다:

    gene_id | gene_name | <cell_type_1> | <cell_type_2> | ...
    G1      | Nkx2-4    | 0.12          | 3.40          | ...

- `gene_id`: 필수 (symbol/Ensembl 무관)
- `gene_name`/`symbol`: 표시용 (없으면 gene_id로 대체)
- 나머지 숫자형 컬럼: 세포타입별 값 (mean_expression 또는 pct_expressing)
- companion 파일 (ptional):
    * `pct`: 동일 shape의 pct_expressing 행렬
    * `gene_index`: gene별 max_mean/max_pct/n_cell_types_detected
    * `cell_type_summary`: cell_type별 n_cells/dataset 구성

long layout(10^7 rows)은 v1에서 명시적으로 거부한다 — wide 또는 v2 DuckDB
loader를 사용해야 한다. Qt에 의존하지 않는다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from models.data_models import Dataset, DatasetType

# 세포타입 컬럼이 아닌 메타/지표 컬럼
_NON_CELL_TYPE_COLUMNS = {
    'gene_id', 'gene', 'geneid', 'id',
    'gene_name', 'gene_symbol', 'symbol', 'gene_symbol_name',
    'cell_type', 'cell_type_level', 'dataset',
    'mean_expression', 'pct_expressing', 'n_cells', 'n_expressing',
    'mean_counts', 'max_mean', 'max_pct', 'n_cell_types_detected',
    'description', 'notes',
}

_GENE_ID_ALIASES = ('gene_id', 'gene', 'geneid', 'ensembl', 'ensembl_id', 'entrez', 'entrez_id', 'id')
_GENE_NAME_ALIASES = ('gene_name', 'symbol', 'gene_symbol', 'gene_symbol_name', 'name')


def _key(name) -> str:
    return str(name).strip().lower().replace(' ', '_')


class ExpressionSummaryLoader:
    """Wide gene × cell-type 발현 요약 로더."""

    def __init__(self, expression_schema: Optional[Dict[str, Any]] = None,
                 logger: Optional[logging.Logger] = None):
        self.schema = dict(expression_schema or {})
        self.logger = logger or logging.getLogger(__name__)

    # ── Public interface ────────────────────────────────────────────────

    def load(self, path: Path, name: Optional[str] = None,
             expression_schema: Optional[Dict[str, Any]] = None) -> Dataset:
        path = Path(path)
        schema = dict(expression_schema or self.schema or {})
        self._reject_long_layout(schema)
        df = self._read_table(path)
        return self.load_from_dataframe(
            df, path=path, name=name or path.stem, expression_schema=schema,
            base_dir=path.parent)

    def load_from_dataframe(self, df: pd.DataFrame, path: Optional[Path] = None,
                            name: Optional[str] = None,
                            expression_schema: Optional[Dict[str, Any]] = None,
                            base_dir: Optional[Path] = None) -> Dataset:
        schema = dict(expression_schema or self.schema or {})
        self._reject_long_layout(schema)
        if 'cell_type' in df.columns:
            raise ValueError(
                "Expression summary long layout is not supported in this version. "
                "Export the wide mean/pct matrices (gene × cell_type) instead.")

        df, cell_types = self._standardize(
            df, cell_type_columns=schema.get('cell_type_columns'))
        if not cell_types:
            raise ValueError(
                "Expression summary (wide) requires at least one numeric cell-type "
                f"column. Available columns: {list(df.columns)}")

        dataset = Dataset(
            name=name or (path.stem if path else "expression_summary"),
            dataset_type=DatasetType.EXPRESSION_SUMMARY,
            file_path=path,
            dataframe=df,
            metadata={
                'loaded_at': pd.Timestamp.now().isoformat(),
                'row_count': len(df),
                'column_count': len(df.columns),
                'cell_types': cell_types,
                'cell_type_count': len(cell_types),
                'value_type': schema.get('value_type', 'mean_expression'),
                'pct_scale': schema.get('pct_scale', '0-1'),
                'cell_type_level': schema.get('cell_type_level', ''),
                'gene_id_type': schema.get('gene_id_type', 'symbol'),
                'normalization': schema.get('normalization', ''),
                'expression_schema': schema,
                'gene_index': None,
                'pct_matrix': None,
                'cell_type_summary': None,
            },
        )

        if base_dir is not None and schema.get('companion_files'):
            self.load_companions(dataset, Path(base_dir))

        self.logger.info(
            f"ExpressionSummaryLoader: {len(df)} genes × {len(cell_types)} cell types")
        return dataset

    # ── Companions ──────────────────────────────────────────────────────

    def load_companions(self, dataset: Dataset, base_dir: Path) -> None:
        """manifest의 companion_files를 같은 폴더에서 로드해 metadata에 붙인다."""
        schema = dataset.metadata.get('expression_schema') or {}
        companions = schema.get('companion_files') or {}
        if not isinstance(companions, dict):
            return

        base_dir = Path(base_dir)

        def _read(name, label):
            if not name:
                return None
            p = base_dir / Path(str(name)).name
            if not p.exists():
                self.logger.warning(f"Expression companion '{label}' not found: {p}")
                return None
            try:
                return self._read_table(p)
            except Exception as exc:  # noqa: BLE001 — companion 실패가 메인 로드를 막지 않게
                self.logger.warning(f"Failed to read expression companion '{label}': {exc}")
                return None

        pct_df = _read(companions.get('pct'), 'pct')
        if pct_df is not None:
            pct_df, _ = self._standardize(
                pct_df, cast_float32=True,
                cell_type_columns=schema.get('cell_type_columns'))
            dataset.metadata['pct_matrix'] = self._align_to_genes(dataset.dataframe, pct_df)

        index_df = _read(companions.get('gene_index'), 'gene_index')
        if index_df is not None:
            dataset.metadata['gene_index'] = self._standardize_gene_table(index_df)

        summary_df = _read(companions.get('cell_type_summary'), 'cell_type_summary')
        if summary_df is not None:
            dataset.metadata['cell_type_summary'] = summary_df

    # ── Standardization ─────────────────────────────────────────────────

    @staticmethod
    def _reject_long_layout(schema: Dict[str, Any]) -> None:
        layout = str(schema.get('layout', 'wide')).lower()
        if layout == 'long':
            raise ValueError(
                "Expression summary long layout is not supported in this version. "
                "Export the wide mean/pct matrices (gene × cell_type) or wait for the "
                "DuckDB-backed long-table loader (v2).")

    def _read_table(self, path: Path) -> pd.DataFrame:
        suffix = path.suffix.lower()
        if suffix == '.parquet':
            return pd.read_parquet(path)
        if suffix == '.csv':
            return pd.read_csv(path)
        if suffix in ('.tsv', '.txt'):
            return pd.read_csv(path, sep='\t')
        if suffix in ('.xlsx', '.xls', '.xlsm'):
            return pd.read_excel(path)
        raise ValueError(
            f"Unsupported expression summary format: {suffix!r} "
            "(use .parquet/.csv/.tsv)")

    def _standardize(self, df: pd.DataFrame,
                     cast_float32: bool = True,
                     cell_type_columns: Optional[List[str]] = None) -> Tuple[pd.DataFrame, List[str]]:
        df = df.copy()

        # gene_id: 표준명이 없으면 alias → 첫 컬럼 순으로 보완
        if 'gene_id' not in df.columns:
            src = next((c for c in df.columns if _key(c) in _GENE_ID_ALIASES), None)
            if src is None and len(df.columns):
                src = df.columns[0]
            if src is not None and src != 'gene_id':
                df = df.rename(columns={src: 'gene_id'})

        if 'gene_id' not in df.columns:
            raise ValueError("Expression summary requires a 'gene_id' column")

        df['gene_id'] = df['gene_id'].astype(str)

        # gene_name: 없으면 symbol/gene_symbol에서 복사 (gene_id fallback)
        if 'gene_name' not in df.columns:
            src = next((c for c in df.columns if _key(c) in _GENE_NAME_ALIASES), None)
            if src is not None:
                df['gene_name'] = df[src].astype(str)
            else:
                df['gene_name'] = df['gene_id']

        # 세포타입 컬럼: schema에 명시되어 있으면 그것을, 아니면 숫자형/비메타 컬럼
        if cell_type_columns:
            cell_types = [c for c in cell_type_columns if c in df.columns]
        else:
            cell_types = [
                c for c in df.columns
                if _key(c) not in _NON_CELL_TYPE_COLUMNS
                and pd.api.types.is_numeric_dtype(df[c])
            ]
        if cast_float32:
            for c in cell_types:
                df[c] = pd.to_numeric(df[c], errors='coerce').astype('float32')

        return df, cell_types

    def _standardize_gene_table(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if 'gene_id' not in df.columns:
            src = next((c for c in df.columns if _key(c) in _GENE_ID_ALIASES), None)
            if src is not None and src != 'gene_id':
                df = df.rename(columns={src: 'gene_id'})
        if 'gene_id' not in df.columns and len(df.columns):
            df = df.rename(columns={df.columns[0]: 'gene_id'})
        if 'gene_id' in df.columns:
            df['gene_id'] = df['gene_id'].astype(str)
        if 'gene_name' not in df.columns:
            src = next((c for c in df.columns if _key(c) in _GENE_NAME_ALIASES), None)
            if src is not None:
                df['gene_name'] = df[src].astype(str)
        return df

    @staticmethod
    def _align_to_genes(primary: pd.DataFrame, companion: pd.DataFrame) -> pd.DataFrame:
        """companion(pct) 행을 primary gene_id 순서에 맞춘다."""
        if 'gene_id' not in companion.columns:
            return companion
        comp = companion.drop_duplicates(subset=['gene_id']).set_index('gene_id')
        aligned = primary[['gene_id']].copy()
        aligned = aligned.join(comp, on='gene_id')
        return aligned
