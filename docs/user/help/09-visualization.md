# 9. Visualization

The **Visualization** menu is organized into groups. General single-dataset
 plots (Volcano, P-adj Histogram, Heatmap, PCA, Gene Expression Bar) sit at the top;
 the rest are grouped into submenus:

- **🧬 GO/KEGG Enrichment** — Dot Plot, Bar Chart, Cluster Dot Plot

- **🔓 ATAC-seq** — Genomic Distribution, TSS Distance, MA Plot,
 TF Motif, TF Footprint, chromVAR (enabled when an ATAC tab is active)

- **🧩 Cross-Dataset Comparison** — plots that combine
 *multiple* datasets (see below)

- **🔗 RNA-ATAC Integration** — the former “Multi-Omics” plots
 (Quadrant, Concordance Heatmap/Bar, Integrated Volcano)

## 9.1 Volcano Plot

Visualize differential expression with log2FC vs. -log10(padj):

- Select **Visualization → Volcano Plot** (or **Ctrl+V**)

- Hover over points to see gene details (tooltip auto-adjusts to stay visible)

- Customize plot with the left panel settings:

 - Adjust log2FC and padj thresholds

 - Change dot colors for up/down/non-significant genes

 - Adjust dot size and axis ranges

 - Customize plot title, axis labels

 - Toggle legend on/off

 - Adjust figure size (width/height)

- All settings are saved between sessions

- Use matplotlib toolbar to zoom, pan, and save images

## 9.2 Expression Heatmap

Display gene expression patterns across samples:

- Select **Visualization → Heatmap**

- Configure settings:

 - **Number of genes:** Top N genes to display (10-500)

 - **Normalization:** Z-score, Min-Max (0-1), Log2 Transform, or None

 - **Gene sorting:**

 - Padj (ascending) - most significant first

 - Log2FC (absolute descending) - largest changes first

 - Hierarchical Clustering - group similar patterns

 - **Colormap:** RdBu_r, viridis, plasma, coolwarm, seismic

 - **Colorbar range:** Set min/max values for color scale

 - **Transpose:** Swap genes (rows) and samples (columns)

- Hover over cells to see gene name, sample name, and expression value

- Tooltips always stay visible (auto-positioning)

## 9.3 Dot Plot

Specialized visualization for dataset comparison results:

- Available only on **Comparison: Statistics** or **Comparison: Gene List** tabs

- Select **Visualization → Dot Plot**

- Features:

 - **Dot size:** Represents significance level (Padj thresholds)

 - **Dot color:** Represents log2 fold change (colormap)

 - **Gene clustering:** Option to reorder genes by similarity

 - **Transpose:** Swap datasets and genes axes

 - **Customizable:** Colormap, colorbar range, labels, legend

- Datasets are automatically spaced for optimal readability

- Settings persist across sessions

## 9.4 P-adj Histogram

View distribution of adjusted p-values:

- Select **Visualization → P-adj Histogram**

- Choose between original p-values or adjusted p-values

- Adjust number of bins (10-200)

- Helps assess data quality and significance thresholds

## 9.5 Gene Expression Bar + Scatter (Grouped)

Compare per-gene expression across sample groups with a grouped bar (mean)
 plus individual replicate points. Best used on a **Filtered** sheet so only a
 small, readable set of genes is shown.

- Select **Visualization → 📊 Gene Expression Bar+Scatter (Grouped)**
 while a DE or Multi-Group tab is active

- **Groups are auto-detected** from (in order): dataset metadata →
 the dataset name (*"A vs B"*) → sample-column name prefixes — so
 balanced 3:3 / 4:4 designs are recognized on open

- **Sample Groups (editable):** reassign any sample to a different group,
 merge groups, or leave a group name empty to exclude it; click **Apply Groups**

- **Group Colors:** pick a custom color per group

- **Significance stars:** compares each group to a chosen **Reference group**
 (Welch t-test or Mann-Whitney U) — `* ≤.05, ** ≤.01, *** ≤.001, **** ≤.0001, ns`

- **Controls:** max genes, sort (Original input order / Symbol / Mean / |log2FC|),
 error bars (SEM / SD / None), show/hide points, log-scale Y

