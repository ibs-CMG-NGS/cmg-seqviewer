# 3. Dataset Database

CMG-SeqViewer maintains a **built-in Parquet database** that stores frequently
 used datasets so you don't have to re-import Excel files every session.
 Datasets saved here load in milliseconds, are automatically registered
 when you drop files into the data folder, and can be merged from
 pipeline output folders with one click.

## 3.1 Opening the Database Browser

Go to **File → 📚 Database → Browse Pre-loaded Datasets...**
 (or press **Ctrl+B**).

The browser shows all registered datasets with columns:

- **Alias** – friendly name you assigned

- **Type** – DE or GO

- **Rows / Genes / Sig. Genes** – quick statistics

- **Organism / Cell Type** – optional metadata

- **Import Date**

Click any column header to sort. Use the **Search** box and
 **Cell Type / Organism** dropdowns to filter the list.

## 3.2 Loading a Dataset from the Database

1. Open the Database Browser

2. Select one or more rows (Shift/Ctrl+click for multi-select, same as a
 normal table)

3. Click **📂 Load Selected Dataset(s)** — each selected dataset opens
 as a new tab immediately

## 3.3 Right-Click Context Menu

Right-click any row (selecting it first if it wasn't already selected) for a
 quick menu with the same actions as the buttons below:
 **📂 Load Selected Dataset(s)**, **✏️ Edit Metadata** / **Bulk Edit**,
 **📤 Export Selected**, **🗑️ Delete Selected**.

## 3.4 Editing Metadata — Single vs. Bulk

4. **1 dataset selected:** the **✏️ Edit Metadata** button/menu item opens
 the single-dataset editor (alias, organism, cell type, tissue, timepoint,
 researcher, tags, notes)

5. **2+ datasets selected:** the same button becomes
 **✏️ Bulk Edit (N)** and opens the **Bulk Edit** dialog:

 - Each field (Condition, Cell Type, Organism, Tissue, Timepoint,
 Researcher, Tags, Notes) has its own checkbox — only
 **checked** fields are overwritten on every selected dataset;
 unchecked fields are left untouched

 - **Alias** is excluded from bulk edit (must stay unique per dataset)

 - **Researcher** and **Tags** are list fields with a
 **Replace** / **Add** mode: *Replace* overwrites the
 existing list, *Add* appends the entered values to whatever
 each dataset already has

 - Click **💾 Apply to N Dataset(s)** to commit

## 3.5 Importing a New Dataset into the Database

Go to **File → 📚 Database → Import Current Dataset to Database...**
 (or press **Ctrl+I**):

1. Select an Excel (.xlsx / .xls) or CSV file

2. Map columns to standard names in the Column Mapper dialog

3. Fill in metadata (alias, organism, cell type, notes — optional)

4. Click **Import** — the file is converted to Parquet and registered

**Tip:** Once imported, the original Excel file is no longer needed.

## 3.6 Export All / Export Selected — Sharing Datasets

Use these to hand off part or all of your local database to a colleague
 (e.g. via a shared network drive or a synced cloud folder):

5. **📤 Export Selected** — exports only the checked/selected rows

6. **📤 Export All** — exports every dataset in the database (asks for
 confirmation first)

7. Both prompt for a destination folder, then write each dataset's
 `metadata.json` entry and its `.parquet` file
 there — i.e. the same folder layout **Import Folder** (below) expects

8. The recipient merges the exported folder back in with
 **📥 Import Folder** (see below) — duplicate `dataset_id`s
 are automatically skipped, so re-importing is always safe

## 3.7 Auto-Registration (Orphan Parquet Files)

If you copy `.parquet` files directly into the
 `datasets/` subfolder of the external data directory,
 click **🔄 Refresh** in the Database Browser.
 The app will:

9. Detect files that are not yet registered

10. Read their columns to auto-determine DE vs GO type

11. Register them with an automatically generated alias
 (derived from the filename)

12. Save the new entries to `metadata.json`

No manual editing of `metadata.json` is needed.

## 3.8 📥 Import Folder — Merging Pipeline Output

When your analysis pipeline produces a separate output folder
 (containing `metadata.json` + `datasets/*.parquet`)
 for each run, use **Import Folder** to merge everything in one step.

### How to use

1. Open the Database Browser
 (**File → Database → Browse Database**)

2. Click the **📥 Import Folder** button in the top toolbar

3. Select the pipeline output folder
 (the folder that contains `metadata.json`
 and a `datasets/` sub-folder)

4. The app reads every dataset entry from
 `metadata.json`, copies the matching
 `.parquet` files into the app database,
 and registers them — **duplicate datasets are automatically
 skipped**

5. A summary dialog shows how many datasets were
 imported / skipped

### When there is no metadata.json

If the selected folder has no `metadata.json`, the app
 falls back to auto-detection: it scans all `.parquet` files,
 determines DE vs GO type from columns, and registers them
 exactly like the **Refresh** button does.

### Duplicate handling

6. Datasets with the same `dataset_id` or filename
 are **never overwritten**

7. Filename collisions receive a short UUID suffix
 (e.g. `ctrl_vs_trt_de_a1b2c3d4.parquet`)

## 3.9 merge_db.py — CLI Tool for Batch Merging

For server/scripted workflows, use the
 `merge_db.py` script at the project root:

```

# Merge one folder into the default app database
python merge_db.py path/to/pipeline_run/

# Merge multiple folders at once
python merge_db.py run1/ run2/ run3/

# Specify a custom target database directory
python merge_db.py run1/ --target D:/my_db/

# Preview without writing any files
python merge_db.py run1/ --dry-run

        Pipeline Output Convention

        For the smoothest workflow, have your R/Python pipeline
        write output in this layout:

        ```

pipeline_run_2026-03-12/
├── metadata.json ← dataset registry
└── datasets/
 ├── CtrlvsKO_de_xxxx.parquet
 └── CtrlvsKO_go_xxxx.parquet

The `metadata.json` format:

```

{
  "version": "1.0",
  "datasets": [
    {
      "dataset_id": "...",
      "alias": "Ctrl vs KO — DE",
      "dataset_type": "DE",
      "file_path": "CtrlvsKO_de_xxxx.parquet",
      "organism": "Mus musculus",
      "cell_type": "MEF"
    }
  ]
}

        Data Folder Location

        Click 📂 Open Data Folder** in the Database Browser to open
        the external data directory in your file explorer.
        The default path is:

            Windows:** %USERPROFILE%/CMG-SeqViewer/data/`

            macOS / Linux:** ~/CMG-SeqViewer/data/`

        Parquet files placed in the datasets/` subfolder
        are picked up on the next Refresh**.

        Deleting Datasets

            Select one or more dataset rows → click 🗑️ Delete Selected**
                (confirmation required) to remove them from the registry
                (the .parquet` file is also deleted)

        See the Right-Click Context Menu and Editing Metadata sections above for
        loading, editing (single/bulk), and exporting.*

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
