"""
Standard Column Names for RNA-Seq Data

모든 데이터셋에서 사용되는 표준 컬럼명을 정의합니다.
데이터 로딩 시 원본 컬럼명을 이 표준명으로 변환하여 사용합니다.
"""


class StandardColumns:
    """표준 컬럼명 정의 클래스"""
    
    # === Differential Expression 컬럼 ===
    
    # 필수 컬럼
    GENE_ID = 'gene_id'          # 유전자 식별자 (ENSEMBL, ENTREZ 등)
    SYMBOL = 'symbol'             # 유전자 심볼 (사람이 읽을 수 있는 이름)
    LOG2FC = 'log2fc'             # Log2 Fold Change
    ADJ_PVALUE = 'adj_pvalue'     # Adjusted P-value (FDR)
    
    # 추가 통계 컬럼
    PVALUE = 'pvalue'             # Raw P-value
    BASE_MEAN = 'base_mean'       # 평균 발현량
    LFCSE = 'lfcse'               # Log2FC Standard Error
    STAT = 'stat'                 # Test Statistic
    
    # === GO/KEGG Analysis 컬럼 ===
    
    # 필수 컬럼
    TERM_ID = 'term_id'           # GO ID 또는 KEGG ID (예: GO:0006955, hsa04110)
    DESCRIPTION = 'description'   # GO Term 또는 KEGG Pathway 설명
    GENE_COUNT = 'gene_count'     # 유전자 개수
    FDR = 'fdr'                   # FDR (adjusted p-value)
    
    # 추가 컬럼
    PVALUE_GO = 'pvalue'          # Raw p-value
    GENE_SYMBOLS = 'gene_symbols' # 유전자 심볼 리스트 (delimiter: /)
    GENE_RATIO = 'gene_ratio'     # Gene Ratio (예: 10/100)
    BG_RATIO = 'bg_ratio'         # Background Ratio
    QVALUE = 'qvalue'             # Q-value
    DIRECTION = 'direction'       # UP/DOWN/TOTAL
    ONTOLOGY = 'ontology'         # BP/CC/MF/KEGG
    GENE_SET = 'gene_set'         # Gene Set 이름
    FOLD_ENRICHMENT = 'fold_enrichment'  # Fold Enrichment
    
    # Clustering Analysis 컬럼
    CLUSTER_ID = 'cluster_id'     # Cluster ID (숫자, 'Small', 'Singleton', 또는 빈 값)
    
    # 하위 호환성을 위한 별칭 (deprecated)
    GO_TERM = DESCRIPTION         # GO term 설명
    GO_GENE_COUNT = GENE_COUNT    # 유전자 개수
    GO_FDR = FDR                  # FDR (adjusted p-value)
    GO_TERM_ID = TERM_ID          # GO term ID (예: GO:0006955)
    GO_PVALUE = PVALUE_GO         # Raw p-value
    GO_GENES = GENE_SYMBOLS       # 유전자 리스트
    
    @classmethod
    def get_de_required(cls) -> list[str]:
        """
        Differential Expression 분석에 필수인 컬럼 반환
        
        Returns:
            필수 컬럼명 리스트
        """
        return [cls.GENE_ID, cls.SYMBOL, cls.LOG2FC, cls.ADJ_PVALUE]
    
    @classmethod
    def get_de_basic(cls) -> list[str]:
        """
        Differential Expression 기본 컬럼 (gene_id + symbol + base_mean)
        
        Returns:
            기본 컬럼명 리스트
        """
        return [cls.GENE_ID, cls.SYMBOL, cls.BASE_MEAN]
    
    @classmethod
    def get_de_statistics(cls) -> list[str]:
        """
        Differential Expression 통계 컬럼 (log2fc, pvalue, adj_pvalue 등)
        
        Returns:
            통계 컬럼명 리스트
        """
        return [cls.LOG2FC, cls.PVALUE, cls.ADJ_PVALUE, cls.LFCSE, cls.STAT]
    
    @classmethod
    def get_de_all(cls) -> list[str]:
        """
        Differential Expression 모든 표준 컬럼
        
        Returns:
            모든 표준 컬럼명 리스트
        """
        return [
            cls.GENE_ID,
            cls.SYMBOL,
            cls.BASE_MEAN,
            cls.LOG2FC,
            cls.LFCSE,
            cls.STAT,
            cls.PVALUE,
            cls.ADJ_PVALUE,
        ]
    
    @classmethod
    def get_go_required(cls) -> list[str]:
        """
        GO/KEGG Analysis에 필수인 컬럼 반환
        
        Returns:
            필수 컬럼명 리스트
        """
        return [cls.TERM_ID, cls.DESCRIPTION, cls.GENE_COUNT, cls.FDR]
    
    @classmethod
    def get_go_all(cls) -> list[str]:
        """
        GO/KEGG Analysis 모든 표준 컬럼
        
        Returns:
            모든 표준 컬럼명 리스트
        """
        return [
            cls.TERM_ID,
            cls.DESCRIPTION,
            cls.GENE_COUNT,
            cls.PVALUE_GO,
            cls.FDR,
            cls.QVALUE,
            cls.GENE_SYMBOLS,
            cls.GENE_RATIO,
            cls.BG_RATIO,
            cls.DIRECTION,
            cls.ONTOLOGY,
            cls.GENE_SET,
            cls.CLUSTER_ID,
        ]
    
    @classmethod
    def is_statistics_column(cls, column_name: str) -> bool:
        """
        주어진 컬럼이 통계 컬럼인지 확인
        
        Args:
            column_name: 확인할 컬럼명
            
        Returns:
            통계 컬럼이면 True
        """
        stats_columns = {
            cls.LOG2FC, cls.PVALUE, cls.ADJ_PVALUE, 
            cls.LFCSE, cls.STAT
        }
        return column_name in stats_columns
    
    @classmethod
    def get_display_name(cls, column_name: str) -> str:
        """
        표준 컬럼명을 사용자 친화적인 표시명으로 변환
        
        Args:
            column_name: 표준 컬럼명
            
        Returns:
            표시용 컬럼명
        """
        display_names = {
            cls.GENE_ID: 'Gene ID',
            cls.LOG2FC: 'Log2 Fold Change',
            cls.PVALUE: 'P-value',
            cls.ADJ_PVALUE: 'Adjusted P-value',
            cls.BASE_MEAN: 'Base Mean',
            cls.LFCSE: 'LFC Std Error',
            cls.STAT: 'Statistic',
            cls.GO_TERM: 'GO Term',
            cls.GO_TERM_ID: 'GO ID',
            cls.GO_GENE_COUNT: 'Gene Count',
            cls.GO_FDR: 'FDR',
            cls.GO_PVALUE: 'P-value',
            cls.GO_GENES: 'Genes',
        }
        return display_names.get(column_name, column_name)
