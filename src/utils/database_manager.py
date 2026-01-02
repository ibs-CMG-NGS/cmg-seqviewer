"""
Database Manager for Pre-loaded Datasets

자주 사용하는 데이터셋을 Parquet 포맷으로 변환하여 저장하고,
메타데이터와 함께 관리하는 시스템입니다.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import pandas as pd

from models.data_models import Dataset, PreloadedDatasetMetadata, DatasetType


class DatabaseManager:
    """Pre-loaded 데이터셋 데이터베이스 관리자"""
    
    def __init__(self, database_dir: Path = None):
        """
        Args:
            database_dir: 데이터베이스 디렉토리 경로 (기본: ./database)
        """
        self.logger = logging.getLogger(__name__)
        
        # 데이터베이스 디렉토리 설정
        if database_dir is None:
            # PyInstaller로 패키징된 경우와 일반 실행 구분
            import sys
            if getattr(sys, 'frozen', False):
                # PyInstaller로 실행된 경우
                base_path = Path(sys._MEIPASS)
            else:
                # 일반 Python 실행
                base_path = Path(__file__).parent.parent.parent
            database_dir = base_path / "database"
        self.database_dir = Path(database_dir)
        self.datasets_dir = self.database_dir / "datasets"
        self.metadata_file = self.database_dir / "metadata.json"
        
        # 디렉토리 생성
        self._ensure_directories()
        
        # 메타데이터 로드
        self.metadata_list: List[PreloadedDatasetMetadata] = []
        self._load_metadata()
    
    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        self.database_dir.mkdir(parents=True, exist_ok=True)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self):
        """메타데이터 파일 로드"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.metadata_list = [
                        PreloadedDatasetMetadata.from_dict(item) 
                        for item in data.get('datasets', [])
                    ]
                
                # 절대 경로를 파일명만으로 수정 (호환성)
                needs_update = False
                for metadata in self.metadata_list:
                    file_path = Path(metadata.file_path)
                    if file_path.is_absolute():
                        # 절대 경로면 파일명만 추출
                        metadata.file_path = file_path.name
                        needs_update = True
                        self.logger.info(f"Converted absolute path to filename: {metadata.file_path}")
                
                # 수정사항이 있으면 저장
                if needs_update:
                    self._save_metadata()
                
                self.logger.info(f"Loaded {len(self.metadata_list)} dataset metadata from database")
            except Exception as e:
                self.logger.error(f"Failed to load metadata: {e}")
                self.metadata_list = []
        else:
            self.metadata_list = []
            self._save_metadata()
    
    def _save_metadata(self):
        """메타데이터 파일 저장"""
        try:
            data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'datasets': [meta.to_dict() for meta in self.metadata_list]
            }
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(self.metadata_list)} dataset metadata")
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            raise
    
    def import_dataset(self, dataset: Dataset, metadata: PreloadedDatasetMetadata) -> bool:
        """
        데이터셋을 데이터베이스에 임포트
        
        Args:
            dataset: Dataset 객체
            metadata: PreloadedDatasetMetadata 객체
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 고유 ID 생성 (없으면)
            if not metadata.dataset_id:
                metadata.dataset_id = str(uuid.uuid4())
            
            # 파일 경로 설정 (상대 경로로 저장 - 파일명만)
            filename = f"{metadata.dataset_id}.parquet"
            file_path = self.datasets_dir / filename
            metadata.file_path = filename  # 파일명만 저장 (상대 경로)
            
            # 임포트 날짜 설정
            metadata.import_date = datetime.now().isoformat()
            
            # 데이터 통계 자동 계산
            metadata.row_count = len(dataset.dataframe)
            metadata.gene_count = len(dataset.get_genes())
            
            # 유의미한 유전자 수 계산 (padj < 0.05)
            if dataset.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
                padj_col = dataset._get_column_name('adj_pvalue')
                if padj_col:
                    try:
                        significant = dataset.dataframe[padj_col].astype(float) < 0.05
                        metadata.significant_genes = significant.sum()
                    except:
                        metadata.significant_genes = 0
            
            # Parquet 형식으로 저장
            # GO 데이터의 경우 _gene_set 컬럼 (set 타입) 처리
            if dataset.dataframe is None:
                raise ValueError("Dataset has no dataframe to save")
            
            df_to_save = dataset.dataframe.copy()
            if '_gene_set' in df_to_save.columns:
                # set을 문자열로 변환 (/ 구분자 사용)
                def convert_set_to_str(x):
                    if isinstance(x, set):
                        return '/'.join(sorted(x)) if x else ''
                    elif pd.isna(x):
                        return ''
                    else:
                        return str(x)
                
                df_to_save['_gene_set'] = df_to_save['_gene_set'].apply(convert_set_to_str)
            
            df_to_save.to_parquet(file_path, engine='pyarrow', compression='snappy')
            
            # 메타데이터 추가 및 저장
            # 기존 데이터셋 ID가 있으면 업데이트, 없으면 추가
            existing_idx = None
            for idx, meta in enumerate(self.metadata_list):
                if meta.dataset_id == metadata.dataset_id:
                    existing_idx = idx
                    break
            
            if existing_idx is not None:
                self.metadata_list[existing_idx] = metadata
                self.logger.info(f"Updated dataset: {metadata.alias}")
            else:
                self.metadata_list.append(metadata)
                self.logger.info(f"Imported new dataset: {metadata.alias}")
            
            self._save_metadata()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import dataset: {e}")
            return False
    
    def load_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """
        데이터베이스에서 데이터셋 로드
        
        Args:
            dataset_id: 데이터셋 ID
            
        Returns:
            Optional[Dataset]: Dataset 객체 또는 None
        """
        # 메타데이터 찾기
        metadata = self.get_metadata(dataset_id)
        if metadata is None:
            self.logger.error(f"Dataset not found: {dataset_id}")
            return None
        
        try:
            # Parquet 파일 경로 처리
            # metadata에 절대 경로가 저장되어 있을 수 있으므로 파일명만 추출
            file_path = Path(metadata.file_path)
            if not file_path.is_absolute():
                # 상대 경로면 datasets 폴더 기준으로 해석
                file_path = self.datasets_dir / file_path.name
            else:
                # 절대 경로면 파일명만 추출하여 현재 datasets 폴더에서 찾기
                filename = file_path.name
                file_path = self.datasets_dir / filename
            
            if not file_path.exists():
                self.logger.error(f"Dataset file not found: {file_path}")
                self.logger.info(f"Looking for file in: {self.datasets_dir}")
                return None
            
            df = pd.read_parquet(file_path, engine='pyarrow')
            
            # GO 데이터의 경우 _gene_set 컬럼을 set으로 복원
            if '_gene_set' in df.columns:
                df['_gene_set'] = df['_gene_set'].apply(
                    lambda x: set(x.split('/')) if isinstance(x, str) and x else set()
                )
            
            # 컬럼명 표준화 (모든 database 파일을 표준화)
            from utils.data_loader import DataLoader
            from models.standard_columns import StandardColumns
            loader = DataLoader()
            
            # 데이터셋 타입에 따라 필수 컬럼 확인
            if metadata.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
                # DE 데이터: gene_id, log2fc, adj_pvalue
                required_standard_cols = [StandardColumns.GENE_ID, StandardColumns.LOG2FC, StandardColumns.ADJ_PVALUE]
            elif metadata.dataset_type == DatasetType.GO_ANALYSIS:
                # GO 데이터: term_id, description, fdr
                required_standard_cols = [StandardColumns.TERM_ID, StandardColumns.DESCRIPTION, StandardColumns.FDR]
            else:
                required_standard_cols = []
            
            all_standard_present = all(col in df.columns for col in required_standard_cols) if required_standard_cols else True
            
            if not all_standard_present:
                # 표준화되지 않은 구버전 database - 변환 필요
                auto_mapping = loader._map_columns(df, metadata.dataset_type)
                df, original_columns = loader._standardize_columns(df, auto_mapping, metadata.dataset_type)
                self.logger.info(f"Converted legacy database columns to standard format")
            else:
                # 이미 표준화된 database
                original_columns = {}
                self.logger.info(f"Database already has standard column names")
            
            # gene_id와 symbol을 문자열로 변환 (ENTREZ ID 등이 정수형일 수 있음)
            if StandardColumns.GENE_ID in df.columns:
                df[StandardColumns.GENE_ID] = df[StandardColumns.GENE_ID].astype(str)
            
            if StandardColumns.SYMBOL in df.columns:
                df[StandardColumns.SYMBOL] = df[StandardColumns.SYMBOL].astype(str)
            
            self.logger.info(f"Available columns: {df.columns.tolist()[:10]}")
            
            # Dataset 객체 생성
            dataset = Dataset(
                name=metadata.alias,
                dataset_type=metadata.dataset_type,
                dataframe=df,
                original_columns=original_columns,  # 원본 컬럼명 참고용
                metadata={
                    'experiment_condition': metadata.experiment_condition,
                    'cell_type': metadata.cell_type,
                    'organism': metadata.organism,
                    'tissue': metadata.tissue,
                    'timepoint': metadata.timepoint,
                    'import_date': metadata.import_date,
                    'notes': metadata.notes,
                    'tags': metadata.tags
                }
            )
            
            self.logger.info(f"Loaded dataset from database: {metadata.alias} ({len(df)} rows)")
            return dataset
            
        except Exception as e:
            self.logger.error(f"Failed to load dataset: {e}")
            return None
    
    def load_multiple_datasets(self, dataset_ids: List[str]) -> List[Dataset]:
        """
        여러 데이터셋을 한 번에 로드
        
        Args:
            dataset_ids: 데이터셋 ID 리스트
            
        Returns:
            List[Dataset]: Dataset 객체 리스트
        """
        datasets = []
        for dataset_id in dataset_ids:
            dataset = self.load_dataset(dataset_id)
            if dataset:
                datasets.append(dataset)
        return datasets
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """
        데이터셋 삭제
        
        Args:
            dataset_id: 데이터셋 ID
            
        Returns:
            bool: 성공 여부
        """
        metadata = self.get_metadata(dataset_id)
        if metadata is None:
            return False
        
        try:
            # 파일 삭제
            file_path = Path(metadata.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # 메타데이터에서 제거
            self.metadata_list = [m for m in self.metadata_list if m.dataset_id != dataset_id]
            self._save_metadata()
            
            self.logger.info(f"Deleted dataset: {metadata.alias}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete dataset: {e}")
            return False
    
    def get_metadata(self, dataset_id: str) -> Optional[PreloadedDatasetMetadata]:
        """
        데이터셋 메타데이터 조회
        
        Args:
            dataset_id: 데이터셋 ID
            
        Returns:
            Optional[PreloadedDatasetMetadata]: 메타데이터 또는 None
        """
        for metadata in self.metadata_list:
            if metadata.dataset_id == dataset_id:
                return metadata
        return None
    
    def get_all_metadata(self) -> List[PreloadedDatasetMetadata]:
        """모든 데이터셋 메타데이터 반환"""
        return self.metadata_list.copy()
    
    def search_datasets(self, 
                       query: str = "",
                       cell_type: str = "",
                       organism: str = "",
                       tags: List[str] = None) -> List[PreloadedDatasetMetadata]:
        """
        데이터셋 검색
        
        Args:
            query: 검색 쿼리 (alias, notes, experiment_condition에서 검색)
            cell_type: 세포 타입 필터
            organism: 생물종 필터
            tags: 태그 필터
            
        Returns:
            List[PreloadedDatasetMetadata]: 검색 결과
        """
        results = self.metadata_list.copy()
        
        # 쿼리 검색
        if query:
            query_lower = query.lower()
            results = [
                meta for meta in results
                if query_lower in meta.alias.lower() or
                   query_lower in meta.notes.lower() or
                   query_lower in meta.experiment_condition.lower()
            ]
        
        # 세포 타입 필터
        if cell_type:
            results = [meta for meta in results if cell_type.lower() in meta.cell_type.lower()]
        
        # 생물종 필터
        if organism:
            results = [meta for meta in results if organism.lower() in meta.organism.lower()]
        
        # 태그 필터
        if tags:
            results = [
                meta for meta in results
                if any(tag in meta.tags for tag in tags)
            ]
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """데이터베이스 통계 정보 반환"""
        total_size = 0
        for meta in self.metadata_list:
            file_path = Path(meta.file_path)
            if file_path.exists():
                total_size += file_path.stat().st_size
        
        return {
            'total_datasets': len(self.metadata_list),
            'total_size_mb': total_size / (1024 * 1024),
            'cell_types': list(set(m.cell_type for m in self.metadata_list if m.cell_type)),
            'organisms': list(set(m.organism for m in self.metadata_list if m.organism)),
            'dataset_types': {
                'differential_expression': sum(1 for m in self.metadata_list if m.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION),
                'go_analysis': sum(1 for m in self.metadata_list if m.dataset_type == DatasetType.GO_ANALYSIS)
            }
        }
