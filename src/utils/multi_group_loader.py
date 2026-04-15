"""
Multi-Group Data Loader

LRT omnibus test 결과 + normalized abundance 통합 CSV/Parquet 파일을 로드합니다.

지원 형식:
  - CSV  : gene_id(index), gene_symbol, baseMean, stat, pvalue, padj, sample_cols...
  - Parquet: 동일 구조 (추후 DB import 대비)

Example CSV structure:
  "","gene_symbol","baseMean","stat","pvalue","padj","HP1hr1","HP1hr2","HPctrl1",...

Usage:
    loader = MultiGroupLoader()
    dataset = loader.load(Path("multi_group_result.csv"))
    # dataset.metadata['sample_columns']  -> ['HP1hr1', 'HP1hr2', ...]
    # dataset.metadata['sample_groups']   -> {'HP1hr': ['HP1hr1','HP1hr2'], ...}
    # dataset.metadata['normalization_type'] -> NormalizationType.NORMALIZED_COUNT
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from models.data_models import Dataset, DatasetType, NormalizationType

# 통계 컬럼명 (소문자): 이 컬럼들은 샘플 컬럼에서 제외
_STAT_COLS = frozenset({
    'gene_id', 'gene_symbol', 'gene_name',
    'basemean', 'base_mean',
    'stat', 'statistic',
    'pvalue', 'p_value', 'p.value',
    'padj', 'p_adj', 'p.adj', 'adj_pvalue', 'adj_p',
    'log2foldchange', 'log2fc', 'log2_fold_change', 'lfc',
    'lfcse', 'se',
})


class MultiGroupLoader:
    """
    Multi-Group 데이터 로더

    CSV / Parquet 형식을 동일한 Dataset 객체로 반환합니다.
    normalization_type 은 기본 NORMALIZED_COUNT 로 설정되며,
    추후 VST 분기 지원을 위한 파라미터를 미리 노출해 둡니다.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------ #
    #  Public interface
    # ------------------------------------------------------------------ #

    def load(
        self,
        path: Path,
        name: Optional[str] = None,
        normalization_type: NormalizationType = NormalizationType.NORMALIZED_COUNT,
    ) -> Dataset:
        """
        파일 확장자에 따라 적합한 로더를 자동 선택합니다.

        Args:
            path: 데이터 파일 경로 (.csv 또는 .parquet)
            name: 데이터셋 이름 (None이면 파일명 사용)
            normalization_type: 발현량 정규화 방법 (기본 NORMALIZED_COUNT)
                                 VST 사용 시 NormalizationType.VST 전달

        Returns:
            Dataset (DatasetType.MULTI_GROUP)
        """
        path = Path(path)
        suffix = path.suffix.lower()

        if suffix == '.csv':
            df = self._read_csv(path)
        elif suffix == '.parquet':
            df = self._read_parquet(path)
        else:
            raise ValueError(
                f"Unsupported file format: '{suffix}'. "
                "MultiGroupLoader supports .csv and .parquet."
            )

        return self._build_dataset(
            df=df,
            path=path,
            name=name or path.stem,
            normalization_type=normalization_type,
        )

    def load_from_csv(
        self,
        path: Path,
        name: Optional[str] = None,
        normalization_type: NormalizationType = NormalizationType.NORMALIZED_COUNT,
    ) -> Dataset:
        """CSV 파일 직접 로드 (명시적 호출용)"""
        df = self._read_csv(Path(path))
        return self._build_dataset(df, Path(path), name or Path(path).stem, normalization_type)

    def load_from_parquet(
        self,
        path: Path,
        name: Optional[str] = None,
        normalization_type: NormalizationType = NormalizationType.NORMALIZED_COUNT,
    ) -> Dataset:
        """Parquet 파일 직접 로드 (DB import 경로)"""
        df = self._read_parquet(Path(path))
        return self._build_dataset(df, Path(path), name or Path(path).stem, normalization_type)

    # ------------------------------------------------------------------ #
    #  File readers
    # ------------------------------------------------------------------ #

    def _read_csv(self, path: Path) -> pd.DataFrame:
        """CSV → DataFrame. 첫 번째 unnamed 컬럼을 gene_id로 처리."""
        df = pd.read_csv(path)

        # R write.csv 방식: 첫 컬럼이 unnamed("" or "Unnamed: 0") → gene_id
        first_col = df.columns[0]
        if first_col == '' or first_col.startswith('Unnamed'):
            df = df.rename(columns={first_col: 'gene_id'})
        elif first_col not in df.columns:
            df.index.name = 'gene_id'
            df = df.reset_index()

        # gene_id 컬럼이 없으면 index 사용
        if 'gene_id' not in df.columns:
            df.insert(0, 'gene_id', df.index.astype(str))

        return df

    def _read_parquet(self, path: Path) -> pd.DataFrame:
        """Parquet → DataFrame."""
        df = pd.read_parquet(path)
        if df.index.name and df.index.name != 'RangeIndex':
            df = df.reset_index().rename(columns={df.index.name: 'gene_id'})
        if 'gene_id' not in df.columns:
            df.insert(0, 'gene_id', df.index.astype(str))
        return df

    # ------------------------------------------------------------------ #
    #  Dataset builder
    # ------------------------------------------------------------------ #

    def _build_dataset(
        self,
        df: pd.DataFrame,
        path: Path,
        name: str,
        normalization_type: NormalizationType,
    ) -> Dataset:
        """DataFrame → Dataset 변환 (메타데이터 포함)"""
        sample_columns = self._detect_sample_columns(df)
        sample_groups = self._parse_groups(sample_columns)

        if not sample_columns:
            raise ValueError(
                "No sample columns detected. "
                "Expected numeric columns beyond stat columns (baseMean, stat, pvalue, padj)."
            )

        self.logger.info(
            f"MultiGroupLoader: {len(df)} genes, "
            f"{len(sample_columns)} sample columns, "
            f"{len(sample_groups)} groups detected"
        )

        dataset = Dataset(
            name=name,
            dataset_type=DatasetType.MULTI_GROUP,
            file_path=path,
            dataframe=df,
            metadata={
                'loaded_at': pd.Timestamp.now().isoformat(),
                'row_count': len(df),
                'column_count': len(df.columns),
                'sample_columns': sample_columns,
                'sample_groups': sample_groups,
                'normalization_type': normalization_type,
                # TODO: VST 분기 시 이 값을 확인해 로그 변환 여부 결정
                # if normalization_type == NormalizationType.VST:
                #     abundance_already_log_transformed = True
            },
        )
        return dataset

    # ------------------------------------------------------------------ #
    #  Column detection helpers
    # ------------------------------------------------------------------ #

    def _detect_sample_columns(self, df: pd.DataFrame) -> List[str]:
        """
        숫자형 컬럼 중 알려진 통계 컬럼을 제외한 나머지를 샘플 컬럼으로 반환.
        컬럼 순서는 원본 CSV 순서를 유지.
        """
        sample_cols = []
        for col in df.columns:
            if col.lower() in _STAT_COLS:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                sample_cols.append(col)
        return sample_cols

    def _parse_groups(self, sample_columns: List[str]) -> Dict[str, List[str]]:
        """
        샘플 컬럼명에서 그룹 파싱.

        규칙: 컬럼명 끝의 숫자(replicate)를 분리해 그룹명 추출.
          'HP1hr1' → group='HP1hr', rep=1
          'ctrl_1' → group='ctrl_', rep=1 (또는 'ctrl')

        그룹 순서: 첫 등장 순서 유지 (원본 CSV 컬럼 순서 반영).
        """
        groups: Dict[str, List[str]] = {}
        pattern = re.compile(r'^(.+?)(\d+)$')

        for col in sample_columns:
            m = pattern.match(col)
            if m:
                group_name = m.group(1).rstrip('_')  # 끝 언더스코어 제거
                if not group_name:
                    group_name = col
            else:
                group_name = col  # 패턴 불일치 → 컬럼 자체가 그룹

            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(col)

        return groups

    # ------------------------------------------------------------------ #
    #  Export helpers (DB import 대비)
    # ------------------------------------------------------------------ #

    def export_to_parquet(self, dataset: Dataset, output_path: Path) -> Path:
        """
        Dataset을 Parquet 파일로 저장합니다.

        DB import 시 활용:
            loader.export_to_parquet(dataset, Path("database/datasets/myexp.parquet"))

        Returns:
            저장된 파일 경로
        """
        if dataset.dataframe is None:
            raise ValueError("Dataset has no dataframe to export.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataset.dataframe.to_parquet(output_path, index=False)
        self.logger.info(f"Exported to parquet: {output_path}")
        return output_path

    # ------------------------------------------------------------------ #
    #  Type detection (data_loader.py 에서 호출용)
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_multi_group_dataframe(df: pd.DataFrame) -> bool:
        """
        DataFrame이 MULTI_GROUP 형식인지 판별합니다.

        조건:
          1. 'padj' 컬럼 존재
          2. 'log2foldchange' / 'log2fc' 컬럼 없음  (DE 타입과 구분)
          3. 숫자형 샘플 컬럼 3개 이상 (통계 컬럼 제외)
        """
        cols_lower = {c.lower() for c in df.columns}

        has_padj = 'padj' in cols_lower or 'p_adj' in cols_lower
        is_not_de = not any(
            kw in cols_lower
            for kw in ('log2foldchange', 'log2fc', 'log2_fold_change', 'lfc')
        )

        # 샘플 컬럼 수 확인
        sample_count = sum(
            1 for col in df.columns
            if col.lower() not in _STAT_COLS
            and pd.api.types.is_numeric_dtype(df[col])
        )

        return has_padj and is_not_de and sample_count >= 3
