# 16. PCA Plot

## 16.1 Overview

Principal Component Analysis (PCA) reduces the high-dimensional
 sample expression space to 2 (or more) principal components,
 making it easy to see how samples cluster and whether replicates
 group together as expected.

**Available for:** Differential Expression datasets that include
 per-sample abundance columns (e.g. `ctrl_1`,
 `ctrl_2`, `trt_1`, …).

## 16.2 Opening the PCA Plot

- Select a DE dataset tab

- Go to **Visualization → 🔵 PCA Plot**
 (or press **Ctrl+P**)

## 16.3 How Sample Columns Are Detected

The app automatically identifies sample columns by exclusion —
 any numeric column that is **not** a standard DE statistics column
 (`log2fc`, `adj_pvalue`, `base_mean`,
 `pvalue`, `stat`, etc.) is treated as a sample
 abundance column. No manual configuration is needed.

The number of detected samples and a column preview are shown in
 the **Dataset Info** panel on the left side of the dialog.

## 16.4 Settings

 | Setting| Default| Description

 | **Top genes (variance)**
 | 500
 | Select the top N most variable genes before PCA.
 Reduces noise from low-variance genes.

 | **Transformation**
 | log2(x+1)
 | Applied to raw abundance values before PCA.

- **log2(x+1)** — standard RNA-seq transform,
 stabilises variance, comparable to DESeq2 vst output

- **log1p** — natural log transform

- **None** — raw values (not recommended for count data)

 | **Feature scaling**
 | StandardScaler
 | Centers each gene to mean=0 and scales to std=1
 across samples before PCA.
 Prevents high-expression genes from dominating the plot.

 | **X / Y axis PC**
 | PC1 / PC2
 | Choose which principal components to display on each axis.
 PC1 always explains the most variance.

 | **Point size**
 | 80
 | Size of sample dots in the scatter plot.

 | **Show sample labels**
 | On
 | Display sample names next to each dot.

Click **🔄 Update Plot** to apply changed settings.

All settings are saved and restored between sessions.

## 16.5 Color By & Sample Groups (editable)

By default points are colored by an auto-detected condition group (from
 dataset metadata, the dataset name, or sample-column prefixes); the
 **Color by** dropdown lets you switch to **Sample** (each point its own
 color) if no meaningful group was detected.

A **Sample Groups (editable)** table (columns: **✓**, Sample, Group)
 lets you override this before plotting:

- **✓ column:** untick a sample to **exclude** it from the PCA
 computation entirely (both the variance selection and the projection)

- **Group column:** double-click to edit — same label = same color;
 blank = ungrouped

- **Select all** / **Clear all** toggle every ✓ checkbox at once

- Click **Apply Groups** to commit and recompute/redraw the PCA

## 16.6 Reading the Plot

- Each dot represents one sample

- Axis labels show the PC number and its **explained variance %**
 — e.g. *PC1 (42.3% variance)*

- A **scree summary** in the bottom-right corner lists
 explained variance for PC1–PC5

- Dashed lines mark the origin (0, 0)

- Good replicates should cluster tightly;
 treatment groups should separate along PC1 or PC2

## 16.7 Comparison with DESeq2 PCA

DESeq2's `plotPCA()` uses VST-normalised counts and
 selects the top 500 variable genes before calling `prcomp()`.
 This app uses the abundance columns already present in your DE table:

- If your pipeline exports **DESeq2 normalised counts**
 (via `counts(dds, normalized=TRUE)`) alongside
 DE statistics, the PCA result will be essentially equivalent
 to DESeq2's plot with the same gene selection and scaling

- If your pipeline exports raw counts, the log2 transform here
 approximates (but does not replicate) the VST step —
 the cluster separation pattern will be similar but
 numbers will differ slightly

## 16.8 Preparing Your Data

To get the best PCA, include normalised sample counts in your
 DE result Excel file before importing to the database:

```

# R example — include normalised counts in the DE output
res   <- results(dds)
ncnts <- counts(dds, normalized = TRUE)
write.csv(cbind(as.data.frame(res), as.data.frame(ncnts)),
          "final_de_result.csv")
        When this file is imported, the per-sample columns
        (ctrl_1`, ctrl_2`, trt_1`, …)
        are automatically detected and used for PCA.

        Export

            💾 Export PCA Scores (CSV)** — saves sample scores
                (PC1, PC2, …) plus explained variance row to a CSV file.
                Useful for custom downstream plots in R/Python.

            🖼 Export Image** — saves the plot as
                PNG (raster) or SVG / PDF (vector).

        Tips

            Start with the default 500 top-variance genes;
                increase to 2000+ if the plot looks noisy

            If you have < 4 samples, PCA is less informative —
                consider a heatmap instead

            Outlier samples appear far from their group cluster —
                investigate before including in downstream analysis

            Use PC1 vs PC3** or PC2 vs PC3** to look for
                secondary sources of variation (batch effects, sex, etc.)

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
