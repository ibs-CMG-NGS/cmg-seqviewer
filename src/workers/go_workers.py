"""
Background Workers for GO/KEGG Analysis

GO Term 클러스터링 등 시간이 걸리는 작업을 백그라운드에서 처리합니다.
"""

from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd
from typing import Dict, List, Optional
import logging

from utils.go_clustering import GOClustering


class GOClusteringWorker(QThread):
    """
    GO Term 클러스터링 백그라운드 작업
    
    Signals:
        progress: 진행률 (0-100)
        finished: 작업 완료 (clustered_df, clusters_dict)
        error: 오류 발생 (error_message)
    """
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(pd.DataFrame, dict)
    error = pyqtSignal(str)
    
    def __init__(self, df: pd.DataFrame, 
                 kappa_threshold: float = 0.4,
                 total_genes: Optional[int] = None):
        """
        Args:
            df: GO/KEGG 분석 결과 DataFrame
            kappa_threshold: Kappa Statistic 임계값
            total_genes: 전체 유전자 수 (background)
        """
        super().__init__()
        self.df = df
        self.kappa_threshold = kappa_threshold
        self.total_genes = total_genes
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """클러스터링 실행"""
        try:
            self.progress.emit(10)
            
            # GOClustering 객체 생성
            clusterer = GOClustering(kappa_threshold=self.kappa_threshold)
            
            self.progress.emit(30)
            
            # 클러스터링 수행
            clustered_df, clusters = clusterer.cluster_terms(
                self.df, 
                total_genes=self.total_genes
            )
            
            self.progress.emit(80)
            
            # 클러스터 통계 계산
            cluster_stats = clusterer.calculate_cluster_statistics(
                clustered_df, 
                clusters
            )
            
            self.progress.emit(100)
            
            # 결과 반환
            result_data = {
                'clustered_df': clustered_df,
                'clusters': clusters,
                'cluster_stats': cluster_stats
            }
            
            self.finished.emit(clustered_df, clusters)
            
        except Exception as e:
            self.logger.error(f"Clustering failed: {e}", exc_info=True)
            self.error.emit(str(e))


class GOEnrichmentWorker(QThread):
    """
    GO Enrichment 분석 백그라운드 작업
    
    실제 GO enrichment 분석을 수행하는 경우 사용
    (현재는 이미 분석된 결과를 로딩하므로 필요시 구현)
    """
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)
    
    def __init__(self, gene_list: List[str], 
                 background_genes: List[str],
                 organism: str = "human"):
        """
        Args:
            gene_list: 분석할 유전자 리스트
            background_genes: 배경 유전자 리스트
            organism: 생물종 (human, mouse 등)
        """
        super().__init__()
        self.gene_list = gene_list
        self.background_genes = background_genes
        self.organism = organism
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """GO Enrichment 분석 실행 (미구현 - 필요시 추가)"""
        try:
            self.progress.emit(10)
            
            # TODO: 실제 GO enrichment 분석 구현
            # 예: gprofiler, enrichr, DAVID API 등 사용
            
            self.progress.emit(50)
            
            # 임시 결과
            result_df = pd.DataFrame({
                'term_id': ['GO:0000001'],
                'description': ['Example GO Term'],
                'pvalue': [0.001],
                'fdr': [0.01],
                'gene_count': [10]
            })
            
            self.progress.emit(100)
            self.finished.emit(result_df)
            
        except Exception as e:
            self.logger.error(f"GO Enrichment failed: {e}", exc_info=True)
            self.error.emit(str(e))
