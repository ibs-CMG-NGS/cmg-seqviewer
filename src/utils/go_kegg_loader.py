"""
GO/KEGG Enrichment Results Loader

여러 형식의 GO/KEGG 분석 결과를 로딩하고 통합합니다.
"""

import pandas as pd
from pathlib import Path
from typing import List, Optional
import logging

from models.data_models import Dataset, DatasetType
from models.standard_columns import StandardColumns

# ---------------------------------------------------------------------------
# 공용 표준화 파이프라인 (plan §8/G4/G5/G6 — 단일 진실원천)
#
# GOKEGGLoader의 기존 메서드들은 아래 모듈 함수에 위임하며,
# enrichment_analyzer.EnrichmentAnalyzer도 동일 함수를 사용한다 (G4/G5/G6).
# ---------------------------------------------------------------------------


def _resolve_logger(logger: Optional[logging.Logger]) -> logging.Logger:
    return logger if logger is not None else logging.getLogger(__name__)


def compute_fold_enrichment(df: pd.DataFrame, logger: Optional[logging.Logger] = None) -> pd.DataFrame:
    """
    gene_ratio와 bg_ratio로부터 fold_enrichment 파생 계산.

    FoldEnrichment = GeneRatio / BgRatio = (k/n) / (M/N)
    - k : DEG 중 해당 term 히트 수
    - n : 전체 DEG 수
    - M : 배경 genome에서 해당 term 크기
    - N : 배경 genome 전체 gene 수

    이미 fold_enrichment 컬럼이 있으면 덮어쓰지 않는다. (G6 — 데이터로더 중복 제거)
    """
    logger = _resolve_logger(logger)
    fe_col = StandardColumns.FOLD_ENRICHMENT
    gr_col = StandardColumns.GENE_RATIO
    br_col = StandardColumns.BG_RATIO

    if fe_col in df.columns:
        return df
    if gr_col not in df.columns or br_col not in df.columns:
        return df

    def _parse_ratio(val) -> float:
        """'10/100' 형식 또는 float 값을 float으로 변환"""
        try:
            if pd.isna(val):
                return float('nan')
            if isinstance(val, (int, float)):
                return float(val)
            parts = str(val).split('/')
            if len(parts) == 2:
                num, den = float(parts[0]), float(parts[1])
                return num / den if den > 0 else float('nan')
        except Exception:
            pass
        return float('nan')

    gr = df[gr_col].apply(_parse_ratio)
    br = df[br_col].apply(_parse_ratio)

    # BgRatio == 0 이면 NaN 처리
    fold_enrichment = gr / br.replace(0, float('nan'))
    df = df.copy()
    df[fe_col] = fold_enrichment.round(4)

    n_computed = fold_enrichment.notna().sum()
    logger.info(f"Computed fold_enrichment for {n_computed}/{len(df)} rows (gene_ratio / bg_ratio)")
    return df


