"""
ATAC-seq Differential Accessibility Data Loader

Excel (.xlsx) 및 Parquet (.parquet) 형식의 ATAC-seq DA 분석 결과를 로드합니다.

지원 형식:
  - Excel: DA_Results 시트 (peak_id, chr, start, end, gene_name, gene_id,
                            annotation, distance_to_tss, baseMean,
                            log2FoldChange, lfcSE, pvalue, padj, direction)
  - Parquet: 동일 구조 또는 표준화된 컬럼명 버전

Usage:
    loader = ATACSeqLoader()
    dataset = loader.load(Path("final_da_result.xlsx"))
    dataset = loader.load(Path("1D_vs_CONTROL_DA.parquet"))
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from models.data_models import Dataset, DatasetType


_DA_SHEET_KEYWORDS = ('da_results', 'da results', 'differential', 'peaks')

COLUMN_PATTERNS: Dict[str, List[str]] = {
    'peak_id':         ['peak_id', 'peakid', 'peak_name', 'peak.id', 'interval'],
    'chromosome':      ['chr', 'chromosome', 'seqnames', 'chrom'],
    'peak_start':      ['start', 'startpos', 'peak_start'],
    'peak_end':        ['end', 'endpos', 'peak_end'],
    'nearest_gene':    ['gene_name', 'nearest_gene', 'symbol', 'genesymbol', 'gene_symbol'],
    'gene_id':         ['gene_id', 'geneid', 'ensembl', 'ensembl_id'],
    'annotation':      ['annotation', 'peak_annotation', 'feature'],
    'distance_to_tss': ['distancetotss', 'distance_to_tss', 'distance.to.tss', 'distancetotss'],
    'base_mean':       ['basemean', 'base_mean', 'conc', 'avg_accessibility'],
    'log2fc':          ['log2foldchange', 'log2fc', 'logfc', 'fold'],
    'lfcse':           ['lfcse', 'lfcstderr', 'lfc_se', 'lfcse'],
    'pvalue':          ['pvalue', 'p.value', 'pval', 'p_value'],
    'adj_pvalue':      ['padj', 'adj_pvalue', 'fdr', 'adj.p.val', 'adj.p.value'],
    'direction':       ['direction', 'regulation'],
}

_ANNOTATION_CATEGORIES = [
    'Promoter', 'Distal Intergenic', 'Intron', "3' UTR", "5' UTR",
    'Exon', 'Downstream', 'Intergenic', 'Enhancer',
]


class ATACSeqLoader:
    """
    ATAC-seq DA 데이터 로더.

    Excel과 Parquet 모두 동일한 COLUMN_PATTERNS로 컬럼을 매핑하며,
    peak_width(end-start)를 계산 컬럼으로 추가합니다.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------ #
    #  Public interface
    # ------------------------------------------------------------------ #

    def load(self, path: Path, name: Optional[str] = None,
            column_mapper_callback=None) -> Dataset:
        """확장자에 따라 Excel 또는 Parquet 자동 선택.

        column_mapper_callback: 필수 컬럼(peak_id/log2fc/adj_pvalue)이 인식되지
        않을 때 수동 매핑 UI 콜백 — (df, dataset_type, auto_mapping) -> {표준: 원본}.
        """
        path = Path(path)
        name = name or path.stem
        suffix = path.suffix.lower()

        if suffix in ('.xlsx', '.xls'):
            return self._load_excel(path, name, column_mapper_callback)
        elif suffix == '.parquet':
            return self._load_parquet(path, name, column_mapper_callback)
        else:
            raise ValueError(f"Unsupported file format for ATAC-seq loader: {suffix}")

    # ------------------------------------------------------------------ #
    #  Detection helper (used by DataLoader)
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_atac_dataframe(df: pd.DataFrame) -> bool:
        """
        peak_id 컬럼 존재 여부로 ATAC DA 데이터 판별.
        MultiGroupLoader.is_multi_group_dataframe() 패턴을 동일하게 적용.
        """
        cols_lower = {c.lower().strip().replace(' ', '_') for c in df.columns}
        atac_id_patterns = {'peak_id', 'peakid', 'peak_name', 'peak.id'}
        return bool(atac_id_patterns & cols_lower)

    # ------------------------------------------------------------------ #
    #  Private loaders
    # ------------------------------------------------------------------ #

    def _load_excel(self, path: Path, name: str, column_mapper_callback=None) -> Dataset:
        """DA_Results 시트(또는 DA 키워드를 가진 첫 번째 시트) 로드."""
        xl = pd.ExcelFile(path)
        sheet = self._select_da_sheet(xl.sheet_names)
        self.logger.debug(f"ATAC Excel: using sheet '{sheet}' from {path.name}")
        df = pd.read_excel(xl, sheet_name=sheet)
        return self._map_and_build(df, name, path, column_mapper_callback)

    def _load_parquet(self, path: Path, name: str, column_mapper_callback=None) -> Dataset:
        """Parquet 파일 로드 (동일 COLUMN_PATTERNS 적용)."""
        df = pd.read_parquet(path)
        self.logger.debug(f"ATAC Parquet: {path.name}, shape={df.shape}")
        return self._map_and_build(df, name, path, column_mapper_callback)

    # ------------------------------------------------------------------ #
    #  Core: mapping + build
    # ------------------------------------------------------------------ #

    def _map_and_build(self, df: pd.DataFrame, name: str, file_path: Path,
                       column_mapper_callback=None) -> Dataset:
        """컬럼 매핑 → 필수 컬럼 확인 → peak_width 계산 → Dataset 생성."""
        mapping = self._map_columns(df)
        df = df.rename(columns=mapping)
        df = self._ensure_required_columns(df, column_mapper_callback)

        # peak_width 계산 (peak_start / peak_end 있을 때)
        if 'peak_start' in df.columns and 'peak_end' in df.columns:
            df['peak_width'] = (df['peak_end'] - df['peak_start']).abs()

        # annotation categories 수집 (필터 패널 드롭다운용)
        annotation_categories: List[str] = []
        if 'annotation' in df.columns:
            raw_cats = df['annotation'].dropna().unique().tolist()
            annotation_categories = self._normalize_annotation_categories(raw_cats)

        # nearest_gene이 peak_id와 동일한 경우(parquet 미완성 데이터) 빈 값으로 처리
        if 'nearest_gene' in df.columns and 'peak_id' in df.columns:
            mask = df['nearest_gene'] == df['peak_id']
            if mask.all():
                df['nearest_gene'] = pd.NA

        original_columns = {v: k for k, v in mapping.items()}

        metadata: dict = {
            'loaded_at': pd.Timestamp.now().isoformat(),
            'annotation_categories': annotation_categories,
        }
        if file_path.suffix.lower() in ('.xlsx', '.xls'):
            metadata['sheet_name'] = 'DA_Results'

        return Dataset(
            name=name,
            dataset_type=DatasetType.ATAC_SEQ,
            file_path=file_path,
            dataframe=df,
            original_columns=original_columns,
            metadata=metadata,
        )

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _map_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        {원본 컬럼명: 표준 컬럼명} 매핑 반환.

        전체 완전 일치를 먼저 한 바퀴 돈 다음, 남은 것만 부분 포함으로 2바퀴째 돈다
        (표준 컬럼 단위로 완전일치->부분일치를 순서대로 처리하면, COLUMN_PATTERNS 뒤쪽
        표준 컬럼의 완전 일치 대상을 앞쪽 표준 컬럼의 부분 포함 단계가 먼저 가로채는
        버그가 있었다 — 예: 'adj_pvalue' 헤더가 자기 패턴 목록에 'adj_pvalue'를 갖고
        있어도, 'pvalue' 표준 컬럼의 부분 포함(「pvalue」 in 「adj_pvalue」)이 먼저 돌아서
        뺏겼다. data_loader.py의 동일 버그와 같은 원인 — §반입 일반성 감사 후속.)
        """
        mapping: Dict[str, str] = {}
        cols_lower = {col: col.lower().replace(' ', '_').replace('.', '_')
                      for col in df.columns}
        already_mapped: set = set()

        # 1단계: 전체 표준 컬럼에 대해 완전 일치부터
        for standard_col, patterns in COLUMN_PATTERNS.items():
            for original_col, lower_col in cols_lower.items():
                if original_col in already_mapped:
                    continue
                if any(lower_col == p for p in patterns):
                    mapping[original_col] = standard_col
                    already_mapped.add(original_col)
                    break

        # 2단계: 완전 일치로 못 찾은 표준 컬럼만 부분 포함으로
        for standard_col, patterns in COLUMN_PATTERNS.items():
            if standard_col in mapping.values():
                continue
            for original_col, lower_col in cols_lower.items():
                if original_col in already_mapped:
                    continue
                if any(p in lower_col for p in patterns):
                    mapping[original_col] = standard_col
                    already_mapped.add(original_col)
                    break

        return mapping

    def _ensure_required_columns(self, df: pd.DataFrame, column_mapper_callback=None) -> pd.DataFrame:
        """필수 컬럼(peak_id/log2fc/adj_pvalue) 확인 — 없으면 column_mapper_callback으로
        수동 매핑을 요청하거나, 콜백이 없으면 사용 가능한 컬럼 목록을 포함한 명확한
        에러를 낸다. COLUMN_PATTERNS에 없는 헤더를 쓰는 파이프라인은 과거엔 여기서
        조용히 통과해 peak_id/log2fc/adj_pvalue가 빈 Dataset이 만들어졌다."""
        from models.standard_columns import StandardColumns
        required = StandardColumns.get_atac_required()
        missing = [c for c in required if c not in df.columns]
        if not missing:
            return df

        if column_mapper_callback:
            from models.data_models import DatasetType
            auto_mapping = {c: c for c in df.columns if c in required}
            user_mapping = column_mapper_callback(df, DatasetType.ATAC_SEQ, auto_mapping)
            if not user_mapping:
                raise ValueError("Column mapping cancelled by user")
            rename = {orig: std for std, orig in user_mapping.items() if orig}
            df = df.rename(columns=rename)
            still_missing = [c for c in required if c not in df.columns]
            if still_missing:
                raise ValueError(
                    f"Missing required ATAC-seq columns after manual mapping: {still_missing}")
            self.logger.info(f"User-provided ATAC-seq column mapping: {user_mapping}")
            return df

        raise ValueError(
            f"Missing required ATAC-seq columns after standardization: {missing}. "
            f"Available columns: {list(df.columns)}. "
            "Recognized header aliases are listed in COLUMN_PATTERNS (atac_seq_loader.py) — "
            "rename the source columns to match one of them, or re-load with a column mapper."
        )

    def _select_da_sheet(self, sheet_names: List[str]) -> str:
        """DA 결과 시트를 우선 선택. 없으면 첫 번째 시트."""
        for sheet in sheet_names:
            lower = sheet.lower().replace(' ', '_')
            if any(kw in lower for kw in _DA_SHEET_KEYWORDS):
                return sheet
        return sheet_names[0]

    def _normalize_annotation_categories(self, raw_cats: List[str]) -> List[str]:
        """
        ChIPseeker annotation 값에서 상위 카테고리를 추출.
        예: "Promoter (<=1kb)" → "Promoter"
        """
        seen: set = set()
        result: List[str] = []
        for cat in sorted(raw_cats):
            prefix = cat.split('(')[0].strip() if '(' in cat else cat.strip()
            if prefix and prefix not in seen:
                seen.add(prefix)
                result.append(prefix)
        return result
