# 4. Data Filtering

## 4.1 Filter Panel

The left Filter Panel provides two filtering modes:

### 1. Gene List Filtering

- Enter gene IDs or symbols in the text area (one per line)

- Paste from clipboard using **Ctrl+V**

- Load from file using **File →Open Gene List**

- Click **Apply Filter** to filter the active tab

### 2. Statistical Filtering

- Set thresholds for:

 - **log2FC:** Minimum absolute fold change

 - **Padj:** Maximum adjusted p-value

- Select up-regulated, down-regulated, or both

- Click **Apply Filter**

## 4.2 Active Tab Filtering

- Switch to any tab (Whole Dataset, Filtered, Comparison results)

- Apply filters - they will be applied to the current tab

- Results appear in a new tab: **"Filtered: [original tab name]"**

## 4.3 Filter Results

Filtered results appear in a new tab with a descriptive name showing:

- Source tab name

- Number of genes filtered

- Filter criteria applied

## 4.4 Column Subset Sheet

To keep only certain *columns* (rather than certain rows), use
 **Analysis → 🧾 Select Columns → Subset Sheet...**:

1. A checklist of all columns in the active dataset opens, pre-ticked to
 match whatever is currently visible (per the Column Display Level)

2. Type in the filter box to narrow the list, and use
 **Select all** / **Clear all** for the currently filtered items

3. Click **OK** — a new child sheet is created with only the ticked
 columns; the original dataset is unchanged

Useful for trimming a wide table down to just the columns you want to export
 or paste into a report.

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
