"""
Multi-Omics Integrator

RNA-seq DE 결과와 ATAC-seq DA 결과를 nearest_gene 또는 promoter window로 JOIN하고
concordance를 계산합니다.

입력 DataFrame 컬럼(StandardColumns 기준):
  RNA-seq : symbol, log2fc, adj_pvalue, base_mean
  ATAC-seq: nearest_gene, log2fc, adj_pvalue, distance_to_tss, annotation

출력 DataFrame 컬럼 (IntegratedColumns 기준):
  symbol, rna_log2fc, rna_padj, rna_base_mean,
  peak_count, atac_log2fc_mean, atac_log2fc_max, atac_padj_min,
  concordance, regulatory_status
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

from models.standard_columns import StandardColumns
from models.multi_omics_dataset import ConcordanceCategory, IntegratedColumns

logger = logging.getLogger(__name__)


class MultiOmicsIntegrator:
    """
    RNA-seq + ATAC-seq 통합 알고리즘

    Args:
        rna_padj_cutoff:  RNA 유의성 cutoff (adj p-value)
        rna_lfc_cutoff:   RNA 유의성 cutoff (|log2FC|)
        atac_padj_cutoff: ATAC 유의성 cutoff (adj p-value)
        atac_lfc_cutoff:  ATAC 유의성 cutoff (|log2FC|)
    """

    def __init__(
        self,
        rna_padj_cutoff: float = 0.05,
        rna_lfc_cutoff: float = 1.0,
        atac_padj_cutoff: float = 0.05,
        atac_lfc_cutoff: float = 1.0,
    ):
        self.rna_padj_cutoff  = rna_padj_cutoff
        self.rna_lfc_cutoff   = rna_lfc_cutoff
        self.atac_padj_cutoff = atac_padj_cutoff
        self.atac_lfc_cutoff  = atac_lfc_cutoff

    # ------------------------------------------------------------------ #
    #  Public interface
    # ------------------------------------------------------------------ #

    def integrate_by_nearest_gene(
        self, rna_df: pd.DataFrame, atac_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        ATAC peak의 nearest_gene 컬럼 기반 JOIN.

        모든 peak이 nearest_gene으로 귀속됩니다.
        """
        atac_grouped = self._group_atac_by_gene(atac_df, gene_col=StandardColumns.NEAREST_GENE)
        return self._build_integrated(rna_df, atac_grouped)

    def integrate_by_promoter(
        self,
        rna_df: pd.DataFrame,
        atac_df: pd.DataFrame,
        tss_window: int = 2000,
    ) -> pd.DataFrame:
        """
        TSS ± tss_window(bp) 이내의 peak만 사용하는 promoter-only 통합.

        ATAC-seq 데이터에 distance_to_tss 컬럼이 있을 때 사용합니다.
        """
        col_dist = StandardColumns.DISTANCE_TO_TSS
        if col_dist not in atac_df.columns:
            logger.warning(
                "distance_to_tss column not found; falling back to nearest_gene"
            )
            return self.integrate_by_nearest_gene(rna_df, atac_df)

        promoter_df = atac_df[atac_df[col_dist].abs() <= tss_window].copy()
        if promoter_df.empty:
            logger.warning(
                f"No peaks within TSS ±{tss_window} bp; "
                "falling back to nearest_gene"
            )
            return self.integrate_by_nearest_gene(rna_df, atac_df)

        atac_grouped = self._group_atac_by_gene(promoter_df, gene_col=StandardColumns.NEAREST_GENE)
        return self._build_integrated(rna_df, atac_grouped)

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _group_atac_by_gene(
        self, atac_df: pd.DataFrame, gene_col: str
    ) -> pd.DataFrame:
        """
        ATAC peak DataFrame을 유전자 심볼로 집계합니다.

        Returns DataFrame with columns:
            nearest_gene, peak_count, atac_log2fc_mean,
            atac_log2fc_max, atac_padj_min
        """
        col_lfc  = StandardColumns.LOG2FC
        col_padj = StandardColumns.ADJ_PVALUE

        # 유전자 심볼이 없는 행 제거
        df = atac_df[atac_df[gene_col].notna() & (atac_df[gene_col] != "")].copy()

        # log2fc, adj_pvalue 컬럼이 없으면 NaN 처리
        if col_lfc not in df.columns:
            df[col_lfc] = np.nan
        if col_padj not in df.columns:
            df[col_padj] = np.nan

        grouped = (
            df.groupby(gene_col)
            .agg(
                peak_count        =(col_lfc,  "count"),
                atac_log2fc_mean  =(col_lfc,  "mean"),
                atac_log2fc_max   =(col_lfc,  lambda x: x.abs().max()),
                atac_padj_min     =(col_padj, "min"),
            )
            .reset_index()
            .rename(columns={gene_col: StandardColumns.NEAREST_GENE})
        )
        return grouped

    def _build_integrated(
        self, rna_df: pd.DataFrame, atac_grouped: pd.DataFrame
    ) -> pd.DataFrame:
        """
        RNA-seq DataFrame과 집계된 ATAC DataFrame을 outer JOIN으로 합치고
        concordance 및 regulatory_status 를 계산합니다.
        """
        # RNA 측 컬럼 선택 & 정규화
        rna = self._extract_rna_columns(rna_df)
        atac = atac_grouped.copy()
        atac = atac.rename(columns={StandardColumns.NEAREST_GENE: IntegratedColumns.GENE_SYMBOL})

        # Outer JOIN — 어느 한쪽에만 있는 유전자도 포함
        merged = pd.merge(
            rna, atac,
            on=IntegratedColumns.GENE_SYMBOL,
            how="outer",
        )

        # Concordance 분류
        merged[IntegratedColumns.CONCORDANCE] = merged.apply(
            self._classify_concordance, axis=1
        )

        # Regulatory status (간단 설명)
        merged[IntegratedColumns.REGULATORY_STATUS] = merged[IntegratedColumns.CONCORDANCE].map(
            self._regulatory_label
        )

        # 컬럼 순서 정리
        ordered_cols = [
            IntegratedColumns.GENE_SYMBOL,
            IntegratedColumns.RNA_LOG2FC,
            IntegratedColumns.RNA_PADJ,
            IntegratedColumns.RNA_BASE_MEAN,
            IntegratedColumns.PEAK_COUNT,
            IntegratedColumns.ATAC_LOG2FC_MEAN,
            IntegratedColumns.ATAC_LOG2FC_MAX,
            IntegratedColumns.ATAC_PADJ_MIN,
            IntegratedColumns.CONCORDANCE,
            IntegratedColumns.REGULATORY_STATUS,
        ]
        existing = [c for c in ordered_cols if c in merged.columns]
        merged = merged[existing]

        logger.info(
            f"Integration complete: {len(merged)} genes "
            f"({merged[IntegratedColumns.CONCORDANCE].value_counts().to_dict()})"
        )
        return merged.reset_index(drop=True)

    def _extract_rna_columns(self, rna_df: pd.DataFrame) -> pd.DataFrame:
        """RNA-seq DataFrame에서 필요한 컬럼만 추출 및 이름 변경"""
        col_sym  = StandardColumns.SYMBOL
        col_lfc  = StandardColumns.LOG2FC
        col_padj = StandardColumns.ADJ_PVALUE
        col_bm   = StandardColumns.BASE_MEAN

        rename_map = {
            col_sym:  IntegratedColumns.GENE_SYMBOL,
            col_lfc:  IntegratedColumns.RNA_LOG2FC,
            col_padj: IntegratedColumns.RNA_PADJ,
        }
        if col_bm in rna_df.columns:
            rename_map[col_bm] = IntegratedColumns.RNA_BASE_MEAN

        available = [c for c in rename_map if c in rna_df.columns]
        rna = rna_df[available].copy().rename(columns={k: rename_map[k] for k in available})

        # symbol이 없으면 gene_id fallback
        if IntegratedColumns.GENE_SYMBOL not in rna.columns:
            if StandardColumns.GENE_ID in rna_df.columns:
                rna[IntegratedColumns.GENE_SYMBOL] = rna_df[StandardColumns.GENE_ID]

        # 중복 gene symbol 제거 (padj 기준으로 가장 유의한 행 유지)
        if IntegratedColumns.RNA_PADJ in rna.columns:
            rna = (
                rna.sort_values(IntegratedColumns.RNA_PADJ)
                   .drop_duplicates(subset=[IntegratedColumns.GENE_SYMBOL], keep="first")
            )

        return rna

    def _classify_concordance(self, row: pd.Series) -> str:
        """
        단일 행에 대해 concordance 카테고리 결정.

        Logic:
          rna_sig  = rna_padj  ≤ cutoff  AND |rna_log2fc|  ≥ cutoff
          atac_sig = atac_padj_min ≤ cutoff AND |atac_log2fc_mean| ≥ cutoff
        """
        rna_lfc  = row.get(IntegratedColumns.RNA_LOG2FC,       np.nan)
        rna_padj = row.get(IntegratedColumns.RNA_PADJ,         np.nan)
        atac_lfc = row.get(IntegratedColumns.ATAC_LOG2FC_MEAN, np.nan)
        atac_padj = row.get(IntegratedColumns.ATAC_PADJ_MIN,   np.nan)

        rna_sig  = (
            pd.notna(rna_padj)  and rna_padj  <= self.rna_padj_cutoff
            and pd.notna(rna_lfc)  and abs(rna_lfc)  >= self.rna_lfc_cutoff
        )
        atac_sig = (
            pd.notna(atac_padj) and atac_padj <= self.atac_padj_cutoff
            and pd.notna(atac_lfc) and abs(atac_lfc) >= self.atac_lfc_cutoff
        )

        if not rna_sig and not atac_sig:
            return ConcordanceCategory.NOT_SIGNIFICANT

        if rna_sig and not atac_sig:
            return ConcordanceCategory.RNA_ONLY

        if atac_sig and not rna_sig:
            return ConcordanceCategory.ATAC_ONLY

        # 둘 다 유의
        rna_up  = rna_lfc  > 0
        atac_up = atac_lfc > 0

        if rna_up and atac_up:
            return ConcordanceCategory.CONCORDANT_BOTH_UP
        if not rna_up and not atac_up:
            return ConcordanceCategory.CONCORDANT_BOTH_DOWN
        if rna_up and not atac_up:
            return ConcordanceCategory.DISCORDANT_RNA_UP
        return ConcordanceCategory.DISCORDANT_RNA_DOWN

    @staticmethod
    def _regulatory_label(category: str) -> str:
        """concordance 카테고리를 사람이 읽을 수 있는 설명으로 변환"""
        labels = {
            ConcordanceCategory.CONCORDANT_BOTH_UP:   "Open chromatin supports upregulation",
            ConcordanceCategory.CONCORDANT_BOTH_DOWN:  "Closed chromatin supports downregulation",
            ConcordanceCategory.DISCORDANT_RNA_UP:     "RNA up but chromatin closed",
            ConcordanceCategory.DISCORDANT_RNA_DOWN:   "RNA down but chromatin open",
            ConcordanceCategory.RNA_ONLY:              "No significant ATAC change",
            ConcordanceCategory.ATAC_ONLY:             "No significant RNA change",
            ConcordanceCategory.NOT_SIGNIFICANT:       "Not significant",
        }
        return labels.get(category, category)
