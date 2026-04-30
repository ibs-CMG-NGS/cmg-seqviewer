"""
Help Documentation Dialog

User manual and documentation viewer for RNA-Seq Data Analyzer.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser,
                            QListWidget, QListWidgetItem, QPushButton, QSplitter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont


def create_help_icon() -> QIcon:
    """Help 다이얼로그용 아이콘 생성"""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # 배경 원
    painter.setBrush(QColor(30, 144, 255))  # Dodger Blue
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 60, 60)
    
    # 물음표
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Arial", 36, QFont.Weight.Bold)
    painter.setFont(font)
    from PyQt6.QtCore import QRect
    painter.drawText(QRect(0, 0, 64, 64), Qt.AlignmentFlag.AlignCenter, "?")
    
    painter.end()
    
    return QIcon(pixmap)


class HelpDialog(QDialog):
    """Help documentation dialog with table of contents"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CMG-SeqViewer - User Documentation")
        self.setWindowIcon(create_help_icon())
        self.setMinimumSize(900, 700)
        
        self._init_ui()
        self._load_content()
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        
        # Splitter for TOC and content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Table of Contents
        self.toc_list = QListWidget()
        self.toc_list.setMaximumWidth(250)
        self.toc_list.currentRowChanged.connect(self._on_toc_selection_changed)
        splitter.addWidget(self.toc_list)
        
        # Right panel: Content viewer
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        splitter.addWidget(self.content_browser)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _load_content(self):
        """Load documentation content"""
        # Table of Contents
        toc_items = [
            "1. Getting Started",
            "2. Loading Data",
            "3. Dataset Database",
            "4. Data Filtering",
            "5. GO/KEGG Analysis",
            "5b. GO Term Comparison",
            "5c. ATAC-seq Analysis",
            "6. Statistical Analysis",
            "7. Visualization",
            "8. Multi-Group Heatmap",
            "9. PCA Plot",
            "10. Dataset Comparison",
            "11. Gene Annotation",
            "12. Export & Clipboard",
            "13. Tips & Shortcuts"
        ]
        
        for item_text in toc_items:
            self.toc_list.addItem(item_text)
        
        # Select first item
        self.toc_list.setCurrentRow(0)
    
    def _on_toc_selection_changed(self, index):
        """Display selected content section"""
        content_sections = [
            self._get_getting_started(),
            self._get_loading_data(),
            self._get_dataset_database(),
            self._get_filtering(),
            self._get_go_kegg_analysis(),
            self._get_go_term_comparison(),
            self._get_atac_seq_analysis(),
            self._get_statistical_analysis(),
            self._get_visualization(),
            self._get_multi_group_heatmap(),
            self._get_pca_plot(),
            self._get_comparison(),
            self._get_gene_annotation(),
            self._get_export(),
            self._get_tips()
        ]
        
        if 0 <= index < len(content_sections):
            self.content_browser.setHtml(content_sections[index])
    
    def _get_getting_started(self):
        """Getting Started section"""
        return """
        <h1>1. Getting Started</h1>
        
        <h2>Overview</h2>
        <p>CMG-SeqViewer is a comprehensive tool for analyzing and visualizing
        genomic sequencing data. This application provides:</p>
        <ul>
            <li>Multi-dataset management and comparison</li>
            <li>Flexible filtering options (statistical, gene list, annotation-based)</li>
            <li>Statistical analysis tools (Fisher's Exact, GSEA)</li>
            <li>Interactive visualizations (Volcano, MA Plot, Heatmap, Dot Plot, Venn)</li>
            <li><b>RNA-seq</b> differential expression (DE) analysis results</li>
            <li><b>ATAC-seq</b> differential accessibility (DA) analysis results</li>
            <li><b>GO/KEGG</b> enrichment analysis results</li>
        </ul>
        
        <h2>Main Interface</h2>
        <p>The interface consists of four main areas:</p>
        <ul>
            <li><b>Top:</b> Dataset Manager - Add, rename, remove, and switch datasets</li>
            <li><b>Left Panel:</b> 
                <ul>
                    <li>Filter Panel - Apply gene list or statistical filters</li>
                    <li>Comparison Panel - Compare multiple datasets</li>
                </ul>
            </li>
            <li><b>Center:</b> Data View - Tabbed display of datasets and results</li>
            <li><b>Bottom:</b> Log Terminal - System messages and status updates</li>
        </ul>
        
        <h2>Menu Bar</h2>
        <p>All menus are always accessible. The application will show appropriate error messages 
        if an operation cannot be performed in the current context.</p>
        <ul>
            <li><b>File:</b> Open datasets, database browser, recent files, export data</li>
            <li><b>Analysis:</b> Filtering, Fisher's Exact Test, GSEA, dataset comparison,
                <b>🌡️ Multi-Group Heatmap</b></li>
            <li><b>View:</b> Column display level, decimal precision</li>
            <li><b>Visualization:</b> Volcano plots, histograms, heatmaps, PCA plots, dot plots, Venn diagrams</li>
            <li><b>Help:</b> About dialog and user documentation</li>
        </ul>
        """
    
    def _get_loading_data(self):
        """Loading Data section"""
        return """
        <h1>2. Loading Data</h1>
        
        <h2>Opening Datasets</h2>
        <p>To load a dataset:</p>
        <ol>
            <li>Click <b>File &rarr;Open Dataset</b> (or press <b>Ctrl+O</b>), or</li>
            <li>Click <b>Add Dataset</b> button in the Dataset Manager, or</li>
            <li>Drag and drop an Excel file directly onto the application</li>
            <li>Enter a name for the dataset (default: filename without extension)</li>
            <li>The dataset will appear in a new tab and in the dataset selector</li>
        </ol>
        
        <h2>Recent Files</h2>
        <p>Access recently opened files quickly:</p>
        <ul>
            <li>Click <b>File &rarr;Recent Files</b></li>
            <li>Shows up to 10 most recent files with 2-3 path levels for clarity</li>
            <li>Click any file to open it (you'll be prompted for a dataset name)</li>
            <li>Files that no longer exist are automatically removed from the list</li>
            <li>Use <b>Clear Recent Files</b> to reset the history</li>
        </ul>
        
        <h2>Managing Datasets</h2>
        <p>Use the Dataset Manager (top of window) to:</p>
        <ul>
            <li><b>Switch:</b> Select a dataset from the dropdown to view it</li>
            <li><b>Rename:</b> Click <b>Rename</b> to change the dataset name</li>
            <li><b>Remove:</b> Click <b>Remove</b> to delete a dataset from the session</li>
        </ul>
        
        <p><i>Note: Renaming a dataset updates all references including tabs, 
        comparison lists, and internal data structures.</i></p>
        
        <h2>Expected Data Format</h2>
        <p>Your input file should contain columns for:</p>
        <ul>
            <li><b>gene_id:</b> Gene identifiers (e.g., ENSMUSG...)</li>
            <li><b>symbol:</b> Gene symbols (e.g., Gapdh, Actb)</li>
            <li><b>log2FoldChange</b> or <b>log2FC:</b> Log2 fold change values</li>
            <li><b>padj</b> or <b>Padj:</b> Adjusted p-values</li>
            <li><b>Sample columns:</b> Expression values for each sample</li>
        </ul>
        
        <p><i>Note: Column names are case-insensitive. The tool will automatically 
        detect variations like "Log2FoldChange", "log2fc", etc.</i></p>
        
        <h2>Opening Gene Lists</h2>
        <p>To load a gene list for filtering:</p>
        <ol>
            <li>Click <b>File &rarr;Open Gene List</b></li>
            <li>Select a text file (.txt) with one gene per line</li>
            <li>Genes will be loaded into the Filter Panel</li>
        </ol>
        
        <h2>Column Display Levels</h2>
        <p>Control which columns are displayed via <b>View &rarr;Column Display Level:</b></p>
        <ul>
            <li><b>Basic:</b> Key identifier columns (Gene ID / peak_id, Symbol / nearest_gene, coordinates)</li>
            <li><b>Stat:</b> Basic + statistical columns (log2FC, padj, base_mean, direction)</li>
            <li><b>Full:</b> All columns in the dataset</li>
        </ul>
        <p><i>Works for both RNA-seq (DE) and ATAC-seq (DA) data types.</i></p>
        
        <h2>Decimal Precision</h2>
        <p>Adjust number display precision via <b>View &rarr;Decimal Precision</b>:</p>
        <ul>
            <li>Choose from 1 to 6 decimal places</li>
            <li>Default is 3 decimal places</li>
            <li>Applies to all numeric columns in the data view</li>
        </ul>
        """
    
    def _get_dataset_database(self):
        """Dataset Database (Import / DB Browser) section"""
        return """
        <h1>3. Dataset Database</h1>

        <p>CMG-SeqViewer maintains a <b>built-in Parquet database</b> that stores frequently
        used datasets so you don't have to re-import Excel files every session.
        Datasets saved here load in milliseconds, are automatically registered
        when you drop files into the data folder, and can be merged from
        pipeline output folders with one click.</p>

        <h2>Opening the Database Browser</h2>
        <p>Go to <b>File &rarr; Database &rarr; Browse Database</b>.</p>
        <p>The browser shows all registered datasets with columns:</p>
        <ul>
            <li><b>Alias</b> – friendly name you assigned</li>
            <li><b>Type</b> – DE or GO</li>
            <li><b>Rows / Genes / Sig. Genes</b> – quick statistics</li>
            <li><b>Organism / Cell Type</b> – optional metadata</li>
            <li><b>Import Date</b></li>
        </ul>
        <p>Click any column header to sort. Use the <b>Search</b> box and
        <b>Cell Type / Organism</b> dropdowns to filter the list.</p>

        <h2>Loading a Dataset from the Database</h2>
        <ol>
            <li>Open the Database Browser</li>
            <li>Select one or more rows (Shift/Ctrl+click for multi-select)</li>
            <li>Click <b>Load Selected</b> — the dataset opens as a new tab immediately</li>
        </ol>

        <h2>Importing a New Dataset into the Database</h2>
        <p>Go to <b>File &rarr; Database &rarr; Import Dataset to Database</b>:</p>
        <ol>
            <li>Select an Excel (.xlsx / .xls) or CSV file</li>
            <li>Map columns to standard names in the Column Mapper dialog</li>
            <li>Fill in metadata (alias, organism, cell type, notes — optional)</li>
            <li>Click <b>Import</b> — the file is converted to Parquet and registered</li>
        </ol>
        <p><b>Tip:</b> Once imported, the original Excel file is no longer needed.</p>

        <h2>Auto-Registration (Orphan Parquet Files)</h2>
        <p>If you copy <code>.parquet</code> files directly into the
        <code>datasets/</code> subfolder of the external data directory,
        click <b>🔄 Refresh</b> in the Database Browser.
        The app will:</p>
        <ul>
            <li>Detect files that are not yet registered</li>
            <li>Read their columns to auto-determine DE vs GO type</li>
            <li>Register them with an automatically generated alias
                (derived from the filename)</li>
            <li>Save the new entries to <code>metadata.json</code></li>
        </ul>
        <p>No manual editing of <code>metadata.json</code> is needed.</p>

        <h2>📥 Import Folder — Merging Pipeline Output</h2>
        <p>When your analysis pipeline produces a separate output folder
        (containing <code>metadata.json</code> + <code>datasets/*.parquet</code>)
        for each run, use <b>Import Folder</b> to merge everything in one step.</p>

        <h3>How to use</h3>
        <ol>
            <li>Open the Database Browser
                (<b>File &rarr; Database &rarr; Browse Database</b>)</li>
            <li>Click the <b>📥 Import Folder</b> button in the top toolbar</li>
            <li>Select the pipeline output folder
                (the folder that contains <code>metadata.json</code>
                and a <code>datasets/</code> sub-folder)</li>
            <li>The app reads every dataset entry from
                <code>metadata.json</code>, copies the matching
                <code>.parquet</code> files into the app database,
                and registers them — <b>duplicate datasets are automatically
                skipped</b></li>
            <li>A summary dialog shows how many datasets were
                imported / skipped</li>
        </ol>

        <h3>When there is no metadata.json</h3>
        <p>If the selected folder has no <code>metadata.json</code>, the app
        falls back to auto-detection: it scans all <code>.parquet</code> files,
        determines DE vs GO type from columns, and registers them
        exactly like the <b>Refresh</b> button does.</p>

        <h3>Duplicate handling</h3>
        <ul>
            <li>Datasets with the same <code>dataset_id</code> or filename
                are <b>never overwritten</b></li>
            <li>Filename collisions receive a short UUID suffix
                (e.g. <code>ctrl_vs_trt_de_a1b2c3d4.parquet</code>)</li>
        </ul>

        <h2>merge_db.py — CLI Tool for Batch Merging</h2>
        <p>For server/scripted workflows, use the
        <code>merge_db.py</code> script at the project root:</p>

        <pre style="background:#f4f4f4; padding:8px; border-radius:4px; font-size:11px;">
# Merge one folder into the default app database
python merge_db.py path/to/pipeline_run/

# Merge multiple folders at once
python merge_db.py run1/ run2/ run3/

# Specify a custom target database directory
python merge_db.py run1/ --target D:/my_db/

# Preview without writing any files
python merge_db.py run1/ --dry-run</pre>

        <h2>Pipeline Output Convention</h2>
        <p>For the smoothest workflow, have your R/Python pipeline
        write output in this layout:</p>
        <pre style="background:#f4f4f4; padding:8px; border-radius:4px; font-size:11px;">
pipeline_run_2026-03-12/
├── metadata.json          ← dataset registry
└── datasets/
    ├── CtrlvsKO_de_xxxx.parquet
    └── CtrlvsKO_go_xxxx.parquet</pre>

        <p>The <code>metadata.json</code> format:</p>
        <pre style="background:#f4f4f4; padding:8px; border-radius:4px; font-size:11px;">
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
}</pre>

        <h2>Data Folder Location</h2>
        <p>Click <b>📂 Open Data Folder</b> in the Database Browser to open
        the external data directory in your file explorer.
        The default path is:</p>
        <ul>
            <li><b>Windows:</b> <code>%USERPROFILE%/CMG-SeqViewer/data/</code></li>
            <li><b>macOS / Linux:</b> <code>~/CMG-SeqViewer/data/</code></li>
        </ul>
        <p>Parquet files placed in the <code>datasets/</code> subfolder
        are picked up on the next <b>Refresh</b>.</p>

        <h2>Editing &amp; Deleting Datasets</h2>
        <ul>
            <li>Select a dataset row → click <b>✏️ Edit</b> to change alias,
                organism, cell type, or notes</li>
            <li>Select a dataset row → click <b>🗑 Delete</b> to remove it
                from the registry (the <code>.parquet</code> file is also deleted)</li>
        </ul>
        """
    
    def _get_filtering(self):
        """Filtering section"""
        return """
        <h1>4. Data Filtering</h1>
        
        <h2>Filter Panel</h2>
        <p>The left Filter Panel provides two filtering modes:</p>
        
        <h3>1. Gene List Filtering</h3>
        <ul>
            <li>Enter gene IDs or symbols in the text area (one per line)</li>
            <li>Paste from clipboard using <b>Ctrl+V</b></li>
            <li>Load from file using <b>File &rarr;Open Gene List</b></li>
            <li>Click <b>Apply Filter</b> to filter the active tab</li>
        </ul>
        
        <h3>2. Statistical Filtering</h3>
        <ul>
            <li>Set thresholds for:
                <ul>
                    <li><b>log2FC:</b> Minimum absolute fold change</li>
                    <li><b>Padj:</b> Maximum adjusted p-value</li>
                </ul>
            </li>
            <li>Select up-regulated, down-regulated, or both</li>
            <li>Click <b>Apply Filter</b></li>
        </ul>
        
        <h2>Active Tab Filtering</h2>
        <ul>
            <li>Switch to any tab (Whole Dataset, Filtered, Comparison results)</li>
            <li>Apply filters - they will be applied to the current tab</li>
            <li>Results appear in a new tab: <b>"Filtered: [original tab name]"</b></li>
        </ul>
        
        <h2>Filter Results</h2>
        <p>Filtered results appear in a new tab with a descriptive name showing:</p>
        <ul>
            <li>Source tab name</li>
            <li>Number of genes filtered</li>
            <li>Filter criteria applied</li>
        </ul>
        """
    
    def _get_atac_seq_analysis(self):
        """ATAC-seq Analysis section"""
        return """
        <h1>5c. ATAC-seq Analysis</h1>

        <p>CMG-SeqViewer supports ATAC-seq Differential Accessibility (DA) results
        in addition to RNA-seq DE data. The application automatically detects ATAC-seq
        data on load based on the presence of a <code>peak_id</code> column.</p>

        <h2>Loading ATAC-seq Data</h2>
        <p>Use <b>File &rarr; Open ATAC-seq Dataset&hellip;</b> or drag-and-drop an Excel/Parquet file.
        Supported formats match the standard DESeq2 DA output (HOMER-annotated):</p>
        <table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;">
            <tr style="background:#f0f0f0;"><th>Standard column</th><th>Accepted input names</th></tr>
            <tr><td>peak_id</td><td>peak_id, peakid, peak_name, interval</td></tr>
            <tr><td>chromosome</td><td>chr, chromosome, seqnames</td></tr>
            <tr><td>peak_start / peak_end</td><td>start / end, startpos / endpos</td></tr>
            <tr><td>nearest_gene</td><td>gene_name, nearest_gene, symbol</td></tr>
            <tr><td>annotation</td><td>annotation, peak_annotation, feature</td></tr>
            <tr><td>distance_to_tss</td><td>distancetotss, distance_to_tss, distance.to.tss</td></tr>
            <tr><td>base_mean</td><td>baseMean, base_mean, conc</td></tr>
            <tr><td>log2fc</td><td>log2FoldChange, log2fc, logFC</td></tr>
            <tr><td>adj_pvalue</td><td>padj, adj_pvalue, FDR</td></tr>
            <tr><td>direction</td><td>direction, regulation</td></tr>
        </table>
        <p>A <code>peak_width</code> column is automatically calculated as
        <code>peak_end &minus; peak_start</code>.</p>

        <h2>Column Display Levels</h2>
        <p>Use <b>View &rarr; Column Display Level</b> to adjust visible columns:</p>
        <ul>
            <li><b>Basic:</b> peak_id, chromosome, peak_start, peak_end, nearest_gene</li>
            <li><b>Stat:</b> Basic + base_mean, log2fc, pvalue, adj_pvalue, direction</li>
            <li><b>Full:</b> Stat + lfcse, annotation, distance_to_tss, gene_id, peak_width</li>
        </ul>

        <h2>ATAC-seq Filtering (Statistical tab)</h2>
        <p>When an ATAC-seq dataset is active, the <b>ATAC-seq Filtering</b> section
        becomes visible below the standard DE filters:</p>
        <ul>
            <li><b>Annot:</b> Filter by genomic annotation category
                (e.g., Intergenic, Intron, Promoter-TSS). Categories are populated
                automatically from the loaded data.</li>
            <li><b>|TSS| &le;:</b> Keep only peaks whose absolute distance to the nearest
                TSS is within the specified number of base pairs.</li>
            <li><b>Peak Width:</b> Filter by minimum and/or maximum peak width (bp).</li>
        </ul>
        <p>Statistical filters (adj. p-value, |log2FC|, direction) also apply to ATAC-seq data.</p>

        <h2>Gene List Filtering</h2>
        <p>Paste <b>gene symbols</b> (nearest gene names) into the Gene List tab, one per line.
        The filter matches against the <code>nearest_gene</code> column.</p>

        <h2>ATAC-seq Visualizations</h2>
        <p>When an ATAC-seq tab is active, three dedicated plots are available under
        <b>Visualization</b>:</p>

        <h3>Genomic Distribution</h3>
        <ul>
            <li>Pie chart of peak annotation categories (Intergenic, Intron, Promoter-TSS, Exon, TTS, &hellip;)</li>
            <li>HOMER/ChIPseeker annotation strings are normalized to broad categories automatically</li>
            <li>Shows peak count and percentage per category</li>
        </ul>

        <h3>TSS Distance Plot</h3>
        <ul>
            <li>Histogram of peak distances to the nearest TSS</li>
            <li>Default range: &plusmn;50,000 bp; configurable with Range and Bins controls</li>
            <li>Reference lines at 0 bp (TSS), &plusmn;2 kb, &plusmn;5 kb</li>
            <li>Summary bar: % peaks within &le;2 kb and &le;5 kb from TSS</li>
        </ul>

        <h3>MA Plot</h3>
        <ul>
            <li>X axis: log&#8322;(base mean accessibility); Y axis: log&#8322; fold change</li>
            <li>Points colored by regulation direction (Up / Down / Not Significant)</li>
            <li>Configurable adj. p-value and |log2FC| thresholds</li>
            <li>Gene label annotation: Top N by |log2FC|, or custom gene list</li>
            <li>Hover tooltip shows nearest_gene, log2FC, base mean, adj. p-value</li>
        </ul>

        <p>The standard <b>Volcano Plot</b> also works with ATAC-seq data
        (uses log2fc and adj_pvalue columns).</p>

        <h2>Annotation Column Explained</h2>
        <p>ATAC-seq peaks are annotated with a genomic context string (HOMER format):</p>
        <ul>
            <li><code>annotation</code> — the gene body that the peak <b>physically overlaps</b>
                (e.g., &ldquo;intron (ENSMUSG00000097836, intron 2 of 4)&rdquo;)</li>
            <li><code>nearest_gene</code> + <code>gene_id</code> — the gene whose
                <b>TSS is closest</b> to the peak center (used for regulatory interpretation)</li>
        </ul>
        <p>These can differ: a peak may overlap an intron of a large gene (annotation) while
        the nearest TSS belongs to a different gene (nearest_gene). For downstream analysis
        (e.g., gene list filtering), <code>nearest_gene</code> is used.</p>
        """

    def _get_statistical_analysis(self):
        """Statistical Analysis section"""
        return """
        <h1>6. Statistical Analysis</h1>
        
        <h2>Fisher's Exact Test</h2>
        <p>Perform Fisher's exact test for gene set enrichment:</p>
        <ol>
            <li>Select <b>Analysis &rarr;Fisher's Exact Test</b></li>
            <li>Enter gene sets or upload pathway definitions</li>
            <li>Results show enrichment p-values and odds ratios</li>
        </ol>
        
        <h2>GSEA Lite</h2>
        <p>Gene Set Enrichment Analysis (lightweight version):</p>
        <ol>
            <li>Select <b>Analysis &rarr;GSEA Lite</b></li>
            <li>Choose gene sets from predefined databases</li>
            <li>View enrichment scores and leading-edge genes</li>
        </ol>
        
        <h2>Dataset Comparison</h2>
        <p>Compare multiple datasets to find common/unique genes:</p>
        <ol>
            <li>Load 2 or more datasets</li>
            <li>Select <b>Analysis &rarr;Compare Datasets</b></li>
            <li>Choose which datasets to compare</li>
            <li>Set statistical thresholds (optional)</li>
            <li>View results in "Comparison: Statistics" tab</li>
        </ol>
        
        <p>Comparison results include:</p>
        <ul>
            <li><b>gene_id, symbol:</b> Gene identifiers</li>
            <li><b>Status:</b> Common, Unique_Dataset1, etc.</li>
            <li><b>Found_in:</b> Which datasets contain this gene</li>
            <li><b>Dataset-specific columns:</b> log2FC and padj for each dataset</li>
        </ul>
        """
    
    def _get_visualization(self):
        """Visualization section"""
        return """
        <h1>7. Visualization</h1>
        
        <h2>Volcano Plot</h2>
        <p>Visualize differential expression with log2FC vs. -log10(padj):</p>
        <ul>
            <li>Select <b>Visualization &rarr; Volcano Plot</b> (or <b>Ctrl+V</b>)</li>
            <li>Hover over points to see gene details (tooltip auto-adjusts to stay visible)</li>
            <li>Customize plot with the left panel settings:
                <ul>
                    <li>Adjust log2FC and padj thresholds</li>
                    <li>Change dot colors for up/down/non-significant genes</li>
                    <li>Adjust dot size and axis ranges</li>
                    <li>Customize plot title, axis labels</li>
                    <li>Toggle legend on/off</li>
                    <li>Adjust figure size (width/height)</li>
                </ul>
            </li>
            <li>All settings are saved between sessions</li>
            <li>Use matplotlib toolbar to zoom, pan, and save images</li>
        </ul>
        
        <h2>Expression Heatmap</h2>
        <p>Display gene expression patterns across samples:</p>
        <ul>
            <li>Select <b>Visualization &rarr; Heatmap</b></li>
            <li>Configure settings:
                <ul>
                    <li><b>Number of genes:</b> Top N genes to display (10-500)</li>
                    <li><b>Normalization:</b> Z-score, Min-Max (0-1), Log2 Transform, or None</li>
                    <li><b>Gene sorting:</b> 
                        <ul>
                            <li>Padj (ascending) - most significant first</li>
                            <li>Log2FC (absolute descending) - largest changes first</li>
                            <li>Hierarchical Clustering - group similar patterns</li>
                        </ul>
                    </li>
                    <li><b>Colormap:</b> RdBu_r, viridis, plasma, coolwarm, seismic</li>
                    <li><b>Colorbar range:</b> Set min/max values for color scale</li>
                    <li><b>Transpose:</b> Swap genes (rows) and samples (columns)</li>
                </ul>
            </li>
            <li>Hover over cells to see gene name, sample name, and expression value</li>
            <li>Tooltips always stay visible (auto-positioning)</li>
        </ul>
        
        <h2>Dot Plot</h2>
        <p>Specialized visualization for dataset comparison results:</p>
        <ul>
            <li>Available only on <b>Comparison: Statistics</b> or <b>Comparison: Gene List</b> tabs</li>
            <li>Select <b>Visualization &rarr; Dot Plot</b></li>
            <li>Features:
                <ul>
                    <li><b>Dot size:</b> Represents significance level (Padj thresholds)</li>
                    <li><b>Dot color:</b> Represents log2 fold change (colormap)</li>
                    <li><b>Gene clustering:</b> Option to reorder genes by similarity</li>
                    <li><b>Transpose:</b> Swap datasets and genes axes</li>
                    <li><b>Customizable:</b> Colormap, colorbar range, labels, legend</li>
                </ul>
            </li>
            <li>Datasets are automatically spaced for optimal readability</li>
            <li>Settings persist across sessions</li>
        </ul>
        
        <h2>P-adj Histogram</h2>
        <p>View distribution of adjusted p-values:</p>
        <ul>
            <li>Select <b>Visualization &rarr; P-adj Histogram</b></li>
            <li>Choose between original p-values or adjusted p-values</li>
            <li>Adjust number of bins (10-200)</li>
            <li>Helps assess data quality and significance thresholds</li>
        </ul>
        
        <h2>Common Features (All Plots)</h2>
        <ul>
            <li><b>High z-order:</b> Tooltips always appear above plot elements and colorbars</li>
            <li><b>Matplotlib toolbar:</b> Pan, zoom, home, back, forward, save image</li>
        </ul>
        """

    def _get_multi_group_heatmap(self):
        """Multi-Group Heatmap section"""
        return """
        <h1>8. Multi-Group Heatmap</h1>

        <h2>Overview</h2>
        <p>The Multi-Group Heatmap visualises LRT (Likelihood Ratio Test) omnibus results as a
        Z-score hierarchical clustermap. It is designed for experiments with &ge;3 conditions
        (e.g. HP1hr, HP4hr, HPctrl) where a single fold-change is not sufficient to capture
        expression dynamics.</p>

        <p><b>Input file format</b> — CSV with columns:</p>
        <pre style="background:#f4f4f4; padding:8px; border-radius:4px; font-size:11px;">
"","gene_symbol","baseMean","stat","pvalue","padj","HP1hr1","HP1hr2",...,"HPctrl3","HPctrl4"</pre>
        <p>The first unnamed column is treated as Ensembl gene ID.
        Sample columns are detected automatically by excluding known statistics columns
        (<code>baseMean, stat, pvalue, padj, log2FC, lfcSE</code> etc.).</p>

        <h2>Loading a Multi-Group Dataset</h2>
        <ol>
            <li><b>File &rarr; Open Dataset</b> (Ctrl+O) and select the CSV/Parquet file</li>
            <li>The app auto-detects it as a Multi-Group dataset
                (presence of <code>padj</code> column + no <code>log2FoldChange</code> + &ge;3 numeric sample columns)</li>
            <li>The dataset opens in the <b>Whole Dataset</b> tab</li>
        </ol>

        <h2>Filtering a Multi-Group Sheet by Gene List</h2>
        <p>You can filter the multi-group sheet to a specific set of genes before heatmap visualisation:</p>
        <ol>
            <li>Enter gene symbols in the <b>Gene List</b> tab of the Filter Panel (one per line)</li>
            <li>Click <b>Apply Filter</b> — a new tab <em>"Filtered: Gene List (N genes)"</em> is created</li>
            <li>This child sheet retains all original metadata (sample columns, groups)</li>
            <li>Open the heatmap from the child sheet — statistical filters are auto-relaxed
                (<code>padj&nbsp;&le;&nbsp;1.0</code>, <code>baseMean&nbsp;&ge;&nbsp;0</code>)
                so all N genes pass through</li>
        </ol>

        <h2>Opening the Heatmap</h2>
        <ol>
            <li>Make sure a Multi-Group tab (Whole Dataset or Filtered child) is active</li>
            <li>Go to <b>Analysis &rarr; 🌡️ Multi-Group Heatmap...</b></li>
        </ol>

        <h2>Control Panel — Left Side</h2>

        <h3>Title</h3>
        <p>Type a custom title. Leave empty for an auto-generated title:
        <em>dataset | Z-score | padj&le;X, baseMean&ge;Y, n=N</em>.
        Click <b>↺</b> to reset to auto.</p>

        <h3>Data Filter</h3>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr style="background:#f0f0f0;"><th>Control</th><th>Default</th><th>Description</th></tr>
            <tr><td>padj &le;</td><td>0.05 (1.0 if pre-filtered)</td>
                <td>LRT adjusted p-value cutoff. Genes above this threshold are excluded.</td></tr>
            <tr><td>baseMean &ge;</td><td>10 (0 if pre-filtered)</td>
                <td>Minimum mean expression. Removes very low-expression genes.</td></tr>
            <tr><td>Top N</td><td>200</td>
                <td>Maximum number of genes to display, sorted by padj ascending.</td></tr>
            <tr><td>Shown</td><td>–</td><td>Actual count of genes after filtering.</td></tr>
        </table>
        <p><em>When opening from a Filtered child sheet, a blue notice confirms
        "⚡ Pre-filtered — filters relaxed".</em></p>

        <h3>Clustering</h3>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr style="background:#f0f0f0;"><th>Control</th><th>Default</th><th>Description</th></tr>
            <tr><td>Linkage</td><td>ward</td><td>ward / average / complete / single</td></tr>
            <tr><td>Metric</td><td>euclidean</td><td>euclidean / correlation / cosine
                (ward always uses euclidean)</td></tr>
            <tr><td>Cluster genes (rows)</td><td>✔</td><td>Hierarchical clustering on rows</td></tr>
            <tr><td>Cluster samples (cols)</td><td>✘</td><td>Uncheck to preserve original sample order</td></tr>
        </table>

        <h3>Gene Clusters</h3>
        <p>Cut the row dendrogram into <em>k</em> clusters using scipy <code>fcluster</code>:</p>
        <ol>
            <li>Check <b>Cut dendrogram into clusters</b></li>
            <li>Set <b>k</b> (2–20)</li>
            <li>Click <b>▶ Refresh Plot</b></li>
            <li>A colour bar appears on the left of the heatmap; sizes are shown next to <em>Sizes:</em></li>
            <li>The <b>🔬 GO Enrichment (per cluster)...</b> button becomes active (Stage 2, coming soon)</li>
        </ol>

        <h3>Display</h3>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr style="background:#f0f0f0;"><th>Control</th><th>Description</th></tr>
            <tr><td>Color map</td><td>RdBu_r / coolwarm / bwr / PiYG / vlag / seismic</td></tr>
            <tr><td>Groups: swatches</td><td>Colour swatch per sample group — click to open colour picker
                (any colour; not limited to preset palette)</td></tr>
            <tr><td>Show gene labels</td><td>Toggle Y-axis gene name labels (disable for >300 genes)</td></tr>
            <tr><td>Gene label size</td><td>Font size for gene labels (4–14 pt)</td></tr>
            <tr><td>Show sample labels</td><td>Toggle X-axis sample name labels</td></tr>
        </table>

        <h3>Color Scale</h3>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr style="background:#f0f0f0;"><th>Control</th><th>Default</th><th>Description</th></tr>
            <tr><td>Auto scale</td><td>✔</td><td>Let seaborn choose vmin/vmax from the data</td></tr>
            <tr><td>Z min / Z max</td><td>−2.0 / 2.0</td>
                <td>Manual colour scale limits (enabled only when Auto scale is off)</td></tr>
        </table>

        <h3>Figure Size</h3>
        <p><b>Width</b> and <b>Height</b> (inches) on one row. Default 14 × 10.</p>

        <h2>Buttons</h2>
        <ul>
            <li><b>▶ Refresh Plot</b> — regenerate the heatmap with current settings</li>
            <li><b>💾 Save Figure...</b> — export as PNG / SVG / PDF</li>
            <li><b>📄 Export Data (CSV)...</b> — export Z-score matrix; includes a
                <code>gene_cluster</code> column when clusters are active</li>
            <li><b>🗄 Export to Parquet...</b> — save for database import</li>
        </ul>

        <h2>Typical Workflow</h2>
        <ol>
            <li>Load <code>multi_group_result.csv</code> (Ctrl+O)</li>
            <li>Optionally: enter gene symbols in Gene List filter → Apply Filter
                to create a focused child sheet</li>
            <li>Go to <b>Analysis &rarr; 🌡️ Multi-Group Heatmap...</b></li>
            <li>Adjust padj/baseMean filters and Top N</li>
            <li>Choose colour map and group colours</li>
            <li>Enable gene clusters (k=3–5) to identify co-expression modules</li>
            <li>▶ Refresh Plot</li>
            <li>Save figure or export CSV</li>
        </ol>

        <h2>Notes</h2>
        <ul>
            <li>Z-score is computed row-wise (per gene across all samples)</li>
            <li>Genes with constant expression (std = 0) are kept but shown as 0</li>
            <li>The colour bar is placed in the lower-left of the figure to avoid
                overlap with the row dendrogram</li>
        </ul>
        """

    def _get_pca_plot(self):
        """PCA Plot section"""
        return """
        <h1>10. PCA Plot</h1>

        <h2>Overview</h2>
        <p>Principal Component Analysis (PCA) reduces the high-dimensional
        sample expression space to 2 (or more) principal components,
        making it easy to see how samples cluster and whether replicates
        group together as expected.</p>

        <p><b>Available for:</b> Differential Expression datasets that include
        per-sample abundance columns (e.g. <code>ctrl_1</code>,
        <code>ctrl_2</code>, <code>trt_1</code>, …).</p>

        <h2>Opening the PCA Plot</h2>
        <ul>
            <li>Select a DE dataset tab</li>
            <li>Go to <b>Visualization &rarr; 🔵 PCA Plot</b>
                (or press <b>Ctrl+P</b>)</li>
        </ul>

        <h2>How Sample Columns Are Detected</h2>
        <p>The app automatically identifies sample columns by exclusion —
        any numeric column that is <b>not</b> a standard DE statistics column
        (<code>log2fc</code>, <code>adj_pvalue</code>, <code>base_mean</code>,
        <code>pvalue</code>, <code>stat</code>, etc.) is treated as a sample
        abundance column.  No manual configuration is needed.</p>

        <p>The number of detected samples and a column preview are shown in
        the <b>Dataset Info</b> panel on the left side of the dialog.</p>

        <h2>Settings</h2>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr style="background:#f0f0f0;">
                <th>Setting</th><th>Default</th><th>Description</th>
            </tr>
            <tr>
                <td><b>Top genes (variance)</b></td>
                <td>500</td>
                <td>Select the top N most variable genes before PCA.
                    Reduces noise from low-variance genes.</td>
            </tr>
            <tr>
                <td><b>Transformation</b></td>
                <td>log2(x+1)</td>
                <td>Applied to raw abundance values before PCA.
                    <ul>
                        <li><b>log2(x+1)</b> — standard RNA-seq transform,
                            stabilises variance, comparable to DESeq2 vst output</li>
                        <li><b>log1p</b> — natural log transform</li>
                        <li><b>None</b> — raw values (not recommended for count data)</li>
                    </ul></td>
            </tr>
            <tr>
                <td><b>Feature scaling</b></td>
                <td>StandardScaler</td>
                <td>Centers each gene to mean=0 and scales to std=1
                    across samples before PCA.
                    Prevents high-expression genes from dominating the plot.</td>
            </tr>
            <tr>
                <td><b>X / Y axis PC</b></td>
                <td>PC1 / PC2</td>
                <td>Choose which principal components to display on each axis.
                    PC1 always explains the most variance.</td>
            </tr>
            <tr>
                <td><b>Point size</b></td>
                <td>80</td>
                <td>Size of sample dots in the scatter plot.</td>
            </tr>
            <tr>
                <td><b>Show sample labels</b></td>
                <td>On</td>
                <td>Display sample names next to each dot.</td>
            </tr>
        </table>
        <p>Click <b>🔄 Update Plot</b> to apply changed settings.</p>
        <p>All settings are saved and restored between sessions.</p>

        <h2>Reading the Plot</h2>
        <ul>
            <li>Each dot represents one sample</li>
            <li>Axis labels show the PC number and its <b>explained variance %</b>
                — e.g. <em>PC1 (42.3% variance)</em></li>
            <li>A <b>scree summary</b> in the bottom-right corner lists
                explained variance for PC1–PC5</li>
            <li>Dashed lines mark the origin (0, 0)</li>
            <li>Good replicates should cluster tightly;
                treatment groups should separate along PC1 or PC2</li>
        </ul>

        <h2>Comparison with DESeq2 PCA</h2>
        <p>DESeq2's <code>plotPCA()</code> uses VST-normalised counts and
        selects the top 500 variable genes before calling <code>prcomp()</code>.
        This app uses the abundance columns already present in your DE table:</p>
        <ul>
            <li>If your pipeline exports <b>DESeq2 normalised counts</b>
                (via <code>counts(dds, normalized=TRUE)</code>) alongside
                DE statistics, the PCA result will be essentially equivalent
                to DESeq2's plot with the same gene selection and scaling</li>
            <li>If your pipeline exports raw counts, the log2 transform here
                approximates (but does not replicate) the VST step —
                the cluster separation pattern will be similar but
                numbers will differ slightly</li>
        </ul>

        <h2>Preparing Your Data</h2>
        <p>To get the best PCA, include normalised sample counts in your
        DE result Excel file before importing to the database:</p>
        <pre style="background:#f4f4f4; padding:8px; border-radius:4px; font-size:11px;">
# R example — include normalised counts in the DE output
res   &lt;- results(dds)
ncnts &lt;- counts(dds, normalized = TRUE)
write.csv(cbind(as.data.frame(res), as.data.frame(ncnts)),
          "final_de_result.csv")</pre>
        <p>When this file is imported, the per-sample columns
        (<code>ctrl_1</code>, <code>ctrl_2</code>, <code>trt_1</code>, …)
        are automatically detected and used for PCA.</p>

        <h2>Export</h2>
        <ul>
            <li><b>💾 Export PCA Scores (CSV)</b> — saves sample scores
                (PC1, PC2, …) plus explained variance row to a CSV file.
                Useful for custom downstream plots in R/Python.</li>
            <li><b>🖼 Export Image</b> — saves the plot as
                PNG (raster) or SVG / PDF (vector).</li>
        </ul>

        <h2>Tips</h2>
        <ul>
            <li>Start with the default 500 top-variance genes;
                increase to 2000+ if the plot looks noisy</li>
            <li>If you have &lt; 4 samples, PCA is less informative —
                consider a heatmap instead</li>
            <li>Outlier samples appear far from their group cluster —
                investigate before including in downstream analysis</li>
            <li>Use <b>PC1 vs PC3</b> or <b>PC2 vs PC3</b> to look for
                secondary sources of variation (batch effects, sex, etc.)</li>
        </ul>
        """

    def _get_comparison(self):
        """Comparison section"""
        return """
        <h1>10. Dataset Comparison</h1>
        
        <h2>Comparison Panel </h2>
        <p>Located in the left panel below the Filter Panel:</p>
        <ul>
            <li><b>Select Datasets:</b> Choose 2 or more datasets to compare</li>
            <li><b>Selection helpers:</b> "Select All" and "Clear Selection" buttons</li>
            <li><b>Comparison Type:</b>
                <ul>
                    <li><b>Gene List Filtering:</b> Compare gene lists only</li>
                    <li><b>Statistics Filtering:</b> Include log2FC and Padj values</li>
                </ul>
            </li>
            <li><b>Options (mutually exclusive):</b>
                <ul>
                    <li><b>Show common genes only (intersection):</b> Genes in ALL datasets</li>
                    <li><b>Include unique genes (union):</b> Genes in ANY dataset (default)</li>
                </ul>
            </li>
        </ul>
        
        <h2>Running Comparisons</h2>
        <ol>
            <li>Load 2 or more datasets</li>
            <li>Select datasets in the Comparison Panel</li>
            <li>Choose comparison type</li>
            <li>Select intersection or union option</li>
            <li>Click <b>Start Comparison</b></li>
            <li>Results appear in a new tab:
            </li>
        </ol>
        
        <h2>Comparison Results</h2>
        <p>The Statistics tab includes:</p>
        <ul>
            <li><b>gene_id, symbol:</b> Gene identifiers</li>
            <li><b>Status:</b> Common, Unique_Dataset1, etc.</li>
            <li><b>Found_in:</b> Comma-separated list of datasets</li>
            <li><b>Dataset columns:</b> For each dataset:
                <ul>
                    <li>Dataset_log2FC - fold change values</li>
                    <li>Dataset_padj - adjusted p-values</li>
                </ul>
            </li>
        </ul>
        
        <h2>Venn Diagram</h2>
        <p>Visualize overlap between 2-3 datasets:</p>
        
        <h3>From Loaded Datasets:</h3>
        <ol>
            <li>Load 2 or 3 datasets</li>
            <li>Select <b>Visualization &rarr; Venn Diagram</b></li>
            <li>Choose datasets to compare</li>
            <li>Set statistical filters (optional):
                <ul>
                    <li>Minimum |log2FC|</li>
                    <li>Maximum Padj</li>
                </ul>
            </li>
            <li>View overlapping and unique genes in each region</li>
        </ol>
        
        <h3>From Comparison Sheet:</h3>
        <ol>
            <li>Run <b>Analysis &rarr;Compare Datasets</b></li>
            <li>Switch to "Comparison: Statistics" tab</li>
            <li>Select <b>Visualization &rarr;Venn Diagram</b></li>
            <li>The tool automatically detects it's a comparison sheet</li>
            <li>Apply statistical filters if needed</li>
        </ol>
        
        <h2>Dot Plot for Comparisons </h2>
        <p>Specialized visualization for comparison results:</p>
        <ol>
            <li>Open a Comparison tab (Statistics or Gene List)</li>
            <li>Select <b>Visualization &rarr;Dot Plot</b></li>
            <li>View all datasets simultaneously with:
                <ul>
                    <li>Dot size = significance (Padj)</li>
                    <li>Dot color = fold change (log2FC)</li>
                    <li>Optional gene clustering for pattern discovery</li>
                </ul>
            </li>
        </ol>
        """
    
    def _get_gene_annotation(self):
        """Gene Annotation section"""
        return """
        <h1>11. Gene Annotation</h1>
        
        <h2>Overview</h2>
        <p>CMG-SeqViewer provides quick access to external gene annotation databases 
        through convenient right-click context menus in data tables.</p>
        
        <h2>Accessing Gene Information</h2>
        <p>Right-click on any gene symbol or gene ID in the data table to access annotation resources:</p>
        
        <h3>For Gene Symbols/IDs:</h3>
        <ul>
            <li><b>🔍 NCBI Gene</b> - Comprehensive gene information
                <ul>
                    <li>Official gene names and symbols</li>
                    <li>Genomic locations and structure</li>
                    <li>Expression data and orthologs</li>
                    <li>References and pathways</li>
                </ul>
            </li>
            <li><b>🔍 GeneCards</b> - Human gene database
                <ul>
                    <li>Integrated information from 150+ sources</li>
                    <li>Disease associations</li>
                    <li>Protein products and domains</li>
                    <li>Best for human genes</li>
                </ul>
            </li>
            <li><b>🔍 Ensembl</b> - Genome browser
                <ul>
                    <li>Multi-species support</li>
                    <li>Detailed genomic annotations</li>
                    <li>Variant information</li>
                    <li>Comparative genomics</li>
                </ul>
            </li>
            <li><b>🔍 UniProt</b> - Protein database
                <ul>
                    <li>Protein sequences and structures</li>
                    <li>Functional annotations</li>
                    <li>Post-translational modifications</li>
                    <li>Protein-protein interactions</li>
                </ul>
            </li>
            <li><b>📚 Google Scholar</b> - Literature search
                <ul>
                    <li>Research publications about the gene</li>
                    <li>Citations and reviews</li>
                    <li>Recent discoveries</li>
                </ul>
            </li>
        </ul>
        
        <h2>GO Term Annotation</h2>
        <p>Right-click on GO term IDs or descriptions in GO analysis results:</p>
        
        <h3>For GO Terms (GO:XXXXXXX):</h3>
        <ul>
            <li><b>🔍 QuickGO (EBI)</b> - Primary GO resource
                <ul>
                    <li>Detailed term definitions</li>
                    <li>Hierarchical relationships (parent/child terms)</li>
                    <li>Associated genes and proteins</li>
                    <li>Fast and comprehensive</li>
                </ul>
            </li>
            <li><b>🔍 AmiGO</b> - Official GO browser
                <ul>
                    <li>Interactive ontology browser</li>
                    <li>Term relationships visualization</li>
                    <li>Gene product annotations</li>
                    <li>Official GO Consortium tool</li>
                </ul>
            </li>
            <li><b>🔍 Gene Ontology</b> - GO documentation
                <ul>
                    <li>Official GO documentation</li>
                    <li>Ontology structure information</li>
                    <li>Best practices and guidelines</li>
                </ul>
            </li>
            <li><b>🔍 NCBI Gene</b> - Genes with this GO term
                <ul>
                    <li>Find genes annotated with this term</li>
                    <li>Cross-reference with your results</li>
                </ul>
            </li>
        </ul>
        
        <h2>KEGG Pathway Annotation</h2>
        <p>Right-click on KEGG pathway IDs or pathway names:</p>
        
        <h3>For KEGG Pathways (e.g., hsa04110):</h3>
        <ul>
            <li><b>🔍 KEGG Pathway</b> - Interactive pathway maps
                <ul>
                    <li>Visual pathway diagrams</li>
                    <li>Gene/protein relationships</li>
                    <li>Compound and reaction information</li>
                    <li>Links to related pathways</li>
                </ul>
            </li>
            <li><b>🔍 KEGG Search</b> - Search KEGG database
                <ul>
                    <li>Find related pathways</li>
                    <li>Search by pathway name or description</li>
                    <li>Cross-species pathway information</li>
                </ul>
            </li>
            <li><b>🔍 Reactome</b> - Alternative pathway database
                <ul>
                    <li>Curated biological pathways</li>
                    <li>Detailed molecular mechanisms</li>
                    <li>Pathway visualization tools</li>
                    <li>Cross-references to other databases</li>
                </ul>
            </li>
            <li><b>🔍 WikiPathways</b> - Community pathways
                <ul>
                    <li>Open collaborative pathway database</li>
                    <li>Regularly updated by community</li>
                    <li>Integration with other tools</li>
                </ul>
            </li>
        </ul>
        
        <h2>General Descriptions</h2>
        <p>Right-click on description columns for general searches:</p>
        <ul>
            <li><b>📚 Google Scholar</b> - Academic literature search</li>
            <li><b>📚 PubMed</b> - Biomedical literature database
                <ul>
                    <li>Research articles and reviews</li>
                    <li>Clinical studies</li>
                    <li>Free full-text articles (PMC)</li>
                </ul>
            </li>
        </ul>
        
        <h2>How It Works</h2>
        <ol>
            <li><b>Auto-detection:</b> The tool automatically detects column types:
                <ul>
                    <li>Gene columns: gene_id, symbol, gene_symbol</li>
                    <li>GO columns: term_id, go_id, or GO:XXXXXXX pattern</li>
                    <li>KEGG columns: pathway_id, kegg_id, or pathway names</li>
                    <li>Description columns: description, term_name, pathway_name</li>
                </ul>
            </li>
            <li><b>ID Extraction:</b> Automatically extracts IDs from text:
                <ul>
                    <li>GO:0008150 extracted from "GO:0008150 biological_process"</li>
                    <li>hsa04110 extracted from pathway descriptions</li>
                </ul>
            </li>
            <li><b>One-click access:</b> Click any menu item to open in default browser</li>
            <li><b>Context-aware:</b> Shows relevant databases based on data type</li>
        </ol>
        
        <h2>Workflow Examples</h2>
        
        <h3>Example 1: Gene Function Research</h3>
        <ol>
            <li>Load DE analysis results</li>
            <li>Filter for significant genes (padj &lt; 0.05, |log2FC| &gt; 1)</li>
            <li>Right-click on interesting gene symbol</li>
            <li>Select "🔍 GeneCards" for comprehensive overview</li>
            <li>Select "📚 Google Scholar" for recent publications</li>
        </ol>
        
        <h3>Example 2: GO Term Investigation</h3>
        <ol>
            <li>Load GO enrichment results</li>
            <li>Filter top enriched terms (FDR &lt; 0.01)</li>
            <li>Right-click on GO term ID</li>
            <li>Select "🔍 QuickGO" to see term hierarchy</li>
            <li>Select "🔍 NCBI Gene" to find related genes</li>
        </ol>
        
        <h3>Example 3: Pathway Analysis</h3>
        <ol>
            <li>Load KEGG enrichment results</li>
            <li>Right-click on enriched pathway</li>
            <li>Select "🔍 KEGG Pathway" to view pathway diagram</li>
            <li>Select "🔍 Reactome" for alternative pathway view</li>
            <li>Compare pathway information across databases</li>
        </ol>
        
        <h2>Tips</h2>
        <ul>
            <li><b>Multiple Databases:</b> Check multiple databases for comprehensive information</li>
            <li><b>Species Consideration:</b> 
                <ul>
                    <li>GeneCards is best for human genes</li>
                    <li>Ensembl supports multiple species</li>
                    <li>NCBI Gene covers many organisms</li>
                </ul>
            </li>
            <li><b>GO Hierarchy:</b> Use QuickGO or AmiGO to explore parent/child term relationships</li>
            <li><b>Pathway Context:</b> View KEGG pathways to understand gene interactions</li>
            <li><b>Literature Review:</b> Use Google Scholar and PubMed to find relevant research</li>
            <li><b>Quick Reference:</b> Right-click is faster than manual web searches</li>
        </ul>
        
        <h2>Benefits</h2>
        <ul>
            <li>✅ <b>No local database needed</b> - Always up-to-date information</li>
            <li>✅ <b>One-click access</b> - Saves time compared to manual searches</li>
            <li>✅ <b>Multiple resources</b> - Compare information across databases</li>
            <li>✅ <b>Context-aware</b> - Shows relevant databases for each data type</li>
            <li>✅ <b>Auto ID extraction</b> - No need to copy-paste IDs manually</li>
        </ul>
        """
    
    def _get_export(self):
        """Export section"""
        return """
        <h1>12. Export &amp; Clipboard</h1>
        
        <h2>Exporting Data</h2>
        <p>Export any tab's data to file:</p>
        <ol>
            <li>Switch to the tab you want to export</li>
            <li>Select <b>File &rarr;Export Current Tab</b> (or <b>Ctrl+E</b>)</li>
            <li>Choose format:
                <ul>
                    <li>Excel (.xlsx)</li>
                    <li>CSV (.csv)</li>
                    <li>TSV (.tsv)</li>
                </ul>
            </li>
            <li>Choose save location and filename</li>
        </ol>
        
        <h2>Cell Selection</h2>
        <p>Flexible cell selection in data tables:</p>
        <ul>
            <li>Click and drag to select individual cells</li>
            <li>Select cell ranges (not just full rows)</li>
            <li>Selection color: light blue for better visibility</li>
            <li>Multi-selection support (Ctrl+Click)</li>
        </ul>
        
        <h2>Clipboard Operations</h2>
        <p>Copy and paste data like in Excel:</p>
        
        <h3>Copying (Ctrl+C):</h3>
        <ul>
            <li>Select cells in any data table</li>
            <li>Press <b>Ctrl+C</b></li>
            <li>Data is copied in tab-delimited format</li>
            <li>Compatible with Excel, spreadsheet apps</li>
        </ul>
        
        <h3>Pasting (Ctrl+V):</h3>
        <ul>
            <li>Copy gene IDs from any source (Excel, text file, etc.)</li>
            <li>Click in the Gene List input area (Filter Panel)</li>
            <li>Press <b>Ctrl+V</b></li>
            <li>Genes are automatically parsed from clipboard</li>
            <li>Works with tab-delimited data - uses first column only</li>
        </ul>
        
        <p><b>Workflow Example:</b></p>
        <ol>
            <li>Find interesting genes in Comparison Statistics table</li>
            <li>Select the gene_id column cells</li>
            <li>Press Ctrl+C to copy</li>
            <li>Click in Gene List input</li>
            <li>Press Ctrl+V to paste</li>
            <li>Apply filter to get detailed view of those genes</li>
        </ol>
        """
    
    def _get_tips(self):
        """Tips and Shortcuts section"""
        return """
        <h1>13. Tips &amp; Shortcuts</h1>
        
        <h2>Keyboard Shortcuts</h2>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr>
                <th>Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><b>Ctrl+O</b></td>
                <td>Open Dataset</td>
            </tr>
            <tr>
                <td><b>Ctrl+E</b></td>
                <td>Export Current Tab</td>
            </tr>
            <tr>
                <td><b>Ctrl+F</b></td>
                <td>Apply Filter</td>
            </tr>
            <tr>
                <td><b>Ctrl+V</b></td>
                <td>Volcano Plot (or Paste in Gene List)</td>
            </tr>
            <tr>
                <td><b>Ctrl+P</b></td>
                <td>PCA Plot</td>
            </tr>
            <tr>
                <td><b>Ctrl+C</b></td>
                <td>Copy Selected Cells</td>
            </tr>
            <tr>
                <td><b>Ctrl+Q</b></td>
                <td>Exit Application</td>
            </tr>
            <tr>
                <td><b>F1</b></td>
                <td>Open this Help Documentation</td>
            </tr>
        </table>
        
        <h2>Best Practices</h2>
        <ul>
            <li><b>Dataset Naming:</b> Use descriptive names when loading datasets for easier identification</li>
            <li><b>Recent Files:</b> Leverage Recent Files menu for quick access to frequently used data</li>
            <li><b>Dataset Renaming:</b> Use the Rename button to update dataset names as your analysis progresses</li>
            <li><b>Data Quality:</b> Ensure your input data has proper gene IDs and symbols</li>
            <li><b>Column Names:</b> Use standard names (gene_id, symbol, log2FC, padj) - case insensitive</li>
            <li><b>Multiple Filters:</b> Apply filters sequentially to narrow down results</li>
            <li><b>Comparison Options:</b> Choose intersection vs. union carefully:
                <ul>
                    <li>Intersection: Find genes changed in ALL conditions (more stringent)</li>
                    <li>Union: Find genes changed in ANY condition (more comprehensive)</li>
                </ul>
            </li>
            <li><b>Visualization Settings:</b> All plot settings are saved between sessions</li>
            <li><b>Tab Management:</b> Close unused tabs (click X) to keep workspace organized</li>
            <li><b>Drag & Drop:</b> Quickly load files by dragging them onto the application window</li>
        </ul>
        
        <h2>New Features Summary</h2>
        <ul>
            <li><b>🌡️ Multi-Group Heatmap:</b> LRT omnibus result CSV → interactive Z-score clustermap
                with group color bars, gene cluster cutting, and CSV export</li>
            <li><b>Gene List Filtering on Multi-Group:</b> Filter by gene symbol on multi-group sheets;
                child filtered sheets can be directly passed to the heatmap dialog</li>
            <li><b>Dataset Database:</b> Parquet-based DB for instant dataset loading</li>
            <li><b>📥 Import Folder:</b> Merge pipeline output folders into the DB in one click</li>
            <li><b>merge_db.py:</b> CLI tool for batch-merging multiple pipeline runs</li>
            <li><b>Auto-Register:</b> Drop parquet files and click Refresh — no metadata editing</li>
            <li><b>🔵 PCA Plot:</b> Sample-level PCA from abundance columns (Ctrl+P)</li>
            <li><b>🔍 GO Term List Filtering:</b> Paste GO:XXXXXXX IDs into the Filter Panel to filter GO datasets to specific terms</li>
            <li><b>📊 GO Term Comparison:</b> Compare enriched GO/KEGG terms across multiple datasets side by side with an interactive dot plot</li>
            <li><b>Window Icons:</b> Each window has a unique icon for easy identification in taskbar</li>
            <li><b>Dataset Rename:</b> Change dataset names anytime - updates everywhere automatically</li>
            <li><b>Recent Files:</b> Quick access to your 10 most recent files with path preview</li>
            <li><b>Drag &amp; Drop:</b> Drop Excel files anywhere to load datasets instantly</li>
            <li><b>Dot Plot:</b> New visualization for comparison results with clustering</li>
            <li><b>Smart Tooltips:</b> Auto-positioning tooltips that never get cut off</li>
            <li><b>Gene Clustering:</b> Reorder genes by similarity in heatmaps and dot plots</li>
            <li><b>Cell Selection:</b> Select individual cells, not just rows</li>
            <li><b>Clipboard:</b> Ctrl+C/V support for Excel-like workflow</li>
            <li><b>Comparison Panel:</b> Dedicated panel for dataset comparisons with clear options</li>
        </ul>
           
        <h2>Performance Tips</h2>
        <ul>
            <li><b>Large Datasets:</b> Use Basic or DE Analysis column view to improve responsiveness</li>
            <li><b>Heatmaps:</b> Limit to top 100-200 genes for better performance</li>
            <li><b>Gene Clustering:</b> May take longer with >100 genes - consider pre-filtering</li>
            <li><b>Multiple Tabs:</b> Close tabs you're not using to free up memory</li>
        </ul>
        
        <h2>Getting Help</h2>
        <ul>
            <li>Press <b>F1</b> anytime to open this documentation</li>
            <li>Check <b>Help &rarr;About</b> for version information and latest features</li>
            <li>Review log messages at the bottom of the window for detailed status</li>
        </ul>
        """
    
    def _get_go_kegg_analysis(self):
        """GO/KEGG Analysis section"""
        return """
        <h1>5. GO/KEGG Analysis</h1>
        
        <h2>Overview</h2>
        <p>CMG-SeqViewer provides specialized tools for Gene Ontology (GO) and KEGG pathway enrichment analysis.</p>
        
        <h2>Loading GO/KEGG Data</h2>
        <p>Load enrichment results from Excel files. The tool automatically detects GO/KEGG data by column names.</p>
        
        <h2>Filtering GO/KEGG Results</h2>
        <p>Filter Panel provides specialized options:</p>
        <ul>
            <li><b>FDR Threshold:</b> Maximum adjusted p-value (default: 0.05)</li>
            <li><b>Ontology:</b> BP (Biological Process), MF (Molecular Function), CC (Cellular Component), KEGG, or All</li>
            <li><b>Gene Set:</b> UP/DOWN/TOTAL (indicates which DEG group was analyzed)</li>
        </ul>
        <p><i>Note: "Gene Set" is different from "Regulation" - it shows which DEG group was used for GO analysis.</i></p>
        
        <h2>GO Term Clustering</h2>
        <p>Cluster similar GO terms to reduce redundancy (ClueGO-style):</p>
        <ol>
            <li>Filter GO data (e.g., FDR &lt; 1e-5, BP, UP)</li>
            <li>Select <b>Analysis &rarr; Cluster GO Terms</b></li>
            <li>Configure:
                <ul>
                    <li><b>Similarity Method:</b> Jaccard (shared genes) or Kappa</li>
                    <li><b>Threshold:</b> 0.0-1.0 (default: 0.3, higher = stricter)</li>
                    <li><b>Clustering Method:</b> average, complete, single, ward</li>
                </ul>
            </li>
            <li>View interactive dialog with network visualization</li>
            <li>Click <b>Apply</b> to create Clustered tab</li>
        </ol>
        
        <h3>Clustering Features:</h3>
        <ul>
            <li>Interactive network (pan, zoom, hover for details)</li>
            <li>Color-coded cluster legend (collapsible)</li>
            <li>Representative terms for each cluster</li>
            <li>Singleton terms (unclustered)</li>
            <li>Multiple layout algorithms</li>
            <li>Results table with cluster IDs</li>
        </ul>
        
        <h2>GO/KEGG Visualization</h2>
        <h3>Dot Plot:</h3>
        <ul>
            <li>Select <b>Visualization &rarr; GO/KEGG Dot Plot</b></li>
            <li>Dot size: gene ratio, gene count, or fixed</li>
            <li>Dot color: FDR, p-value, or q-value</li>
            <li>Shows top N enriched terms</li>
        </ul>
        
        <h3>Bar Chart:</h3>
        <ul>
            <li>Select <b>Visualization &rarr; GO/KEGG Bar Chart</b></li>
            <li>Shows -log10(FDR) for top terms</li>
            <li>Color-coded by ontology</li>
        </ul>
        
        <h3>Network Chart:</h3>
        <ul>
            <li>Select <b>Visualization &rarr; GO/KEGG Network Chart</b></li>
            <li>Requires Clustered tab</li>
            <li>Nodes sized by gene count or FDR</li>
            <li>Edges weighted by similarity</li>
            <li>Color-coded by cluster with legend</li>
        </ul>
        
        <h2>Common Workflows</h2>
        <p><b>Basic Analysis:</b></p>
        <ol>
            <li>Load GO data</li>
            <li>Filter (FDR &lt; 0.05, BP, UP)</li>
            <li>Create Dot Plot</li>
            <li>Export results</li>
        </ol>
        
        <p><b>Clustered Analysis:</b></p>
        <ol>
            <li>Load GO data</li>
            <li>Filter (FDR &lt; 1e-5, BP)</li>
            <li>Cluster GO Terms</li>
            <li>Apply clustering</li>
            <li>Create Network Chart</li>
            <li>Export clustered results</li>
        </ol>
        
        <h2>GO Term List Filtering</h2>
        <p>Filter a GO/KEGG dataset to a specific set of GO term IDs — useful when you already know
        which terms you want to compare across datasets.</p>

        <h3>How to use</h3>
        <ol>
            <li>Make sure a <b>GO/KEGG dataset tab</b> is active</li>
            <li>Open the <b>Filter Panel</b> and select the <b>Gene List</b> tab</li>
            <li>Enter GO term IDs (one per line) — e.g.:
                <pre style="background:#f4f4f4; padding:6px; border-radius:4px; font-size:11px;">GO:0006915
GO:0007049
GO:0008150</pre>
            </li>
            <li>Click <b>Apply Filter</b></li>
            <li>A new tab appears: <em>"Filtered: GO Term List (N terms)"</em></li>
        </ol>

        <h3>Notes</h3>
        <ul>
            <li>GO term IDs must follow the <code>GO:XXXXXXX</code> or <code>KEGG:xxxXXXXX</code> format</li>
            <li>If the active dataset is not a GO/KEGG type, or if non-GO IDs are entered into
                Gene Symbol mode, the app shows a warning and aborts</li>
            <li>The filter matches against the <code>term_id</code> / <code>go_id</code> column
                of the GO dataset</li>
            <li>Filtered results can be passed directly to the GO Term Comparison workflow</li>
        </ul>

        <h2>Best Practices</h2>
        <ul>
            <li>Filter to meaningful FDR before clustering (&lt; 1e-5 recommended)</li>
            <li>Cluster each ontology (BP, MF, CC) separately</li>
            <li>Start with 0.3 similarity threshold, increase for fewer clusters</li>
            <li>Focus on representative terms for biological interpretation</li>
            <li>Re-filter Filtered tabs to narrow down results further</li>
        </ul>
        """

    def _get_go_term_comparison(self):
        """GO Term Comparison section"""
        return """
        <h1>5b. GO Term Comparison</h1>

        <h2>Overview</h2>
        <p>GO Term Comparison lets you compare enriched GO/KEGG terms <b>across multiple datasets</b>
        side by side. It collects a union of terms from all selected datasets and builds
        a comparison table with FDR, gene count, and fold enrichment per dataset — then
        optionally visualizes the result as an interactive dot plot.</p>

        <h2>Requirements</h2>
        <ul>
            <li>At least <b>2 GO/KEGG datasets</b> loaded in the session</li>
            <li>A <b>GO term ID list</b> entered in the Filter Panel (Gene List input area) —
                the comparison is scoped to these terms only</li>
        </ul>
        <p><em>If no GO term IDs are provided, the app shows an error and cancels.</em></p>

        <h2>Step-by-Step Workflow</h2>
        <ol>
            <li>Load 2 or more GO/KEGG datasets (e.g., Ctrl_GO, KO_GO, OE_GO)</li>
            <li>Enter the GO term IDs you want to compare in the <b>Filter Panel → Gene List</b>:
                <pre style="background:#f4f4f4; padding:6px; border-radius:4px; font-size:11px;">GO:0006915
GO:0007049
GO:0008150</pre>
            </li>
            <li>Open the <b>Comparison Panel</b> (left panel, below Filter Panel)</li>
            <li>Select the GO datasets to compare</li>
            <li>Set <b>Comparison Type</b> to <em>GO Term Comparison</em></li>
            <li>Click <b>Apply</b></li>
            <li>A new tab appears: <em>"Comparison: GO Terms"</em></li>
        </ol>

        <h2>Comparison Results Table</h2>
        <p>The result tab contains one row per GO term with columns for each dataset:</p>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr style="background:#f0f0f0;">
                <th>Column</th><th>Description</th>
            </tr>
            <tr><td><code>term_id</code></td><td>GO/KEGG term identifier (e.g., GO:0006915)</td></tr>
            <tr><td><code>description</code></td><td>Term name / description</td></tr>
            <tr><td><code>ontology</code></td><td>BP / MF / CC / KEGG</td></tr>
            <tr><td><code>&lt;Dataset&gt;_fdr</code></td><td>Adjusted p-value (FDR) for each dataset</td></tr>
            <tr><td><code>&lt;Dataset&gt;_gene_count</code></td><td>Number of enriched genes</td></tr>
            <tr><td><code>&lt;Dataset&gt;_fold_enrichment</code></td><td>Fold enrichment score</td></tr>
            <tr><td><code>found_in</code></td><td>Comma-separated list of datasets where the term is significant</td></tr>
        </table>
        <p>Terms not found in a dataset receive <code>NaN</code> for that dataset's columns.</p>

        <h2>GO Term Comparison Dot Plot</h2>
        <p>After running a GO Term Comparison, visualize the result as a dot plot:</p>
        <ol>
            <li>Switch to the <em>"Comparison: GO Terms"</em> tab</li>
            <li>Click <b>Visualization → GO/KEGG Dot Plot</b></li>
        </ol>

        <h3>Plot Layout</h3>
        <ul>
            <li><b>X-axis:</b> Datasets (one column per dataset)</li>
            <li><b>Y-axis:</b> GO terms</li>
            <li><b>Dot color:</b> FDR value (color scale: low FDR = deep color)</li>
            <li><b>Dot size:</b> Gene Count or Fold Enrichment (selectable)</li>
        </ul>

        <h3>Dot Plot Controls</h3>
        <table border="1" cellpadding="5" cellspacing="0" width="100%">
            <tr style="background:#f0f0f0;"><th>Control</th><th>Description</th></tr>
            <tr><td><b>Dot Size Metric</b></td>
                <td>Choose what determines dot area:
                    <ul>
                        <li><b>Gene Count</b> — absolute number of enriched genes</li>
                        <li><b>Fold Enrichment</b> — enrichment score relative to background</li>
                        <li><b>Gene Ratio</b> — fraction of genes in the term (if available)</li>
                    </ul>
                </td>
            </tr>
            <tr><td><b>Top N Terms</b></td>
                <td>Limit the plot to the N most significant GO terms (ranked by minimum FDR across datasets)</td>
            </tr>
            <tr><td><b>Transpose</b></td>
                <td>Swap axes: X = GO Terms, Y = Datasets</td>
            </tr>
            <tr><td><b>Color Map</b></td>
                <td>Matplotlib colormap for FDR values (default: <em>RdYlBu_r</em>)</td>
            </tr>
            <tr><td><b>FDR range</b></td>
                <td>Min/max FDR cutoff for the color scale</td>
            </tr>
            <tr><td><b>Figure Size</b></td>
                <td>Width and height in inches</td>
            </tr>
        </table>

        <h3>Legend</h3>
        <p>The dot size legend uses <b>three biologically meaningful reference values</b>
        (small / medium / large) derived from the chosen metric's typical range,
        so dot sizes are consistent across different datasets and plots.</p>

        <h3>Export</h3>
        <ul>
            <li><b>💾 Save Figure</b> — PNG / SVG / PDF</li>
            <li>Right-click the comparison result table to copy or export as CSV</li>
        </ul>

        <h2>Tips</h2>
        <ul>
            <li>Pre-filter each GO dataset by FDR before running comparison —
                this reduces noise in the result table</li>
            <li>Enter only biologically relevant GO term IDs (e.g., terms from a published
                pathway list) to keep the comparison focused</li>
            <li>Use <b>Transpose</b> when you have many datasets but few terms</li>
            <li>Terms with <code>NaN</code> FDR appear as empty (no dot) in the plot —
                this visually highlights dataset-specific enrichment</li>
        </ul>
        """

