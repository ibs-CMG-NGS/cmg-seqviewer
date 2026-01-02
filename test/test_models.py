"""
Unit tests for Data Models
"""

import pytest
import pandas as pd
from models.data_models import (
    DifferentialExpressionData,
    GOAnalysisData,
    Dataset,
    DatasetType,
    FilterCriteria,
    ComparisonResult
)


class TestDifferentialExpressionData:
    """DifferentialExpressionData 테스트"""
    
    def test_is_significant(self):
        """유의성 판단 테스트"""
        de_data = DifferentialExpressionData(
            gene_id="BRCA1",
            log2fc=2.5,
            pvalue=0.001,
            adj_pvalue=0.01
        )
        
        assert de_data.is_significant(adj_pvalue_cutoff=0.05, log2fc_cutoff=1.0) is True
        assert de_data.is_significant(adj_pvalue_cutoff=0.005, log2fc_cutoff=1.0) is False
    
    def test_regulation(self):
        """발현 방향 테스트"""
        up_gene = DifferentialExpressionData(gene_id="UP1", log2fc=2.0)
        down_gene = DifferentialExpressionData(gene_id="DOWN1", log2fc=-2.0)
        no_change = DifferentialExpressionData(gene_id="NC1", log2fc=0.0)
        
        assert up_gene.regulation == "Up"
        assert down_gene.regulation == "Down"
        assert no_change.regulation == "No change"


class TestDataset:
    """Dataset 테스트"""
    
    def test_dataset_creation(self):
        """데이터셋 생성 테스트"""
        df = pd.DataFrame({
            'gene': ['BRCA1', 'TP53', 'EGFR'],
            'log2fc': [2.5, -1.8, 1.2],
            'pvalue': [0.001, 0.002, 0.05],
            'padj': [0.01, 0.02, 0.1]
        })
        
        dataset = Dataset(
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
        
        assert dataset.name == "Test Dataset"
        assert len(dataset.dataframe) == 3
        assert dataset.metadata['row_count'] == 3
    
    def test_get_filtered_data(self):
        """필터링 테스트"""
        df = pd.DataFrame({
            'gene': ['BRCA1', 'TP53', 'EGFR', 'MYC'],
            'log2fc': [2.5, -1.8, 1.2, 0.5],
            'padj': [0.01, 0.02, 0.03, 0.1]
        })
        
        dataset = Dataset(
            name="Test",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=df,
            column_mapping={
                'gene': 'gene_id',
                'log2fc': 'log2fc',
                'padj': 'adj_pvalue'
            }
        )
        
        filtered = dataset.get_filtered_data(adj_pvalue_max=0.05, log2fc_min=1.0)
        
        assert len(filtered) == 2  # BRCA1, TP53
    
    def test_get_genes(self):
        """유전자 목록 추출 테스트"""
        df = pd.DataFrame({
            'gene': ['BRCA1', 'TP53', 'EGFR'],
            'log2fc': [2.5, -1.8, 1.2]
        })
        
        dataset = Dataset(
            name="Test",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=df,
            column_mapping={'gene': 'gene_id', 'log2fc': 'log2fc'}
        )
        
        genes = dataset.get_genes()
        assert len(genes) == 3
        assert 'BRCA1' in genes


class TestFilterCriteria:
    """FilterCriteria 테스트"""
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        criteria = FilterCriteria(
            adj_pvalue_max=0.01,
            log2fc_min=2.0,
            gene_list=['BRCA1', 'TP53']
        )
        
        d = criteria.to_dict()
        assert d['adj_pvalue_max'] == 0.01
        assert d['log2fc_min'] == 2.0
        assert d['gene_list'] == ['BRCA1', 'TP53']
    
    def test_from_dict(self):
        """딕셔너리로부터 생성 테스트"""
        d = {
            'adj_pvalue_max': 0.01,
            'log2fc_min': 2.0,
            'gene_list': ['BRCA1']
        }
        
        criteria = FilterCriteria.from_dict(d)
        assert criteria.adj_pvalue_max == 0.01
        assert criteria.log2fc_min == 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