def standardize_columns(df: pd.DataFrame, logger: Optional[logging.Logger] = None) -> pd.DataFrame:
    """
    컬럼명을 표준 이름으로 변환 (GO/KEGG 결과 — 원본 컬럼 -> StandardColumns).

    GO ID, GO Term -> term_id, description / KEGG ID, KEGG Pathway -> term_id, description
    """
    logger = _resolve_logger(logger)
    df = df.copy()

    column_mapping = {
        'GO ID': StandardColumns.TERM_ID, 'KEGG ID': StandardColumns.TERM_ID,
        'GO id': StandardColumns.TERM_ID, 'KEGG id': StandardColumns.TERM_ID,
        'Term ID': StandardColumns.TERM_ID, 'term_id': StandardColumns.TERM_ID,
        'ID': StandardColumns.TERM_ID,
        'GO Term': StandardColumns.DESCRIPTION, 'KEGG Pathway': StandardColumns.DESCRIPTION,
        'GO term': StandardColumns.DESCRIPTION, 'KEGG pathway': StandardColumns.DESCRIPTION,
        'Description': StandardColumns.DESCRIPTION, 'Term': StandardColumns.DESCRIPTION,
        'Gene Symbols': StandardColumns.GENE_SYMBOLS, 'Gene symbols': StandardColumns.GENE_SYMBOLS,
        'Genes': StandardColumns.GENE_SYMBOLS, 'Gene ID': StandardColumns.GENE_SYMBOLS,
        'geneID': StandardColumns.GENE_SYMBOLS,
        'core_enrichment': StandardColumns.GENE_SYMBOLS,
        'Core Enrichment': StandardColumns.GENE_SYMBOLS,
        'core enrichment': StandardColumns.GENE_SYMBOLS,
        'coreEnrichment': StandardColumns.GENE_SYMBOLS,
        'P-value': StandardColumns.PVALUE_GO, 'P-Value': StandardColumns.PVALUE_GO,
        'pvalue': StandardColumns.PVALUE_GO,
        'Adjusted P-value': StandardColumns.FDR, 'Adjusted P-Value': StandardColumns.FDR,
        'padj': StandardColumns.FDR, 'FDR': StandardColumns.FDR, 'p.adjust': StandardColumns.FDR,
        'Q-value': StandardColumns.QVALUE, 'Q-Value': StandardColumns.QVALUE,
        'qvalue': StandardColumns.QVALUE,
        'Gene Ratio': StandardColumns.GENE_RATIO, 'Gene ratio': StandardColumns.GENE_RATIO,
        'GeneRatio': StandardColumns.GENE_RATIO,
        'Background Ratio': StandardColumns.BG_RATIO, 'Background ratio': StandardColumns.BG_RATIO,
        'BgRatio': StandardColumns.BG_RATIO,
        'Gene Count': StandardColumns.GENE_COUNT, 'Gene count': StandardColumns.GENE_COUNT,
        'Count': StandardColumns.GENE_COUNT,
        'Direction': StandardColumns.DIRECTION, 'direction': StandardColumns.DIRECTION,
        'Regulation': StandardColumns.DIRECTION, 'regulation': StandardColumns.DIRECTION,
        'Ontology': StandardColumns.ONTOLOGY, 'ontology': StandardColumns.ONTOLOGY,
        'Category': StandardColumns.ONTOLOGY, 'category': StandardColumns.ONTOLOGY,
        'ONTOLOGY': StandardColumns.ONTOLOGY,
        'Gene Set': StandardColumns.GENE_SET, 'Gene.Set': StandardColumns.GENE_SET,
        'gene set': StandardColumns.GENE_SET, 'gene.set': StandardColumns.GENE_SET,
        'GeneSet': StandardColumns.GENE_SET, 'geneset': StandardColumns.GENE_SET,
        'GO.ID': StandardColumns.TERM_ID, 'KEGG.ID': StandardColumns.TERM_ID,
        'GO.Term': StandardColumns.DESCRIPTION, 'KEGG.Pathway': StandardColumns.DESCRIPTION,
        'Gene.Symbols': StandardColumns.GENE_SYMBOLS,
        'Adjusted.P-value': StandardColumns.FDR, 'Adjusted.P.value': StandardColumns.FDR,
        'Gene.Ratio': StandardColumns.GENE_RATIO, 'Background.Ratio': StandardColumns.BG_RATIO,
        'Gene.Count': StandardColumns.GENE_COUNT,
    }

    rename_dict = {}
    for col in df.columns:
        if col in column_mapping:
            rename_dict[col] = column_mapping[col]

    if rename_dict:
        df.rename(columns=rename_dict, inplace=True)
        logger.info(f"Standardized columns: {rename_dict}")

    # 중복 컬럼 병합 (같은 표준 컬럼명으로 여러 원본 컬럼이 매핑되는 경우)
    if df.columns.duplicated().any():
        duplicated_names = df.columns[df.columns.duplicated()].unique().tolist()
        for col_name in duplicated_names:
            dup_cols = [i for i, c in enumerate(df.columns) if c == col_name]
            if len(dup_cols) >= 2:
                merged = df.iloc[:, dup_cols[0]].copy()
                for idx in dup_cols[1:]:
                    merged = merged.fillna(df.iloc[:, idx])
                df.iloc[:, dup_cols[0]] = merged
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
        logger.info(f"Merged duplicate columns (NaN-filled): {duplicated_names}")

    df = compute_fold_enrichment(df, logger)

    # 파이프라인이 분석 파라미터를 ontology='Info' 행으로 삽입한 경우 제거
    ontology_col = StandardColumns.ONTOLOGY
    if ontology_col in df.columns:
        info_mask = df[ontology_col].astype(str).str.strip().str.lower() == 'info'
        if info_mask.any():
            n = int(info_mask.sum())
            df = df[~info_mask].copy()
            logger.info(f"Dropped {n} pipeline metadata rows (ontology='Info')")
    drop_cols = [c for c in ['Parameter', 'Value'] if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)
        logger.info(f"Dropped pipeline-metadata-only columns: {drop_cols}")

    return df


