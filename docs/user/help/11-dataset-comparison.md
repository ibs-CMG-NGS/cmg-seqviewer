# 11. Dataset Comparison

## 11.1 Comparison Panel

Located in the left panel below the Filter Panel:

- **Select Datasets:** Choose 2 or more datasets to compare

- **Selection helpers:** "Select All" and "Clear Selection" buttons

- **Comparison Type:**

 - **Gene List Filtering:** Compare gene lists only

 - **Statistics Filtering:** Include log2FC and Padj values

- **Options (mutually exclusive):**

 - **Show common genes only (intersection):** Genes in ALL datasets

 - **Include unique genes (union):** Genes in ANY dataset (default)

## 11.2 Running Comparisons

1. Load 2 or more datasets

2. Select datasets in the Comparison Panel

3. Choose comparison type

4. Select intersection or union option

5. Click **Start Comparison**

6. Results appear in a new tab:

## 11.3 Comparison Results

The Statistics tab includes:

7. **gene_id, symbol:** Gene identifiers

8. **Status:** Common, Unique_Dataset1, etc.

9. **Found_in:** Comma-separated list of datasets

10. **Dataset columns:** For each dataset:

 - Dataset_log2FC - fold change values

 - Dataset_padj - adjusted p-values

## 11.4 Venn Diagram

Visualize overlap between 2-3 datasets:

### From Loaded Datasets:

1. Load 2 or 3 datasets

2. Select **Visualization → Venn Diagram**

3. Choose datasets to compare

4. Set statistical filters (optional):

 - Minimum |log2FC|

 - Maximum Padj

5. View overlapping and unique genes in each region

### From Comparison Sheet:

1. Run **Analysis →Compare Datasets**

2. Switch to "Comparison: Statistics" tab

3. Select **Visualization →Venn Diagram**

4. The tool automatically detects it's a comparison sheet

5. Apply statistical filters if needed

## 11.5 Dot Plot for Comparisons

Specialized visualization for comparison results:

1. Open a Comparison tab (Statistics or Gene List)

2. Select **Visualization →Dot Plot**

3. View all datasets simultaneously with:

 - Dot size = significance (Padj)

 - Dot color = fold change (log2FC)

 - Optional gene clustering for pattern discovery

## 11.6 Meta Volcano Plot

Visualizes the meta-analysis columns produced by a
 **Statistics Filtering** comparison (2+ datasets, Fisher/Stouffer combined
 p-values) as a volcano-style plot of overall reproducible signal.

1. Run **Compare → Statistics Filtering** across 2 or more datasets
 so the *"Comparison: Statistics"* sheet contains the meta
 columns (`meta_pvalue_fisher`, `meta_log2fc_mean`,
 `meta_direction`, `meta_found_in`, …)

2. With that sheet active, go to **Visualization →
 🧩 Cross-Dataset Comparison → 🌋 Meta Volcano Plot (Comparison sheet)**

3. **X axis:** choose the effect-size source — pooled log2FC
 (random-effects), mean log2FC, or mean log2 fold-enrichment

4. **Y axis:** −log₁₀ of the chosen meta p-value source
 (Fisher, Fisher FDR, Stouffer, or Random-effects)

5. **meta p ≤** and **|mean log2FC| ≥** thresholds define
 significance; a minimum-datasets-found-in cutoff further requires a gene
 to appear in at least *k* of the compared datasets

6. Genes with a consistent direction across datasets
 (**concordant**) are colored up (red) / down (blue); genes where
 datasets disagree on direction (**discordant**) are shown in gray —
 this highlights which hits are reproducible versus dataset-specific

7. Hover a point for its gene name and underlying statistics

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
