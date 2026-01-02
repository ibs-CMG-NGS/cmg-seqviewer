"""
Example usage of RNA-Seq Data Analyzer
"""

from pathlib import Path
from models.data_models import Dataset, DatasetType, FilterCriteria
from utils.data_loader import DataLoader
from utils.statistics import StatisticalAnalyzer


def example_load_and_filter():
    """데이터 로드 및 필터링 예제"""
    
    # 1. 데이터 로더 생성
    loader = DataLoader()
    
    # 2. Excel 파일 로드
    file_path = Path("sample_data/differential_expression.xlsx")
    dataset = loader.load_from_excel(file_path, dataset_name="My Experiment")
    
    print(f"Loaded dataset: {dataset.name}")
    print(f"Type: {dataset.dataset_type.value}")
    print(f"Rows: {len(dataset.dataframe)}")
    print(f"Columns: {list(dataset.dataframe.columns)}")
    
    # 3. 필터링
    criteria = FilterCriteria(
        adj_pvalue_max=0.05,
        log2fc_min=1.0
    )
    
    filtered_df = dataset.get_filtered_data(**criteria.to_dict())
    print(f"\nFiltered results: {len(filtered_df)} genes")
    print(filtered_df.head())


def example_statistical_analysis():
    """통계 분석 예제"""
    
    # 1. 데이터셋 로드
    loader = DataLoader()
    dataset = loader.load_from_excel(
        Path("sample_data/differential_expression.xlsx")
    )
    
    # 2. 관심 유전자 리스트
    gene_list = ['BRCA1', 'TP53', 'EGFR', 'MYC', 'KRAS']
    
    # 3. Fisher's Exact Test
    analyzer = StatisticalAnalyzer()
    result = analyzer.fisher_exact_test(gene_list, dataset)
    
    print("Fisher's Exact Test Results:")
    print(f"P-value: {result['pvalue']:.4e}")
    print(f"Odds Ratio: {result['odds_ratio']:.2f}")
    print(f"Significant: {result['significant']}")
    
    # 4. GSEA Lite
    gsea_result = analyzer.gsea_lite(gene_list, dataset)
    
    print("\nGSEA Lite Results:")
    print(f"Mean log2FC: {gsea_result['mean_log2fc']:.2f}")
    print(f"Enrichment direction: {gsea_result['enrichment_direction']}")


def example_compare_datasets():
    """다중 데이터셋 비교 예제"""
    
    # 1. 여러 데이터셋 로드
    loader = DataLoader()
    
    dataset1 = loader.load_from_excel(
        Path("sample_data/experiment1.xlsx"),
        dataset_name="Experiment 1"
    )
    
    dataset2 = loader.load_from_excel(
        Path("sample_data/experiment2.xlsx"),
        dataset_name="Experiment 2"
    )
    
    # 2. 비교 분석
    analyzer = StatisticalAnalyzer()
    comparison = analyzer.compare_datasets([dataset1, dataset2])
    
    print("Comparison Results:")
    print(f"Common genes: {len(comparison.common_genes)}")
    print(f"Unique to {dataset1.name}: {len(comparison.unique_genes[dataset1.name])}")
    print(f"Unique to {dataset2.name}: {len(comparison.unique_genes[dataset2.name])}")
    
    # 3. 비교 테이블 출력
    if comparison.comparison_table is not None:
        print("\nComparison Table (first 5 rows):")
        print(comparison.comparison_table.head())


if __name__ == "__main__":
    print("=" * 80)
    print("RNA-Seq Data Analyzer - Usage Examples")
    print("=" * 80)
    
    print("\n1. Load and Filter Example")
    print("-" * 80)
    try:
        example_load_and_filter()
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n2. Statistical Analysis Example")
    print("-" * 80)
    try:
        example_statistical_analysis()
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n3. Compare Datasets Example")
    print("-" * 80)
    try:
        example_compare_datasets()
    except Exception as e:
        print(f"Error: {e}")
