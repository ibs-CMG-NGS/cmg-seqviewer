"""
Unit tests for Data Models

Dataset 은 표준 컬럼명(gene_id / log2fc / adj_pvalue …)을 전제로 동작한다
(DataLoader 가 로드 시 원본 컬럼을 표준명으로 변환). 테스트도 표준명을 쓴다.
"""

import pandas as pd
import pytest

from models.data_models import (
    DifferentialExpressionData,
    GOAnalysisData,
    Dataset,
    DatasetType,
    FilterCriteria
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


class TestGOAnalysisData:
    """GOAnalysisData 테스트"""

    def test_is_significant(self):
        term = GOAnalysisData(term_id="GO:0006955", term_name="immune response",
                              gene_count=25, fdr=0.01)

        assert term.is_significant(fdr_cutoff=0.05) is True
        assert term.is_significant(fdr_cutoff=0.001) is False


def _de_dataframe() -> pd.DataFrame:
    return pd.DataFrame({
        'gene_id': ['BRCA1', 'TP53', 'EGFR', 'MYC'],
        'symbol': ['BRCA1', 'TP53', 'EGFR', 'MYC'],
        'log2fc': [2.5, -1.8, 1.2, 0.5],
        'pvalue': [0.001, 0.002, 0.05, 0.2],
        'adj_pvalue': [0.01, 0.02, 0.03, 0.1],
    })


class TestDataset:
    """Dataset 테스트"""

    def test_dataset_creation(self):
        """데이터셋 생성 테스트"""
        dataset = Dataset(
            name="Test Dataset",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=_de_dataframe(),
        )

        assert dataset.name == "Test Dataset"
        assert len(dataset.dataframe) == 4
        assert dataset.metadata['row_count'] == 4
        assert dataset.metadata['column_count'] == 5

    def test_dataset_validity(self):
        """필수 표준 컬럼이 있으면 유효하다"""
        valid = Dataset(
            name="Valid",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=_de_dataframe(),
        )
        assert valid.is_valid is True

        invalid = Dataset(
            name="Invalid",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=pd.DataFrame({'gene_id': ['A'], 'log2fc': [1.0]}),
        )
        assert invalid.is_valid is False

    def test_get_filtered_data(self):
        """adj_pvalue / |log2fc| 기준 필터링 테스트"""
        dataset = Dataset(
            name="Test",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=_de_dataframe(),
        )

        filtered = dataset.get_filtered_data(adj_pvalue_max=0.05, log2fc_min=1.0)

        # BRCA1(2.5), TP53(-1.8), EGFR(1.2) 통과 / MYC(0.5) 탈락
        assert len(filtered) == 3
        assert set(filtered['gene_id']) == {'BRCA1', 'TP53', 'EGFR'}

    def test_get_genes(self):
        """유전자 목록 추출 테스트"""
        dataset = Dataset(
            name="Test",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=_de_dataframe(),
        )

        genes = dataset.get_genes()
        assert len(genes) == 4
        assert 'BRCA1' in genes

    def test_get_summary(self):
        """요약 통계 테스트"""
        dataset = Dataset(
            name="Test",
            dataset_type=DatasetType.DIFFERENTIAL_EXPRESSION,
            dataframe=_de_dataframe(),
        )

        summary = dataset.get_summary()
        assert summary['total_genes'] == 4
        assert summary['significant_genes'] == 3
        assert summary['upregulated'] == 2
        assert summary['downregulated'] == 1


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
