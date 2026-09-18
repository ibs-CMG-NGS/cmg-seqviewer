# 18. IGV Integration

## 18.1 Overview

[IGV (Integrative Genomics Viewer)](https://igv.org/) is a separate
 desktop application for browsing raw genomic tracks (BigWig signal, BAM alignments).
 CMG-SeqViewer can talk to a locally running IGV over its
 **port command listener** so you can jump straight from an ATAC-seq peak row
 in a table to that exact locus in IGV — no manual coordinate copying.

*Requires IGV desktop to be installed and running separately;
 this app does not bundle or launch IGV itself.*

## 18.2 One-time IGV Setup

1. In IGV: **View → Preferences → Advanced** → enable
 **"Enable port"** (default port **60151**)

2. Keep IGV running while using CMG-SeqViewer

## 18.3 IGV Settings Dialog

Open via **View → 🔬 IGV Settings...**

3. **Connection:** Port number (default 60151) and a
 **Test Connection** button showing ● Connected / ✗ Not running

4. **Navigation:**

 - **Context padding (bp):** extra flanking region added around the
 peak when jumping IGV to a locus (default 500 bp)

 - **Auto-set genome on send:** if checked, IGV's genome is switched
 automatically using the dataset's `genome_build` metadata
 (or the last genome used) before navigating

5. **Signal Tracks:** a list of BigWig/BAM files to keep handy.
 **+ Add Track** to browse for files, **Remove Selected** to drop a row,
 and **Load All Tracks in IGV Now** to push the whole list into IGV in
 one click (useful at the start of a session so all your coverage tracks
 are loaded before you start browsing peaks)

Settings (port, padding, auto-genome, track list) persist between sessions.

## 18.4 Sending a Peak to IGV

Right-click any row of an active **ATAC-seq** tab (the dataset must have
 `chromosome` / `peak_start` / `peak_end` columns):

6. **🔬 Send to IGV** — navigates the running IGV window to
 `chromosome:peak_start−peak_end`
 (widened by the configured context padding)

7. **📋 Copy Locus** — copies `chr:start-end` to the clipboard
 without touching IGV, for pasting elsewhere

If IGV is not reachable, a warning explains how to enable the port listener.

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
