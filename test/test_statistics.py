"""
Unit tests for Statistical Analysis
"""

import pytest
import pandas as pd
import numpy as np
from models.data_models import Dataset, DatasetType
from utils.statistics import StatisticalAnalyzer


class TestStatisticalAnalyzer:
    """StatisticalAnalyzer 테스트"""
    
    @pytest.fixture
    def sample_dataset(self):
        """샘플 데이터셋 생성"""
        np.random.seed(42)
        n = 100
        
        df = pd.DataFrame({
            'gene': [f'GENE{i}' for i in range(n)],
            'log2fc': np.random.randn(n) * 2,
            'pvalue': np.random.uniform(0, 1, n),
            'padj': np.random.uniform(0, 1, n)
        })
        
        # 일부 유전자를 유의미하게 설정
        df.loc[:20, 'padj'] = 0.01
        df.loc[:20, 'log2fc'] = np.random.randn(21) * 3 + 2
        
        return Dataset(
            name="Test Dataset",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=df,
            column_mapping={
                'gene': 'gene_id',
                'log2fc': 'log2fc',
                'pvalue': 'pvalue',
                'padj': 'adj_pvalue'
            }
        )
    
    def test_fisher_exact_test(self, sample_dataset):
        """Fisher's exact test 테스트"""
        analyzer = StatisticalAnalyzer()
        
        # 유의미한 유전자 리스트 (일부는 데이터셋에 있음)
        gene_list = [f'GENE{i}' for i in range(15)]
        
        result = analyzer.fisher_exact_test(
            gene_list, sample_dataset,
            adj_pvalue_cutoff=0.05,
            log2fc_cutoff=1.0
        )
        
        assert 'pvalue' in result
        assert 'odds_ratio' in result
        assert 'in_list_significant' in result
        assert isinstance(result['pvalue'], float)
        assert result['pvalue'] >= 0 and result['pvalue'] <= 1
    
    def test_gsea_lite(self, sample_dataset):
        """GSEA lite 테스트"""
        analyzer = StatisticalAnalyzer()
        
        gene_list = [f'GENE{i}' for i in range(15)]
        
        result = analyzer.gsea_lite(gene_list, sample_dataset)
        
        assert 'mean_log2fc' in result
        assert 'median_log2fc' in result
        assert 'enrichment_direction' in result
        assert result['enrichment_direction'] in ['up', 'down', 'none']
    
    def test_compare_datasets(self, sample_dataset):
        """데이터셋 비교 테스트"""
        analyzer = StatisticalAnalyzer()
        
        # 두 번째 데이터셋 생성 (약간 다른 데이터)
        df2 = sample_dataset.dataframe.copy()
        df2['log2fc'] = df2['log2fc'] * 0.8
        
        dataset2 = Dataset(
            name="Test Dataset 2",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=df2,
            column_mapping=sample_dataset.column_mapping
        )
        
        result = analyzer.compare_datasets([sample_dataset, dataset2])
        
        assert result is not None
        assert isinstance(result.common_genes, list)
        assert isinstance(result.unique_genes, dict)
        assert len(result.dataset_names) == 2
    
    def test_calculate_overlap_significance(self):
        """겹침 유의성 계산 테스트"""
        analyzer = StatisticalAnalyzer()
        
        set1 = [f'GENE{i}' for i in range(50)]
        set2 = [f'GENE{i}' for i in range(25, 75)]
        
        result = analyzer.calculate_overlap_significance(
            set1, set2, background_size=1000
        )
        
        assert 'overlap_size' in result
        assert 'pvalue' in result
        assert 'fold_enrichment' in result
        assert result['overlap_size'] == 25  # 50-25 = 25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
