# 2. Loading Data

## 2.1 Opening Datasets

To load a dataset:

1. Click **File →Open Dataset** (or press **Ctrl+O**), or

2. Click **Add Dataset** button in the Dataset Manager, or

3. Drag and drop an Excel file directly onto the application

4. Enter a name for the dataset (default: filename without extension)

5. The dataset will appear in a new tab and in the dataset selector

## 2.2 Recent Files

Access recently opened files quickly:

6. Click **File →Recent Files**

7. Shows up to 10 most recent files with 2-3 path levels for clarity

8. Click any file to open it (you'll be prompted for a dataset name)

9. Files that no longer exist are automatically removed from the list

10. Use **Clear Recent Files** to reset the history

## 2.3 Managing Datasets

Use the Dataset Tree (top of window) to:

11. **Switch:** Click a root dataset to view its **Whole Dataset**, or a
 child node (Filtered / Comparison / Clustered / Plot) to jump to that sheet

12. **Rename:** Select a node and click **Rename** — works for both
 **root datasets and derived sheets** (e.g. rename a "Filtered:" sheet to
 disambiguate identical filters applied to different datasets)

13. **Remove:** Click **Remove** to delete a dataset from the session

*Note: Renaming a dataset updates all references including tabs,
 comparison lists, and internal data structures.*

## 2.4 Expected Data Format

Your input file should contain columns for:

14. **gene_id:** Gene identifiers (e.g., ENSMUSG...)

15. **symbol:** Gene symbols (e.g., Gapdh, Actb)

16. **log2FoldChange** or **log2FC:** Log2 fold change values

17. **padj** or **Padj:** Adjusted p-values

18. **Sample columns:** Expression values for each sample

*Note: Column names are case-insensitive. The tool will automatically
 detect variations like "Log2FoldChange", "log2fc", etc.*

## 2.5 Opening Gene Lists

To load a gene list for filtering:

1. Click **File →Open Gene List**

2. Select a text file (.txt) with one gene per line

3. Genes will be loaded into the Filter Panel

## 2.6 Column Display Levels

Control which columns are displayed via **View →Column Display Level:**

4. **Basic:** Key identifier columns (Gene ID / peak_id, Symbol / nearest_gene, coordinates)

5. **Stat:** Basic + statistical columns (log2FC, padj, base_mean, direction)

6. **Full:** All columns in the dataset

*Works for both RNA-seq (DE) and ATAC-seq (DA) data types.*

## 2.7 Decimal Precision

Adjust number display precision via **View →Decimal Precision**:

7. Choose from 1 to 6 decimal places

8. Default is 3 decimal places

9. Applies to all numeric columns in the data view

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