def extract_direction_ontology(df: pd.DataFrame, logger: Optional[logging.Logger] = None) -> pd.DataFrame:
    """
    Gene Set 컬럼에서 Direction과 Ontology 추출.

    Gene Set 형식: "UP_BP", "DOWN_MF", "UP_CC", "KEGG", "TOTAL_KEGG" 등.
    """
    logger = _resolve_logger(logger)
    if StandardColumns.GENE_SET not in df.columns:
        logger.warning("Gene Set column not found, skipping direction/ontology extraction")
        return df

    def parse_gene_set(gene_set_value):
        if pd.isna(gene_set_value):
            return 'UNKNOWN', 'UNKNOWN'
        gene_set_str = str(gene_set_value).strip().upper()

        ontology = 'UNKNOWN'
        if 'KEGG' in gene_set_str:
            ontology = 'KEGG'
        elif '_BP' in gene_set_str or gene_set_str.endswith('BP'):
            ontology = 'BP'
        elif '_MF' in gene_set_str or gene_set_str.endswith('MF'):
            ontology = 'MF'
        elif '_CC' in gene_set_str or gene_set_str.endswith('CC'):
            ontology = 'CC'

        direction = 'UNKNOWN'
        if 'KEGG' in gene_set_str:
            # 기존 서픽스 관례: KEGG_UP / KEGG_DOWN / KEGG_TOTAL / 단독 KEGG
            if '_UP' in gene_set_str or gene_set_str.endswith('UP'):
                direction = 'UP'
            elif '_DOWN' in gene_set_str or gene_set_str.endswith('DOWN'):
                direction = 'DOWN'
            elif '_TOTAL' in gene_set_str or gene_set_str.endswith('TOTAL'):
                direction = 'TOTAL'
            # plan §6.3 라벨 관례 (프리픽스): UP_KEGG / DOWN_KEGG / TOTAL_KEGG
            elif gene_set_str.startswith('UP'):
                direction = 'UP'
            elif gene_set_str.startswith('DOWN'):
                direction = 'DOWN'
            elif gene_set_str.startswith('TOTAL'):
                direction = 'TOTAL'
            else:
                direction = 'TOTAL'
        elif gene_set_str.startswith('UP'):
            direction = 'UP'
        elif gene_set_str.startswith('DOWN'):
            direction = 'DOWN'
        elif gene_set_str.startswith('TOTAL'):
            direction = 'TOTAL'

        return direction, ontology

    need_direction = StandardColumns.DIRECTION not in df.columns
    need_ontology = StandardColumns.ONTOLOGY not in df.columns

    if need_direction or need_ontology:
        logger.info("Extracting direction/ontology from Gene Set column")
        parsed = df[StandardColumns.GENE_SET].apply(parse_gene_set)
        if need_direction:
            df[StandardColumns.DIRECTION] = parsed.apply(lambda x: x[0])
        if need_ontology:
            df[StandardColumns.ONTOLOGY] = parsed.apply(lambda x: x[1])

    if StandardColumns.ONTOLOGY in df.columns and df[StandardColumns.ONTOLOGY].isna().any():
        logger.info(f"Found {df[StandardColumns.ONTOLOGY].isna().sum()} NaN values in "
                    f"Ontology column, filling from Gene Set")
        mask = df[StandardColumns.ONTOLOGY].isna()
        parsed = df.loc[mask, StandardColumns.GENE_SET].apply(parse_gene_set)
        df.loc[mask, StandardColumns.ONTOLOGY] = parsed.apply(lambda x: x[1])

    if StandardColumns.DIRECTION in df.columns and df[StandardColumns.DIRECTION].isna().any():
        logger.info(f"Found {df[StandardColumns.DIRECTION].isna().sum()} NaN values in "
                    f"Direction column, filling from Gene Set")
        mask = df[StandardColumns.DIRECTION].isna()
        parsed = df.loc[mask, StandardColumns.GENE_SET].apply(parse_gene_set)
        df.loc[mask, StandardColumns.DIRECTION] = parsed.apply(lambda x: x[0])

    return df


