"""
Multi-Omics Dataset Model

RNA-seq DE 결과와 ATAC-seq DA 결과를 연결하는 통합 데이터셋 컨테이너입니다.
nearest_gene 컬럼 기반 JOIN으로 concordance를 계산합니다.
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

from models.data_models import Dataset, DatasetType


# concordance 카테고리 상수
class ConcordanceCategory:
    CONCORDANT_BOTH_UP   = "Concordant_Both_UP"
    CONCORDANT_BOTH_DOWN = "Concordant_Both_DOWN"
    DISCORDANT_RNA_UP    = "Discordant_RNA_UP_ATAC_DOWN"
    DISCORDANT_RNA_DOWN  = "Discordant_RNA_DOWN_ATAC_UP"
    RNA_ONLY             = "RNA_only"
    ATAC_ONLY            = "ATAC_only"
    NOT_SIGNIFICANT      = "Not_significant"

    ALL = [
        CONCORDANT_BOTH_UP,
        CONCORDANT_BOTH_DOWN,
        DISCORDANT_RNA_UP,
        DISCORDANT_RNA_DOWN,
        RNA_ONLY,
        ATAC_ONLY,
        NOT_SIGNIFICANT,
    ]

    # 시각화용 색상 맵
    COLORS = {
        CONCORDANT_BOTH_UP:   "#D73027",   # Red
        CONCORDANT_BOTH_DOWN: "#4575B4",   # Blue
        DISCORDANT_RNA_UP:    "#FC8D59",   # Orange
        DISCORDANT_RNA_DOWN:  "#91BFDB",   # Light blue
        RNA_ONLY:             "#A6D96A",   # Green
        ATAC_ONLY:            "#FDAE61",   # Yellow-orange
        NOT_SIGNIFICANT:      "#CCCCCC",   # Gray
    }


# 통합 결과 컬럼명 상수
class IntegratedColumns:
    GENE_SYMBOL        = "symbol"
    RNA_LOG2FC         = "rna_log2fc"
    RNA_PADJ           = "rna_padj"
    RNA_BASE_MEAN      = "rna_base_mean"
    PEAK_COUNT         = "peak_count"
    ATAC_LOG2FC_MEAN   = "atac_log2fc_mean"
    ATAC_LOG2FC_MAX    = "atac_log2fc_max"
    ATAC_PADJ_MIN      = "atac_padj_min"
    CONCORDANCE        = "concordance"
    REGULATORY_STATUS  = "regulatory_status"


@dataclass
class MultiOmicsDataset:
    """
    RNA-seq + ATAC-seq 통합 데이터셋

    Attributes:
        name:               데이터셋 표시 이름
        rna_dataset:        RNA-seq DE Dataset (DatasetType.DIFFERENTIAL_EXPRESSION)
        atac_dataset:       ATAC-seq DA Dataset (DatasetType.ATAC_SEQ)
        integration_method: "nearest_gene" | "promoter_only"
        tss_window:         promoter_only 모드에서 TSS 기준 upstream/downstream (bp)
        rna_padj_cutoff:    RNA sig. 기준 adjusted p-value
        rna_lfc_cutoff:     RNA sig. 기준 |log2FC|
        atac_padj_cutoff:   ATAC sig. 기준 adjusted p-value
        atac_lfc_cutoff:    ATAC sig. 기준 |log2FC|
        integrated_data:    통합 결과 DataFrame (integrate() 후 채워짐)
    """
    name: str
    rna_dataset: Dataset
    atac_dataset: Dataset
    integration_method: str = "nearest_gene"   # "nearest_gene" | "promoter_only"
    tss_window: int = 2000
    rna_padj_cutoff: float = 0.05
    rna_lfc_cutoff: float = 1.0
    atac_padj_cutoff: float = 0.05
    atac_lfc_cutoff: float = 1.0
    integrated_data: Optional[pd.DataFrame] = field(default=None)

    @property
    def is_integrated(self) -> bool:
        return self.integrated_data is not None and not self.integrated_data.empty

    def integrate(self) -> pd.DataFrame:
        """
        MultiOmicsIntegrator를 호출하여 통합 DataFrame을 계산하고
        self.integrated_data에 저장합니다.
        """
        from utils.multi_omics_integrator import MultiOmicsIntegrator
        integrator = MultiOmicsIntegrator(
            rna_padj_cutoff=self.rna_padj_cutoff,
            rna_lfc_cutoff=self.rna_lfc_cutoff,
            atac_padj_cutoff=self.atac_padj_cutoff,
            atac_lfc_cutoff=self.atac_lfc_cutoff,
        )

        rna_df  = self.rna_dataset.dataframe
        atac_df = self.atac_dataset.dataframe

        if self.integration_method == "promoter_only":
            result = integrator.integrate_by_promoter(rna_df, atac_df, self.tss_window)
        else:
            result = integrator.integrate_by_nearest_gene(rna_df, atac_df)

        self.integrated_data = result
        return result

    def get_category_counts(self) -> dict:
        """카테고리별 유전자 수 반환"""
        if not self.is_integrated:
            return {}
        col = IntegratedColumns.CONCORDANCE
        return self.integrated_data[col].value_counts().to_dict()

    def get_concordant_genes(self) -> pd.DataFrame:
        """concordant 유전자 (Both UP + Both DOWN) 반환"""
        if not self.is_integrated:
            return pd.DataFrame()
        mask = self.integrated_data[IntegratedColumns.CONCORDANCE].isin([
            ConcordanceCategory.CONCORDANT_BOTH_UP,
            ConcordanceCategory.CONCORDANT_BOTH_DOWN,
        ])
        return self.integrated_data[mask].copy()

    def to_dataset(self) -> Dataset:
        """시각화/내보내기용 Dataset 래퍼 반환"""
        return Dataset(
            name=self.name,
            dataset_type=DatasetType.MULTI_OMICS,
            dataframe=self.integrated_data,
            metadata={
                "integration_method": self.integration_method,
                "rna_dataset": self.rna_dataset.name,
                "atac_dataset": self.atac_dataset.name,
                "tss_window": self.tss_window,
            },
        )
