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
            "3. Data Filtering",
            "4. GO/KEGG Analysis",
            "5. Statistical Analysis",
            "6. Visualization",
            "7. Dataset Comparison",
            "8. Export & Clipboard",
            "9. Tips & Shortcuts"
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
            self._get_filtering(),
            self._get_go_kegg_analysis(),
            self._get_statistical_analysis(),
            self._get_visualization(),
            self._get_comparison(),
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
        RNA-Seq differential expression data. This application provides:</p>
        <ul>
            <li>Multi-dataset management and comparison</li>
            <li>Flexible filtering options</li>
            <li>Statistical analysis tools (Fisher's Exact, GSEA)</li>
            <li>Interactive visualizations (Volcano, Heatmap, Dot Plot, Venn)</li>
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
            <li><b>File:</b> Open datasets, recent files, export data</li>
            <li><b>Analysis:</b> Filtering, Fisher's Exact Test, GSEA, dataset comparison</li>
            <li><b>View:</b> Column display level, decimal precision</li>
            <li><b>Visualization:</b> Volcano plots, histograms, heatmaps, dot plots, Venn diagrams</li>
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
            <li><b>Basic:</b> Gene ID, Symbol, and Abundance columns only</li>
            <li><b>DE Analysis:</b> Basic + log2FC and padj columns</li>
            <li><b>Full:</b> All columns in the dataset</li>
        </ul>
        
        <h2>Decimal Precision</h2>
        <p>Adjust number display precision via <b>View &rarr;Decimal Precision</b>:</p>
        <ul>
            <li>Choose from 1 to 6 decimal places</li>
            <li>Default is 3 decimal places</li>
            <li>Applies to all numeric columns in the data view</li>
        </ul>
        """
    
    def _get_filtering(self):
        """Filtering section"""
        return """
        <h1>3. Data Filtering</h1>
        
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
    
    def _get_statistical_analysis(self):
        """Statistical Analysis section"""
        return """
        <h1>5. Statistical Analysis</h1>
        
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
        <h1>6. Visualization</h1>
        
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
    
    def _get_comparison(self):
        """Comparison section"""
        return """
        <h1>7. Dataset Comparison</h1>
        
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
    
    def _get_export(self):
        """Export section"""
        return """
        <h1>8. Export & Clipboard</h1>
        
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
        <h1>9. Tips & Shortcuts</h1>
        
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
            <li><b>Window Icons:</b> Each window has a unique icon for easy identification in taskbar</li>
            <li><b>Dataset Rename:</b> Change dataset names anytime - updates everywhere automatically</li>
            <li><b>Recent Files:</b> Quick access to your 10 most recent files with path preview</li>
            <li><b>Drag & Drop:</b> Drop Excel files anywhere to load datasets instantly</li>
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
        <h1>4. GO/KEGG Analysis</h1>
        
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
        
        <h2>Best Practices</h2>
        <ul>
            <li>Filter to meaningful FDR before clustering (&lt; 1e-5 recommended)</li>
            <li>Cluster each ontology (BP, MF, CC) separately</li>
            <li>Start with 0.3 similarity threshold, increase for fewer clusters</li>
            <li>Focus on representative terms for biological interpretation</li>
            <li>Re-filter Filtered tabs to narrow down results further</li>
        </ul>
        """

