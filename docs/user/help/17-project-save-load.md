# 17. Project Save/Load

## 17.1 Overview

CMG-SeqViewer saves your analysis session to a small **.seqproj** file.
 Rather than copying all the data, it stores a **recipe**: the source files/IDs
 plus the parameters used to derive every sheet. On open, the app reloads the
 sources and **re-runs** those steps to rebuild the session. This keeps project
 files tiny (a few KB) and uses no extra memory, but it means the
 **original source files must still be available** when you reopen.

## 17.2 Saving a Project

1. Go to **File → Save Project** (**Ctrl+Shift+S**) to save to the
 current project path, or **File → Save Project As...**
 (**Ctrl+Alt+S**) to always be prompted for a (new) location/filename

2. Choose a location and filename (extension `.seqproj` is added automatically)

*Save Project (Ctrl+Shift+S) reuses the last save location once the session
 has been saved once; use Save Project As... to save a copy elsewhere or under a
 different name without changing what subsequent Ctrl+Shift+S saves overwrite.*

What is saved in the `.seqproj` file:

3. **Datasets** — file paths (relative to the project file for portability) or
 database IDs for DB-sourced datasets

4. **Filtered sheets** — filter parameters (replayed on restore)

5. **Comparison sheets** — the source dataset names and comparison type
 (gene-list / statistics / GO-term), replayed on restore

6. **RNA–ATAC integration results** — the integration recipe
 (RNA/ATAC sources, method, thresholds), replayed on restore

7. **Plot tabs (📈)** — plot type and visualization parameters
 (`plot_params`) for Volcano and Heatmap tabs pinned via
 *📌 Pin to Tab*

8. **UI state** — last active tab index

## 17.3 Opening a Project

1. Go to **File → Open Project...** or press **Ctrl+Shift+O**

2. If a session is already loaded (any dataset tabs open), a
 **Save / Discard / Cancel** prompt appears first — opening a project
 always starts a brand-new session, replacing the current one:

 - **Save** — saves the current session first (Save Project /
 Save Project As flow), then proceeds to open the new project

 - **Discard** — closes the current session without saving and
 proceeds

 - **Cancel** — aborts; nothing is opened or closed

 If **Save** is chosen but the save is itself cancelled or fails, the
 whole operation is aborted so unsaved work is never silently lost.
 (An empty session with no datasets loaded skips this prompt.)

3. Select a `.seqproj` file

4. The app reloads each source dataset, replays its filters/plots, then
 regenerates comparison and integration results

If something cannot be restored, a **Project Restore — Partial** dialog
 appears and separates two cases: **source files not found** (a file moved or
 was deleted — that dataset and everything derived from it is skipped) and
 **generated results that must be recreated manually** (see Limitations).

## 17.4 Recent Projects

Recently opened project files appear in **File → Recent Projects**
 for one-click access.

## 17.5 File Portability

File paths inside `.seqproj` are stored **relative** to the
 project file, so you can move the project folder together with its data files
 (keeping the directory structure) to another machine and it will still open.
 Datasets loaded from the internal **database** store a database ID instead —
 no external file needed.

## 17.6 What is NOT (yet) restored automatically

These are reported in the **Project Restore — Partial** dialog so you know
 exactly what to recreate — nothing is lost silently:

5. **GO Term clustering results** (Clustered sheets) — recreate via
 **Analysis → Cluster GO Terms**

6. **Cross-species harmonized** and **meta-analysis** results

Other notes:

7. Only **Volcano** and **Heatmap** can be pinned as persistent tabs and
 therefore saved. Other visualizations (MA, PCA, GO dot/bar, Quadrant,
 Meta Volcano, Venn, UpSet, …) are modal dialogs and are not part of the
 saved session.

8. Because the session is **re-derived**, sheets are recomputed from the
 current source files rather than stored verbatim. If a source file changed
 since saving, the restored sheets reflect the new file.

9. Restored plots are drawn from the parent dataset's full table.

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