_GENE_SPLIT_RE = None  # 모듈 로드 시 컴파일 (lazy)


def _gene_split_re():
    """[;/,] 다구분자 정규식 (A5)."""
    import re
    return re.compile(r"[;/,]")


def parse_gene_symbols(df: pd.DataFrame, logger: Optional[logging.Logger] = None) -> pd.DataFrame:
    """
    Gene Symbols 컬럼 파싱 — [;/,] 다구분자 정규화 후 `/`-재조인, set 변환 (A5).

    gseapy `Genes`는 `;` 구분, GOATOOLS 기여 유전자는 리스트 → 컨버터에서
    re.split(r'[;/,]') 정규화 후 `/`로 재조인해 기존 `/`-split 기반
    `_parse_gene_symbols`/클러스터링 폴백과 호환되게 한다.
    """
    logger = _resolve_logger(logger)
    gene_col = StandardColumns.GENE_SYMBOLS if StandardColumns.GENE_SYMBOLS in df.columns else None
    if gene_col is None:
        for cand in ('geneID', 'Genes', 'genes', 'GeneID', 'Gene Symbols', 'GeneSymbols',
                     'core_enrichment', 'core enrichment', 'Core Enrichment'):
            if cand in df.columns:
                gene_col = cand
                logger.info(f"_gene_set fallback: using unmapped column '{cand}' as gene list")
                break

    split_re = _gene_split_re()

    def _normalize(gene_str) -> str:
        """[;/,] 분리 → strip → 빈 토큰 제거 → '/' 재조인."""
        if pd.isna(gene_str):
            return ""
        tokens = [t.strip() for t in split_re.split(str(gene_str))]
        return "/".join(t for t in tokens if t)

    if gene_col is not None:
        df = df.copy()
        df['_gene_set'] = df[gene_col].apply(
            lambda x: set(_normalize(x).split('/')) if _normalize(x) else set()
        )
    else:
        logger.warning(
            "No gene-list column found (Gene Symbols/Genes/geneID/core_enrichment/...) — "
            "_gene_set will be empty for all rows, so GO clustering will not merge overlapping terms."
        )
        df = df.copy()
        df['_gene_set'] = [set() for _ in range(len(df))]

    return df


# 표준 GO/KEGG 결과 컬럼 순서 (파이프라인 반입 ↔ in-app 분석 결과 정합용).
# 공통 표준 컬럼을 먼저, 부가 통계(추가 컬럼)와 내부 컬럼을 뒤에 둔다.
# 파이프라인 반입 출력(final_go_result.xlsx → 로더)의 상대 순서를 기준으로 한 공통 순서.
# R 어휘: ..., pvalue, fdr, qvalue, gene_symbols(geneID), gene_count(Count), [gene_set, fold], ..., ontology, direction
_STANDARD_GO_COLUMN_ORDER = [
    StandardColumns.TERM_ID,          # 'term_id'
    StandardColumns.DESCRIPTION,      # 'description'
    StandardColumns.GENE_RATIO,       # 'gene_ratio'
    StandardColumns.BG_RATIO,         # 'bg_ratio'
    StandardColumns.PVALUE_GO,        # 'pvalue'
    StandardColumns.FDR,              # 'fdr'
    StandardColumns.QVALUE,           # 'qvalue'
    StandardColumns.GENE_SYMBOLS,     # 'gene_symbols'
    StandardColumns.GENE_COUNT,       # 'gene_count'
    StandardColumns.GENE_SET,         # 'gene_set'
    StandardColumns.FOLD_ENRICHMENT,  # 'fold_enrichment'
    StandardColumns.ONTOLOGY,         # 'ontology'
    StandardColumns.DIRECTION,        # 'direction'
    # 부가 통계 (in-app prerank/ORA 보존 컬럼)
    'bg_count', 'odds_ratio', 'combined_score', 'nes', 'fwer_pvalue',
    # 파이프라인 잔여 어휘 (R clusterProfiler category 등)
    'subcategory', 'category',
    # 내부 컬럼
    '_gene_set', '_engine',
]


