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

    # === ATAC-seq 전용 컬럼 ===

    PEAK_ID = 'peak_id'                   # Peak 식별자 (예: Interval_40044)
    CHROMOSOME = 'chromosome'             # 염색체 (예: chr1, 1)
    PEAK_START = 'peak_start'             # Peak 시작 위치 (bp)
    PEAK_END = 'peak_end'                 # Peak 끝 위치 (bp)
    NEAREST_GENE = 'nearest_gene'         # 가장 가까운 유전자 심볼
    ANNOTATION = 'annotation'             # Genomic annotation (Promoter / Enhancer / Intergenic 등)
    DISTANCE_TO_TSS = 'distance_to_tss'   # TSS까지 거리 (bp, 음수=upstream)
    PEAK_WIDTH = 'peak_width'             # Peak 너비 (peak_end - peak_start, 계산 컬럼)
    # base_mean, log2fc, lfcse, pvalue, adj_pvalue, direction → 기존 DE 컬럼 재사용

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
    def get_atac_required(cls) -> list[str]:
        """ATAC-seq DA 분석에 최소 필수인 컬럼"""
        return [cls.PEAK_ID, cls.LOG2FC, cls.ADJ_PVALUE]

    @classmethod
    def get_atac_basic(cls) -> list[str]:
        """ATAC basic 표시 수준: 위치 + 대표 유전자"""
        return [cls.PEAK_ID, cls.CHROMOSOME, cls.PEAK_START, cls.PEAK_END, cls.NEAREST_GENE]

    @classmethod
    def get_atac_stat(cls) -> list[str]:
        """ATAC stat 표시 수준: basic + 통계 컬럼"""
        return cls.get_atac_basic() + [cls.BASE_MEAN, cls.LOG2FC, cls.PVALUE, cls.ADJ_PVALUE]

    @classmethod
    def get_atac_all(cls) -> list[str]:
        """ATAC full 표시 수준: stat + 어노테이션 컬럼"""
        return cls.get_atac_stat() + [cls.LFCSE, cls.ANNOTATION, cls.DISTANCE_TO_TSS, cls.GENE_ID, cls.PEAK_WIDTH]

    # === chromVAR Differential TF Activity 컬럼 ===

    CHROMVAR_MOTIF_ID    = 'chromvar_motif_id'    # JASPAR ID (예: MA0006.1)
    CHROMVAR_TF_NAME     = 'chromvar_tf_name'     # TF 이름 (예: Ahr::Arnt)
    CHROMVAR_MEAN_COMPARE = 'chromvar_mean_compare'  # compare 조건 평균 z-score
    CHROMVAR_MEAN_BASE   = 'chromvar_mean_base'   # base(Control) 평균 z-score
    CHROMVAR_DELTA       = 'chromvar_delta'       # z-score 차이 (compare - base)
    CHROMVAR_PVALUE      = 'chromvar_pvalue'      # raw p-value
    CHROMVAR_PADJ        = 'chromvar_padj'        # adjusted p-value

    @classmethod
    def get_chromvar_required(cls) -> list[str]:
        return [cls.CHROMVAR_MOTIF_ID, cls.CHROMVAR_DELTA, cls.CHROMVAR_PADJ]

    @classmethod
    def get_chromvar_all(cls) -> list[str]:
        return [
            cls.CHROMVAR_MOTIF_ID, cls.CHROMVAR_TF_NAME,
            cls.CHROMVAR_MEAN_COMPARE, cls.CHROMVAR_MEAN_BASE,
            cls.CHROMVAR_DELTA, cls.CHROMVAR_PVALUE, cls.CHROMVAR_PADJ,
        ]

    # === TF Footprinting 컬럼 (TOBIAS BINDetect) ===

    FOOTPRINT_MOTIF_NAME = 'fp_motif_name'   # TF 이름
    FOOTPRINT_MOTIF_ID   = 'fp_motif_id'     # Motif ID (예: MA0002.1_RUNX1)
    COND1_SCORE          = 'cond1_score'     # cond1 mean footprint score
    COND2_SCORE          = 'cond2_score'     # cond2 mean footprint score
    COND1_BOUND          = 'cond1_bound'     # cond1 bound site 수
    COND2_BOUND          = 'cond2_bound'     # cond2 bound site 수
    FOOTPRINT_CHANGE     = 'footprint_change'   # cond1 - cond2 change score
    FOOTPRINT_PVALUE     = 'footprint_pvalue'   # 유의성 p-value
    COND1_NAME           = 'cond1_name'     # 메타데이터: cond1 이름
    COND2_NAME           = 'cond2_name'     # 메타데이터: cond2 이름

    @classmethod
    def get_footprint_required(cls) -> list[str]:
        return [cls.FOOTPRINT_MOTIF_NAME, cls.COND1_SCORE, cls.COND2_SCORE]

    @classmethod
    def get_footprint_all(cls) -> list[str]:
        return [
            cls.FOOTPRINT_MOTIF_NAME, cls.FOOTPRINT_MOTIF_ID,
            cls.COND1_SCORE, cls.COND2_SCORE,
            cls.COND1_BOUND, cls.COND2_BOUND,
            cls.FOOTPRINT_CHANGE, cls.FOOTPRINT_PVALUE,
        ]

    # === TF Motif Enrichment 컬럼 (HOMER / MEME-Suite AME) ===

    MOTIF_NAME = 'motif_name'           # TF 이름 (예: IRF1, RUNX1)
    MOTIF_ID = 'motif_id'               # 데이터베이스 ID (예: MA0002.1)
    CONSENSUS = 'consensus'             # 컨센서스 서열 (예: TGYGGT)
    MOTIF_PVALUE = 'motif_pvalue'       # enrichment p-value
    MOTIF_QVALUE = 'motif_qvalue'       # FDR-adjusted p-value
    MOTIF_LOG_PVALUE = 'log_pvalue'     # log10(p-value) — HOMER 제공
    TARGET_PCT = 'target_pct'           # foreground 내 발견 비율 (%)
    BG_PCT = 'bg_pct'                   # background 내 발견 비율 (%)
    TARGET_COUNT = 'target_count'       # foreground에서 발견된 peak 수
    BG_COUNT = 'bg_count'               # background에서 발견된 peak 수

    @classmethod
    def get_motif_required(cls) -> list[str]:
        """Motif enrichment 분석에 필수 컬럼"""
        return [cls.MOTIF_NAME, cls.MOTIF_PVALUE]

    @classmethod
    def get_motif_all(cls) -> list[str]:
        return [
            cls.MOTIF_NAME, cls.MOTIF_ID, cls.CONSENSUS,
            cls.MOTIF_PVALUE, cls.MOTIF_QVALUE, cls.MOTIF_LOG_PVALUE,
            cls.TARGET_PCT, cls.BG_PCT, cls.TARGET_COUNT, cls.BG_COUNT,
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
            cls.SYMBOL: 'Symbol',
            cls.LOG2FC: 'Log2 Fold Change',
            cls.PVALUE: 'P-value',
            cls.ADJ_PVALUE: 'Adjusted P-value',
            cls.BASE_MEAN: 'Base Mean',
            cls.LFCSE: 'LFC Std Error',
            cls.STAT: 'Statistic',
            cls.DIRECTION: 'Direction',
            cls.GO_TERM: 'GO Term',
            cls.GO_TERM_ID: 'GO ID',
            cls.GO_GENE_COUNT: 'Gene Count',
            cls.GO_FDR: 'FDR',
            cls.GO_PVALUE: 'P-value',
            cls.GO_GENES: 'Genes',
            # ATAC-seq
            cls.PEAK_ID: 'Peak ID',
            cls.CHROMOSOME: 'Chr',
            cls.PEAK_START: 'Start',
            cls.PEAK_END: 'End',
            cls.NEAREST_GENE: 'Nearest Gene',
            cls.ANNOTATION: 'Annotation',
            cls.DISTANCE_TO_TSS: 'Distance to TSS',
            cls.PEAK_WIDTH: 'Peak Width (bp)',
            # Motif enrichment
            cls.MOTIF_NAME: 'TF Name',
            cls.MOTIF_ID: 'Motif ID',
            cls.CONSENSUS: 'Consensus',
            cls.MOTIF_PVALUE: 'P-value',
            cls.MOTIF_QVALUE: 'Q-value',
            cls.TARGET_PCT: 'Target %',
            cls.BG_PCT: 'Background %',
        }
        return display_names.get(column_name, column_name)
