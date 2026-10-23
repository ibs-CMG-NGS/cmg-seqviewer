"""
Cell-type Composition 로더 (propeller/limma 결과).

R 파이프라인의 일반적인 출력 형태:

    cell_type | PropMean.Control | PropMean.Treatment | PropRatio | P.Value | FDR

- `cell_type` : 세포 타입 이름 (행 식별자)
- `PropMean.<condition>` : 조건별 평균 비율 (가변 개수)
- `PropRatio` : 조건 간 비율 차이
- `P.Value` / `FDR` : 통계 유의성

표준화 결과:
- 세포 타입 컬럼 → `cell_type`
- `PropRatio` 계열 → `prop_ratio`
- `P.Value` 계열 → `pvalue`
- `FDR`/`padj` 계열 → `fdr`
- `PropMean.<condition>` 컬럼은 조건명이 가변이므로 **원본 이름 그대로 보존**하고,
  `Dataset.metadata['mean_columns']` / `['conditions']`에 기록한다.

DataLoader/MultiGroupLoader와 동일하게 Qt에 의존하지 않는다.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from models.data_models import Dataset, DatasetType

_CELL_TYPE_KEYS = {
    'cell_type', 'celltype', 'cell_type_name', 'celltype_name',
    'population', 'cell_population',
}
_PVALUE_KEYS = {'pvalue', 'p_value', 'p.value', 'pval', 'p-value'}
_FDR_KEYS = {
    'fdr', 'padj', 'p_adj', 'p.adj', 'p_adjusted', 'p.adjust',
    'adj_pvalue', 'adj_p', 'qvalue', 'q_value', 'q.value',
}
_PROP_RATIO_KEYS = {'propratio', 'prop_ratio', 'prop.ratio', 'prop_ratio_change'}

# "PropMean.<condition>" / "prop_mean_<condition>" / "PropMean <condition>"
_PROP_MEAN_RE = re.compile(r'^prop[._]?mean[._\-\s]+(.+)$', re.IGNORECASE)


def _key(name) -> str:
    """비교용 키: 소문자화 + 공백/하이픈을 언더스코어로."""
    return re.sub(r'[\s\-]+', '_', str(name).strip().lower())


def prop_mean_condition(column) -> Optional[str]:
    """`PropMean.<condition>` 컬럼이면 조건명을, 아니면 None."""
    m = _PROP_MEAN_RE.match(str(column).strip())
    return m.group(1).strip() if m else None


class CompositionLoader:
    """Cell-type composition 결과 로더."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # ── Public interface ────────────────────────────────────────────────

    @staticmethod
    def is_composition_dataframe(df: pd.DataFrame) -> bool:
        """composition 표인지 판별.

        조건: 세포 타입 컬럼 + (`PropRatio` 또는 `PropMean.*` 2개 이상) + p-value/FDR.
        """
        if df is None or df.empty:
            return False
        cols = list(df.columns)
        has_cell = any(_key(c) in _CELL_TYPE_KEYS for c in cols)
        if not has_cell:
            return False
        means = [c for c in cols if prop_mean_condition(c) is not None]
        has_ratio = any(_key(c) in _PROP_RATIO_KEYS for c in cols)
        has_stat = any(_key(c) in _PVALUE_KEYS or _key(c) in _FDR_KEYS for c in cols)
        return has_stat and (has_ratio or len(means) >= 2)

    def load(self, path: Path, name: Optional[str] = None) -> Dataset:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix in ('.xlsx', '.xls', '.xlsm'):
            df = pd.read_excel(path)
        elif suffix == '.parquet':
            df = pd.read_parquet(path)
        elif suffix == '.csv':
            df = pd.read_csv(path)
        elif suffix in ('.tsv', '.txt'):
            df = pd.read_csv(path, sep='\t')
        else:
            raise ValueError(
                f"Unsupported composition file format: {suffix!r} "
                "(use .xlsx/.csv/.tsv/.parquet)")
        return self.load_from_dataframe(df, path, name or path.stem)

    def load_from_dataframe(self, df: pd.DataFrame, path: Optional[Path] = None,
                            name: Optional[str] = None) -> Dataset:
        df, mean_columns, conditions = self._standardize(df)

        if 'cell_type' not in df.columns:
            raise ValueError(
                "Missing required composition column 'cell_type'. "
                f"Available columns: {list(df.columns)}")
        if not mean_columns and 'prop_ratio' not in df.columns:
            raise ValueError(
                "Composition data needs either 'PropMean.<condition>' columns or "
                f"'PropRatio'. Available columns: {list(df.columns)}")

        dataset = Dataset(
            name=name or (path.stem if path else "composition"),
            dataset_type=DatasetType.COMPOSITION,
            file_path=path,
            dataframe=df,
            metadata={
                'loaded_at': pd.Timestamp.now().isoformat(),
                'row_count': len(df),
                'column_count': len(df.columns),
                'cell_type_column': 'cell_type',
                'mean_columns': mean_columns,
                'conditions': conditions,
            },
        )
        self.logger.info(
            f"CompositionLoader: {len(df)} cell types, "
            f"{len(mean_columns)} condition mean column(s)")
        return dataset

    # ── Standardization ─────────────────────────────────────────────────

    def _standardize(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], List[str]]:
        df = df.copy()

        # 세포 타입 컬럼
        cell_col = next((c for c in df.columns if _key(c) in _CELL_TYPE_KEYS), None)
        if cell_col is not None and cell_col != 'cell_type':
            df = df.rename(columns={cell_col: 'cell_type'})

        # p-value / FDR / PropRatio (이미 대상 이름이 있으면 건드리지 않음)
        def _rename_first(aliases: set, target: str):
            nonlocal df
            if target in df.columns:
                return
            src = next((c for c in df.columns if _key(c) in aliases), None)
            if src is not None and src != target:
                df = df.rename(columns={src: target})

        _rename_first(_PVALUE_KEYS, 'pvalue')
        _rename_first(_FDR_KEYS, 'fdr')
        _rename_first(_PROP_RATIO_KEYS, 'prop_ratio')

        # 중복 컬럼 제거 (keep first)
        if df.columns.duplicated().any():
            df = df.loc[:, ~df.columns.duplicated(keep='first')]

        mean_columns = [c for c in df.columns if prop_mean_condition(c) is not None]
        conditions = [prop_mean_condition(c) for c in mean_columns]

        # 수치형 변환
        for col in mean_columns + [c for c in ('prop_ratio', 'pvalue', 'fdr') if c in df.columns]:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'cell_type' in df.columns:
            df['cell_type'] = df['cell_type'].astype(str).str.strip()
            df = df[df['cell_type'].notna() & (df['cell_type'] != '')].copy()
            df = df[~df['cell_type'].str.lower().isin(('nan', 'none'))].copy()

        return df.reset_index(drop=True), mean_columns, conditions