def reorder_standard_go_frame(df: pd.DataFrame) -> pd.DataFrame:
    """표준/부가/내부 컬럼 순서로 재정렬 (없는 컬럼은 생략, 미지 컬럼은 끝에 원순서 보존)."""
    present = list(df.columns)
    ordered = [c for c in _STANDARD_GO_COLUMN_ORDER if c in df.columns]
    tail = [c for c in present if c not in ordered]
    return df[ordered + tail]


def standardize_go_dataframe(df: pd.DataFrame, logger: Optional[logging.Logger] = None) -> pd.DataFrame:
    """
    GO/KEGG 결과 표준화 파이프라인 (단일 진실원천 — plan §8/G4/G5/G6).

    순서: 컬럼 표준화(+fold 파생) → direction/ontology 추출 → `_gene_set` 파싱.
    기존 GOKEGGLoader 메서드와 동일 동작이며 enrichment 엔진도 이 함수를 사용한다.
    """
    logger = _resolve_logger(logger)
    df = standardize_columns(df, logger)
    df = extract_direction_ontology(df, logger)
    if StandardColumns.DIRECTION not in df.columns:
        df[StandardColumns.DIRECTION] = 'UNKNOWN'
    if StandardColumns.ONTOLOGY not in df.columns:
        df[StandardColumns.ONTOLOGY] = 'UNKNOWN'
    df = parse_gene_symbols(df, logger)
    return reorder_standard_go_frame(df)