- **Values:** raw counts by default; supports **3+ groups** including Multi-Group datasets

- **Export:** figure (PNG / PDF / SVG / TIFF, 300 dpi) and per-group
 mean / SD / SEM / n + p-value table (CSV / Excel)

## 9.6 Cross-Dataset Comparison (Multiple Datasets)

The **Visualization → 🧩 Cross-Dataset Comparison** submenu groups every
 plot that aggregates *several* loaded datasets at once. You do **not** need to
 pre-build filtered tabs — when you pick one of these, a **selection popup**
 lists the eligible datasets; check the ones to include (2 or more) and the chart
 computes directly from the raw data.

- **⚫ Dot Plot / ⭕ Venn Diagram (Comparison sheet)** — driven by a
 *Comparison* result sheet (see section 10)

- **🔗 DA Peak Overlap (ATAC-seq)** — peak-ID overlap across ATAC
 datasets: Venn (2–3) or UpSet (4+)

- **📊 DE/DA Count Summary (stacked)** — see below

- **🧬 Genomic Annotation Comparison (ATAC-seq)** — see below

### DE/DA Count Summary

Stacked bar of significant **up** vs **down** counts per dataset — a
 quick "how many DEGs / DA-peaks in each condition" summary across experiments.

- Works for DE and ATAC (DA) datasets (both use `log2fc` +
 `adj_pvalue`)

- Up-regulated bars rise above 0, down-regulated fall below 0
 (default red / blue)

- **In-dialog thresholds:** `FDR ≤` and `|log2FC| ≥`
 (down to 3 decimals, e.g. 0.585) — change them to re-aggregate instantly,
 using the same rule as the statistical filter

- **Bar Colors:** click the **Up-regulated** / **Down-regulated**
 color swatches to open a color picker and customize either bar color;
 the plot redraws immediately

- **Show as % of total** toggle; **Export Data** writes the
 up/down/total table (CSV / TSV / Excel)

### Genomic Annotation Comparison (ATAC-seq)

Compares the genomic-feature composition of peaks (Promoter, Exon, Intron, UTR,
 Intergenic, …) across multiple ATAC datasets. Three display modes:

- **Counts** / **Proportion (%)** — one stacked bar per dataset

- **Enrichment (log2 sig/all)** — grouped bars of
 log₂(significant proportion ÷ all-peaks proportion) per feature.
 **0** = same as background, **positive** = significant peaks are
 *enriched* in that feature, **negative** = depleted. This is the
 clearest view of *which genomic features the changes concentrate in*.

- **Peak set:** **Significant only** (default) or **All peaks**. Note:
 if datasets share one consensus peak set, the *All peaks* distribution is
 nearly identical across them (it only serves as the background reference) —
 use *Significant only* or *Enrichment* to compare conditions.

- In-dialog `FDR` / `|log2FC|` thresholds define
 "significant"; **Export Data** saves the category×dataset matrix

## 9.7 Common Features (All Plots)

- **High z-order:** Tooltips always appear above plot elements and colorbars

- **Matplotlib toolbar:** Pan, zoom, home, back, forward, save image

- **Legend position:** the Plot Labels panel includes an
 **outside right** option that places the legend beside the plot so it never
 covers the data (useful for stacked bars with many categories)

## 9.8 📌 Pin to Tab

Keep a plot open as a persistent tab instead of a dialog popup:

1. Open any Volcano Plot or Heatmap dialog and configure the plot

2. Click **📌 Pin to Tab** at the bottom of the dialog

3. The plot appears as a new tab (📈) in the center data view

4. The tab is also registered in the Dataset Tree under the parent dataset

Pinned plot tabs are saved with the project (**.seqproj**) and restored on next open.

## 9.9 Plot Settings Dock (Right Panel)

When a pinned plot tab is active, a **Plot Settings** panel automatically appears
 on the right side of the window:

5. All the same controls as the dialog left panel (thresholds, colors, colormap, etc.)

6. Changes apply to the plot in real time

7. The dock hides automatically when you switch to a non-plot tab

8. Can be moved or floated like any standard dock panel

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
