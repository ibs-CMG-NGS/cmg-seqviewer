"""
Statistical Analysis Module for RNA-Seq Data

통계 분석 기능을 제공합니다:
- Fisher's Exact Test
- Gene Set Enrichment Analysis (GSEA) Lite
- 다중 데이터셋 비교
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Dict, Optional, Tuple
import logging
from models.data_models import Dataset, DatasetType, ComparisonResult
from models.standard_columns import StandardColumns


class StatisticalAnalyzer:
    """
    RNA-Seq 데이터 통계 분석기
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def fisher_exact_test(self, gene_list: List[str], dataset: Dataset,
                         background_size: Optional[int] = None,
                         adj_pvalue_cutoff: float = 0.05,
                         log2fc_cutoff: float = 1.0) -> Dict[str, any]:
        """
        Fisher's Exact Test를 사용한 유의성 검사
        
        관심 유전자 리스트가 데이터셋에서 통계적으로 유의미한 차이를 보이는지 확인합니다.
        
        Args:
            gene_list: 관심 유전자 리스트
            dataset: 분석할 데이터셋
            background_size: 전체 유전자 수 (None이면 데이터셋 크기 사용)
            adj_pvalue_cutoff: Adjusted p-value 임계값
            log2fc_cutoff: log2 Fold Change 임계값
            
        Returns:
            분석 결과 딕셔너리
        """
        self.logger.info(f"Running Fisher's exact test on {len(gene_list)} genes")
        
        if dataset.dataset_type != DatasetType.DIFFERENTIAL_EXPRESSION:
            raise ValueError("Fisher's exact test requires Differential Expression dataset")
        
        df = dataset.dataframe
        if df is None or df.empty:
            raise ValueError("Dataset is empty")
        
        # 표준 컬럼명 직접 사용
        gene_col = StandardColumns.GENE_ID
        adj_pval_col = StandardColumns.ADJ_PVALUE
        log2fc_col = StandardColumns.LOG2FC
        
        # 필수 컬럼 확인
        if not all([gene_col in df.columns, adj_pval_col in df.columns, log2fc_col in df.columns]):
            self.logger.error(f"Available columns: {df.columns.tolist()}")
            self.logger.error(f"Missing required standard columns")
            raise ValueError(f"Required columns not found: {gene_col}, {adj_pval_col}, {log2fc_col}")
        
        # 유의미한 유전자 찾기
        sig_genes = df[
            (df[adj_pval_col] <= adj_pvalue_cutoff) &
            (abs(df[log2fc_col]) >= log2fc_cutoff)
        ][gene_col].tolist()
        
        # 2x2 contingency table 구성
        # | In list & Significant | In list & Not significant |
        # | Not in list & Significant | Not in list & Not significant |
        
        in_list_sig = len(set(gene_list) & set(sig_genes))
        in_list_not_sig = len(set(gene_list) - set(sig_genes))
        not_in_list_sig = len(set(sig_genes) - set(gene_list))
        
        if background_size is None:
            background_size = len(df)
        
        not_in_list_not_sig = background_size - in_list_sig - in_list_not_sig - not_in_list_sig
        
        # Fisher's exact test 수행
        table = [[in_list_sig, in_list_not_sig],
                [not_in_list_sig, not_in_list_not_sig]]
        
        odds_ratio, pvalue = stats.fisher_exact(table, alternative='greater')
        
        result = {
            'pvalue': pvalue,
            'odds_ratio': odds_ratio,
            'in_list_significant': in_list_sig,
            'in_list_total': len(gene_list),
            'dataset_significant': len(sig_genes),
            'dataset_total': background_size,
            'enrichment_fold': (in_list_sig / len(gene_list)) / (len(sig_genes) / background_size) if len(sig_genes) > 0 else 0,
            'contingency_table': table,
            'significant': pvalue < 0.05,
        }
        
        self.logger.info(
            f"Fisher test result: p={pvalue:.4e}, OR={odds_ratio:.2f}, "
            f"{in_list_sig}/{len(gene_list)} genes significant"
        )
        
        return result
    
    def gsea_lite(self, gene_list: List[str], dataset: Dataset,
                 adj_pvalue_cutoff: float = 0.05) -> Dict[str, any]:
        """
        간단한 Gene Set Enrichment Analysis
        
        유전자 리스트가 데이터셋에서 한쪽으로 편향되어 있는지 확인합니다.
        
        Args:
            gene_list: 관심 유전자 리스트
            dataset: 분석할 데이터셋
            adj_pvalue_cutoff: Adjusted p-value 임계값
            
        Returns:
            분석 결과 딕셔너리
        """
        self.logger.info(f"Running GSEA lite on {len(gene_list)} genes")
        
        if dataset.dataset_type != DatasetType.DIFFERENTIAL_EXPRESSION:
            raise ValueError("GSEA requires Differential Expression dataset")
        
        if dataset.dataframe is None:
            raise ValueError("Dataset dataframe is None")
            
        df = dataset.dataframe.copy()
        
        # 표준 컬럼명 직접 사용
        gene_col = StandardColumns.GENE_ID
        log2fc_col = StandardColumns.LOG2FC
        adj_pval_col = StandardColumns.ADJ_PVALUE
        
        # 필수 컬럼 확인
        if not all([gene_col in df.columns, log2fc_col in df.columns, adj_pval_col in df.columns]):
            self.logger.error(f"Available columns: {df.columns.tolist()}")
            raise ValueError(f"Required columns not found: {gene_col}, {log2fc_col}, {adj_pval_col}")
        
        # 관심 유전자만 필터링
        df_filtered = df[df[gene_col].isin(gene_list)].copy()
        
        if len(df_filtered) == 0:
            return {
                'mean_log2fc': 0,
                'median_log2fc': 0,
                'upregulated_count': 0,
                'downregulated_count': 0,
                'significant_count': 0,
                'total_count': 0,
                'enrichment_direction': 'none',
                'wilcoxon_pvalue': 1.0,
            }
        
        # 통계 계산
        mean_log2fc = df_filtered[log2fc_col].mean()
        median_log2fc = df_filtered[log2fc_col].median()
        
        sig_df = df_filtered[df_filtered[adj_pval_col] <= adj_pvalue_cutoff]
        up_count = len(sig_df[sig_df[log2fc_col] > 0])
        down_count = len(sig_df[sig_df[log2fc_col] < 0])
        
        # Wilcoxon signed-rank test (양측 검정)
        try:
            _, wilcoxon_pvalue = stats.wilcoxon(df_filtered[log2fc_col])
        except:
            wilcoxon_pvalue = 1.0
        
        # 방향 결정
        if mean_log2fc > 0 and wilcoxon_pvalue < 0.05:
            direction = 'up'
        elif mean_log2fc < 0 and wilcoxon_pvalue < 0.05:
            direction = 'down'
        else:
            direction = 'none'
        
        result = {
            'mean_log2fc': mean_log2fc,
            'median_log2fc': median_log2fc,
            'upregulated_count': up_count,
            'downregulated_count': down_count,
            'significant_count': len(sig_df),
            'total_count': len(df_filtered),
            'enrichment_direction': direction,
            'wilcoxon_pvalue': wilcoxon_pvalue,
        }
        
        self.logger.info(
            f"GSEA result: mean_log2fc={mean_log2fc:.2f}, "
            f"direction={direction}, p={wilcoxon_pvalue:.4e}"
        )
        
        return result
    
    def compare_datasets(self, datasets: List[Dataset], gene_list: Optional[List[str]] = None,
                        adj_pvalue_cutoff: float = 0.05,
                        log2fc_cutoff: float = 1.0) -> ComparisonResult:
        """
        다중 데이터셋 비교
        
        Args:
            datasets: 비교할 데이터셋 리스트
            gene_list: 비교할 유전자 리스트 (None이면 유의미한 유전자만)
            adj_pvalue_cutoff: Adjusted p-value 임계값
            log2fc_cutoff: log2 Fold Change 임계값
            
        Returns:
            ComparisonResult 객체
        """
        self.logger.info(f"Comparing {len(datasets)} datasets")
        
        if len(datasets) < 2:
            raise ValueError("At least 2 datasets required for comparison")
        
        # 각 데이터셋의 유의미한 유전자 추출
        dataset_genes = {}
        for dataset in datasets:
            if dataset.dataset_type != DatasetType.DIFFERENTIAL_EXPRESSION:
                continue
            
            genes = dataset.get_genes({
                'adj_pvalue_max': adj_pvalue_cutoff,
                'log2fc_min': log2fc_cutoff,
            })
            dataset_genes[dataset.name] = set(genes)
        
        # 특정 유전자 리스트가 주어진 경우
        if gene_list:
            gene_set = set(gene_list)
            dataset_genes = {name: genes & gene_set 
                           for name, genes in dataset_genes.items()}
        
        # 교집합 및 고유 유전자 계산
        all_genes = set.union(*dataset_genes.values()) if dataset_genes else set()
        common_genes = set.intersection(*dataset_genes.values()) if dataset_genes else set()
        
        unique_genes = {}
        for name, genes in dataset_genes.items():
            unique = genes - set.union(*[g for n, g in dataset_genes.items() if n != name])
            unique_genes[name] = list(unique)
        
        # 비교 테이블 생성
        comparison_df = self._create_comparison_table(
            datasets, list(all_genes) if gene_list is None else gene_list
        )
        
        result = ComparisonResult(
            dataset_names=list(dataset_genes.keys()),
            common_genes=list(common_genes),
            unique_genes=unique_genes,
            comparison_table=comparison_df,
            metadata={
                'adj_pvalue_cutoff': adj_pvalue_cutoff,
                'log2fc_cutoff': log2fc_cutoff,
                'total_genes': len(all_genes),
                'common_genes_count': len(common_genes),
            }
        )
        
        self.logger.info(
            f"Comparison complete: {len(all_genes)} total genes, "
            f"{len(common_genes)} common genes"
        )
        
        return result
    
    def _create_comparison_table(self, datasets: List[Dataset], 
                                 genes: List[str]) -> pd.DataFrame:
        """
        비교 테이블 생성
        
        각 데이터셋의 log2FC와 adj.p-value를 비교합니다.
        """
        data = {'Gene': genes}
        
        for dataset in datasets:
            if dataset.dataset_type != DatasetType.DIFFERENTIAL_EXPRESSION:
                continue
            
            df = dataset.dataframe
            if df is None:
                continue
            
            # 표준 컬럼명 직접 사용
            gene_col = StandardColumns.GENE_ID
            log2fc_col = StandardColumns.LOG2FC
            adj_pval_col = StandardColumns.ADJ_PVALUE
            
            if not all([gene_col in df.columns, log2fc_col in df.columns, adj_pval_col in df.columns]):
                continue
            
            # 유전자별 값 매핑
            gene_to_log2fc = dict(zip(df[gene_col], df[log2fc_col]))
            gene_to_pval = dict(zip(df[gene_col], df[adj_pval_col]))
            
            data[f'{dataset.name}_log2FC'] = [gene_to_log2fc.get(g, np.nan) for g in genes]
            data[f'{dataset.name}_adj.pval'] = [gene_to_pval.get(g, np.nan) for g in genes]
        
        return pd.DataFrame(data)
    
    def calculate_overlap_significance(self, set1: List[str], set2: List[str],
                                      background_size: int) -> Dict[str, any]:
        """
        두 유전자 집합의 겹침 유의성 계산 (Hypergeometric test)
        
        Args:
            set1: 첫 번째 유전자 집합
            set2: 두 번째 유전자 집합
            background_size: 전체 유전자 수
            
        Returns:
            유의성 검정 결과
        """
        overlap = len(set(set1) & set(set2))
        
        # Hypergeometric test
        pvalue = stats.hypergeom.sf(overlap - 1, background_size, len(set1), len(set2))
        
        expected_overlap = (len(set1) * len(set2)) / background_size
        fold_enrichment = overlap / expected_overlap if expected_overlap > 0 else 0
        
        return {
            'overlap_size': overlap,
            'set1_size': len(set1),
            'set2_size': len(set2),
            'background_size': background_size,
            'expected_overlap': expected_overlap,
            'fold_enrichment': fold_enrichment,
            'pvalue': pvalue,
            'significant': pvalue < 0.05,
        }