class GOKEGGLoader:
    """GO/KEGG 분석 결과 로딩 클래스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_from_excel(self, file_path: Path, name: Optional[str] = None) -> Dataset:
        """
        Excel 파일에서 GO/KEGG 결과 로딩 (여러 시트)
        
        Direction과 Ontology는 데이터 내부 컬럼에서 읽어옴.
        시트 이름은 gene_set으로만 사용.
        
        Args:
            file_path: Excel 파일 경로
            name: 데이터셋 이름 (기본값: 파일명)
            
        Returns:
            통합된 Dataset 객체
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            excel_file = pd.ExcelFile(file_path)
            all_dfs = []
            
            for sheet_name in excel_file.sheet_names:
                # Analysis_Info 같은 메타데이터 시트는 건너뛰기
                sheet_name_str = str(sheet_name).lower()
                if 'info' in sheet_name_str or 'metadata' in sheet_name_str or 'analysis' in sheet_name_str:
                    self.logger.info(f"Skipping metadata sheet: {sheet_name}")
                    continue
                
                # 시트 읽기 (NaN 처리 개선)
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # 완전히 빈 행 제거
                df = df.dropna(how='all')
                
                # 빈 DataFrame이면 건너뛰기
                if df.empty:
                    self.logger.warning(f"Empty sheet skipped: {sheet_name}")
                    continue
                
                # 첫 번째 행이 실제 헤더인지 확인 (NaN이 많으면 헤더가 밀렸을 가능성)
                # 첫 행의 NaN 비율이 50% 이상이면 헤더를 다시 설정
                if df.columns[0] == 'Unnamed: 0' or df.iloc[0].isna().sum() / len(df.columns) > 0.5:
                    # 첫 번째 행을 헤더로 사용
                    df.columns = df.iloc[0]
                    df = df[1:].reset_index(drop=True)
                    
                    # 컬럼명의 NaN 제거
                    df.columns = [str(col) if pd.notna(col) else f"Unnamed_{i}" 
                                 for i, col in enumerate(df.columns)]
                
                # 다시 빈 행 제거
                df = df.dropna(how='all')
                
                # NaN이 포함된 컬럼명 정리 (예: 'Description' 뒤에 NaN 컬럼이 있는 경우)
                # NaN 컬럼이 있으면 이전 컬럼과 병합
                cleaned_columns = []
                for i, col in enumerate(df.columns):
                    col_str = str(col)
                    if col_str.startswith('Unnamed:') or col_str == 'nan':
                        # NaN 컬럼은 건너뛰거나 삭제
                        continue
                    cleaned_columns.append(col)
                
                # NaN 컬럼 제거
                if len(cleaned_columns) < len(df.columns):
                    df = df[cleaned_columns]
                    self.logger.info(f"Removed {len(df.columns) - len(cleaned_columns)} unnamed columns from '{sheet_name}'")
                
                if df.empty:
                    continue
                
                # KEGG 시트는 구조적으로 Ontology 컬럼이 없다(clusterProfiler enrichKEGG()
                # 출력엔 그 필드 자체가 없음 — 'KEGG ID'/'KEGG Pathway' 컬럼으로만 구분됨).
                # 모듈 기반 워크플로우에서는 Gene Set 값이 'Cluster01' 같은 모듈 ID라 텍스트에서
                # ontology 를 유추할 수도 없다(예전 'KEGG_UP' 식 표기와 다름). 그대로 두면 BP/CC/MF
                # 시트와 concat 후 이 행들의 Ontology 가 NaN → 'UNKNOWN' 으로 빠진다. 시트 자체가
                # 구조적으로 KEGG 임이 명백하므로(Ontology 컬럼 부재 + KEGG ID/Pathway 컬럼 존재)
                # 여기서 직접 stamp 한다.
                raw_cols_lower = {str(c).strip().lower() for c in df.columns}
                has_ontology_col = any(c in raw_cols_lower for c in ('ontology', 'category'))
                is_kegg_sheet = (
                    any(c in raw_cols_lower for c in
                        ('kegg id', 'kegg.id', 'kegg pathway', 'kegg.pathway'))
                    or 'kegg' in sheet_name_str
                )
                if is_kegg_sheet and not has_ontology_col:
                    df[StandardColumns.ONTOLOGY] = 'KEGG'
                    self.logger.info(
                        f"Sheet '{sheet_name}': no Ontology column but structurally KEGG "
                        f"(KEGG ID/Pathway columns or 'KEGG' in sheet name) — stamping ontology='KEGG'")

                # Gene set 이름 추가 (시트 이름)
                # 원본 파일에 이미 Gene Set 컬럼이 있을 수 있으므로 확인 후 추가
                if 'Gene Set' not in df.columns:
                    df[StandardColumns.GENE_SET] = sheet_name

                # 각 시트를 병합 전에 표준화 (중요!)
                df = self._standardize_columns(df)
                
                all_dfs.append(df)
                self.logger.info(f"Loaded sheet '{sheet_name}': {len(df)} terms")
            
            if not all_dfs:
                raise ValueError("No valid sheets found in Excel file")
            
            # 모든 시트를 하나의 DataFrame으로 병합 (이제 컬럼명이 통일됨)
            merged_df = pd.concat(all_dfs, ignore_index=True)
            self.logger.info(f"Merged {len(all_dfs)} sheets into {len(merged_df)} terms")

            
            # Gene Set에서 Direction과 Ontology 추출
            merged_df = self._extract_direction_ontology(merged_df)
            
            # Direction과 Ontology가 없으면 UNKNOWN으로 설정
            if StandardColumns.DIRECTION not in merged_df.columns:
                merged_df[StandardColumns.DIRECTION] = 'UNKNOWN'
            if StandardColumns.ONTOLOGY not in merged_df.columns:
                merged_df[StandardColumns.ONTOLOGY] = 'UNKNOWN'
            
            # Gene Symbols를 set으로 파싱
            merged_df = self._parse_gene_symbols(merged_df)
            # 표준 헤더 순서 정합 (in-app 결과와 동일 순서 — 파이프라인 반입/분석 결과 일관)
            merged_df = reorder_standard_go_frame(merged_df)
            
            # Dataset 객체 생성
            dataset_name = name or file_path.stem
            dataset = Dataset(
                name=dataset_name,
                dataset_type=DatasetType.GO_ANALYSIS,
                dataframe=merged_df,
                original_columns={},
                metadata={'source_file': str(file_path)}
            )
            
            self.logger.info(f"Loaded GO/KEGG data from Excel: {len(merged_df)} terms from {len(all_dfs)} sheets")
            return dataset
            
        except Exception as e:
            self.logger.error(f"Failed to load GO/KEGG Excel file: {e}")
            raise
    
    def load_from_csv_files(self, file_paths: List[Path], name: str = "GO/KEGG Analysis") -> Dataset:
        """
        여러 CSV 파일에서 GO/KEGG 결과 로딩
        
        Direction과 Ontology는 데이터 내부 컬럼에서 읽어옴.
        
        Args:
            file_paths: CSV 파일 경로 리스트
            name: 데이터셋 이름
            
        Returns:
            통합된 Dataset 객체
        """
        all_dfs = []
        
        for file_path in file_paths:
            if not file_path.exists():
                self.logger.warning(f"File not found, skipping: {file_path}")
                continue
            
            try:
                # CSV 읽기 (NaN 처리 개선)
                df = pd.read_csv(file_path)
                
                # 완전히 빈 행 제거
                df = df.dropna(how='all')
                
                if df.empty:
                    self.logger.warning(f"Empty file skipped: {file_path}")
                    continue
                
                # 첫 번째 행이 실제 헤더인지 확인
                if df.columns[0] == 'Unnamed: 0' or df.iloc[0].isna().sum() / len(df.columns) > 0.5:
                    df.columns = df.iloc[0]
                    df = df[1:].reset_index(drop=True)
                    
                    # 컬럼명의 NaN 제거
                    df.columns = [str(col) if pd.notna(col) else f"Unnamed_{i}" 
                                 for i, col in enumerate(df.columns)]
                
                # 다시 빈 행 제거
                df = df.dropna(how='all')
                
                # NaN이 포함된 컬럼명 정리
                cleaned_columns = []
                for i, col in enumerate(df.columns):
                    col_str = str(col)
                    if col_str.startswith('Unnamed:') or col_str == 'nan':
                        continue
                    cleaned_columns.append(col)
                
                # NaN 컬럼 제거
                if len(cleaned_columns) < len(df.columns):
                    df = df[cleaned_columns]
                
                if df.empty:
                    continue
                
                # Gene set 이름 추가 (파일 이름)
                df[StandardColumns.GENE_SET] = file_path.stem
                
                all_dfs.append(df)
                self.logger.info(f"Loaded CSV '{file_path.name}': {len(df)} terms, {len(df.columns)} columns")
                
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                continue
        
        if not all_dfs:
            raise ValueError("No valid CSV files loaded")
        
        # 모든 파일을 하나의 DataFrame으로 병합
        merged_df = pd.concat(all_dfs, ignore_index=True)
        
        # 컬럼명 표준화
        merged_df = self._standardize_columns(merged_df)
        
        # Direction과 Ontology가 없으면 UNKNOWN으로 설정
        if StandardColumns.DIRECTION not in merged_df.columns:
            merged_df[StandardColumns.DIRECTION] = 'UNKNOWN'
        if StandardColumns.ONTOLOGY not in merged_df.columns:
            merged_df[StandardColumns.ONTOLOGY] = 'UNKNOWN'
        
        # Gene Symbols를 set으로 파싱
        merged_df = self._parse_gene_symbols(merged_df)
        merged_df = reorder_standard_go_frame(merged_df)
        
        # Dataset 객체 생성
        dataset = Dataset(
            name=name,
            dataset_type=DatasetType.GO_ANALYSIS,
            dataframe=merged_df,
            original_columns={},
            metadata={'source_files': [str(p) for p in file_paths]}
        )
        
        self.logger.info(f"Loaded GO/KEGG data from {len(file_paths)} CSV files: {len(merged_df)} terms")
        return dataset
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        return standardize_columns(df, self.logger)
    def _compute_fold_enrichment(self, df: pd.DataFrame) -> pd.DataFrame:
        return compute_fold_enrichment(df, self.logger)
    def _extract_direction_ontology(self, df: pd.DataFrame) -> pd.DataFrame:
        return extract_direction_ontology(df, self.logger)
    def _parse_gene_symbols(self, df: pd.DataFrame) -> pd.DataFrame:
        return parse_gene_symbols(df, self.logger)
