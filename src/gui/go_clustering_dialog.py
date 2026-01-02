# -*- coding: utf-8 -*-
"""
Interactive GO Term Clustering Dialog

This dialog provides an interface for clustering GO enrichment results
using Jaccard similarity and hierarchical clustering, with ClueGO-style
network visualization.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QWidget, QTabWidget, QTextEdit,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QFormLayout,
    QSlider, QCheckBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QBrush, QColor, QPixmap, QIcon

from models.standard_columns import StandardColumns
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from scipy.spatial import ConvexHull

import pandas as pd
import numpy as np
import networkx as nx
from math import ceil, sqrt

from utils.go_clustering import GOClustering


class ClusteringWorker(QThread):
    """Background thread for performing GO term clustering"""
    
    finished = pyqtSignal(object, object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    
    def __init__(self, df, similarity_threshold):
        super().__init__()
        self.df = df
        self.similarity_threshold = similarity_threshold
        
    def run(self):
        """Execute clustering in background thread"""
        try:
            self.progress.emit(10)
            
            # Ensure _gene_set column exists
            if '_gene_set' not in self.df.columns:
                # Try to create _gene_set from gene columns
                # Check many possible column names (standard + common variations)
                gene_col = None
                possible_cols = [
                    'gene_symbols',  # standardized column name
                    'geneID', 'Genes', 'genes', 'GeneID',
                    'Gene Symbols', 'GeneSymbols', 'gene_id',
                    'core_enrichment', 'core enrichment'
                ]
                for col in possible_cols:
                    if col in self.df.columns:
                        gene_col = col
                        break
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Available columns: {list(self.df.columns)}")
                logger.info(f"Found gene column: {gene_col}")
                
                if gene_col:
                    self.df['_gene_set'] = self.df[gene_col].apply(
                        lambda x: set(str(x).split('/')) if pd.notna(x) and str(x).strip() else set()
                    )
                    # Log sample gene sets
                    non_empty = [gs for gs in self.df['_gene_set'] if len(gs) > 0]
                    logger.info(f"Created _gene_set: {len(non_empty)} non-empty out of {len(self.df)}")
                else:
                    # No gene column found - create empty sets
                    logger.warning("No gene column found! Creating empty gene sets.")
                    self.df['_gene_set'] = [set() for _ in range(len(self.df))]
            
            self.progress.emit(30)
            clustering = GOClustering(similarity_threshold=self.similarity_threshold)
            clustered_df, clusters = clustering.cluster_terms(self.df)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Clustering result: {len(clusters)} clusters returned")
            if clusters:
                logger.info(f"Cluster sizes: {[len(m) for m in list(clusters.values())[:10]]}")
            
            # Verify clustered_df has the expected columns
            logger.info(f"Clustered DF columns: {list(clustered_df.columns)}")
            logger.info(f"Clustered DF cluster_id sample: {clustered_df['cluster_id'].value_counts().head()}")
            logger.info(f"Clustered DF representative count: {clustered_df['is_representative'].sum()}")
            
            self.progress.emit(90)
            self.finished.emit(clustered_df, clusters)
            self.progress.emit(100)
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n\n{traceback.format_exc()}")


class GOClusteringDialog(QDialog):
    """Interactive dialog for GO term clustering and visualization"""
    
    # Signal to emit clustered data back to main GUI
    clustered_data_ready = pyqtSignal(pd.DataFrame)
    
    COLORS = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
        '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',
        '#EF476F', '#06FFA5', '#118AB2', '#FFD166', '#073B4C',
        '#A8DADC', '#E63946', '#F1FAEE', '#457B9D', '#1D3557'
    ]
    
    def __init__(self, dataset, parent=None):
        super().__init__(parent)
        # Extract DataFrame from Dataset object
        if hasattr(dataset, 'dataframe'):
            self.dataset = dataset.dataframe.copy()
        else:
            self.dataset = dataset.copy()
        self.clustered_df = None
        self.clusters = None
        self.network_graph = None
        self.node_positions = None
        self.cluster_colors = {}
        
        # Visualization settings (will be updated from widgets)
        self.node_size = 100
        self.edge_alpha = 0.2
        self.label_size = 9
        self.show_hulls = True
        
        # Cluster size filter settings
        self.min_cluster_size = 2
        self.max_cluster_size = 100
        
        self.setWindowTitle("GO Term Clustering")
        self.resize(1400, 900)
        # Enable maximize button
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        settings_panel = self._create_settings_panel()
        splitter.addWidget(settings_panel)
        results_panel = self._create_results_panel()
        splitter.addWidget(results_panel)
        # Adjust ratio: 2:8 to give more space to network visualization
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 8)
        # Set initial sizes (20% settings, 80% results)
        total_width = 1400
        splitter.setSizes([int(total_width * 0.2), int(total_width * 0.8)])
        layout.addWidget(splitter)
        button_layout = self._create_buttons()
        layout.addLayout(button_layout)
        
    def _create_settings_panel(self):
        """Create the left panel with clustering settings and help"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Clustering Parameters Group
        params_group = QGroupBox("⚙️ Clustering Parameters")
        params_layout = QFormLayout(params_group)
        params_layout.setVerticalSpacing(12)
        
        # Similarity Threshold with Slider
        threshold_container = QWidget()
        threshold_layout = QVBoxLayout(threshold_container)
        threshold_layout.setContentsMargins(0, 0, 0, 0)
        threshold_layout.setSpacing(4)
        
        # Spinbox and slider in horizontal layout
        threshold_input_layout = QHBoxLayout()
        
        self.similarity_spin = QDoubleSpinBox()
        self.similarity_spin.setRange(0.0, 1.0)
        self.similarity_spin.setSingleStep(0.05)
        self.similarity_spin.setValue(0.7)
        self.similarity_spin.setDecimals(2)
        self.similarity_spin.setMinimumWidth(60)
        self.similarity_spin.setToolTip("Jaccard similarity threshold (0.0-1.0)")
        threshold_input_layout.addWidget(self.similarity_spin)
        
        self.similarity_slider = QSlider(Qt.Orientation.Horizontal)
        self.similarity_slider.setRange(0, 100)
        self.similarity_slider.setValue(70)
        self.similarity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.similarity_slider.setTickInterval(10)
        threshold_input_layout.addWidget(self.similarity_slider)
        
        # Connect slider and spinbox
        self.similarity_slider.valueChanged.connect(
            lambda v: self.similarity_spin.setValue(v / 100.0)
        )
        self.similarity_spin.valueChanged.connect(
            lambda v: self.similarity_slider.setValue(int(v * 100))
        )
        
        threshold_layout.addLayout(threshold_input_layout)
        
        # Help text for threshold
        threshold_help = QLabel(
            "<small><i>Recommended: <b>0.7</b> for balanced clustering<br>"
            "Higher (0.8-0.9) = tighter, more specific clusters<br>"
            "Lower (0.4-0.6) = broader, more general clusters</i></small>"
        )
        threshold_help.setStyleSheet("color: #666; margin-left: 2px;")
        threshold_help.setWordWrap(True)
        threshold_layout.addWidget(threshold_help)
        
        params_layout.addRow("Similarity Threshold:", threshold_container)
        
        # Cluster Size Filter
        size_filter_label = QLabel("<b>Valid Cluster Size Range</b>")
        params_layout.addRow("", size_filter_label)
        
        # Min cluster size
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(2, 50)
        self.min_size_spin.setValue(2)
        self.min_size_spin.setToolTip("Minimum number of terms to form a valid cluster")
        self.min_size_spin.setMinimumWidth(60)
        params_layout.addRow("Min Terms:", self.min_size_spin)
        
        # Max cluster size
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setRange(3, 200)
        self.max_size_spin.setValue(100)
        self.max_size_spin.setToolTip("Maximum number of terms in a valid cluster")
        self.max_size_spin.setMinimumWidth(60)
        params_layout.addRow("Max Terms:", self.max_size_spin)
        
        size_help = QLabel(
            "<small><i>Clusters outside this range will be<br>"
            "displayed separately on the right side</i></small>"
        )
        size_help.setStyleSheet("color: #666; margin-left: 2px;")
        size_help.setWordWrap(True)
        params_layout.addRow("", size_help)
        
        layout.addWidget(params_group)
        
        # Run Button
        self.run_button = QPushButton("▶ Run Clustering")
        self.run_button.clicked.connect(self._run_clustering)
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 16px;
                font-size: 11pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        layout.addWidget(self.run_button)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        layout.addSpacing(10)
        
        # How to Use
        howto_group = QGroupBox("📖 How to Use")
        howto_layout = QVBoxLayout(howto_group)
        
        howto_text = QLabel(
            "<ol style='margin-left: -20px;'>"
            "<li><b>Set similarity threshold</b> - Default 0.7 works well</li>"
            "<li><b>Set cluster size range</b> - Filter valid cluster sizes</li>"
            "<li><b>Click 'Run Clustering'</b> - Wait for analysis</li>"
            "<li><b>Explore network</b> - Hover, zoom, adjust labels</li>"
            "<li><b>Review clusters</b> - Check Summary and tables</li>"
            "<li><b>Export results</b> - Save to Excel for further use</li>"
            "</ol>"
        )
        howto_text.setWordWrap(True)
        howto_text.setStyleSheet("font-size: 9pt;")
        howto_layout.addWidget(howto_text)
        
        layout.addWidget(howto_group)
        
        # Visualization Guide
        guide_group = QGroupBox("📊 Network Visualization")
        guide_layout = QVBoxLayout(guide_group)
        
        help_content = QTextEdit()
        help_content.setReadOnly(True)
        help_content.setMaximumHeight(280)
        help_content.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6;")
        help_content.setHtml("""
        <style>
            body { font-family: 'Segoe UI', Arial; font-size: 9pt; }
            h4 { color: #2c3e50; margin-top: 6px; margin-bottom: 3px; }
            ul { margin-top: 2px; margin-bottom: 2px; padding-left: 18px; }
            li { margin-bottom: 1px; }
            .highlight { color: #007bff; font-weight: bold; }
        </style>
        
        <h4>🔵 Nodes</h4>
        <ul>
            <li><span class="highlight">Large</span>: Representative terms (lowest FDR)</li>
            <li><span class="highlight">Small</span>: Member terms</li>
            <li><span class="highlight">Colors</span>: Unique per cluster</li>
            <li><span class="highlight">Gray</span>: Singletons or excluded</li>
        </ul>
        
        <h4>📐 Layout</h4>
        <ul>
            <li><b>Valid clusters</b>: Grid layout on left/center</li>
            <li><b>Small/Large clusters</b>: Right side column</li>
            <li><b>Hulls</b>: Convex boundaries around clusters</li>
        </ul>
        
        <h4>🔗 Edges</h4>
        <ul>
            <li>Connect similar terms (Jaccard >0.3)</li>
            <li>Width = similarity strength</li>
        </ul>
        
        <h4>🖱️ Interaction</h4>
        <ul>
            <li><b>Hover</b>: See term details</li>
            <li><b>Zoom/Pan</b>: Use toolbar</li>
            <li><b>Refresh</b>: Update label count & node size</li>
        </ul>
        """)
        guide_layout.addWidget(help_content)
        
        layout.addWidget(guide_group)
        
        layout.addStretch()
        
        return panel
        
    def _create_results_panel(self):
        """Create the right panel with results tabs"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.results_label = QLabel("No clustering results yet. Configure settings and click 'Run Clustering'.")
        self.results_label.setWordWrap(True)
        layout.addWidget(self.results_label)
        self.tab_widget = QTabWidget()
        self.tab_widget.setEnabled(False)
        network_tab = self._create_network_tab()
        self.tab_widget.addTab(network_tab, "Network Visualization")
        summary_tab = self._create_summary_tab()
        self.tab_widget.addTab(summary_tab, "Summary")
        cluster_tab = self._create_cluster_tab()
        self.tab_widget.addTab(cluster_tab, "Clustered Terms")
        representative_tab = self._create_representative_tab()
        self.tab_widget.addTab(representative_tab, "Representatives")
        layout.addWidget(self.tab_widget)
        return panel
        
    def _create_network_tab(self):
        """Create the network visualization tab with customization settings"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Settings panel with GroupBox
        settings_group = QGroupBox("🎨 Visualization Settings")
        settings_layout = QHBoxLayout(settings_group)
        settings_layout.setContentsMargins(8, 8, 8, 8)
        
        # Node size
        node_size_label = QLabel("Node Size:")
        settings_layout.addWidget(node_size_label)
        
        self.node_size_spin = QSpinBox()
        self.node_size_spin.setRange(100, 3000)
        self.node_size_spin.setSingleStep(100)
        self.node_size_spin.setValue(100)
        self.node_size_spin.setToolTip("Size of representative nodes (members are 30% of this)")
        self.node_size_spin.setMinimumWidth(80)
        settings_layout.addWidget(self.node_size_spin)
        
        settings_layout.addSpacing(20)
        
        # Edge transparency
        edge_alpha_label = QLabel("Edge Opacity:")
        settings_layout.addWidget(edge_alpha_label)
        
        self.edge_alpha_spin = QDoubleSpinBox()
        self.edge_alpha_spin.setRange(0.0, 1.0)
        self.edge_alpha_spin.setSingleStep(0.1)
        self.edge_alpha_spin.setValue(0.2)
        self.edge_alpha_spin.setDecimals(1)
        self.edge_alpha_spin.setToolTip("Transparency of edges (0=invisible, 1=opaque)")
        self.edge_alpha_spin.setMinimumWidth(60)
        settings_layout.addWidget(self.edge_alpha_spin)
        
        settings_layout.addSpacing(20)
        
        # Label font size
        label_size_label = QLabel("Label Size:")
        settings_layout.addWidget(label_size_label)
        
        self.label_size_spin = QSpinBox()
        self.label_size_spin.setRange(6, 16)
        self.label_size_spin.setValue(9)
        self.label_size_spin.setToolTip("Font size of term labels")
        self.label_size_spin.setMinimumWidth(60)
        settings_layout.addWidget(self.label_size_spin)
        
        settings_layout.addSpacing(20)
        
        # Show convex hulls
        self.show_hulls_checkbox = QCheckBox("Show Hulls")
        self.show_hulls_checkbox.setChecked(True)
        self.show_hulls_checkbox.setToolTip("Show convex hull boundaries around clusters")
        settings_layout.addWidget(self.show_hulls_checkbox)
        
        settings_layout.addSpacing(20)
        
        # Refresh button
        self.refresh_button = QPushButton("🔄 Refresh Plot")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.refresh_button.clicked.connect(self._update_network_graph)
        self.refresh_button.setEnabled(False)
        self.refresh_button.setToolTip("Update the network visualization with current settings")
        settings_layout.addWidget(self.refresh_button)
        
        settings_layout.addStretch()
        
        layout.addWidget(settings_group)

        # Matplotlib figure
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.mpl_connect('motion_notify_event', self._on_network_hover)

        # Toolbar
        self.toolbar = NavigationToolbar(self.canvas, tab)

        # Place canvas and a Qt-side legend in a horizontal split so the
        # canvas fills the left area and the legend is a persistent Qt widget
        content_hbox = QHBoxLayout()

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.toolbar)
        left_layout.addWidget(self.canvas)

        # Legend container on the right (scrollable via QListWidget)
        legend_group = QGroupBox("Legend")
        legend_layout = QVBoxLayout(legend_group)
        legend_layout.setContentsMargins(6, 6, 6, 6)
        self.legend_list = QListWidget()
        self.legend_list.setWordWrap(True)
        self.legend_list.setMinimumWidth(260)
        legend_layout.addWidget(self.legend_list)

        content_hbox.addWidget(left_widget, 4)
        content_hbox.addWidget(legend_group, 1)

        layout.addLayout(content_hbox)

        return tab
        
    def _create_summary_tab(self):
        """Create the summary statistics tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        return tab
        
    def _create_cluster_tab(self):
        """Create the clustered terms table tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.cluster_table = QTableWidget()
        self.cluster_table.setSortingEnabled(True)
        layout.addWidget(self.cluster_table)
        return tab
        
    def _create_representative_tab(self):
        """Create the representative terms table tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.representative_table = QTableWidget()
        self.representative_table.setSortingEnabled(True)
        layout.addWidget(self.representative_table)
        return tab
        
    def _create_buttons(self):
        """Create bottom button layout"""
        layout = QHBoxLayout()
        layout.addStretch()
        self.export_button = QPushButton("Export Clusters")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_clusters)
        layout.addWidget(self.export_button)
        self.apply_button = QPushButton("Apply")
        self.apply_button.setEnabled(False)
        self.apply_button.setToolTip("Apply clustering and create filtered dataset")
        self.apply_button.clicked.connect(self._apply_clustering)
        layout.addWidget(self.apply_button)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        layout.addWidget(close_button)
        return layout
        
    def _run_clustering(self):
        """Execute clustering in background thread"""
        if self.dataset is None or self.dataset.empty:
            QMessageBox.warning(self, "No Data", "No GO enrichment data available for clustering.")
            return
        
        # Update cluster size parameters
        self.min_cluster_size = self.min_size_spin.value()
        self.max_cluster_size = self.max_size_spin.value()
        
        similarity_threshold = self.similarity_spin.value()
        self.run_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.worker = ClusteringWorker(self.dataset, similarity_threshold)
        self.worker.finished.connect(self._on_clustering_finished)
        self.worker.error.connect(self._on_clustering_error)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.start()
        
    def _on_clustering_finished(self, clustered_df, clusters):
        """Handle clustering completion"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"_on_clustering_finished: received clustered_df with {len(clustered_df)} rows")
        logger.info(f"_on_clustering_finished: cluster_id value_counts: {clustered_df['cluster_id'].value_counts().head()}")
        logger.info(f"_on_clustering_finished: representative count: {clustered_df['is_representative'].sum()}")
        
        self.clustered_df = clustered_df
        self.clusters = clusters
        self.run_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._update_results()
        self.tab_widget.setEnabled(True)
        self.export_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        
        # Count valid clusters and singletons correctly
        n_clusters = len(clusters)  # clusters dict already excludes singletons
        n_singletons = len(clustered_df[clustered_df['cluster_id'] == -1])
        self.results_label.setText(f"Clustering complete: {n_clusters} clusters, {n_singletons} singletons")
        
    def _on_clustering_error(self, error_message):
        """Handle clustering error"""
        self.run_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Clustering Error", f"An error occurred during clustering:\\n\\n{error_message}")
        
    def _update_results(self):
        """Update all result displays"""
        if self.clustered_df is None:
            return
        self._update_network_graph()
        self._update_summary()
        self._update_cluster_table()
        self._update_representative_table()
        
    def get_clustered_dataframe(self):
        """Get the clustered DataFrame for creating a filtered dataset"""
        return self.clustered_df

    def _update_network_graph(self):
        """Update the network visualization with current settings"""
        if self.clustered_df is None or self.clusters is None:
            return
        
        # Update visualization settings from widgets
        self.node_size = self.node_size_spin.value()
        self.edge_alpha = self.edge_alpha_spin.value()
        self.label_size = self.label_size_spin.value()
        self.show_hulls = self.show_hulls_checkbox.isChecked()
        
        self.figure.clear()
        # Create subplot with space for legend on the right
        # Use subplots_adjust to reserve 20% space on the right for legend
        ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(right=0.75)  # Reserve 25% for legend
        
        # Build network graph
        G = nx.Graph()
        for idx, row in self.clustered_df.iterrows():
            G.add_node(idx, **row.to_dict())
        
        # Add edges based on gene overlap
        gene_col = None
        for col in ['geneID', 'Genes', 'genes']:
            if col in self.clustered_df.columns:
                gene_col = col
                break
        
        if gene_col:
            for i, row1 in self.clustered_df.iterrows():
                genes1 = set(str(row1[gene_col]).split('/'))
                for j, row2 in self.clustered_df.iterrows():
                    if i >= j:
                        continue
                    genes2 = set(str(row2[gene_col]).split('/'))
                    intersection = len(genes1 & genes2)
                    union = len(genes1 | genes2)
                    if union > 0:
                        similarity = intersection / union
                        if similarity > 0.3:
                            G.add_edge(i, j, weight=similarity)
        
        self.network_graph = G
        
        # Categorize clusters by size FIRST
        valid_clusters = []
        small_clusters = []
        large_clusters = []
        
        for cluster_id, members in self.clusters.items():
            size = len(members)
            if size == 1:  # Singletons handled separately
                continue
            elif size < self.min_cluster_size:
                small_clusters.append((cluster_id, members))
            elif size > self.max_cluster_size:
                large_clusters.append((cluster_id, members))
            else:
                valid_clusters.append((cluster_id, members))
        
        # Assign colors to clusters based on validity
        self.cluster_colors = {}
        cluster_ids = sorted(set(self.clustered_df['cluster_id']))
        
        # Color assignment
        color_idx = 0
        for cluster_id in cluster_ids:
            if cluster_id == -1:
                # Singletons: gray
                self.cluster_colors[cluster_id] = '#999999'
            elif any(c[0] == cluster_id for c in small_clusters):
                # Small clusters: light gray
                self.cluster_colors[cluster_id] = '#BBBBBB'
            elif any(c[0] == cluster_id for c in large_clusters):
                # Large clusters: dark gray
                self.cluster_colors[cluster_id] = '#777777'
            else:
                # Valid clusters: use color palette
                self.cluster_colors[cluster_id] = self.COLORS[color_idx % len(self.COLORS)]
                color_idx += 1
        
        # Layout clusters - ONLY VALID CLUSTERS (exclude small/large/singletons)
        cluster_positions = {}
        grid_spacing = 20.0  # Increased spacing for better separation (was 15.0)
        
        # Valid clusters in grid layout - sort by size (largest first) for better organization
        if valid_clusters:
            # Sort clusters by size (descending) so largest clusters are at top-left
            valid_clusters_sorted = sorted(valid_clusters, key=lambda x: len(x[1]), reverse=True)
            
            n_clusters = len(valid_clusters_sorted)
            grid_cols = ceil(sqrt(n_clusters))
            grid_rows = ceil(n_clusters / grid_cols)
            
            for cluster_idx, (cluster_id, members) in enumerate(valid_clusters_sorted):
                # Grid layout: top-left to bottom-right
                # Note: matplotlib y-axis increases upward, so we negate row for top-down layout
                row = cluster_idx // grid_cols
                col = cluster_idx % grid_cols
                center_x = col * grid_spacing
                center_y = -row * grid_spacing  # Negative for top-to-bottom layout
                
                subgraph = G.subgraph(members)
                if len(members) > 1:
                    # Much larger k for better spread
                    sub_pos = nx.spring_layout(subgraph, k=2.5, iterations=50, scale=2.0)
                else:
                    sub_pos = {members[0]: (0, 0)}
                
                for node, (x, y) in sub_pos.items():
                    # Larger multiplier for more spread
                    cluster_positions[node] = (center_x + x * 3.0, center_y + y * 3.0)
        
        # Skip small clusters, large clusters, and singletons from visualization
        # They are still in the data and can be exported, just not drawn
        
        self.node_positions = cluster_positions
        
        # Draw convex hulls for valid clusters (if enabled)
        if self.show_hulls:
            for cluster_id, members in valid_clusters:
                if len(members) < 3:
                    continue
                points = np.array([cluster_positions[m] for m in members])
                try:
                    hull = ConvexHull(points)
                    hull_points = points[hull.vertices]
                    polygon = Polygon(hull_points, alpha=0.2, 
                                    facecolor=self.cluster_colors[cluster_id],
                                    edgecolor=self.cluster_colors[cluster_id], 
                                    linewidth=2)
                    ax.add_patch(polygon)
                except:
                    pass
        
        # Draw edges with configurable transparency
        for edge in G.edges(data=True):
            n1, n2, data = edge
            if n1 in cluster_positions and n2 in cluster_positions:
                x1, y1 = cluster_positions[n1]
                x2, y2 = cluster_positions[n2]
                weight = data.get('weight', 0.5)
                # Use configurable edge alpha
                ax.plot([x1, x2], [y1, y2], color='gray', alpha=self.edge_alpha, 
                       linewidth=weight * 1.5, zorder=1)
        
        # Draw nodes with improved sizing
        for node in G.nodes():
            if node not in cluster_positions:
                continue
            
            x, y = cluster_positions[node]
            cluster_id = G.nodes[node]['cluster_id']
            is_rep = G.nodes[node].get('is_representative', False)
            
            # Check if this is a singleton (cluster_id = -1)
            if cluster_id == -1:
                color = '#999999'  # Gray for singletons
            else:
                color = self.cluster_colors.get(cluster_id, '#999999')
            
            if is_rep:
                # Representative nodes: larger and bold border
                size = self.node_size * 1.5
                edge_color = 'black'
                edge_width = 3
            else:
                # Member nodes: smaller
                size = self.node_size * 0.3
                edge_color = color
                edge_width = 1.5
            
            ax.scatter(x, y, s=size, c=color, edgecolors=edge_color, 
                      linewidths=edge_width, zorder=2)
        
        # Draw labels for representative terms only (clearer visualization)
        # Collect all label positions first to detect and adjust overlaps
        label_positions = []
        
        for idx, row in self.clustered_df.iterrows():
            if idx not in cluster_positions:
                continue
            
            # Only label representative terms
            if not row.get('is_representative', False):
                continue
            
            x, y = cluster_positions[idx]
            desc_col = None
            # Try multiple possible column names (case-insensitive)
            for col in ['description', 'Description', 'Term', 'term', 'GO Term', 'KEGG Pathway']:
                if col in row.index:
                    desc_col = col
                    break
            
            if desc_col:
                label = row[desc_col]
                # Truncate long labels more aggressively to reduce overlap
                if len(label) > 30:
                    label = label[:27] + '...'
                
                # Offset label slightly upward to reduce node-label overlap
                label_y = y + 0.3
                
                # Use configurable label size with higher transparency to see through overlaps
                ax.text(x, label_y, label, fontsize=self.label_size, ha='center', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                               edgecolor='gray', alpha=0.75, linewidth=0.8),
                       zorder=4, weight='bold')
        
        # Populate the Qt-side legend list so it's always visible independently
        # of Matplotlib layout/backends. Clear previous items first.
        try:
            self.legend_list.clear()
        except Exception:
            # If legend widget isn't available (older state), skip gracefully
            pass

        # Valid clusters - show up to a reasonable number
        for cluster_id, members in valid_clusters:
            color = self.cluster_colors.get(cluster_id, '#444444')
            # Get representative term (full text for tooltip, truncated for label)
            rep_term = None
            for m in members:
                if self.clustered_df.loc[m, 'is_representative']:
                    desc_col = None
                    # Try multiple possible column names (case-insensitive)
                    for col in ['description', 'Description', 'Term', 'term', 'GO Term', 'KEGG Pathway']:
                        if col in self.clustered_df.columns:
                            desc_col = col
                            break
                    if desc_col:
                        rep_term = str(self.clustered_df.loc[m, desc_col])
                    break

            if rep_term:
                label = f"C{cluster_id} ({len(members)}): {rep_term if len(rep_term) <= 80 else rep_term[:77] + '...'}"
            else:
                label = f"C{cluster_id} ({len(members)})"

            try:
                item = QListWidgetItem(label)
                pix = QPixmap(14, 14)
                pix.fill(QColor(color))
                item.setIcon(QIcon(pix))
                item.setToolTip(rep_term if rep_term else label)
                self.legend_list.addItem(item)
            except Exception:
                # silently ignore widget errors in headless/static analysis
                pass

        # Add small/large/singleton summaries (count from full data, not drawn)
        # Calculate singleton count from the full clustered_df
        singleton_count = len([idx for idx, row in self.clustered_df.iterrows() 
                              if row['cluster_id'] == -1])
        
        if small_clusters:
            item = QListWidgetItem(f"Small (<{self.min_cluster_size}): {len(small_clusters)} (not shown)")
            pix = QPixmap(12, 12)
            pix.fill(QColor('#CCCCCC'))
            item.setIcon(QIcon(pix))
            self.legend_list.addItem(item)

        if large_clusters:
            item = QListWidgetItem(f"Large (>{self.max_cluster_size}): {len(large_clusters)} (not shown)")
            pix = QPixmap(12, 12)
            pix.fill(QColor('#777777'))
            item.setIcon(QIcon(pix))
            self.legend_list.addItem(item)

        if singleton_count > 0:
            item = QListWidgetItem(f"Singletons: {singleton_count} (not shown)")
            pix = QPixmap(12, 12)
            pix.fill(QColor('#999999'))
            item.setIcon(QIcon(pix))
            self.legend_list.addItem(item)

        # Set axis limits with proper margins (from backup file style)
        if cluster_positions:
            x_coords = [pos[0] for pos in cluster_positions.values()]
            y_coords = [pos[1] for pos in cluster_positions.values()]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
            x_range = x_max - x_min
            y_range = y_max - y_min
            # Use 15% margins like the backup file for better spacing
            x_margin = x_range * 0.15 if x_range > 0 else 1
            y_margin = y_range * 0.15 if y_range > 0 else 1
            ax.set_xlim(x_min - x_margin, x_max + x_margin)
            ax.set_ylim(y_min - y_margin, y_max + y_margin)
        
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Apply tight_layout to optimize the plot area (since legend is Qt widget,
        # we can use full figure space)
        try:
            self.figure.tight_layout()
        except Exception:
            pass
        
        self.canvas.draw()
        
    def _on_network_hover(self, event):
        """Handle mouse hover over network graph"""
        if event.inaxes is None or self.node_positions is None:
            return
        mouse_x, mouse_y = event.xdata, event.ydata
        closest_node = None
        min_distance = float('inf')
        for node, (x, y) in self.node_positions.items():
            distance = sqrt((mouse_x - x)**2 + (mouse_y - y)**2)
            is_rep = self.clustered_df.loc[node, 'is_representative']
            threshold = 0.3 if is_rep else 0.15
            if distance < threshold and distance < min_distance:
                closest_node = node
                min_distance = distance
        if closest_node is not None:
            row = self.clustered_df.loc[closest_node]
            desc_col = None
            # Try multiple possible column names (case-insensitive)
            for col in ['description', 'Description', 'Term', 'term', 'GO Term', 'KEGG Pathway']:
                if col in row.index:
                    desc_col = col
                    break
            fdr_col = None
            for col in ['fdr', 'p.adjust', 'FDR', 'padj', 'qvalue']:
                if col in row.index:
                    fdr_col = col
                    break
            count_col = None
            for col in ['gene_count', 'Count', 'count', 'GeneRatio']:
                if col in row.index:
                    count_col = col
                    break
            tooltip_text = ""
            if desc_col:
                tooltip_text += f"{row[desc_col]}\\n"
            if fdr_col:
                tooltip_text += f"FDR: {row[fdr_col]:.2e}\\n"
            if count_col:
                tooltip_text += f"Count: {row[count_col]}\\n"
            tooltip_text += f"Cluster: {row['cluster_id']}"
            self.canvas.setToolTip(tooltip_text)
        else:
            self.canvas.setToolTip("")
            
    def _update_summary(self):
        """Update the summary statistics tab"""
        if self.clustered_df is None or self.clusters is None:
            return
        
        n_total = len(self.clustered_df)
        
        # Categorize clusters
        valid_clusters = []
        small_clusters = []
        large_clusters = []
        
        # Count singletons from clustered_df (cluster_id == -1)
        n_singletons = len(self.clustered_df[self.clustered_df['cluster_id'] == -1])
        
        for cluster_id, members in self.clusters.items():
            size = len(members)
            # Note: clusters dict already excludes singletons (filtered in utils)
            if size < self.min_cluster_size:
                small_clusters.append(cluster_id)
            elif size > self.max_cluster_size:
                large_clusters.append(cluster_id)
            else:
                valid_clusters.append(cluster_id)
        
        cluster_sizes = [len(self.clusters[c]) for c in valid_clusters]
        if cluster_sizes:
            avg_size = np.mean(cluster_sizes)
            max_size = max(cluster_sizes)
            min_size = min(cluster_sizes)
        else:
            avg_size = max_size = min_size = 0
        
        n_representatives = self.clustered_df['is_representative'].sum()
        
        summary_html = f"""
        <html>
        <head>
        <style>
            body {{ font-family: Arial; font-size: 11pt; }}
            h2 {{ color: #2c3e50; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
            th {{ background-color: #3498db; color: white; padding: 8px; text-align: left; }}
            td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .filter-info {{ background-color: #fff3cd; padding: 10px; margin: 10px 0; 
                           border-left: 4px solid #ffc107; }}
        </style>
        </head>
        <body>
        
        <h2>Clustering Summary</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td><b>Total GO Terms</b></td><td>{n_total}</td></tr>
            <tr><td><b>Valid Clusters</b></td><td>{len(valid_clusters)} 
                ({self.min_cluster_size}–{self.max_cluster_size} terms)</td></tr>
            <tr><td><b>Small Clusters</b></td><td>{len(small_clusters)} 
                (<{self.min_cluster_size} terms)</td></tr>
            <tr><td><b>Large Clusters</b></td><td>{len(large_clusters)} 
                (>{self.max_cluster_size} terms)</td></tr>
            <tr><td><b>Singleton Terms</b></td><td>{n_singletons}</td></tr>
            <tr><td><b>Representative Terms</b></td><td>{n_representatives}</td></tr>
            <tr><td><b>Average Valid Cluster Size</b></td><td>{avg_size:.1f}</td></tr>
            <tr><td><b>Largest Valid Cluster</b></td><td>{max_size} terms</td></tr>
            <tr><td><b>Smallest Valid Cluster</b></td><td>{min_size} terms</td></tr>
        </table>
        
        <div class="filter-info">
            <b>ℹ️ Cluster Details:</b> All cluster information including IDs, 
            sizes, and representative terms are shown in the <b>Network Visualization legend</b> 
            on the right side of the network chart. Use the legend to identify clusters by color.
        </div>
        
        </body></html>
        """
        
        self.summary_text.setHtml(summary_html)
        
    def _update_cluster_table(self):
        """Update the clustered terms table with zebra striping"""
        if self.clustered_df is None:
            return
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"_update_cluster_table: clustered_df has {len(self.clustered_df)} rows")
        logger.info(f"_update_cluster_table: cluster_id unique values: {self.clustered_df['cluster_id'].unique()[:10]}")
        logger.info(f"_update_cluster_table: has cluster_id column: {'cluster_id' in self.clustered_df.columns}")
        
        df = self.clustered_df.copy()
        
        # Move cluster_id to first column
        if 'cluster_id' in df.columns:
            cols = df.columns.tolist()
            cols.remove('cluster_id')
            cols = ['cluster_id'] + cols
            df = df[cols]
        
        fdr_col = None
        for col in ['fdr', 'p.adjust', 'FDR', 'padj', 'qvalue']:
            if col in df.columns:
                fdr_col = col
                break
        if fdr_col:
            # Sort by cluster_id (descending so -1 singletons are at bottom), then by FDR
            df = df.sort_values(['cluster_id', fdr_col], ascending=[False, True])
        else:
            df = df.sort_values('cluster_id', ascending=False)
        
        self.cluster_table.setRowCount(len(df))
        self.cluster_table.setColumnCount(len(df.columns))
        self.cluster_table.setHorizontalHeaderLabels(df.columns.tolist())
        
        # Group by cluster for alternating colors BY CLUSTER (not by row)
        current_cluster = None
        cluster_color_index = 0  # Track which color to use for current cluster
        
        for i, (idx, row) in enumerate(df.iterrows()):
            cluster_id_raw = row['cluster_id']
            
            # Convert cluster_id to readable format
            if cluster_id_raw == -1:
                cluster_id_display = 'Singleton'
            elif cluster_id_raw in self.clusters:
                cluster_size = len(self.clusters[cluster_id_raw])
                if cluster_size >= self.min_cluster_size:
                    # Valid cluster - use cluster number
                    cluster_id_display = str(cluster_id_raw)
                else:
                    # Small cluster (shouldn't happen often)
                    cluster_id_display = 'Small'
            else:
                cluster_id_display = str(cluster_id_raw)
            
            # Debug: log first few rows
            if i < 3:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Table row {i}: cluster_id_raw={cluster_id_raw}, cluster_id_display={cluster_id_display}, rep_term='{row.get('representative_term', 'N/A')}'")
            
            # When cluster changes, toggle the color
            if cluster_id_raw != current_cluster:
                current_cluster = cluster_id_raw
                cluster_color_index = 1 - cluster_color_index  # Toggle between 0 and 1
            
            # Zebra striping BY CLUSTER: white and light gray alternate per cluster
            if cluster_color_index == 0:
                bg_color = QColor(255, 255, 255)  # White
            else:
                bg_color = QColor(240, 240, 240)  # Light gray
            
            for j, col in enumerate(df.columns):
                value = row[col]
                
                # Special handling for cluster_id column
                if col == 'cluster_id':
                    text = cluster_id_display
                elif isinstance(value, float):
                    if value < 0.001:
                        text = f"{value:.2e}"
                    else:
                        text = f"{value:.4f}"
                else:
                    text = str(value)
                item = QTableWidgetItem(text)
                item.setBackground(QBrush(bg_color))
                self.cluster_table.setItem(i, j, item)
        
        self.cluster_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
    def _update_representative_table(self):
        """Update the representative terms table with zebra striping"""
        if self.clustered_df is None:
            return
        df = self.clustered_df[self.clustered_df['is_representative'] == True].copy()
        fdr_col = None
        for col in ['p.adjust', 'FDR', 'padj', 'qvalue']:
            if col in df.columns:
                fdr_col = col
                break
        if fdr_col:
            df = df.sort_values(fdr_col)
        
        self.representative_table.setRowCount(len(df))
        self.representative_table.setColumnCount(len(df.columns))
        self.representative_table.setHorizontalHeaderLabels(df.columns.tolist())
        
        for i, (idx, row) in enumerate(df.iterrows()):
            # Simple zebra striping: white and light gray
            if i % 2 == 0:
                bg_color = QColor(255, 255, 255)  # White
            else:
                bg_color = QColor(240, 240, 240)  # Light gray
            
            for j, col in enumerate(df.columns):
                value = row[col]
                if isinstance(value, float):
                    if value < 0.001:
                        text = f"{value:.2e}"
                    else:
                        text = f"{value:.4f}"
                else:
                    text = str(value)
                item = QTableWidgetItem(text)
                item.setBackground(QBrush(bg_color))
                self.representative_table.setItem(i, j, item)
        
        self.representative_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
    def _export_clusters(self):
        """Export clustering results to Excel file"""
        if self.clustered_df is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Clustering Results", "", "Excel Files (*.xlsx)")
        if not file_path:
            return
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                self.clustered_df.to_excel(writer, sheet_name='All Terms', index=False)
                representatives = self.clustered_df[self.clustered_df['is_representative'] == True]
                representatives.to_excel(writer, sheet_name='Representatives', index=False)
                cluster_summary = []
                for cluster_id, members in self.clusters.items():
                    if len(members) == 1:
                        continue
                    cluster_df = self.clustered_df[self.clustered_df['cluster_id'] == cluster_id]
                    rep_row = cluster_df[cluster_df['is_representative'] == True]
                    if not rep_row.empty:
                        rep_row = rep_row.iloc[0]
                        desc_col = None
                        for col in ['Description', 'Term', 'term']:
                            if col in rep_row.index:
                                desc_col = col
                                break
                        rep_term = rep_row[desc_col] if desc_col else "N/A"
                    else:
                        rep_term = "N/A"
                    cluster_summary.append({'Cluster ID': cluster_id, 'Size': len(members), 'Representative': rep_term, 'Color': self.cluster_colors.get(cluster_id, '#999999')})
                summary_df = pd.DataFrame(cluster_summary)
                summary_df.to_excel(writer, sheet_name='Cluster Summary', index=False)
            QMessageBox.information(self, "Export Successful", f"Clustering results exported to:\\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export clustering results:\\n\\n{str(e)}")
    
    def _apply_clustering(self):
        """
        Apply clustering results to the dataset and emit to main GUI
        
        Creates a new DataFrame with cluster_id column added:
        - Valid clusters (size >= min): cluster ID as string ("0", "1", "2", ...)
        - Small clusters (1 < size < min): "Small"
        - Singletons (size == 1): "Singleton"
        - Unclustered (no clustering run): empty string ""
        """
        if self.clustered_df is None or self.clustered_df.empty:
            QMessageBox.warning(
                self,
                "No Clustering Results",
                "Please run clustering first before applying results."
            )
            return
        
        try:
            # Use clustered_df directly (already contains all original columns + cluster_id)
            # Don't use self.dataset as it may have different index
            result_df = self.clustered_df.copy()
            
            # Remove internal columns (_gene_set, is_representative, representative_term)
            cols_to_remove = ['_gene_set', 'is_representative', 'representative_term']
            for col in cols_to_remove:
                if col in result_df.columns:
                    result_df = result_df.drop(columns=[col])
            
            # Add cluster_id column if not exists (should already exist from clustering)
            if 'cluster_id' not in result_df.columns:
                result_df['cluster_id'] = ''
            
            # Rename cluster_id to StandardColumns.CLUSTER_ID
            if 'cluster_id' in result_df.columns and StandardColumns.CLUSTER_ID != 'cluster_id':
                result_df = result_df.rename(columns={'cluster_id': StandardColumns.CLUSTER_ID})
            
            # Map cluster_id values to readable format
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Clusters dict keys: {list(self.clusters.keys())[:10] if self.clusters else 'None'}")
            logger.info(f"Unique cluster_id values in result_df: {result_df[StandardColumns.CLUSTER_ID].unique()[:10]}")
            
            for idx in result_df.index:
                cluster_id_raw = result_df.loc[idx, StandardColumns.CLUSTER_ID]
                
                # Determine cluster_id value based on cluster type
                # Note: self.clusters already contains only valid clusters (size >= min_size)
                if cluster_id_raw == -1:
                    # Singleton
                    cluster_value = 'Singleton'
                elif cluster_id_raw in self.clusters:
                    # Valid cluster (already filtered by size)
                    cluster_value = str(cluster_id_raw)
                else:
                    # Not in clusters dict means it was filtered out (too small)
                    cluster_value = 'Small'
                
                result_df.loc[idx, StandardColumns.CLUSTER_ID] = cluster_value
            
            # Emit the result to main GUI
            logger.info(f"Emitting clustered data with {len(result_df)} rows")
            logger.info(f"Result columns: {result_df.columns.tolist()}")
            logger.info(f"Cluster_id sample values: {result_df[StandardColumns.CLUSTER_ID].value_counts().head()}")
            
            self.clustered_data_ready.emit(result_df)
            
            # Show confirmation
            # Count valid clusters by checking if value is numeric string
            n_valid = len([c for c in result_df[StandardColumns.CLUSTER_ID] 
                          if isinstance(c, str) and c.isdigit()])
            n_small = len(result_df[result_df[StandardColumns.CLUSTER_ID] == 'Small'])
            n_singleton = len(result_df[result_df[StandardColumns.CLUSTER_ID] == 'Singleton'])
            n_unclustered = len(result_df[result_df[StandardColumns.CLUSTER_ID] == ''])
            
            msg = "Clustering applied successfully!\n\n"
            msg += f"✓ Valid clusters: {n_valid} terms\n"
            if n_small > 0:
                msg += f"⚠ Small clusters: {n_small} terms\n"
            msg += f"○ Singletons: {n_singleton} terms\n"
            if n_unclustered > 0:
                msg += f"- Unclustered: {n_unclustered} terms\n"
            msg += f"\n📊 Total: {len(result_df)} terms"
            
            QMessageBox.information(self, "Apply Successful", msg)
            
            # Close the dialog
            self.accept()
            
        except Exception as e:
            import traceback
            QMessageBox.critical(
                self,
                "Apply Error",
                f"Failed to apply clustering results:\\n\\n{str(e)}\\n\\n{traceback.format_exc()}"
            )
