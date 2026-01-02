"""
Data Models for RNA-Seq Analysis

RNA-Seq 데이터를 표현하는 모델 클래스들을 정의합니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import pandas as pd
from pathlib import Path


class DatasetType(Enum):
    """데이터셋 타입"""
    DIFFERENTIAL_EXPRESSION = "differential_expression"
    GO_ANALYSIS = "go_analysis"
    UNKNOWN = "unknown"


class FilterMode(Enum):
    """필터링 모드"""
    GENE_LIST = "gene_list"  # 유전자 리스트 기반 필터링
    STATISTICAL = "statistical"  # 통계값 기반 필터링 (p-value, FC)


@dataclass
class DifferentialExpressionData:
    """
    차등 발현 분석 데이터 (Differential Expression)
    
    필수 컬럼:
        - Gene ID/Symbol
        - log2FC (log2 Fold Change)
        - p-value
        - adjusted p-value (adj.p-value, FDR)
    """
    gene_id: str
    gene_symbol: Optional[str] = None
    log2fc: float = 0.0
    pvalue: float = 1.0
    adj_pvalue: float = 1.0
    base_mean: Optional[float] = None
    additional_fields: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_significant(self, adj_pvalue_cutoff: float = 0.05, 
                       log2fc_cutoff: float = 1.0) -> bool:
        """통계적 유의성 판단"""
        return (abs(self.log2fc) >= log2fc_cutoff and 
                self.adj_pvalue <= adj_pvalue_cutoff)
    
    @property
    def regulation(self) -> str:
        """발현 방향 (Up/Down/No change)"""
        if self.log2fc > 0:
            return "Up"
        elif self.log2fc < 0:
            return "Down"
        else:
            return "No change"


@dataclass
class GOAnalysisData:
    """
    Gene Ontology (GO) 분석 데이터
    
    필수 컬럼:
        - Term (GO Term)
        - Gene Count
        - p-value
        - FDR (False Discovery Rate)
    """
    term_id: str
    term_name: str
    gene_count: int
    pvalue: float = 1.0
    fdr: float = 1.0
    genes: List[str] = field(default_factory=list)
    category: Optional[str] = None  # BP, MF, CC
    additional_fields: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_significant(self, fdr_cutoff: float = 0.05) -> bool:
        """통계적 유의성 판단"""
        return self.fdr <= fdr_cutoff


@dataclass
class Dataset:
    """
    RNA-Seq 데이터셋
    
    여러 타입의 데이터를 담을 수 있는 컨테이너입니다.
    
    Note: 
        dataframe의 컬럼명은 모두 표준 컬럼명(StandardColumns)을 사용합니다.
        원본 컬럼명은 original_columns에 참고용으로 저장됩니다.
    """
    name: str
    dataset_type: DatasetType
    file_path: Optional[Path] = None
    dataframe: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 원본 컬럼명 참고 정보 (표준 컬럼명 -> 원본 컬럼명)
    # 표시 목적으로만 사용, 실제 데이터 접근에는 사용하지 않음
    original_columns: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """데이터셋 초기화 후 처리"""
        if self.dataframe is not None:
            self.metadata['row_count'] = len(self.dataframe)
            self.metadata['column_count'] = len(self.dataframe.columns)
    
    @property
    def is_valid(self) -> bool:
        """데이터셋 유효성 검사"""
        if self.dataframe is None or self.dataframe.empty:
            return False
        
        # 타입별 필수 컬럼 검사 (표준 컬럼명 사용)
        if self.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            required = ['gene_id', 'log2fc', 'adj_pvalue']
        elif self.dataset_type == DatasetType.GO_ANALYSIS:
            required = ['term', 'gene_count', 'fdr']
        else:
            return True
        
        # DataFrame에 필수 컬럼이 있는지 확인
        df_cols = set(self.dataframe.columns)
        return all(col in df_cols for col in required)
    
    def get_filtered_data(self, **filters) -> pd.DataFrame:
        """
        필터 조건에 맞는 데이터 반환
        
        Args:
            **filters: 필터 조건 (예: adj_pvalue_max=0.05, log2fc_min=1.0)
            
        Returns:
            필터링된 DataFrame
        """
        if self.dataframe is None:
            return pd.DataFrame()
        
        filtered = self.dataframe.copy()
        
        # Differential Expression 필터 (표준 컬럼명 직접 사용)
        if self.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            if 'adj_pvalue_max' in filters:
                if 'adj_pvalue' in filtered.columns:
                    filtered = filtered[filtered['adj_pvalue'] <= filters['adj_pvalue_max']]
            
            if 'log2fc_min' in filters:
                if 'log2fc' in filtered.columns:
                    filtered = filtered[abs(filtered['log2fc']) >= filters['log2fc_min']]
            
            if 'gene_list' in filters and filters['gene_list']:
                if 'gene_id' in filtered.columns:
                    filtered = filtered[filtered['gene_id'].isin(filters['gene_list'])]
        
        # GO Analysis 필터 (표준 컬럼명 직접 사용)
        elif self.dataset_type == DatasetType.GO_ANALYSIS:
            if 'fdr_max' in filters:
                if 'fdr' in filtered.columns:
                    filtered = filtered[filtered['fdr'] <= filters['fdr_max']]
        
        return filtered
    
    def get_genes(self, filters: Optional[Dict] = None) -> List[str]:
        """
        유전자 목록 반환
        
        Args:
            filters: 필터 조건 (선택)
            
        Returns:
            유전자 ID 리스트
        """
        if filters:
            df = self.get_filtered_data(**filters)
        else:
            df = self.dataframe
        
        if df is None or df.empty:
            return []
        
        # 표준 컬럼명 직접 사용
        if 'gene_id' in df.columns:
            return df['gene_id'].tolist()
        
        return []
    
    def get_summary(self) -> Dict[str, Any]:
        """데이터셋 요약 정보 반환"""
        summary = {
            'name': self.name,
            'type': self.dataset_type.value,
            'file_path': str(self.file_path) if self.file_path else None,
            'valid': self.is_valid,
        }
        summary.update(self.metadata)
        
        if self.dataframe is not None and not self.dataframe.empty:
            # 타입별 추가 통계 (표준 컬럼명 직접 사용)
            if self.dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
                if 'adj_pvalue' in self.dataframe.columns and 'log2fc' in self.dataframe.columns:
                    sig_genes = self.dataframe[
                        (self.dataframe['adj_pvalue'] < 0.05) & 
                        (abs(self.dataframe['log2fc']) > 1.0)
                    ]
                    summary['total_genes'] = len(self.dataframe)
                    summary['significant_genes'] = len(sig_genes)
                    summary['upregulated'] = len(sig_genes[sig_genes['log2fc'] > 0])
                    summary['downregulated'] = len(sig_genes[sig_genes['log2fc'] < 0])
            
            elif self.dataset_type == DatasetType.GO_ANALYSIS:
                if 'fdr' in self.dataframe.columns:
                    sig_terms = self.dataframe[self.dataframe['fdr'] < 0.05]
                    summary['total_terms'] = len(self.dataframe)
                    summary['significant_terms'] = len(sig_terms)
        
        return summary


@dataclass
class FilterCriteria:
    """
    필터링 기준
    
    두 가지 필터링 모드를 지원:
    1. GENE_LIST: gene_list에 있는 유전자만 필터링
    2. STATISTICAL: adj_pvalue, log2fc 기준으로 필터링 (DE) 또는 fdr, ontology, direction 기준 (GO)
    """
    mode: FilterMode = FilterMode.STATISTICAL
    
    # Statistical 모드용 (DE)
    adj_pvalue_max: float = 0.05
    log2fc_min: float = 1.0
    regulation_direction: str = "both"  # "up", "down", "both"
    
    # Statistical 모드용 (GO)
    fdr_max: float = 0.05
    ontology: str = "All"  # "All", "BP", "MF", "CC", "KEGG"
    go_direction: str = "All"  # "All", "UP", "DOWN", "TOTAL"
    
    # Gene List 모드용
    gene_list: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'mode': self.mode.value,
            'adj_pvalue_max': self.adj_pvalue_max,
            'log2fc_min': self.log2fc_min,
            'gene_list': self.gene_list,
            'fdr_max': self.fdr_max,
            'regulation_direction': self.regulation_direction,
            'ontology': self.ontology,
            'go_direction': self.go_direction,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterCriteria':
        """딕셔너리로부터 생성"""
        # mode는 enum으로 변환
        if 'mode' in data and isinstance(data['mode'], str):
            data['mode'] = FilterMode(data['mode'])
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class ComparisonResult:
    """다중 데이터셋 비교 결과"""
    dataset_names: List[str]
    common_genes: List[str] = field(default_factory=list)
    unique_genes: Dict[str, List[str]] = field(default_factory=dict)
    comparison_table: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_overlap_stats(self) -> Dict[str, int]:
        """교집합 통계 반환"""
        return {
            'total_datasets': len(self.dataset_names),
            'common_genes_count': len(self.common_genes),
            'unique_genes_per_dataset': {
                name: len(genes) for name, genes in self.unique_genes.items()
            }
        }


@dataclass
class PreloadedDatasetMetadata:
    """Pre-loaded 데이터셋 메타데이터"""
    dataset_id: str                      # 고유 ID (UUID)
    alias: str                           # 사용자 지정 별명
    original_filename: str               # 원본 파일명
    dataset_type: DatasetType           # DIFFERENTIAL_EXPRESSION or GO_ANALYSIS
    
    # 실험 정보
    experiment_condition: str = ""       # 실험 조건 (예: "Treatment vs Control")
    cell_type: str = ""                  # 세포 타입 (예: "HeLa", "MCF7")
    organism: str = ""                   # 생물종 (예: "Homo sapiens", "Mus musculus")
    tissue: str = ""                     # 조직 (예: "Liver", "Brain")
    timepoint: str = ""                  # 시간점 (예: "24h", "48h")
    
    # 데이터 정보
    row_count: int = 0                   # 행 개수
    gene_count: int = 0                  # 유전자 개수
    significant_genes: int = 0           # 유의미한 유전자 수 (padj<0.05)
    
    # 메타데이터
    import_date: str = ""                # 데이터베이스 임포트 날짜
    file_path: str = ""                  # 저장된 파일 경로 (parquet)
    notes: str = ""                      # 사용자 메모
    tags: List[str] = field(default_factory=list)  # 태그 (검색용)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (JSON 저장용)"""
        return {
            'dataset_id': self.dataset_id,
            'alias': self.alias,
            'original_filename': self.original_filename,
            'dataset_type': self.dataset_type.value,
            'experiment_condition': self.experiment_condition,
            'cell_type': self.cell_type,
            'organism': self.organism,
            'tissue': self.tissue,
            'timepoint': self.timepoint,
            'row_count': int(self.row_count),  # numpy int64 -> Python int
            'gene_count': int(self.gene_count),  # numpy int64 -> Python int
            'significant_genes': int(self.significant_genes),  # numpy int64 -> Python int
            'import_date': self.import_date,
            'file_path': self.file_path,
            'notes': self.notes,
            'tags': self.tags
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PreloadedDatasetMetadata':
        """딕셔너리에서 생성"""
        return PreloadedDatasetMetadata(
            dataset_id=data['dataset_id'],
            alias=data['alias'],
            original_filename=data['original_filename'],
            dataset_type=DatasetType(data['dataset_type']),
            experiment_condition=data.get('experiment_condition', ''),
            cell_type=data.get('cell_type', ''),
            organism=data.get('organism', ''),
            tissue=data.get('tissue', ''),
            timepoint=data.get('timepoint', ''),
            row_count=data.get('row_count', 0),
            gene_count=data.get('gene_count', 0),
            significant_genes=data.get('significant_genes', 0),
            import_date=data.get('import_date', ''),
            file_path=data.get('file_path', ''),
            notes=data.get('notes', ''),
            tags=data.get('tags', [])
        )
