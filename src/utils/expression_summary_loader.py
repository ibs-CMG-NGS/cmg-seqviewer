"""
Expression Summary 로더 (HypoMap 등 gene × cell-type 발현 요약).

기본 레이아웃은 **wide**이다:

    gene_id | gene_name | <cell_type_1> | <cell_type_2> | ...
    G1      | Nkx2-4    | 0.12          | 3.40          | ...

- `gene_id`: 필수 (symbol/Ensembl 무관)
- `gene_name`/`symbol`: 표시용 (없으면 gene_id로 대체)
- 나머지 숫자형 컬럼: 세포타입별 값 (mean_expression 또는 pct_expressing)
- companion 파일 (optional):
    * `pct`: 동일 shape의 pct_expressing 행렬
    * `gene_index`: gene별 max_mean/max_pct/n_cell_types_detected
    * `cell_type_summary`: cell_type별 n_cells/dataset 구성

v1은 **wide layout**을 기본으로 지원하고, per-dataset long layout은 최대
5,000,000행까지 pivot으로 wide를 만들어 사용할 수 있다. 10^7 규모의 전체
long table은 메모리/시간 문제로 거부하며 wide 또는 v2 DuckDB loader를 쓴다.
Qt에 의존하지 않는다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from models.data_models import Dataset, DatasetType

# long layout은 v1에서 pivot으로 wide를 만든다. 10^7 규모는 메모리/시간이 커서
# 거부하고 wide 또는 v2 DuckDB 경로를 사용한다.
MAX_LONG_ROWS = 5_000_000

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
        df = self._read_table(path)
        return self.load_from_dataframe(
            df, path=path, name=name or path.stem, expression_schema=schema,
            base_dir=path.parent)

    def load_from_dataframe(self, df: pd.DataFrame, path: Optional[Path] = None,
                            name: Optional[str] = None,
                            expression_schema: Optional[Dict[str, Any]] = None,
                            base_dir: Optional[Path] = None) -> Dataset:
        schema = dict(expression_schema or self.schema or {})
        long_extras: Dict[str, Any] = {}
        layout = 'wide'
        if 'cell_type' in df.columns:
            layout = 'long'
            df, cell_types, long_extras = self._pivot_long(df, schema)
        else:
            df, cell_types = self._standardize(
                df, cell_type_columns=schema.get('cell_type_columns'))

        if not cell_types:
            raise ValueError(
                "Expression summary requires at least one numeric cell-type "
                f"column. Available columns: {list(df.columns)}")

        pct_scale = (schema.get('pct_scale')
                     or long_extras.get('pct_scale') or '0-1')

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
                'layout': layout,
                'value_type': schema.get('value_type', 'mean_expression'),
                'pct_scale': pct_scale,
                'cell_type_level': schema.get('cell_type_level', ''),
                'gene_id_type': schema.get('gene_id_type', 'symbol'),
                'normalization': schema.get('normalization', ''),
                'expression_schema': schema,
                'gene_index': long_extras.get('gene_index'),
                'pct_matrix': long_extras.get('pct_matrix'),
                'cell_type_summary': long_extras.get('cell_type_summary'),
            },
        )

        if base_dir is not None and schema.get('companion_files'):
            self.load_companions(dataset, Path(base_dir))
        if layout == 'long':
            self._reindex_long(dataset)

        self.logger.info(
            f"ExpressionSummaryLoader: {len(df)} genes × {len(cell_types)} cell types "
            f"({layout})")
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

    # ── Long → wide pivot ───────────────────────────────────────────────

    def _pivot_long(self, df: pd.DataFrame,
                    schema: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str], Dict[str, Any]]:
        """long 표(gene_id, cell_type, mean_expression, pct_expressing, ...)를 wide로 변환.

        per-dataset long(수백만 행)은 v1에서 pivot해 사용할 수 있다. 10^7 규모는
        메모리/시간 문제로 거부한다.
        """
        if len(df) > MAX_LONG_ROWS:
            raise ValueError(
                f"Expression summary long table has {len(df):,} rows; the v1 pivot "
                f"limit is {MAX_LONG_ROWS:,}. Use the wide mean/pct matrices or wait "
                "for the DuckDB-backed long-table loader (v2).")
        required = {'cell_type', 'mean_expression'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"Expression summary long layout is missing {sorted(missing)}. "
                f"Available columns: {list(df.columns)}")

        df = df.copy()
        if 'gene_id' not in df.columns:
            src = next((c for c in df.columns if _key(c) in _GENE_ID_ALIASES), None)
            if src is None and len(df.columns):
                src = df.columns[0]
            if src is not None and src != 'gene_id':
                df = df.rename(columns={src: 'gene_id'})
        if 'gene_id' not in df.columns:
            raise ValueError("Expression summary requires a 'gene_id' column")
        df['gene_id'] = df['gene_id'].astype(str)

        if 'gene_name' not in df.columns:
            src = next((c for c in df.columns if _key(c) in _GENE_NAME_ALIASES), None)
            df['gene_name'] = df[src].astype(str) if src is not None else df['gene_id']
        else:
            df['gene_name'] = df['gene_name'].fillna(df['gene_id']).astype(str)

        df['cell_type'] = df['cell_type'].astype(str)
        has_dataset = ('dataset' in df.columns and df['dataset'].notna().any())
        if has_dataset:
            labels = df['cell_type'] + ' || ' + df['dataset'].astype(str)
        else:
            labels = df['cell_type']
        df['_label'] = labels

        pct_scale = schema.get('pct_scale')
        if 'pct_expressing' in df.columns:
            df['_pct'] = pd.to_numeric(df['pct_expressing'], errors='coerce')
            if pct_scale is None:
                mx = df['_pct'].max()
                pct_scale = '0-100' if pd.notna(mx) and float(mx) > 1.5 else '0-1'
        else:
            df['_pct'] = np.nan
            pct_scale = pct_scale or '0-1'

        # gene × label 중복은 첫 값 사용 (파이프라인 long은 unique)
        base = df.drop_duplicates(['gene_id', '_label'])
        mean_wide = base.pivot(index='gene_id', columns='_label',
                               values='mean_expression')
        cell_types = [str(c) for c in mean_wide.columns]

        names = df.drop_duplicates('gene_id').set_index('gene_id')['gene_name']
        wide = mean_wide.reset_index()
        wide.insert(1, 'gene_name', wide['gene_id'].map(names))
        wide[cell_types] = wide[cell_types].apply(pd.to_numeric, errors='coerce')
        wide[cell_types] = wide[cell_types].fillna(0.0).astype('float32')

        pct_matrix = None
        if base['_pct'].notna().any():
            pct_wide = base.pivot(index='gene_id', columns='_label', values='_pct')
            pct_matrix = pct_wide.reset_index()
            pct_matrix[cell_types] = pct_matrix[cell_types].apply(
                pd.to_numeric, errors='coerce')
            pct_matrix[cell_types] = pct_matrix[cell_types].fillna(0.0).astype('float32')

        # cell_type_summary
        agg = {}
        if 'n_cells' in df.columns:
            agg['n_cells'] = ('n_cells', 'max')
        if 'pct_expressing' in df.columns:
            agg['n_genes_detected'] = ('_pct', lambda s: int((s > 0).sum()))
        if agg:
            summary = df.groupby('_label').agg(**agg).reset_index()
            summary = summary.rename(columns={'_label': 'cell_type'})
        else:
            summary = pd.DataFrame({'cell_type': cell_types})

        # gene_index
        gi_agg = {'max_mean_expression': ('mean_expression', 'max')}
        if 'pct_expressing' in df.columns:
            gi_agg['max_pct_expressing'] = ('_pct', 'max')
            gi_agg['n_cell_types_detected'] = ('_pct', lambda s: int((s > 0).sum()))
        gene_index = df.groupby('gene_id').agg(**gi_agg).reset_index()
        gene_index = gene_index.merge(
            df.drop_duplicates('gene_id')[['gene_id', 'gene_name']],
            on='gene_id', how='left')
        try:
            top_idx = df.groupby('gene_id')['mean_expression'].idxmax()
            top = df.loc[top_idx, ['gene_id', '_label', 'mean_expression']].rename(
                columns={'_label': 'top_cell_type',
                         'mean_expression': 'top_mean_expression'})
            gene_index = gene_index.merge(top, on='gene_id', how='left')
        except Exception:
            pass

        extras = {
            'pct_scale': pct_scale,
            'pct_matrix': pct_matrix,
            'gene_index': gene_index,
            'cell_type_summary': summary,
        }
        return wide, cell_types, extras

    @staticmethod
    def _reindex_long(dataset: Dataset) -> None:
        """gene_index에 있는 모든 유전자가 검색되도록 wide를 재색인하고 0으로 채운다."""
        index_df = dataset.metadata.get('gene_index')
        if not isinstance(index_df, pd.DataFrame) or 'gene_id' not in index_df.columns:
            return
        ids = index_df['gene_id'].astype(str).tolist()
        if not ids:
            return
        cell_types = list(dataset.metadata.get('cell_types') or [])
        order = pd.DataFrame({'gene_id': ids})
        wide = order.merge(dataset.dataframe, on='gene_id', how='left')
        if 'gene_name' in wide.columns:
            wide['gene_name'] = wide['gene_name'].fillna(wide['gene_id'])
        for c in cell_types:
            if c in wide.columns:
                wide[c] = pd.to_numeric(wide[c], errors='coerce').fillna(0.0).astype('float32')
        dataset.dataframe = wide
        dataset.metadata['row_count'] = len(wide)

        pct = dataset.metadata.get('pct_matrix')
        if isinstance(pct, pd.DataFrame) and 'gene_id' in pct.columns:
            pct = order.merge(pct, on='gene_id', how='left')
            for c in cell_types:
                if c in pct.columns:
                    pct[c] = pd.to_numeric(pct[c], errors='coerce').fillna(0.0).astype('float32')
            dataset.metadata['pct_matrix'] = pct

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
