"""Pure filtering engine shared by the GUI presenter and headless services.

No Qt imports. ``MainPresenter`` delegates its private filter helpers here so
the GUI and CLI/MCP cannot drift apart.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

import pandas as pd

from models.data_models import Dataset, DatasetType, FilterCriteria, FilterMode
from models.standard_columns import StandardColumns


class FilterEngine:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def filter(
        self, dataset: Optional[Dataset], criteria: FilterCriteria
    ) -> Optional[pd.DataFrame]:
        if dataset is None or dataset.dataframe is None:
            return None
        if criteria.mode == FilterMode.COLUMN_SUBSET:
            return self.subset_columns(dataset, criteria.subset_columns)
        if criteria.mode == FilterMode.KEYWORD:
            keyword = (criteria.search_keyword or "").strip()
            if not keyword:
                return None
            column = criteria.search_column or self.keyword_search_column(dataset)
            return self.filter_by_keyword(dataset, keyword, column)
        if criteria.mode == FilterMode.GENE_LIST:
            if criteria.term_id_list:
                return self.filter_go_by_term_ids(dataset, criteria.term_id_list)
            if criteria.gene_list:
                return self.filter_by_gene_list(dataset, criteria.gene_list)
            return None
        dataset_type = dataset.dataset_type
        if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            return self.filter_by_statistics(
                dataset,
                adj_pvalue_max=criteria.adj_pvalue_max,
                log2fc_min=criteria.log2fc_min,
                regulation_direction=criteria.regulation_direction,
            )
        if dataset_type == DatasetType.GO_ANALYSIS:
            return self.filter_by_statistics(
                dataset,
                fdr_max=criteria.fdr_max,
                ontology=criteria.ontology,
                go_direction=criteria.go_direction,
                fold_enrichment_min=getattr(criteria, "fold_enrichment_min", 0.0),
                min_gene_count=getattr(criteria, "go_min_gene_count", 0),
            )
        if dataset_type == DatasetType.MULTI_GROUP:
            return self.filter_mg_by_statistics(
                dataset,
                padj_max=criteria.mg_padj_max,
                basemean_min=criteria.mg_basemean_min,
            )
        if dataset_type == DatasetType.COMPOSITION:
            return self.filter_composition_by_statistics(
                dataset, fdr_max=criteria.fdr_max
            )
        if dataset_type == DatasetType.ATAC_SEQ:
            return self.filter_atac_by_statistics(
                dataset,
                adj_pvalue_max=criteria.adj_pvalue_max,
                log2fc_min=criteria.log2fc_min,
                regulation_direction=criteria.regulation_direction,
                atac_annotation=criteria.atac_annotation,
                atac_distance_max=criteria.atac_distance_max,
                atac_peak_width_min=criteria.atac_peak_width_min,
                atac_peak_width_max=criteria.atac_peak_width_max,
            )
        return None

    def keyword_search_column(self, dataset: Dataset) -> str:
        if dataset.dataframe is None:
            return ""
        cols = list(dataset.dataframe.columns)
        if dataset.dataset_type == DatasetType.GO_ANALYSIS:
            order = [
                StandardColumns.DESCRIPTION,
                StandardColumns.TERM_ID,
                "description",
                "term_id",
            ]
        else:
            order = [
                StandardColumns.SYMBOL,
                "symbol",
                "gene_symbol",
                "gene_name",
                StandardColumns.GENE_ID,
                "gene_id",
                StandardColumns.DESCRIPTION,
                "description",
            ]
        for col in order:
            if col in cols:
                return col
        for col in cols:
            if dataset.dataframe[col].dtype == object:
                return col
        return cols[0] if cols else ""

    def filter_by_keyword(
        self, dataset: Dataset, keyword: str, column: str
    ) -> pd.DataFrame:
        df = dataset.dataframe
        if column not in df.columns:
            return df.iloc[0:0]
        mask = (
            df[column]
            .astype(str)
            .str.contains(keyword, case=False, na=False, regex=False)
        )
        return df[mask]

    def subset_columns(self, dataset: Dataset, columns) -> pd.DataFrame:
        df = dataset.dataframe
        keep = [col for col in df.columns if col in set(columns or [])]
        return df[keep] if keep else df.iloc[:, 0:0]

    def filter_by_gene_list(
        self, dataset: Dataset, gene_list: List[str]
    ) -> pd.DataFrame:
        df = dataset.dataframe
        dataset_type = dataset.dataset_type

        if dataset_type == DatasetType.GO_ANALYSIS:
            return self.filter_go_by_gene_symbols(df, gene_list)
        if dataset_type == DatasetType.ATAC_SEQ:
            if StandardColumns.NEAREST_GENE in df.columns:
                gene_col = StandardColumns.NEAREST_GENE
            elif StandardColumns.GENE_ID in df.columns:
                gene_col = StandardColumns.GENE_ID
            else:
                self.logger.error(f"Available columns: {df.columns.tolist()}")
                raise ValueError(
                    f"ATAC-seq 데이터에 '{StandardColumns.NEAREST_GENE}' 컬럼이 없습니다. "
                    "데이터를 다시 불러오거나 컬럼 매핑을 확인하세요."
                )
        elif StandardColumns.SYMBOL in df.columns:
            gene_col = StandardColumns.SYMBOL
        elif "gene_symbol" in df.columns:
            gene_col = "gene_symbol"
        elif StandardColumns.GENE_ID in df.columns:
            gene_col = StandardColumns.GENE_ID
        else:
            self.logger.error(f"Available columns: {df.columns.tolist()}")
            raise ValueError(
                f"Neither '{StandardColumns.SYMBOL}' nor 'gene_symbol' nor "
                f"'{StandardColumns.GENE_ID}' column found in dataset"
            )

        gene_order = {g.strip().lower(): i for i, g in enumerate(gene_list)}
        mask = df[gene_col].astype(str).str.strip().str.lower().isin(gene_order)
        filtered = (
            df[mask]
            .assign(
                _gene_list_rank=df.loc[mask, gene_col]
                .astype(str)
                .str.strip()
                .str.lower()
                .map(gene_order)
            )
            .sort_values("_gene_list_rank")
            .copy()
        )
        self.logger.info(
            f"Gene list filter: {len(filtered)}/{len(df)} rows matched, "
            f"order preserved from input list"
        )
        return filtered

    def filter_go_by_gene_symbols(
        self, df: pd.DataFrame, gene_list: List[str]
    ) -> pd.DataFrame:
        gs_col = StandardColumns.GENE_SYMBOLS
        if gs_col not in df.columns:
            self.logger.error(
                f"gene_symbols column not found. Available: {df.columns.tolist()}"
            )
            raise ValueError(
                f"GO 데이터에 '{gs_col}' 컬럼이 없습니다. "
                "데이터를 다시 불러오거나 컬럼 매핑을 확인하세요."
            )

        query_set = {g.upper() for g in gene_list if g.strip()}

        def count_hits(cell_value) -> int:
            if not isinstance(cell_value, str) or not cell_value.strip():
                return 0
            symbols = {
                s.strip().upper()
                for s in re.split(r"[,;/\s]+", cell_value)
                if s.strip()
            }
            return len(symbols & query_set)

        hit_counts = df[gs_col].apply(count_hits)
        mask = hit_counts > 0
        filtered = df[mask].copy()
        filtered["_hit_count"] = hit_counts[mask]
        filtered = filtered.sort_values("_hit_count", ascending=False).drop(
            columns="_hit_count"
        )
        self.logger.info(
            f"GO gene-symbol filter: {len(filtered)}/{len(df)} terms matched "
            f"({len(query_set)} query genes)"
        )
        return filtered

    def filter_go_by_term_ids(
        self, dataset: Dataset, term_id_list: List[str]
    ) -> pd.DataFrame:
        df = dataset.dataframe
        tid_col = StandardColumns.TERM_ID
        if tid_col not in df.columns:
            self.logger.error(
                f"term_id column not found. Available: {df.columns.tolist()}"
            )
            raise ValueError(
                f"GO 데이터에 '{tid_col}' 컬럼이 없습니다. "
                "데이터를 다시 불러오거나 컬럼 매핑을 확인하세요."
            )

        id_order = {
            tid.strip().upper(): i for i, tid in enumerate(term_id_list) if tid.strip()
        }
        mask = df[tid_col].astype(str).str.strip().str.upper().isin(id_order)
        filtered = (
            df[mask]
            .assign(
                _sort_key=df.loc[mask, tid_col]
                .astype(str)
                .str.strip()
                .str.upper()
                .map(id_order)
            )
            .sort_values("_sort_key")
            .drop(columns="_sort_key")
            .copy()
        )
        self.logger.info(
            f"GO term-id filter: {len(filtered)}/{len(df)} terms matched "
            f"({len(id_order)} query IDs)"
        )
        return filtered

    def filter_by_statistics(
        self,
        dataset: Dataset,
        adj_pvalue_max: Optional[float] = None,
        log2fc_min: Optional[float] = None,
        fdr_max: Optional[float] = None,
        ontology: Optional[str] = None,
        go_direction: Optional[str] = None,
        fold_enrichment_min: Optional[float] = None,
        min_gene_count: Optional[int] = None,
        regulation_direction: str = "both",
    ) -> pd.DataFrame:
        dataset_type = dataset.dataset_type
        df = dataset.dataframe.copy()

        if dataset_type == DatasetType.DIFFERENTIAL_EXPRESSION:
            adj_pval_col = StandardColumns.ADJ_PVALUE
            log2fc_col = StandardColumns.LOG2FC
            if not all([adj_pval_col in df.columns, log2fc_col in df.columns]):
                self.logger.error(f"Available columns: {df.columns.tolist()}")
                raise ValueError(
                    f"Required columns not found: {adj_pval_col}, {log2fc_col}"
                )
            mask = (df[adj_pval_col] <= adj_pvalue_max) & (
                abs(df[log2fc_col]) >= log2fc_min
            )
            filtered = df[mask]
            if regulation_direction == "up":
                filtered = filtered[filtered[log2fc_col] > 0]
            elif regulation_direction == "down":
                filtered = filtered[filtered[log2fc_col] < 0]
            self.logger.info(
                f"Statistical filter (DE): {len(filtered)}/{len(df)} rows "
                f"(p≤{adj_pvalue_max}, |FC|≥{log2fc_min}, "
                f"dir={regulation_direction})"
            )
        elif dataset_type == DatasetType.GO_ANALYSIS:
            fdr_col = StandardColumns.FDR
            if fdr_col not in df.columns:
                self.logger.error(f"Available columns: {df.columns.tolist()}")
                raise ValueError(f"FDR column not found: {fdr_col}")
            mask = df[fdr_col] <= fdr_max
            if ontology and ontology != "All":
                ontology_col = StandardColumns.ONTOLOGY
                if ontology_col in df.columns:
                    mask = mask & (df[ontology_col].str.upper() == ontology.upper())
            if go_direction and go_direction != "All":
                gene_set_col = StandardColumns.GENE_SET
                if gene_set_col in df.columns:
                    mask = mask & (df[gene_set_col].str.upper() == go_direction.upper())
            if fold_enrichment_min and fold_enrichment_min > 0:
                fe_col = StandardColumns.FOLD_ENRICHMENT
                if fe_col in df.columns:
                    fe_vals = pd.to_numeric(df[fe_col], errors="coerce")
                    mask = mask & (fe_vals >= fold_enrichment_min)
            if min_gene_count and min_gene_count > 0:
                gc_col = StandardColumns.GENE_COUNT
                if gc_col in df.columns:
                    gc_vals = pd.to_numeric(df[gc_col], errors="coerce")
                    mask = mask & (gc_vals >= min_gene_count)
            filtered = df[mask]
            filter_desc = f"FDR≤{fdr_max}"
            if fold_enrichment_min and fold_enrichment_min > 0:
                filter_desc += f", FE≥{fold_enrichment_min}"
            if min_gene_count and min_gene_count > 0:
                filter_desc += f", Count≥{min_gene_count}"
            if ontology and ontology != "All":
                filter_desc += f", {ontology}"
            if go_direction and go_direction != "All":
                filter_desc += f", {go_direction}"
            self.logger.info(
                f"Statistical filter (GO): {len(filtered)}/{len(df)} rows "
                f"({filter_desc})"
            )
        else:
            raise ValueError(f"Cannot filter dataset type: {dataset_type.value}")
        return filtered

    def filter_mg_by_statistics(
        self, dataset: Dataset, padj_max: float, basemean_min: float
    ) -> pd.DataFrame:
        df = dataset.dataframe.copy()
        col_lower = {c.lower(): c for c in df.columns}
        padj_col = (
            col_lower.get("padj")
            or col_lower.get("adj_pvalue")
            or col_lower.get("p_adj")
        )
        basemean_col = col_lower.get("basemean") or col_lower.get("base_mean")
        if padj_col:
            df = df[df[padj_col] <= padj_max]
        if basemean_col and basemean_min > 0:
            df = df[df[basemean_col] >= basemean_min]
        self.logger.info(
            f"Multi-Group filter: {len(df)}/{len(dataset.dataframe)} rows "
            f"(padj≤{padj_max}, baseMean≥{basemean_min})"
        )
        return df

    def filter_composition_by_statistics(
        self, dataset: Dataset, fdr_max: float
    ) -> pd.DataFrame:
        df = dataset.dataframe.copy()
        col = (
            "fdr"
            if "fdr" in df.columns
            else ("pvalue" if "pvalue" in df.columns else None)
        )
        if col is not None:
            df = df[pd.to_numeric(df[col], errors="coerce") <= fdr_max]
        self.logger.info(
            f"Composition filter: {len(df)}/{len(dataset.dataframe)} rows "
            f"(fdr≤{fdr_max})"
        )
        return df

    def filter_atac_by_statistics(
        self,
        dataset: Dataset,
        adj_pvalue_max: float,
        log2fc_min: float,
        regulation_direction: str = "both",
        atac_annotation: str = "All",
        atac_distance_max: Optional[int] = None,
        atac_peak_width_min: Optional[int] = None,
        atac_peak_width_max: Optional[int] = None,
    ) -> pd.DataFrame:
        df = dataset.dataframe.copy()
        if "adj_pvalue" in df.columns:
            df = df[df["adj_pvalue"] <= adj_pvalue_max]
        if "log2fc" in df.columns:
            df = df[df["log2fc"].abs() >= log2fc_min]
            if regulation_direction == "up":
                df = df[df["log2fc"] > 0]
            elif regulation_direction == "down":
                df = df[df["log2fc"] < 0]
        if atac_annotation != "All" and "annotation" in df.columns:
            df = df[
                df["annotation"].astype(str).str.startswith(atac_annotation, na=False)
            ]
        if atac_distance_max is not None and "distance_to_tss" in df.columns:
            df = df[df["distance_to_tss"].abs() <= atac_distance_max]
        if "peak_width" in df.columns:
            if atac_peak_width_min is not None:
                df = df[df["peak_width"] >= atac_peak_width_min]
            if atac_peak_width_max is not None:
                df = df[df["peak_width"] <= atac_peak_width_max]
        self.logger.info(
            f"ATAC filter: {len(df)}/{len(dataset.dataframe)} peaks "
            f"(p≤{adj_pvalue_max}, |FC|≥{log2fc_min}, annot={atac_annotation})"
        )
        return df
