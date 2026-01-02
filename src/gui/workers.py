"""
Worker Threads for Asynchronous Operations

QThread를 사용한 비동기 작업 처리
대용량 데이터 로딩 및 필터링 시 GUI 블로킹 방지
"""

from PyQt6.QtCore import QThread, pyqtSignal
from pathlib import Path
from typing import List, Optional
import logging

from models.data_models import Dataset, FilterCriteria
from utils.data_loader import DataLoader
from utils.statistics import StatisticalAnalyzer


class DataLoadWorker(QThread):
    """
    데이터 로딩 Worker
    
    대용량 Excel 파일을 비동기로 로드합니다.
    """
    
    # Signals
    progress = pyqtSignal(int)  # 진행률 (0-100)
    finished = pyqtSignal(Dataset)  # 완료 시 데이터셋 반환
    error = pyqtSignal(str)  # 오류 메시지
    
    def __init__(self, file_path: Path, dataset_name: Optional[str] = None):
        super().__init__()
        self.file_path = file_path
        self.dataset_name = dataset_name
        self.logger = logging.getLogger(__name__)
        self.data_loader = DataLoader()
    
    def run(self):
        """작업 실행"""
        try:
            self.progress.emit(10)
            
            # 데이터 로드
            dataset = self.data_loader.load_from_excel(
                self.file_path, self.dataset_name
            )
            
            self.progress.emit(50)
            
            # 데이터 검증
            if not dataset.is_valid:
                self.logger.warning("Dataset validation failed")
            
            self.progress.emit(100)
            
            # 완료
            self.finished.emit(dataset)
            
        except Exception as e:
            self.logger.error(f"Data load worker failed: {e}", exc_info=True)
            self.error.emit(str(e))


class FilterWorker(QThread):
    """
    필터링 Worker
    
    대용량 데이터 필터링을 비동기로 처리합니다.
    """
    
    # Signals
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)  # pd.DataFrame
    error = pyqtSignal(str)
    
    def __init__(self, dataset: Dataset, criteria: FilterCriteria):
        super().__init__()
        self.dataset = dataset
        self.criteria = criteria
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """작업 실행"""
        try:
            self.progress.emit(20)
            
            # 필터링 실행
            filtered_df = self.dataset.get_filtered_data(**self.criteria.to_dict())
            
            self.progress.emit(80)
            
            # 완료
            self.progress.emit(100)
            self.finished.emit(filtered_df)
            
        except Exception as e:
            self.logger.error(f"Filter worker failed: {e}", exc_info=True)
            self.error.emit(str(e))


class AnalysisWorker(QThread):
    """
    통계 분석 Worker
    
    통계 분석을 비동기로 처리합니다.
    """
    
    # Signals
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict, str)  # result, analysis_type
    error = pyqtSignal(str)
    
    def __init__(self, analysis_type: str, gene_list: List[str], dataset: Dataset):
        super().__init__()
        self.analysis_type = analysis_type
        self.gene_list = gene_list
        self.dataset = dataset
        self.logger = logging.getLogger(__name__)
        self.analyzer = StatisticalAnalyzer()
    
    def run(self):
        """작업 실행"""
        try:
            self.progress.emit(30)
            
            # 분석 실행
            if self.analysis_type == "fisher":
                result = self.analyzer.fisher_exact_test(
                    self.gene_list, self.dataset
                )
            elif self.analysis_type == "gsea":
                result = self.analyzer.gsea_lite(
                    self.gene_list, self.dataset
                )
            else:
                raise ValueError(f"Unknown analysis type: {self.analysis_type}")
            
            self.progress.emit(90)
            
            # 완료
            self.progress.emit(100)
            self.finished.emit(result, self.analysis_type)
            
        except Exception as e:
            self.logger.error(f"Analysis worker failed: {e}", exc_info=True)
            self.error.emit(str(e))


class ComparisonWorker(QThread):
    """
    데이터셋 비교 Worker
    
    다중 데이터셋 비교를 비동기로 처리합니다.
    """
    
    # Signals
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)  # ComparisonResult
    error = pyqtSignal(str)
    
    def __init__(self, datasets: List[Dataset], gene_list: Optional[List[str]] = None,
                 adj_pvalue_cutoff: float = 0.05, log2fc_cutoff: float = 1.0):
        super().__init__()
        self.datasets = datasets
        self.gene_list = gene_list
        self.adj_pvalue_cutoff = adj_pvalue_cutoff
        self.log2fc_cutoff = log2fc_cutoff
        self.logger = logging.getLogger(__name__)
        self.analyzer = StatisticalAnalyzer()
    
    def run(self):
        """작업 실행"""
        try:
            self.progress.emit(20)
            
            # 비교 실행
            result = self.analyzer.compare_datasets(
                self.datasets,
                gene_list=self.gene_list,
                adj_pvalue_cutoff=self.adj_pvalue_cutoff,
                log2fc_cutoff=self.log2fc_cutoff
            )
            
            self.progress.emit(80)
            
            # 완료
            self.progress.emit(100)
            self.finished.emit(result)
            
        except Exception as e:
            self.logger.error(f"Comparison worker failed: {e}", exc_info=True)
            self.error.emit(str(e))


class ExportWorker(QThread):
    """
    데이터 내보내기 Worker
    
    대용량 데이터 내보내기를 비동기로 처리합니다.
    """
    
    # Signals
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, df, file_path: Path):
        super().__init__()
        self.df = df
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """작업 실행"""
        try:
            self.progress.emit(30)
            
            # 파일 형식에 따라 저장
            if self.file_path.suffix == '.csv':
                self.df.to_csv(self.file_path, index=False)
            elif self.file_path.suffix == '.tsv':
                self.df.to_csv(self.file_path, sep='\t', index=False)
            elif self.file_path.suffix in ['.xlsx', '.xls']:
                self.df.to_excel(self.file_path, index=False)
            else:
                raise ValueError(f"Unsupported file format: {self.file_path.suffix}")
            
            self.progress.emit(90)
            
            # 완료
            self.progress.emit(100)
            self.finished.emit()
            
        except Exception as e:
            self.logger.error(f"Export worker failed: {e}", exc_info=True)
            self.error.emit(str(e))
