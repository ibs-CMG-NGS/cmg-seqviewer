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
        """
        컬럼명을 표준 이름으로 변환
        
        GO ID, GO Term -> term_id, description
        KEGG ID, KEGG Pathway -> term_id, description
        
        Args:
            df: 원본 DataFrame
            
        Returns:
            표준화된 DataFrame
        """
        df = df.copy()
        
        # 컬럼명 매핑 패턴
        column_mapping = {
            # Term ID
            'GO ID': StandardColumns.TERM_ID,
            'KEGG ID': StandardColumns.TERM_ID,
            'GO id': StandardColumns.TERM_ID,
            'KEGG id': StandardColumns.TERM_ID,
            'Term ID': StandardColumns.TERM_ID,
            'term_id': StandardColumns.TERM_ID,
            'ID': StandardColumns.TERM_ID,
            
            # Description
            'GO Term': StandardColumns.DESCRIPTION,
            'KEGG Pathway': StandardColumns.DESCRIPTION,
            'GO term': StandardColumns.DESCRIPTION,
            'KEGG pathway': StandardColumns.DESCRIPTION,
            'Description': StandardColumns.DESCRIPTION,
            'Term': StandardColumns.DESCRIPTION,
            
            # Gene Symbols
            'Gene Symbols': StandardColumns.GENE_SYMBOLS,
            'Gene symbols': StandardColumns.GENE_SYMBOLS,
            'Genes': StandardColumns.GENE_SYMBOLS,
            'Gene ID': StandardColumns.GENE_SYMBOLS,
            'geneID': StandardColumns.GENE_SYMBOLS,
            
            # Statistics
            'P-value': StandardColumns.PVALUE_GO,
            'P-Value': StandardColumns.PVALUE_GO,
            'pvalue': StandardColumns.PVALUE_GO,
            'Adjusted P-value': StandardColumns.FDR,
            'Adjusted P-Value': StandardColumns.FDR,
            'padj': StandardColumns.FDR,
            'FDR': StandardColumns.FDR,
            'p.adjust': StandardColumns.FDR,
            'Q-value': StandardColumns.QVALUE,
            'Q-Value': StandardColumns.QVALUE,
            'qvalue': StandardColumns.QVALUE,
            
            # Ratios
            'Gene Ratio': StandardColumns.GENE_RATIO,
            'Gene ratio': StandardColumns.GENE_RATIO,
            'GeneRatio': StandardColumns.GENE_RATIO,
            'Background Ratio': StandardColumns.BG_RATIO,
            'Background ratio': StandardColumns.BG_RATIO,
            'BgRatio': StandardColumns.BG_RATIO,
            
            # Count
            'Gene Count': StandardColumns.GENE_COUNT,
            'Gene count': StandardColumns.GENE_COUNT,
            'Count': StandardColumns.GENE_COUNT,
            
            # Direction and Ontology (데이터에 포함되어 있을 경우)
            'Direction': StandardColumns.DIRECTION,
            'direction': StandardColumns.DIRECTION,
            'Regulation': StandardColumns.DIRECTION,
            'regulation': StandardColumns.DIRECTION,
            
            'Ontology': StandardColumns.ONTOLOGY,
            'ontology': StandardColumns.ONTOLOGY,
            'Category': StandardColumns.ONTOLOGY,
            'category': StandardColumns.ONTOLOGY,
            'ONTOLOGY': StandardColumns.ONTOLOGY,
            
            # Gene Set (추가된 시트 이름 컬럼)
            'Gene Set': StandardColumns.GENE_SET,
            'gene set': StandardColumns.GENE_SET,
            'GeneSet': StandardColumns.GENE_SET,
            'geneset': StandardColumns.GENE_SET,
        }
        
        # 컬럼명 변경
        rename_dict = {}
        for col in df.columns:
            if col in column_mapping:
                rename_dict[col] = column_mapping[col]
        
        if rename_dict:
            df.rename(columns=rename_dict, inplace=True)
            self.logger.info(f"Standardized columns: {rename_dict}")
        
        # 중복 컬럼 제거 (같은 표준 컬럼명으로 여러 원본 컬럼이 매핑되는 경우)
        # 예: 'GO ID'와 'KEGG ID' 둘 다 'term_id'로 매핑되면 중복 발생
        if df.columns.duplicated().any():
            duplicates_count = df.columns.duplicated().sum()
            duplicated_names = df.columns[df.columns.duplicated()].unique().tolist()
            
            # 중복된 컬럼 중 첫 번째만 유지 (첫 번째가 가장 중요한 데이터일 가능성이 높음)
            df = df.loc[:, ~df.columns.duplicated(keep='first')]
            
            self.logger.warning(f"Removed {duplicates_count} duplicate columns: {duplicated_names}")
            self.logger.info(f"Remaining columns after deduplication: {list(df.columns)}")
        
        return df
    
    def _extract_direction_ontology(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gene Set 컬럼에서 Direction과 Ontology 정보 추출
        
        Gene Set 형식: "UP_BP", "DOWN_MF", "UP_CC", "KEGG" 등
        - UP/DOWN: Direction
        - BP/MF/CC: Ontology (Biological Process, Molecular Function, Cellular Component)
        
        Args:
            df: DataFrame
            
        Returns:
            direction과 ontology 컬럼이 추가된 DataFrame
        """
        if StandardColumns.GENE_SET not in df.columns:
            self.logger.warning(f"Gene Set column not found, skipping direction/ontology extraction")
            return df
        
        def parse_gene_set(gene_set_value):
            """Gene Set 값에서 direction과 ontology 파싱"""
            if pd.isna(gene_set_value):
                return 'UNKNOWN', 'UNKNOWN'
            
            gene_set_str = str(gene_set_value).strip().upper()
            
            # Ontology 추출 (Direction보다 먼저 체크)
            ontology = 'UNKNOWN'
            if 'KEGG' in gene_set_str:
                ontology = 'KEGG'
            elif '_BP' in gene_set_str or gene_set_str.endswith('BP'):
                ontology = 'BP'
            elif '_MF' in gene_set_str or gene_set_str.endswith('MF'):
                ontology = 'MF'
            elif '_CC' in gene_set_str or gene_set_str.endswith('CC'):
                ontology = 'CC'
            
            # Direction 추출
            direction = 'UNKNOWN'
            if 'KEGG' in gene_set_str:
                # KEGG는 UP/DOWN 구분 (KEGG_UP, KEGG_DOWN, KEGG_TOTAL)
                if '_UP' in gene_set_str or gene_set_str.endswith('UP'):
                    direction = 'UP'
                elif '_DOWN' in gene_set_str or gene_set_str.endswith('DOWN'):
                    direction = 'DOWN'
                elif '_TOTAL' in gene_set_str or gene_set_str.endswith('TOTAL'):
                    direction = 'TOTAL'
                else:
                    direction = 'TOTAL'  # KEGG만 있으면 TOTAL
            elif gene_set_str.startswith('UP'):
                direction = 'UP'
            elif gene_set_str.startswith('DOWN'):
                direction = 'DOWN'
            elif gene_set_str.startswith('TOTAL'):
                direction = 'TOTAL'
            
            return direction, ontology
        
        # Direction과 Ontology 추출 (각각 독립적으로 체크)
        need_direction = StandardColumns.DIRECTION not in df.columns
        need_ontology = StandardColumns.ONTOLOGY not in df.columns
        
        # Ontology 컬럼이 있어도 KEGG 행에 NaN이 있을 수 있으므로 재추출
        if need_direction or need_ontology:
            self.logger.info(f"Extracting direction/ontology from Gene Set column")
            parsed = df[StandardColumns.GENE_SET].apply(parse_gene_set)
            
            if need_direction:
                df[StandardColumns.DIRECTION] = parsed.apply(lambda x: x[0])
            
            if need_ontology:
                df[StandardColumns.ONTOLOGY] = parsed.apply(lambda x: x[1])
        
        # Ontology 컬럼이 있더라도 NaN 값을 Gene Set에서 채우기
        if StandardColumns.ONTOLOGY in df.columns:
            ontology_col = df[StandardColumns.ONTOLOGY]
            if ontology_col.isna().any():
                self.logger.info(f"Found {ontology_col.isna().sum()} NaN values in Ontology column, filling from Gene Set")
                # NaN인 행만 재추출
                mask = ontology_col.isna()
                parsed = df.loc[mask, StandardColumns.GENE_SET].apply(parse_gene_set)
                df.loc[mask, StandardColumns.ONTOLOGY] = parsed.apply(lambda x: x[1])
        
        # Direction도 동일하게 처리
        if StandardColumns.DIRECTION in df.columns:
            direction_col = df[StandardColumns.DIRECTION]
            if direction_col.isna().any():
                self.logger.info(f"Found {direction_col.isna().sum()} NaN values in Direction column, filling from Gene Set")
                mask = direction_col.isna()
                parsed = df.loc[mask, StandardColumns.GENE_SET].apply(parse_gene_set)
                df.loc[mask, StandardColumns.DIRECTION] = parsed.apply(lambda x: x[0])
        
        return df
    
    def _parse_gene_symbols(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gene Symbols 컬럼 파싱 (/ 구분자로 분리하여 set으로 변환)
        
        Args:
            df: DataFrame
            
        Returns:
            _gene_set 컬럼이 추가된 DataFrame
        """
        if StandardColumns.GENE_SYMBOLS in df.columns:
            df['_gene_set'] = df[StandardColumns.GENE_SYMBOLS].apply(
                lambda x: set(str(x).split('/')) if pd.notna(x) else set()
            )
        else:
            df['_gene_set'] = [set() for _ in range(len(df))]
        
        return df
