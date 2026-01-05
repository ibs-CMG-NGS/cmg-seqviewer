"""
Data Loader for RNA-Seq Analysis

Excel 파일로부터 RNA-Seq 데이터를 로드하고 파싱합니다.
"""

import pandas as pd
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Callable
import logging
from models.data_models import Dataset, DatasetType
from models.standard_columns import StandardColumns


class DataLoader:
    """
    RNA-Seq 데이터 로더
    
    Excel 파일을 읽고, 컬럼을 매핑하여 Dataset 객체를 생성합니다.
    """
    
    def __init__(self, mapping_config_path: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        
        # 사용자 정의 매핑 설정 파일
        if mapping_config_path is None:
            mapping_config_path = Path.home() / '.rna_seq_analyzer' / 'column_mappings.json'
        self.mapping_config_path = mapping_config_path
        self.custom_mappings: Dict[str, Dict[str, str]] = self._load_custom_mappings()
        
        # 표준 컬럼명 패턴 정의
        self.de_column_patterns = {
            'gene_id': ['gene_id', 'geneid', 'id', 'ensembl', 'ensembl_id', 'entrez', 'entrez_id'],
            'symbol': ['symbol', 'gene_symbol', 'gene', 'gene_name'],
            'log2fc': ['log2fc', 'log2foldchange', 'logfc', 'fold_change', 'fc'],
            'pvalue': ['pvalue', 'p.value', 'p_value', 'pval'],
            'adj_pvalue': ['padj', 'adj.p.value', 'adj_p_value', 'fdr', 'q_value', 'qvalue'],
            'base_mean': ['basemean', 'base_mean', 'mean', 'avg_expression'],
            'lfcse': ['lfcse', 'lfc_se', 'lfcstderr', 'log2fc_se'],
            'stat': ['stat', 'statistic', 'test_stat'],
        }
        
        self.go_column_patterns = {
            'term_id': ['term_id', 'go_id', 'kegg_id', 'pathway_id', 'id', 'go id', 'kegg id'],
            'description': ['description', 'term', 'go_term', 'go term', 'kegg_pathway', 'kegg pathway', 'pathway', 'term_name'],
            'gene_count': ['gene_count', 'gene count', 'count', 'size', 'n_genes'],
            'pvalue': ['pvalue', 'p.value', 'p_value', 'p-value', 'pval'],
            'fdr': ['fdr', 'padj', 'adj.p.value', 'adjusted p-value', 'adjusted_p-value'],
            'qvalue': ['qvalue', 'q-value', 'q_value'],
            'gene_symbols': ['gene_symbols', 'gene symbols', 'genes', 'gene_list', 'geneid', 'gene id'],
            'gene_ratio': ['gene_ratio', 'gene ratio', 'generatio'],
            'bg_ratio': ['bg_ratio', 'background_ratio', 'background ratio', 'bgratio'],
            'gene_set': ['gene_set', 'gene set', 'geneset', 'set'],
            'ontology': ['ontology', 'category', 'type'],
            'direction': ['direction', 'regulation', 'change'],
        }
    
    def _load_custom_mappings(self) -> Dict[str, Dict[str, str]]:
        """사용자 정의 매핑 로드"""
        if not self.mapping_config_path.exists():
            return {}
        
        try:
            with open(self.mapping_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load custom mappings: {e}")
            return {}
    
    def save_custom_mapping(self, dataset_type: DatasetType, mapping: Dict[str, str]):
        """
        사용자 정의 매핑 저장
        
        Args:
            dataset_type: 데이터셋 타입
            mapping: {표준 컬럼: 원본 컬럼} 매핑
        """
        key = dataset_type.value
        self.custom_mappings[key] = mapping
        
        # 파일로 저장
        try:
            self.mapping_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.mapping_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.custom_mappings, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved custom mapping for {dataset_type.value}")
        except Exception as e:
            self.logger.error(f"Failed to save custom mapping: {e}")
    
    def get_custom_mapping(self, dataset_type: DatasetType) -> Optional[Dict[str, str]]:
        """저장된 사용자 정의 매핑 가져오기"""
        return self.custom_mappings.get(dataset_type.value)
    
    def load_from_excel(self, file_path: Path, dataset_name: Optional[str] = None,
                       dataset_type: Optional[DatasetType] = None,
                       sheet_name: Optional[str] = None,
                       column_mapper_callback: Optional[Callable] = None) -> Dataset:
        """
        Excel 파일로부터 데이터셋 로드
        
        Args:
            file_path: Excel 파일 경로
            dataset_name: 데이터셋 이름 (None이면 파일명 사용)
            dataset_type: 데이터셋 타입 (None이면 자동 감지)
            sheet_name: 시트명 (None이면 첫 번째 시트)
            column_mapper_callback: 컬럼 매핑 UI 콜백 함수
                                   (df, dataset_type, auto_mapping) -> Dict[str, str] 반환
            
        Returns:
            로드된 Dataset 객체
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            ValueError: 데이터 형식이 올바르지 않을 때
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.logger.debug(f"Loading data from: {file_path}")
        
        # 데이터셋 이름 설정
        if dataset_name is None:
            dataset_name = file_path.stem
        
        try:
            # Excel 파일 읽기
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)
            
            self.logger.debug(f"Loaded {len(df)} rows, {len(df.columns)} columns")
            
            # 데이터셋 타입 자동 감지
            if dataset_type is None:
                dataset_type = self._detect_dataset_type(df)
                self.logger.debug(f"Detected dataset type: {dataset_type.value}")  # debug로 변경
            
            # 컬럼 매핑 (자동 + 사용자 정의)
            auto_mapping = self._map_columns(df, dataset_type)
            self.logger.debug(f"Auto-detected column mapping: {auto_mapping}")  # debug로 변경
            
            # 저장된 사용자 정의 매핑 확인
            custom_mapping = self.get_custom_mapping(dataset_type)
            if custom_mapping:
                self.logger.debug(f"Found custom mapping: {custom_mapping}")  # debug로 변경
                # 사용자 정의 매핑을 {원본: 표준} 형식으로 변환
                # custom_mapping은 {표준: 원본} 형식으로 저장되어 있음
                final_mapping = {v: k for k, v in custom_mapping.items()}
            else:
                # 자동 매핑 사용 (이미 {원본: 표준} 형식)
                final_mapping = auto_mapping
            
            # 필수 컬럼 누락 시 사용자에게 매핑 요청
            # _has_required_columns는 {표준: 원본} 형식을 기대
            check_mapping = {v: k for k, v in final_mapping.items()}
            if not self._has_required_columns(check_mapping, dataset_type):
                self.logger.warning("Missing required columns. User mapping required.")
                
                if column_mapper_callback:
                    # GUI 콜백을 통해 사용자에게 매핑 요청
                    user_mapping = column_mapper_callback(df, dataset_type, auto_mapping)
                    if user_mapping:
                        # user_mapping은 {표준: 원본} 형식
                        final_mapping = {v: k for k, v in user_mapping.items()}
                        self.logger.info(f"User-provided mapping: {user_mapping}")
                    else:
                        raise ValueError("Column mapping cancelled by user")
                else:
                    raise ValueError(f"Missing required columns for {dataset_type.value}")
            
            # ✨ 컬럼명 표준화 (핵심 변경!)
            df, original_columns = self._standardize_columns(df, final_mapping, dataset_type)
            
            # 낮은 발현량 유전자 제거 (메모리 최적화)
            # 이제 표준 컬럼명 사용
            original_rows = len(df)
            df = self._remove_zero_abundance_genes(df, {}, dataset_type)  # 빈 dict 전달 (표준 컬럼명 사용)
            removed_rows = original_rows - len(df)
            if removed_rows > 0:
                self.logger.debug(f"Filtered out {removed_rows} low-expression genes (baseMean threshold applied) - {removed_rows/original_rows*100:.1f}% removed")
            
            dataset = Dataset(
                name=dataset_name,
                dataset_type=dataset_type,
                file_path=file_path,
                dataframe=df,
                original_columns=original_columns,  # 원본 컬럼명 참고용 저장
                metadata={
                    'sheet_name': sheet_name,
                    'loaded_at': pd.Timestamp.now().isoformat(),
                    'zero_genes_removed': removed_rows
                }
            )
            
            # 유효성 검사
            if not dataset.is_valid:
                self.logger.warning(f"Dataset validation failed. Missing required columns.")
            
            return dataset
            
        except Exception as e:
            self.logger.error(f"Failed to load data: {e}", exc_info=True)
            raise
    
    def _detect_dataset_type(self, df: pd.DataFrame) -> DatasetType:
        """
        데이터프레임으로부터 데이터셋 타입 자동 감지
        
        Args:
            df: 데이터프레임
            
        Returns:
            감지된 DatasetType
        """
        columns_lower = [col.lower().replace(' ', '_') for col in df.columns]
        
        # Differential Expression 패턴 확인
        de_score = 0
        for standard_col, patterns in self.de_column_patterns.items():
            if any(pattern in col for col in columns_lower for pattern in patterns):
                de_score += 1
        
        # GO Analysis 패턴 확인
        go_score = 0
        for standard_col, patterns in self.go_column_patterns.items():
            if any(pattern in col for col in columns_lower for pattern in patterns):
                go_score += 1
        
        # 점수가 높은 타입 선택
        if de_score >= 3:
            return DatasetType.DIFFERENTIAL_EXPRESSION
        elif go_score >= 3:
            return DatasetType.GO_ANALYSIS
        else:
            return DatasetType.UNKNOWN
    
    def _map_columns(self, df: pd.DataFrame, dataset_type: DatasetType) -> Dict[str, str]:
        """
        데이터프레임 컬럼을 표준 컬럼명으로 매핑
        
        Args:
            df: 데이터프레임
            dataset_type: 데이터셋 타입
            
        Returns:
            컬럼 매핑 딕셔너리 {원본 컬럼명: 표준 컬럼명}
        """
        mapping = {}
        columns_lower = {col: col.lower().replace(' ', '_') for col in df.columns}
        
        # 타입에 따른 패턴 선택
        if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            patterns = self.de_column_patterns
        elif dataset_type == DatasetType.GO_ANALYSIS:
            patterns = self.go_column_patterns
        else:
            return mapping
        
        # 각 표준 컬럼에 대해 매칭되는 실제 컬럼 찾기
        for standard_col, pattern_list in patterns.items():
            matched = False
            for original_col, lower_col in columns_lower.items():
                if any(pattern in lower_col for pattern in pattern_list):
                    mapping[original_col] = standard_col
                    matched = True
                    break
            
            if not matched:
                self.logger.debug(f"No match found for standard column: {standard_col}")
        
        return mapping
    
    def _standardize_columns(self, df: pd.DataFrame, 
                            mapping: Dict[str, str],
                            dataset_type: DatasetType) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        DataFrame의 컬럼명을 표준 이름으로 변경
        
        Args:
            df: 원본 DataFrame
            mapping: {원본 컬럼: 표준 컬럼} 매핑
            dataset_type: 데이터셋 타입
            
        Returns:
            (표준화된 DataFrame, {표준 컬럼: 원본 컬럼} 딕셔너리)
        """
        df = df.copy()
        
        # Unnamed: 0 처리 - gene_id가 없으면 Unnamed: 0을 gene_id로 사용
        unnamed_cols = [col for col in df.columns if col.startswith('Unnamed:')]
        if unnamed_cols and 'gene_id' not in mapping.values():
            # 첫 번째 Unnamed 컬럼을 gene_id로 사용
            unnamed_col = unnamed_cols[0]
            mapping[unnamed_col] = 'gene_id'
            self.logger.info(f"Using '{unnamed_col}' as gene_id")
        
        # 원본 컬럼명 저장 (참고용)
        original_columns = {std: orig for orig, std in mapping.items()}
        
        # 컬럼 리네임
        df.rename(columns=mapping, inplace=True)
        
        # 모든 문자열 컬럼의 앞뒤 공백 제거 (description NaN 문제 해결)
        for col in df.columns:
            if df[col].dtype == 'object':  # 문자열 컬럼
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
        
        # gene_id와 symbol을 문자열로 변환 (ENTREZ ID 등이 정수형일 수 있음)
        if StandardColumns.GENE_ID in df.columns:
            df[StandardColumns.GENE_ID] = df[StandardColumns.GENE_ID].astype(str)
        
        if StandardColumns.SYMBOL in df.columns:
            df[StandardColumns.SYMBOL] = df[StandardColumns.SYMBOL].astype(str)
        
        # 필수 컬럼 체크
        if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            required = StandardColumns.get_de_required()
        elif dataset_type == DatasetType.GO_ANALYSIS:
            required = StandardColumns.get_go_required()
        else:
            required = []
        
        missing = [col for col in required if col not in df.columns]
        if missing:
            available = list(df.columns)
            raise ValueError(
                f"Missing required columns after standardization: {missing}\n"
                f"Available columns: {available}\n"
                f"Mapping used: {mapping}"
            )
        
        self.logger.info(f"Standardized columns: {list(mapping.values())}")
        self.logger.info(f"Original column names preserved: {original_columns}")
        
        return df, original_columns
    
    def _has_required_columns(self, mapping: Dict[str, str], dataset_type: DatasetType) -> bool:
        """
        필수 컬럼이 모두 매핑되었는지 확인
        
        Args:
            mapping: {표준 컬럼: 원본 컬럼} 매핑
            dataset_type: 데이터셋 타입
            
        Returns:
            필수 컬럼 모두 매핑되었으면 True
        """
        if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            required = ['gene_id', 'log2fc', 'adj_pvalue']
        elif dataset_type == DatasetType.GO_ANALYSIS:
            required = ['description', 'gene_count', 'fdr']
        else:
            return True
        
        return all(std_col in mapping for std_col in required)
    
    def load_gene_list_from_file(self, file_path: Path) -> List[str]:
        """
        파일로부터 유전자 리스트 로드
        
        Args:
            file_path: 텍스트 파일 경로 (한 줄에 하나의 유전자 ID)
            
        Returns:
            유전자 ID 리스트
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                genes = [line.strip() for line in f if line.strip()]
            
            self.logger.info(f"Loaded {len(genes)} genes from {file_path}")
            return genes
            
        except Exception as e:
            self.logger.error(f"Failed to load gene list: {e}", exc_info=True)
            raise
    
    def parse_gene_list_from_text(self, text: str) -> List[str]:
        """
        텍스트로부터 유전자 리스트 파싱
        
        Args:
            text: 유전자 리스트 텍스트 (줄바꿈, 쉼표, 탭 등으로 구분)
            
        Returns:
            유전자 ID 리스트
        """
        # 여러 구분자로 분리
        separators = ['\n', '\r\n', '\t', ',', ';', ' ']
        genes = [text]
        
        for sep in separators:
            new_genes = []
            for gene in genes:
                new_genes.extend(gene.split(sep))
            genes = new_genes
        
        # 공백 제거 및 중복 제거
        genes = list(set(gene.strip() for gene in genes if gene.strip()))
        
        self.logger.info(f"Parsed {len(genes)} unique genes from text")
        return genes
    
    def _remove_zero_abundance_genes(self, df: pd.DataFrame, column_mapping: Dict[str, str], 
                                     dataset_type: DatasetType) -> pd.DataFrame:
        """
        낮은 발현량 유전자 제거 (baseMean 기반)
        
        Args:
            df: 데이터프레임 (표준화된 컬럼명 사용)
            column_mapping: 컬럼 매핑 (더 이상 사용하지 않음, 하위 호환성용)
            dataset_type: 데이터셋 타입
            
        Returns:
            필터링된 데이터프레임
        """
        if dataset_type != DatasetType.DIFFERENTIAL_EXPRESSION:
            return df  # DE 데이터셋이 아니면 필터링하지 않음
        
        # 표준 컬럼명 사용
        basemean_col = StandardColumns.BASE_MEAN
        
        # baseMean이 없으면 샘플 카운트로 계산
        if basemean_col not in df.columns:
            # 표준 DE 컬럼 목록
            standard_de_cols = set(StandardColumns.get_de_all())
            
            # 샘플 카운트 컬럼 찾기 (표준 컬럼이 아닌 숫자형 컬럼)
            sample_cols = []
            for col in df.columns:
                if col not in standard_de_cols and pd.api.types.is_numeric_dtype(df[col]):
                    sample_cols.append(col)
            
            if not sample_cols:
                return df  # 샘플 컬럼이 없으면 필터링하지 않음
            
            # baseMean 계산
            df['_temp_baseMean'] = df[sample_cols].mean(axis=1)
            basemean_col = '_temp_baseMean'
        
        # 동적 threshold 계산
        # 표준 컬럼 목록
        standard_de_cols = set(StandardColumns.get_de_all())
        
        # 샘플 수 계산
        sample_count = len([c for c in df.columns 
                           if c not in standard_de_cols 
                           and pd.api.types.is_numeric_dtype(df[c])])
        threshold = max(5, sample_count)
        
        # baseMean이 threshold 이상인 유전자만 유지
        filtered_df = df[df[basemean_col] >= threshold].copy()
        
        # 임시 컬럼 제거
        if '_temp_baseMean' in filtered_df.columns:
            filtered_df = filtered_df.drop(columns=['_temp_baseMean'])
        
        return filtered_df
    
    def get_available_sheets(self, file_path: Path) -> List[str]:
        """
        Excel 파일의 시트 목록 반환
        
        Args:
            file_path: Excel 파일 경로
            
        Returns:
            시트 이름 리스트
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            excel_file = pd.ExcelFile(file_path)
            return excel_file.sheet_names
        except Exception as e:
            self.logger.error(f"Failed to read Excel sheets: {e}")
            return []
