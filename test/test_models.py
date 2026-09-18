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

        # 절대 log2fc >= 1.0 & padj <= 0.05 → BRCA1(2.5/0.01), TP53(1.8/0.02), EGFR(1.2/0.03)
        # MYC(0.5/0.10)는 padj 초과로 제외 — 산술상 3행 (기대값 수정, plan 실행 중 drift 정정)
        assert len(filtered) == 3
        assert set(filtered['gene_id']) == {'BRCA1', 'TP53', 'EGFR'}
    
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


# --------------------------------------------------------------------------
# Gene List 필터 순서 보존 (사용자 입력 순서 = 의도된 동작, 히트맵 등 시각화 정합)
# --------------------------------------------------------------------------

class TestGeneListOrderPreservation:
    def _presenter(self, df, dtype):
        from types import SimpleNamespace
        from models.data_models import DatasetType
        from presenters.main_presenter import MainPresenter
        import logging
        p = MainPresenter.__new__(MainPresenter)
        p.current_dataset = SimpleNamespace(dataset_type=dtype, dataframe=df)
        p.logger = logging.getLogger("t")
        return p

    def test_gene_list_filter_keeps_input_order_and_rank(self):
        """필터: 입력 순서 유지 + _gene_list_rank 신호열 보존 (DE/MG/ATAC 공통 경로)."""
        import pandas as pd
        from models.data_models import DatasetType
        df = pd.DataFrame({
            "gene_symbol": ["Zz1", "Aa2", "Mm3", "Bb4"],
            "padj": [0.01, 0.02, 0.03, 0.04],
            "s1": [1., 2., 3., 4.], "s2": [2., 3., 4., 5.], "s3": [3., 4., 5., 6.],
        })
        p = self._presenter(df, DatasetType.MULTI_GROUP)
        out = p._filter_by_gene_list(["Mm3", "Zz1", "Bb4"])
        assert list(out["gene_symbol"]) == ["Mm3", "Zz1", "Bb4"]
        assert list(out["_gene_list_rank"]) == [0, 1, 2]

    def test_multi_group_heatmap_respects_gene_list_order(self, qtbot):
        """멀티그룹 히트맵: rank 프레임이면 stat/padj 재정렬 생략(입력 순서)."""
        import pandas as pd
        from types import SimpleNamespace
        from gui.multi_group_heatmap_dialog import MultiGroupHeatmapDialog
        w = MultiGroupHeatmapDialog.__new__(MultiGroupHeatmapDialog)
        w.df = pd.DataFrame({
            "gene_symbol": ["U1", "U2", "U3"], "_gene_list_rank": [0, 1, 2],
            "stat": [100., 5., 50.], "padj": [.01, .02, .03],
            "s1": [1., 2., 3.], "s2": [2., 3., 4.], "s3": [3., 4., 5.],
        })
        w.padj_spin = SimpleNamespace(value=lambda: 1.0)
        w.basemean_spin = SimpleNamespace(value=lambda: 0.0)
        w.top_n_spin = SimpleNamespace(value=lambda: 2)
        w._last_rank_method = None
        out = w._get_filtered_data()
        assert list(out["gene_symbol"]) == ["U1", "U2"]
        assert w._last_rank_method == "gene list order (input order)"

    def test_multi_group_heatmap_stat_ranking_without_rank(self, qtbot):
        """rank열 없으면 기존 |stat| 랭킹 유지 (회귀 방지)."""
        import pandas as pd
        from types import SimpleNamespace
        from gui.multi_group_heatmap_dialog import MultiGroupHeatmapDialog
        w = MultiGroupHeatmapDialog.__new__(MultiGroupHeatmapDialog)
        w.df = pd.DataFrame({
            "gene_symbol": ["A", "B", "C"], "stat": [100., 5., 50.], "padj": [.01, .02, .03],
            "s1": [1., 2., 3.], "s2": [2., 3., 4.], "s3": [3., 4., 5.],
        })
        w.padj_spin = SimpleNamespace(value=lambda: 1.0)
        w.basemean_spin = SimpleNamespace(value=lambda: 0.0)
        w.top_n_spin = SimpleNamespace(value=lambda: 3)
        w._last_rank_method = None
        out = w._get_filtered_data()
        assert list(out["gene_symbol"]) == ["A", "C", "B"]
        assert w._last_rank_method == "|stat| (LRT test statistic)"

    def test_pairwise_heatmap_input_order(self):
        """pairwise heatmap: sorting='input' → DataFrame 행 순서 그대로 표시."""
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.figure import Figure
        from plots.heatmap import render_heatmap
        df = pd.DataFrame({
            "gene_id": ["u3", "u1", "u2"], "_gene_list_rank": [2, 0, 1],
            "s1": [1., 4., 2.], "s2": [2., 5., 3.], "s3": [3., 6., 4.],
            "padj": [.01, .02, .03],
        })
        _, labels = render_heatmap(Figure(), df, {"n_genes": 3, "sorting": "input",
                                                  "normalization": "none"})
        assert labels == ["u1", "u2", "u3"]

    def test_pairwise_heatmap_rank_frame_default_keeps_user_order(self):
        """rank 프레임 + 기본 파라미터 → top-N 선택(padj) 후 사용자 순서로 표시."""
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.figure import Figure
        from plots.heatmap import render_heatmap
        df = pd.DataFrame({
            "gene_id": ["u3", "u1", "u2"], "_gene_list_rank": [2, 0, 1],
            "s1": [1., 4., 2.], "s2": [2., 5., 3.], "s3": [3., 6., 4.],
            "padj": [.01, .02, .03],
        })
        _, labels = render_heatmap(Figure(), df, {"n_genes": 2, "normalization": "none"})
        assert labels == ["u3", "u1"]

    def test_pairwise_heatmap_no_rank_default_unchanged(self):
        """rank열 없는 일반 프레임 → 기존 padj 오름차순 동작 유지 (회귀 방지)."""
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.figure import Figure
        from plots.heatmap import render_heatmap
        df = pd.DataFrame({
            "gene_id": ["u3", "u1", "u2"],
            "s1": [1., 4., 2.], "s2": [2., 5., 3.], "s3": [3., 6., 4.],
            "padj": [.01, .02, .03],
        })
        _, labels = render_heatmap(Figure(), df, {"n_genes": 3, "normalization": "none"})
        assert labels == ["u3", "u1", "u2"]

    def test_heatmap_widget_auto_input_order(self, qtbot):
        """HeatmapWidget: rank 프레임이면 'Input order' 자동 기본, 명시 지정은 존중."""
        import pandas as pd
        from gui.visualization_dialog import HeatmapWidget
        df = pd.DataFrame({
            "gene_id": ["u3", "u1", "u2"], "_gene_list_rank": [2, 0, 1],
            "s1": [1., 4., 2.], "s2": [2., 5., 3.], "s3": [3., 6., 4.], "padj": [.01, .02, .03]})
        w = HeatmapWidget(df)
        qtbot.addWidget(w)
        assert w.sorting == 'input' and w.sort_combo.currentText() == "Input order"
        w2 = HeatmapWidget(df, plot_params={"sorting": "clustering"})
        qtbot.addWidget(w2)
        assert w2.sorting == 'clustering'
        df2 = df.drop(columns=["_gene_list_rank"])
        w3 = HeatmapWidget(df2)
        qtbot.addWidget(w3)
        assert w3.sorting == 'padj'
