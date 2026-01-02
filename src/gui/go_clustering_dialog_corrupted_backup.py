# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-

"""

Interactive GO Term Clustering Dialog"""



This dialog provides an interface for clustering GO enrichment resultsInteractive GO Term Clustering Dialog"""

using Jaccard similarity and hierarchical clustering, with ClueGO-style

network visualization.

"""

This dialog provides an interface for clustering GO enrichment resultsInteractive GO Term Clustering Dialog with Real-time Network Visualization"""

from PyQt6.QtWidgets import (

    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,using Jaccard similarity and hierarchical clustering, with ClueGO-style

    QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,

    QHeaderView, QSplitter, QWidget, QTabWidget, QTextEdit,network visualization."""

    QFileDialog, QMessageBox, QProgressBar

)"""

from PyQt6.QtCore import Qt, QThread, pyqtSignal

from PyQt6.QtGui import QFont, QBrush, QColorInteractive GO Term Clustering Dialog with Real-time Network Visualization



import matplotlibfrom PyQt6.QtWidgets import (

matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,from PyQt6.QtWidgets import (

from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from matplotlib.figure import Figure    QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,

import matplotlib.pyplot as plt

from matplotlib.patches import Polygon    QHeaderView, QSplitter, QWidget, QTabWidget, QTextEdit,    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,"""

from scipy.spatial import ConvexHull

    QFileDialog, QMessageBox, QProgressBar

import pandas as pd

import numpy as np)    QLabel, QSlider, QSpinBox, QCheckBox, QPushButton,

import networkx as nx

from math import ceil, sqrtfrom PyQt6.QtCore import Qt, QThread, pyqtSignal



from core.go_clustering import GOClusteringfrom PyQt6.QtGui import QFont, QBrush, QColor    QGroupBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,





class ClusteringWorker(QThread):

    """Background thread for performing GO term clustering"""import matplotlib    QTabWidget, QWidget, QSplitter, QProgressBar, QMessageBox,

    

    finished = pyqtSignal(object, object)matplotlib.use('Qt5Agg')

    error = pyqtSignal(str)

    progress = pyqtSignal(int)from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas    QScrollAreafrom PyQt6.QtWidgets import (

    

    def __init__(self, df, similarity_threshold):from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

        super().__init__()

        self.df = dffrom matplotlib.figure import Figure)

        self.similarity_threshold = similarity_threshold

        import matplotlib.pyplot as plt

    def run(self):

        """Execute clustering in background thread"""from matplotlib.patches import Polygonfrom PyQt6.QtCore import Qt, QThread, pyqtSignal    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,

        try:

            self.progress.emit(10)from scipy.spatial import ConvexHull

            clustering = GOClustering()

            self.progress.emit(30)from PyQt6.QtGui import QColor, QBrush, QFont

            distance_threshold = 1.0 - self.similarity_threshold

            clustered_df, clusters = clustering.cluster_terms(self.df, distance_threshold=distance_threshold)import pandas as pd

            self.progress.emit(90)

            self.finished.emit(clustered_df, clusters)import numpy as npfrom typing import Optional, Dict, List    QLabel, QSlider, QSpinBox, QCheckBox, QPushButton,

            self.progress.emit(100)

        except Exception as e:import networkx as nx

            self.error.emit(str(e))

from math import ceil, sqrtimport pandas as pd



class GOClusteringDialog(QDialog):

    """Interactive dialog for GO term clustering and visualization"""

    from core.go_clustering import GOClusteringimport logging    QGroupBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,

    COLORS = [

        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',

        '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',

        '#EF476F', '#06FFA5', '#118AB2', '#FFD166', '#073B4C',

        '#A8DADC', '#E63946', '#F1FAEE', '#457B9D', '#1D3557'

    ]class ClusteringWorker(QThread):

    

    def __init__(self, dataset, parent=None):    """Background thread for performing GO term clustering"""from models.data_models import Dataset    QTabWidget, QWidget, QSplitter, QProgressBar, QMessageBox,

        super().__init__(parent)

        self.dataset = dataset.copy()    

        self.clustered_df = None

        self.clusters = None    finished = pyqtSignal(object, object)  # clustered_df, clustersfrom models.standard_columns import StandardColumns

        self.network_graph = None

        self.node_positions = None    error = pyqtSignal(str)

        self.cluster_colors = {}

        self.top_n_labels = 10    progress = pyqtSignal(int)from gui.main_window import NumericTableWidgetItem    QScrollArea

        self.node_size = 1000

        self.setWindowTitle("GO Term Clustering")    

        self.resize(1400, 900)

        self._init_ui()    def __init__(self, df, similarity_threshold):

        

    def _init_ui(self):        super().__init__()

        """Initialize the user interface"""

        layout = QVBoxLayout(self)        self.df = df# Matplotlib imports)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        settings_panel = self._create_settings_panel()        self.similarity_threshold = similarity_threshold

        splitter.addWidget(settings_panel)

        results_panel = self._create_results_panel()        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

        splitter.addWidget(results_panel)

        splitter.setStretchFactor(0, 3)    def run(self):

        splitter.setStretchFactor(1, 7)

        layout.addWidget(splitter)        """Execute clustering in background thread"""from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbarfrom PyQt6.QtCore import Qt, QThread, pyqtSignal

        button_layout = self._create_buttons()

        layout.addLayout(button_layout)        try:

        

    def _create_settings_panel(self):            self.progress.emit(10)from matplotlib.figure import Figure

        """Create the left panel with clustering settings and help"""

        panel = QWidget()            

        layout = QVBoxLayout(panel)

        title = QLabel("Clustering Settings")            # Initialize clusteringimport matplotlib.pyplot as pltfrom PyQt6.QtGui import QColor

        title_font = QFont()

        title_font.setPointSize(12)            clustering = GOClustering()

        title_font.setBold(True)

        title.setFont(title_font)            self.progress.emit(30)import matplotlib.cm as cm

        layout.addWidget(title)

        threshold_label = QLabel("Similarity Threshold:")            

        layout.addWidget(threshold_label)

        self.similarity_spin = QDoubleSpinBox()            # Perform clusteringimport networkx as nxfrom typing import Optional, Dict, List

        self.similarity_spin.setRange(0.0, 1.0)

        self.similarity_spin.setSingleStep(0.05)            distance_threshold = 1.0 - self.similarity_threshold

        self.similarity_spin.setValue(0.5)

        self.similarity_spin.setDecimals(2)            clustered_df, clusters = clustering.cluster_terms(import numpy as np

        layout.addWidget(self.similarity_spin)

        help_text = QLabel("GO terms with similarity above this threshold\nwill be grouped into the same cluster.\n\nHigher values create more clusters.")                self.df, 

        help_text.setWordWrap(True)

        help_text.setStyleSheet("color: gray; font-size: 9pt;")                distance_threshold=distance_thresholdimport pandas as pd

        layout.addWidget(help_text)

        self.run_button = QPushButton("Run Clustering")            )

        self.run_button.clicked.connect(self._run_clustering)

        layout.addWidget(self.run_button)            self.progress.emit(90)

        self.progress_bar = QProgressBar()

        self.progress_bar.setVisible(False)            

        layout.addWidget(self.progress_bar)

        layout.addSpacing(20)            # Emit resultsclass ClusteringWorker(QThread):import logging

        help_title = QLabel("Network Visualization Guide")

        help_title_font = QFont()            self.finished.emit(clustered_df, clusters)

        help_title_font.setPointSize(11)

        help_title_font.setBold(True)            self.progress.emit(100)    """Background worker thread for clustering execution"""

        help_title.setFont(help_title_font)

        layout.addWidget(help_title)            

        help_content = QTextEdit()

        help_content.setReadOnly(True)        except Exception as e:    

        help_content.setMaximumHeight(400)

        help_content.setHtml("""            self.error.emit(str(e))

        <style>

            body { font-family: Arial; font-size: 10pt; }    finished = pyqtSignal(pd.DataFrame, dict)  # (clustered_df, clusters)

            h3 { color: #2c3e50; margin-top: 10px; margin-bottom: 5px; }

            ul { margin-top: 5px; margin-bottom: 5px; }

            li { margin-bottom: 3px; }

        </style>class GOClusteringDialog(QDialog):    progress = pyqtSignal(str)  # progress messagefrom models.data_models import Dataset

        <h3>Node Representation</h3>

        <ul>    """

            <li><b>Large nodes</b>: Representative terms (lowest FDR in cluster)</li>

            <li><b>Small nodes</b>: Member terms in the cluster</li>    Interactive dialog for GO term clustering and visualization.    error = pyqtSignal(str)  # error message

            <li><b>Node color</b>: Each cluster has a unique color</li>

            <li><b>Gray nodes</b>: Singleton terms (no clustering)</li>    

        </ul>

        <h3>Cluster Layout</h3>    Features:    from models.standard_columns import StandardColumns

        <ul>

            <li>Terms are arranged in a <b>grid layout</b></li>    - Adjustable similarity threshold

            <li>Each cluster occupies a separate grid cell</li>

            <li>Within each cluster, terms are positioned using spring layout</li>    - Network visualization with grid layout    def __init__(self, df: pd.DataFrame, similarity_threshold: float):

            <li><b>Convex hulls</b> (polygons) outline each cluster boundary</li>

        </ul>    - Cluster summary statistics

        <h3>Edges (Connections)</h3>

        <ul>    - Representative term selection        super().__init__()from gui.main_window import NumericTableWidgetItem

            <li>Lines connect GO terms with similar gene sets</li>

            <li>Line width indicates similarity strength</li>    - Export functionality

            <li>Only significant similarities are shown</li>

        </ul>    """        self.df = df

        <h3>Interactive Features</h3>

        <ul>    

            <li><b>Hover</b>: Move mouse over a node to see term details</li>

            <li><b>Labels</b>: Top N most significant terms are labeled</li>    # Color palette (ClueGO-inspired)        self.similarity_threshold = similarity_threshold

            <li><b>Zoom</b>: Use toolbar to zoom and pan</li>

            <li><b>Customize</b>: Adjust label count and node size below</li>    COLORS = [

        </ul>

        <h3>Singletons</h3>        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',        self.logger = logging.getLogger(__name__)

        <ul>

            <li>Terms that don't cluster with others appear in gray</li>        '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',

            <li>These are unique or highly specific terms</li>

            <li>Still included in the analysis and export</li>        '#EF476F', '#06FFA5', '#118AB2', '#FFD166', '#073B4C',    # Matplotlib imports

        </ul>

        """)        '#A8DADC', '#E63946', '#F1FAEE', '#457B9D', '#1D3557'

        layout.addWidget(help_content)

        layout.addStretch()    ]    def run(self):

        return panel

            

    def _create_results_panel(self):

        """Create the right panel with results tabs"""    def __init__(self, dataset, parent=None):        """Execute clustering"""from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

        panel = QWidget()

        layout = QVBoxLayout(panel)        """

        self.results_label = QLabel("No clustering results yet. Configure settings and click 'Run Clustering'.")

        self.results_label.setWordWrap(True)        Initialize the clustering dialog.        try:

        layout.addWidget(self.results_label)

        self.tab_widget = QTabWidget()        

        self.tab_widget.setEnabled(False)

        network_tab = self._create_network_tab()        Args:            from utils.go_clustering import GOClusteringfrom matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar

        self.tab_widget.addTab(network_tab, "Network Visualization")

        summary_tab = self._create_summary_tab()            dataset: DataFrame with GO enrichment results

        self.tab_widget.addTab(summary_tab, "Summary")

        cluster_tab = self._create_cluster_tab()            parent: Parent widget            

        self.tab_widget.addTab(cluster_tab, "Clustered Terms")

        representative_tab = self._create_representative_tab()        """

        self.tab_widget.addTab(representative_tab, "Representatives")

        layout.addWidget(self.tab_widget)        super().__init__(parent)            self.progress.emit("Initializing clustering...")from matplotlib.figure import Figure

        return panel

                self.dataset = dataset.copy()

    def _create_network_tab(self):

        """Create the network visualization tab with customization settings"""        self.clustered_df = None            

        tab = QWidget()

        layout = QVBoxLayout(tab)        self.clusters = None

        settings_widget = QWidget()

        settings_layout = QHBoxLayout(settings_widget)        self.network_graph = None            clusterer = GOClustering()import matplotlib.pyplot as plt

        settings_layout.setContentsMargins(5, 5, 5, 5)

        label_count_label = QLabel("Labels to show:")        self.node_positions = None

        settings_layout.addWidget(label_count_label)

        self.top_n_spin = QSpinBox()        self.cluster_colors = {}            clustered_df, clusters = clusterer.cluster_terms(

        self.top_n_spin.setRange(0, 50)

        self.top_n_spin.setValue(10)        

        self.top_n_spin.setToolTip("Number of most significant terms to label")

        settings_layout.addWidget(self.top_n_spin)        # Network visualization settings                self.df, import matplotlib.cm as cm

        settings_layout.addSpacing(20)

        node_size_label = QLabel("Node size:")        self.top_n_labels = 10

        settings_layout.addWidget(node_size_label)

        self.node_size_spin = QSpinBox()        self.node_size = 1000                distance_threshold=1.0 - self.similarity_threshold

        self.node_size_spin.setRange(100, 2000)

        self.node_size_spin.setSingleStep(100)        

        self.node_size_spin.setValue(1000)

        self.node_size_spin.setToolTip("Size of representative term nodes")        self.setWindowTitle("GO Term Clustering")            )import networkx as nx

        settings_layout.addWidget(self.node_size_spin)

        settings_layout.addSpacing(20)        self.resize(1400, 900)

        self.refresh_button = QPushButton("Refresh Plot")

        self.refresh_button.setStyleSheet("""                    

            QPushButton {

                background-color: #17a2b8;        self._init_ui()

                color: white;

                border: none;                    self.progress.emit("Clustering complete!")import numpy as np

                padding: 5px 15px;

                border-radius: 3px;    def _init_ui(self):

                font-weight: bold;

            }        """Initialize the user interface"""            self.finished.emit(clustered_df, clusters)

            QPushButton:hover {

                background-color: #138496;        layout = QVBoxLayout(self)

            }

            QPushButton:pressed {                    

                background-color: #117a8b;

            }        # Create main splitter

            QPushButton:disabled {

                background-color: #cccccc;        splitter = QSplitter(Qt.Orientation.Horizontal)        except Exception as e:

                color: #666666;

            }        

        """)

        self.refresh_button.clicked.connect(self._update_network_graph)        # Left panel: Settings and help            self.logger.error(f"Clustering error: {e}", exc_info=True)

        self.refresh_button.setEnabled(False)

        settings_layout.addWidget(self.refresh_button)        settings_panel = self._create_settings_panel()

        settings_layout.addStretch()

        layout.addWidget(settings_widget)        splitter.addWidget(settings_panel)            self.error.emit(str(e))

        self.figure = Figure(figsize=(10, 8))

        self.canvas = FigureCanvas(self.figure)        

        self.canvas.mpl_connect('motion_notify_event', self._on_network_hover)

        self.toolbar = NavigationToolbar(self.canvas, tab)        # Right panel: Resultsclass ClusteringWorker(QThread):

        layout.addWidget(self.toolbar)

        layout.addWidget(self.canvas)        results_panel = self._create_results_panel()

        return tab

                splitter.addWidget(results_panel)

    def _create_summary_tab(self):

        """Create the summary statistics tab"""        

        tab = QWidget()

        layout = QVBoxLayout(tab)        # Set splitter proportions (30% left, 70% right)class GOClusteringDialog(QDialog):    """Background worker thread for clustering execution"""

        self.summary_text = QTextEdit()

        self.summary_text.setReadOnly(True)        splitter.setStretchFactor(0, 3)

        layout.addWidget(self.summary_text)

        return tab        splitter.setStretchFactor(1, 7)    """Interactive GO Term Clustering Dialog (Settings + Real-time Visualization)"""

        

    def _create_cluster_tab(self):        

        """Create the clustered terms table tab"""

        tab = QWidget()        layout.addWidget(splitter)        

        layout = QVBoxLayout(tab)

        self.cluster_table = QTableWidget()        

        self.cluster_table.setSortingEnabled(True)

        layout.addWidget(self.cluster_table)        # Bottom buttons    def __init__(self, dataset: Dataset, parent=None):

        return tab

                button_layout = self._create_buttons()

    def _create_representative_tab(self):

        """Create the representative terms table tab"""        layout.addLayout(button_layout)        super().__init__(parent)    finished = pyqtSignal(pd.DataFrame, dict)  # (clustered_df, clusters)

        tab = QWidget()

        layout = QVBoxLayout(tab)        

        self.representative_table = QTableWidget()

        self.representative_table.setSortingEnabled(True)    def _create_settings_panel(self):        self.dataset = dataset

        layout.addWidget(self.representative_table)

        return tab        """Create the left panel with clustering settings and help"""

        

    def _create_buttons(self):        panel = QWidget()        self.clustered_df: Optional[pd.DataFrame] = None    progress = pyqtSignal(str)  # progress message

        """Create bottom button layout"""

        layout = QHBoxLayout()        layout = QVBoxLayout(panel)

        layout.addStretch()

        self.export_button = QPushButton("Export Clusters")                self.clusters: Optional[Dict] = None

        self.export_button.setEnabled(False)

        self.export_button.clicked.connect(self._export_clusters)        # Title

        layout.addWidget(self.export_button)

        self.apply_button = QPushButton("Apply")        title = QLabel("Clustering Settings")        self.logger = logging.getLogger(__name__)    error = pyqtSignal(str)  # error message

        self.apply_button.setEnabled(False)

        self.apply_button.setToolTip("Apply clustering and create filtered dataset")        title_font = QFont()

        layout.addWidget(self.apply_button)

        close_button = QPushButton("Close")        title_font.setPointSize(12)        

        close_button.clicked.connect(self.reject)

        layout.addWidget(close_button)        title_font.setBold(True)

        return layout

                title.setFont(title_font)        self.setWindowTitle(f"GO Term Clustering - {dataset.name}")    

    def _run_clustering(self):

        """Execute clustering in background thread"""        layout.addWidget(title)

        if self.dataset is None or self.dataset.empty:

            QMessageBox.warning(self, "No Data", "No GO enrichment data available for clustering.")                self.setMinimumSize(1400, 900)

            return

        similarity_threshold = self.similarity_spin.value()        # Similarity threshold

        self.run_button.setEnabled(False)

        self.progress_bar.setVisible(True)        threshold_label = QLabel("Similarity Threshold:")        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)    def __init__(self, df: pd.DataFrame, similarity_threshold: float):

        self.progress_bar.setValue(0)

        self.worker = ClusteringWorker(self.dataset, similarity_threshold)        layout.addWidget(threshold_label)

        self.worker.finished.connect(self._on_clustering_finished)

        self.worker.error.connect(self._on_clustering_error)                

        self.worker.progress.connect(self.progress_bar.setValue)

        self.worker.start()        self.similarity_spin = QDoubleSpinBox()

        

    def _on_clustering_finished(self, clustered_df, clusters):        self.similarity_spin.setRange(0.0, 1.0)        self._init_ui()        super().__init__()

        """Handle clustering completion"""

        self.clustered_df = clustered_df        self.similarity_spin.setSingleStep(0.05)

        self.clusters = clusters

        self.run_button.setEnabled(True)        self.similarity_spin.setValue(0.5)    

        self.progress_bar.setVisible(False)

        self._update_results()        self.similarity_spin.setDecimals(2)

        self.tab_widget.setEnabled(True)

        self.export_button.setEnabled(True)        layout.addWidget(self.similarity_spin)    def _init_ui(self):        self.df = df

        self.apply_button.setEnabled(True)

        self.refresh_button.setEnabled(True)        

        n_clusters = len([c for c in self.clusters.values() if len(c) > 1])

        n_singletons = len([c for c in self.clusters.values() if len(c) == 1])        help_text = QLabel(        """Initialize UI"""

        self.results_label.setText(f"Clustering complete: {n_clusters} clusters, {n_singletons} singletons")

                    "GO terms with similarity above this threshold\n"

    def _on_clustering_error(self, error_message):

        """Handle clustering error"""            "will be grouped into the same cluster.\n\n"        main_layout = QHBoxLayout(self)        self.similarity_threshold = similarity_threshold

        self.run_button.setEnabled(True)

        self.progress_bar.setVisible(False)            "Higher values create more clusters."

        QMessageBox.critical(self, "Clustering Error", f"An error occurred during clustering:\n\n{error_message}")

                )        

    def _update_results(self):

        """Update all result displays"""        help_text.setWordWrap(True)

        if self.clustered_df is None:

            return        help_text.setStyleSheet("color: gray; font-size: 9pt;")        # Splitter for resizable panels        self.logger = logging.getLogger(__name__)

        self._update_network_graph()

        self._update_summary()        layout.addWidget(help_text)

        self._update_cluster_table()

        self._update_representative_table()                splitter = QSplitter(Qt.Orientation.Horizontal)

        

    def _update_network_graph(self):        # Run button

        """Update the network visualization with current settings"""

        if self.clustered_df is None or self.clusters is None:        self.run_button = QPushButton("Run Clustering")            

            return

        self.top_n_labels = self.top_n_spin.value()        self.run_button.clicked.connect(self._run_clustering)

        self.node_size = self.node_size_spin.value()

        self.figure.clear()        layout.addWidget(self.run_button)        # Left: Settings panel

        ax = self.figure.add_subplot(111)

        G = nx.Graph()        

        for idx, row in self.clustered_df.iterrows():

            G.add_node(idx, **row.to_dict())        # Progress bar        settings_panel = self._create_settings_panel()    def run(self):

        gene_col = None

        for col in ['geneID', 'Genes', 'genes']:        self.progress_bar = QProgressBar()

            if col in self.clustered_df.columns:

                gene_col = col        self.progress_bar.setVisible(False)        splitter.addWidget(settings_panel)

                break

        if gene_col:        layout.addWidget(self.progress_bar)

            for i, row1 in self.clustered_df.iterrows():

                genes1 = set(str(row1[gene_col]).split('/'))                        """Execute clustering"""

                for j, row2 in self.clustered_df.iterrows():

                    if i >= j:        layout.addSpacing(20)

                        continue

                    genes2 = set(str(row2[gene_col]).split('/'))                # Right: Results panel (tabs)

                    intersection = len(genes1 & genes2)

                    union = len(genes1 | genes2)        # Help section

                    if union > 0:

                        similarity = intersection / union        help_title = QLabel("Network Visualization Guide")        results_panel = self._create_results_panel()        try:

                        if similarity > 0.3:

                            G.add_edge(i, j, weight=similarity)        help_title_font = QFont()

        self.network_graph = G

        self.cluster_colors = {}        help_title_font.setPointSize(11)        splitter.addWidget(results_panel)

        cluster_ids = sorted(set(self.clustered_df['cluster_id']))

        for i, cluster_id in enumerate(cluster_ids):        help_title_font.setBold(True)

            if cluster_id == -1:

                self.cluster_colors[cluster_id] = '#999999'        help_title.setFont(help_title_font)                    from utils.go_clustering import GOClustering

            else:

                self.cluster_colors[cluster_id] = self.COLORS[i % len(self.COLORS)]        layout.addWidget(help_title)

        cluster_positions = {}

        n_clusters = len([c for c in self.clusters.values() if len(c) > 1])                # Set initial sizes (30% : 70%)

        if n_clusters > 0:

            grid_cols = ceil(sqrt(n_clusters))        help_content = QTextEdit()

            grid_rows = ceil(n_clusters / grid_cols)

            grid_spacing = 5.0        help_content.setReadOnly(True)        splitter.setSizes([400, 1000])            

            cluster_idx = 0

            for cluster_id, members in self.clusters.items():        help_content.setMaximumHeight(400)

                if len(members) == 1:

                    continue        help_content.setHtml("""        

                row = cluster_idx // grid_cols

                col = cluster_idx % grid_cols        <style>

                center_x = col * grid_spacing

                center_y = row * grid_spacing            body { font-family: Arial; font-size: 10pt; }        main_layout.addWidget(splitter)            self.progress.emit("Initializing clustering...")

                subgraph = G.subgraph(members)

                if len(members) > 1:            h3 { color: #2c3e50; margin-top: 10px; margin-bottom: 5px; }

                    sub_pos = nx.spring_layout(subgraph, k=0.5, iterations=50)

                else:            ul { margin-top: 5px; margin-bottom: 5px; }        

                    sub_pos = {members[0]: (0, 0)}

                for node, (x, y) in sub_pos.items():            li { margin-bottom: 3px; }

                    cluster_positions[node] = (center_x + x, center_y + y)

                cluster_idx += 1        </style>        # Bottom: Buttons            clustering = GOClustering(similarity_threshold=self.similarity_threshold)

        singleton_nodes = [idx for idx, row in self.clustered_df.iterrows() if row['cluster_id'] == -1]

        if singleton_nodes:        

            n_singletons = len(singleton_nodes)

            singleton_cols = ceil(sqrt(n_singletons))        <h3>Node Representation</h3>        button_layout = self._create_buttons()

            for i, node in enumerate(singleton_nodes):

                row = i // singleton_cols        <ul>

                col = i % singleton_cols

                cluster_positions[node] = (col * 1.5, -(row + 1) * 1.5)            <li><b>Large nodes</b>: Representative terms (lowest FDR in cluster)</li>        main_layout.addLayout(button_layout)            

        self.node_positions = cluster_positions

        for cluster_id, members in self.clusters.items():            <li><b>Small nodes</b>: Member terms in the cluster</li>

            if len(members) < 3 or cluster_id == -1:

                continue            <li><b>Node color</b>: Each cluster has a unique color</li>    

            points = np.array([cluster_positions[m] for m in members])

            try:            <li><b>Gray nodes</b>: Singleton terms (no clustering)</li>

                hull = ConvexHull(points)

                hull_points = points[hull.vertices]        </ul>    def _create_settings_panel(self) -> QWidget:            self.progress.emit("Calculating similarity matrix...")

                polygon = Polygon(hull_points, alpha=0.2, facecolor=self.cluster_colors[cluster_id], edgecolor=self.cluster_colors[cluster_id], linewidth=2)

                ax.add_patch(polygon)        

            except:

                pass        <h3>Cluster Layout</h3>        """Create left settings panel"""

        for edge in G.edges(data=True):

            n1, n2, data = edge        <ul>

            if n1 in cluster_positions and n2 in cluster_positions:

                x1, y1 = cluster_positions[n1]            <li>Terms are arranged in a <b>grid layout</b></li>        panel = QWidget()            clustered_df, clusters = clustering.cluster_terms(self.df)

                x2, y2 = cluster_positions[n2]

                weight = data.get('weight', 0.5)            <li>Each cluster occupies a separate grid cell</li>

                ax.plot([x1, x2], [y1, y2], color='gray', alpha=0.3, linewidth=weight * 2, zorder=1)

        for node in G.nodes():            <li>Within each cluster, terms are positioned using spring layout</li>        layout = QVBoxLayout(panel)

            if node not in cluster_positions:

                continue            <li><b>Convex hulls</b> (polygons) outline each cluster boundary</li>

            x, y = cluster_positions[node]

            cluster_id = G.nodes[node]['cluster_id']        </ul>                    

            is_rep = G.nodes[node].get('is_representative', False)

            color = self.cluster_colors.get(cluster_id, '#999999')        

            if is_rep:

                size = self.node_size        <h3>Edges (Connections)</h3>        # Dataset information

                edge_color = 'black'

                edge_width = 2        <ul>

            else:

                size = self.node_size * 0.4            <li>Lines connect GO terms with similar gene sets</li>        info_group = QGroupBox("📊 Dataset Information")            self.progress.emit("Clustering complete!")

                edge_color = color

                edge_width = 1            <li>Line width indicates similarity strength</li>

            ax.scatter(x, y, s=size, c=color, edgecolors=edge_color, linewidths=edge_width, zorder=2)

        if self.top_n_labels > 0:            <li>Only significant similarities are shown</li>        info_layout = QFormLayout()

            fdr_col = None

            for col in ['p.adjust', 'FDR', 'padj', 'qvalue']:        </ul>

                if col in self.clustered_df.columns:

                    fdr_col = col                info_layout.addRow("Dataset:", QLabel(self.dataset.name))            self.finished.emit(clustered_df, clusters)

                    break

            if fdr_col:        <h3>Interactive Features</h3>

                top_terms = self.clustered_df.nsmallest(self.top_n_labels, fdr_col)

                for idx, row in top_terms.iterrows():        <ul>        info_layout.addRow("Total Terms:", QLabel(str(len(self.dataset.dataframe))))

                    if idx in cluster_positions:

                        x, y = cluster_positions[idx]            <li><b>Hover</b>: Move mouse over a node to see term details</li>

                        desc_col = None

                        for col in ['Description', 'Term', 'term']:            <li><b>Labels</b>: Top N most significant terms are labeled</li>        info_group.setLayout(info_layout)            

                            if col in row.index:

                                desc_col = col            <li><b>Zoom</b>: Use toolbar to zoom and pan</li>

                                break

                        if desc_col:            <li><b>Customize</b>: Adjust label count and node size below</li>        layout.addWidget(info_group)

                            label = row[desc_col]

                            if len(label) > 40:        </ul>

                                label = label[:37] + '...'

                            ax.text(x, y, label, fontsize=8, ha='center', va='bottom', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.8), zorder=3)                        except Exception as e:

        if cluster_positions:

            x_coords = [pos[0] for pos in cluster_positions.values()]        <h3>Singletons</h3>

            y_coords = [pos[1] for pos in cluster_positions.values()]

            x_min, x_max = min(x_coords), max(x_coords)        <ul>        # Clustering Parameters

            y_min, y_max = min(y_coords), max(y_coords)

            x_range = x_max - x_min            <li>Terms that don't cluster with others appear in gray</li>

            y_range = y_max - y_min

            x_margin = x_range * 0.15 if x_range > 0 else 1            <li>These are unique or highly specific terms</li>        params_group = QGroupBox("⚙️ Clustering Parameters")            self.logger.error(f"Clustering failed: {e}", exc_info=True)

            y_margin = y_range * 0.15 if y_range > 0 else 1

            ax.set_xlim(x_min - x_margin, x_max + x_margin)            <li>Still included in the analysis and export</li>

            ax.set_ylim(y_min - y_margin, y_max + y_margin)

        ax.set_aspect('equal')        </ul>        params_layout = QFormLayout()

        ax.axis('off')

        self.canvas.draw()        """)

        

    def _on_network_hover(self, event):        layout.addWidget(help_content)                    self.error.emit(str(e))

        """Handle mouse hover over network graph"""

        if event.inaxes is None or self.node_positions is None:        

            return

        mouse_x, mouse_y = event.xdata, event.ydata        layout.addStretch()        # Similarity Threshold

        closest_node = None

        min_distance = float('inf')        

        for node, (x, y) in self.node_positions.items():

            distance = sqrt((mouse_x - x)**2 + (mouse_y - y)**2)        return panel        similarity_layout = QHBoxLayout()

            is_rep = self.clustered_df.loc[node, 'is_representative']

            threshold = 0.3 if is_rep else 0.15        

            if distance < threshold and distance < min_distance:

                closest_node = node    def _create_results_panel(self):        self.similarity_slider = QSlider(Qt.Orientation.Horizontal)

                min_distance = distance

        if closest_node is not None:        """Create the right panel with results tabs"""

            row = self.clustered_df.loc[closest_node]

            desc_col = None        panel = QWidget()        self.similarity_slider.setRange(30, 90)

            for col in ['Description', 'Term', 'term']:

                if col in row.index:        layout = QVBoxLayout(panel)

                    desc_col = col

                    break                self.similarity_slider.setValue(70)  # default 0.7

            fdr_col = None

            for col in ['p.adjust', 'FDR', 'padj', 'qvalue']:        # Results label

                if col in row.index:

                    fdr_col = col        self.results_label = QLabel("No clustering results yet. Configure settings and click 'Run Clustering'.")        self.similarity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)class GOClusteringDialog(QDialog):

                    break

            count_col = None        self.results_label.setWordWrap(True)

            for col in ['Count', 'count', 'GeneRatio']:

                if col in row.index:        layout.addWidget(self.results_label)        self.similarity_slider.setTickInterval(10)

                    count_col = col

                    break        

            tooltip_text = ""

            if desc_col:        # Tab widget            """Interactive GO Term Clustering Dialog (Settings + Real-time Visualization)"""

                tooltip_text += f"{row[desc_col]}\n"

            if fdr_col:        self.tab_widget = QTabWidget()

                tooltip_text += f"FDR: {row[fdr_col]:.2e}\n"

            if count_col:        self.tab_widget.setEnabled(False)        self.similarity_spin = QDoubleSpinBox()

                tooltip_text += f"Count: {row[count_col]}\n"

            tooltip_text += f"Cluster: {row['cluster_id']}"        

            self.canvas.setToolTip(tooltip_text)

        else:        # Network tab        self.similarity_spin.setRange(0.3, 0.9)    

            self.canvas.setToolTip("")

                    network_tab = self._create_network_tab()

    def _update_summary(self):

        """Update the summary statistics tab"""        self.tab_widget.addTab(network_tab, "Network Visualization")        self.similarity_spin.setSingleStep(0.05)

        if self.clustered_df is None or self.clusters is None:

            return        

        n_total = len(self.clustered_df)

        n_clusters = len([c for c in self.clusters.values() if len(c) > 1])        # Summary tab        self.similarity_spin.setValue(0.7)    def __init__(self, dataset: Dataset, parent=None):

        n_singletons = len([c for c in self.clusters.values() if len(c) == 1])

        cluster_sizes = [len(c) for c in self.clusters.values() if len(c) > 1]        summary_tab = self._create_summary_tab()

        if cluster_sizes:

            avg_size = np.mean(cluster_sizes)        self.tab_widget.addTab(summary_tab, "Summary")        self.similarity_spin.setDecimals(2)

            max_size = max(cluster_sizes)

            min_size = min(cluster_sizes)        

        else:

            avg_size = max_size = min_size = 0        # Cluster table tab                super().__init__(parent)

        n_representatives = self.clustered_df['is_representative'].sum()

        summary_html = f"""        cluster_tab = self._create_cluster_tab()

        <html>

        <head>        self.tab_widget.addTab(cluster_tab, "Clustered Terms")        # Link slider and spinbox

            <style>

                body {{ font-family: Arial; font-size: 11pt; }}        

                h2 {{ color: #2c3e50; }}

                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}        # Representative table tab        self.similarity_slider.valueChanged.connect(        self.dataset = dataset

                th {{ background-color: #3498db; color: white; padding: 8px; text-align: left; }}

                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}        representative_tab = self._create_representative_tab()

                tr:nth-child(even) {{ background-color: #f2f2f2; }}

            </style>        self.tab_widget.addTab(representative_tab, "Representatives")            lambda v: self.similarity_spin.setValue(v / 100.0)

        </head>

        <body>        

            <h2>Clustering Summary</h2>

            <table>        layout.addWidget(self.tab_widget)        )        self.logger = logging.getLogger(__name__)

                <tr><th>Metric</th><th>Value</th></tr>

                <tr><td><b>Total GO Terms</b></td><td>{n_total}</td></tr>        

                <tr><td><b>Number of Clusters</b></td><td>{n_clusters}</td></tr>

                <tr><td><b>Singleton Terms</b></td><td>{n_singletons}</td></tr>        return panel        self.similarity_spin.valueChanged.connect(

                <tr><td><b>Representative Terms</b></td><td>{n_representatives}</td></tr>

                <tr><td><b>Average Cluster Size</b></td><td>{avg_size:.1f}</td></tr>        

                <tr><td><b>Largest Cluster</b></td><td>{max_size} terms</td></tr>

                <tr><td><b>Smallest Cluster</b></td><td>{min_size} terms</td></tr>    def _create_network_tab(self):            lambda v: self.similarity_slider.setValue(int(v * 100))        

            </table>

            <h2>Cluster Details</h2>        """Create the network visualization tab with customization settings"""

            <table>

                <tr><th>Cluster ID</th><th>Size</th><th>Representative Term</th></tr>        tab = QWidget()        )

        """

        for cluster_id in sorted(self.clusters.keys()):        layout = QVBoxLayout(tab)

            members = self.clusters[cluster_id]

            if len(members) == 1:                        self.setWindowTitle("? Interactive GO Term Clustering")

                continue

            cluster_df = self.clustered_df[self.clustered_df['cluster_id'] == cluster_id]        # Settings panel for network customization

            rep_row = cluster_df[cluster_df['is_representative'] == True]

            if not rep_row.empty:        settings_widget = QWidget()        similarity_layout.addWidget(self.similarity_slider, stretch=3)

                rep_row = rep_row.iloc[0]

                desc_col = None        settings_layout = QHBoxLayout(settings_widget)

                for col in ['Description', 'Term', 'term']:

                    if col in rep_row.index:        settings_layout.setContentsMargins(5, 5, 5, 5)        similarity_layout.addWidget(self.similarity_spin, stretch=1)        self.setMinimumSize(1400, 800)

                        desc_col = col

                        break        

                rep_term = rep_row[desc_col] if desc_col else "N/A"

            else:        # Label count setting        

                rep_term = "N/A"

            color = self.cluster_colors.get(cluster_id, '#999999')        label_count_label = QLabel("Labels to show:")

            summary_html += f"""

                <tr>        settings_layout.addWidget(label_count_label)        params_layout.addRow("Similarity Threshold:", similarity_layout)        

                    <td style="background-color: {color}; color: white; font-weight: bold;">{cluster_id}</td>

                    <td>{len(members)}</td>        

                    <td>{rep_term}</td>

                </tr>        self.top_n_spin = QSpinBox()        

            """

        summary_html += """        self.top_n_spin.setRange(0, 50)

            </table>

        </body>        self.top_n_spin.setValue(10)        # Threshold help        # ?button ?

        </html>

        """        self.top_n_spin.setToolTip("Number of most significant terms to label")

        self.summary_text.setHtml(summary_html)

                settings_layout.addWidget(self.top_n_spin)        threshold_help = QLabel(

    def _update_cluster_table(self):

        """Update the clustered terms table"""        

        if self.clustered_df is None:

            return        settings_layout.addSpacing(20)            "<small><i>"        self.setWindowFlags(

        df = self.clustered_df.copy()

        fdr_col = None        

        for col in ['p.adjust', 'FDR', 'padj', 'qvalue']:

            if col in df.columns:        # Node size setting            "<b>Higher (0.8-0.9):</b> Fewer, very similar clusters<br>"

                fdr_col = col

                break        node_size_label = QLabel("Node size:")

        if fdr_col:

            df = df.sort_values(['cluster_id', fdr_col])        settings_layout.addWidget(node_size_label)            "<b>Medium (0.6-0.7):</b> Balanced clustering<br>"            Qt.WindowType.Window |

        else:

            df = df.sort_values('cluster_id')        

        self.cluster_table.setRowCount(len(df))

        self.cluster_table.setColumnCount(len(df.columns))        self.node_size_spin = QSpinBox()            "<b>Lower (0.3-0.5):</b> More, diverse clusters<br>"

        self.cluster_table.setHorizontalHeaderLabels(df.columns.tolist())

        for i, (idx, row) in enumerate(df.iterrows()):        self.node_size_spin.setRange(100, 2000)

            cluster_id = row['cluster_id']

            color = self.cluster_colors.get(cluster_id, '#999999')        self.node_size_spin.setSingleStep(100)            "<b>Recommended:</b> 0.7"            Qt.WindowType.WindowMaximizeButtonHint |

            for j, col in enumerate(df.columns):

                value = row[col]        self.node_size_spin.setValue(1000)

                if isinstance(value, float):

                    if value < 0.001:        self.node_size_spin.setToolTip("Size of representative term nodes")            "</i></small>"

                        text = f"{value:.2e}"

                    else:        settings_layout.addWidget(self.node_size_spin)

                        text = f"{value:.4f}"

                else:                )            Qt.WindowType.WindowCloseButtonHint

                    text = str(value)

                item = QTableWidgetItem(text)        settings_layout.addSpacing(20)

                if cluster_id != -1:

                    qcolor = QColor(color)                threshold_help.setWordWrap(True)

                    qcolor.setAlpha(50)

                    item.setBackground(QBrush(qcolor))        # Refresh button

                self.cluster_table.setItem(i, j, item)

        self.cluster_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)        self.refresh_button = QPushButton("Refresh Plot")        threshold_help.setStyleSheet("color: #666; padding: 5px; background: #f0f0f0; border-radius: 3px;")        )

        

    def _update_representative_table(self):        self.refresh_button.setStyleSheet("""

        """Update the representative terms table"""

        if self.clustered_df is None:            QPushButton {        params_layout.addRow("", threshold_help)

            return

        df = self.clustered_df[self.clustered_df['is_representative'] == True].copy()                background-color: #17a2b8;

        fdr_col = None

        for col in ['p.adjust', 'FDR', 'padj', 'qvalue']:                color: white;                

            if col in df.columns:

                fdr_col = col                border: none;

                break

        if fdr_col:                padding: 5px 15px;        # Method display

            df = df.sort_values(fdr_col)

        self.representative_table.setRowCount(len(df))                border-radius: 3px;

        self.representative_table.setColumnCount(len(df.columns))

        self.representative_table.setHorizontalHeaderLabels(df.columns.tolist())                font-weight: bold;        method_label = QLabel("<b>Hierarchical Clustering</b> (Average Linkage)")        # Settings

        for i, (idx, row) in enumerate(df.iterrows()):

            cluster_id = row['cluster_id']            }

            color = self.cluster_colors.get(cluster_id, '#999999')

            for j, col in enumerate(df.columns):            QPushButton:hover {        method_label.setStyleSheet("color: #0066cc;")

                value = row[col]

                if isinstance(value, float):                background-color: #138496;

                    if value < 0.001:

                        text = f"{value:.2e}"            }        params_layout.addRow("Method:", method_label)        self.clustered_df = None

                    else:

                        text = f"{value:.4f}"            QPushButton:pressed {

                else:

                    text = str(value)                background-color: #117a8b;        

                item = QTableWidgetItem(text)

                qcolor = QColor(color)            }

                qcolor.setAlpha(80)

                item.setBackground(QBrush(qcolor))            QPushButton:disabled {        params_group.setLayout(params_layout)        self.clusters = None

                self.representative_table.setItem(i, j, item)

        self.representative_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)                background-color: #cccccc;

        

    def _export_clusters(self):                color: #666666;        layout.addWidget(params_group)

        """Export clustering results to Excel file"""

        if self.clustered_df is None:            }

            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Export Clustering Results", "", "Excel Files (*.xlsx)")        """)                self.worker = None

        if not file_path:

            return        self.refresh_button.clicked.connect(self._update_network_graph)

        try:

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:        self.refresh_button.setEnabled(False)        # Run Clustering button

                self.clustered_df.to_excel(writer, sheet_name='All Terms', index=False)

                representatives = self.clustered_df[self.clustered_df['is_representative'] == True]        settings_layout.addWidget(self.refresh_button)

                representatives.to_excel(writer, sheet_name='Representatives', index=False)

                cluster_summary = []                self.preview_btn = QPushButton("🔄 Run Clustering")        

                for cluster_id, members in self.clusters.items():

                    if len(members) == 1:        settings_layout.addStretch()

                        continue

                    cluster_df = self.clustered_df[self.clustered_df['cluster_id'] == cluster_id]                self.preview_btn.setStyleSheet("""

                    rep_row = cluster_df[cluster_df['is_representative'] == True]

                    if not rep_row.empty:        layout.addWidget(settings_widget)

                        rep_row = rep_row.iloc[0]

                        desc_col = None                    QPushButton {        self._init_ui()

                        for col in ['Description', 'Term', 'term']:

                            if col in rep_row.index:        # Matplotlib figure

                                desc_col = col

                                break        self.figure = Figure(figsize=(10, 8))                background-color: #0066cc;

                        rep_term = rep_row[desc_col] if desc_col else "N/A"

                    else:        self.canvas = FigureCanvas(self.figure)

                        rep_term = "N/A"

                    cluster_summary.append({'Cluster ID': cluster_id, 'Size': len(members), 'Representative': rep_term, 'Color': self.cluster_colors.get(cluster_id, '#999999')})        self.canvas.mpl_connect('motion_notify_event', self._on_network_hover)                color: white;    

                summary_df = pd.DataFrame(cluster_summary)

                summary_df.to_excel(writer, sheet_name='Cluster Summary', index=False)        

            QMessageBox.information(self, "Export Successful", f"Clustering results exported to:\n{file_path}")

        except Exception as e:        # Toolbar                font-weight: bold;

            QMessageBox.critical(self, "Export Error", f"Failed to export clustering results:\n\n{str(e)}")

                    self.toolbar = NavigationToolbar(self.canvas, tab)

    def get_clustered_dataframe(self):

        """Get the clustered DataFrame for creating a filtered dataset"""                        padding: 10px;    def _init_ui(self):

        return self.clustered_df

        layout.addWidget(self.toolbar)

        layout.addWidget(self.canvas)                border-radius: 5px;

        

        return tab            }        """UI - ?: ?, ?? ?""

        

    def _create_summary_tab(self):            QPushButton:hover {

        """Create the summary statistics tab"""

        tab = QWidget()                background-color: #0052a3;        main_layout = QVBoxLayout(self)

        layout = QVBoxLayout(tab)

                    }

        self.summary_text = QTextEdit()

        self.summary_text.setReadOnly(True)            QPushButton:disabled {        

        layout.addWidget(self.summary_text)

                        background-color: #cccccc;

        return tab

                    }        #  Splitter ( )

    def _create_cluster_tab(self):

        """Create the clustered terms table tab"""        """)

        tab = QWidget()

        layout = QVBoxLayout(tab)        self.preview_btn.clicked.connect(self._run_clustering)        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        

        # Table        layout.addWidget(self.preview_btn)

        self.cluster_table = QTableWidget()

        self.cluster_table.setSortingEnabled(True)                

        layout.addWidget(self.cluster_table)

                # Progress bar

        return tab

                self.progress_bar = QProgressBar()        # === ? ?: ? ===

    def _create_representative_tab(self):

        """Create the representative terms table tab"""        self.progress_bar.setVisible(False)

        tab = QWidget()

        layout = QVBoxLayout(tab)        self.progress_bar.setRange(0, 0)  # indeterminate        left_panel = self._create_settings_panel()

        

        # Table        layout.addWidget(self.progress_bar)

        self.representative_table = QTableWidget()

        self.representative_table.setSortingEnabled(True)                self.main_splitter.addWidget(left_panel)

        layout.addWidget(self.representative_table)

                # Status label

        return tab

                self.status_label = QLabel("")        

    def _create_buttons(self):

        """Create bottom button layout"""        self.status_label.setWordWrap(True)

        layout = QHBoxLayout()

                self.status_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")        # === ?:  ?===

        layout.addStretch()

                layout.addWidget(self.status_label)

        # Export button

        self.export_button = QPushButton("Export Clusters")                right_panel = self._create_visualization_panel()

        self.export_button.setEnabled(False)

        self.export_button.clicked.connect(self._export_clusters)        # Result Options

        layout.addWidget(self.export_button)

                repr_group = QGroupBox("📋 Result Options")        self.main_splitter.addWidget(right_panel)

        # Apply button

        self.apply_button = QPushButton("Apply")        repr_layout = QFormLayout()

        self.apply_button.setEnabled(False)

        self.apply_button.setToolTip("Apply clustering and create filtered dataset")                

        layout.addWidget(self.apply_button)

                self.show_repr_check = QCheckBox("Show representative terms only")

        # Close button

        close_button = QPushButton("Close")        self.show_repr_check.setChecked(True)        # Splitter  ? (30% : 70%)

        close_button.clicked.connect(self.reject)

        layout.addWidget(close_button)        self.show_repr_check.setToolTip("Show only the most significant term from each cluster")

        

        return layout                self.main_splitter.setSizes([400, 1000])

        

    def _run_clustering(self):        self.max_terms_spin = QSpinBox()

        """Execute clustering in background thread"""

        # Validate dataset        self.max_terms_spin.setRange(5, 200)        

        if self.dataset is None or self.dataset.empty:

            QMessageBox.warning(        self.max_terms_spin.setValue(50)

                self,

                "No Data",        self.max_terms_spin.setSuffix(" terms")        main_layout.addWidget(self.main_splitter)

                "No GO enrichment data available for clustering."

            )        

            return

                    self.min_cluster_size_spin = QSpinBox()        

        # Get threshold

        similarity_threshold = self.similarity_spin.value()        self.min_cluster_size_spin.setRange(1, 20)

        

        # Disable UI        self.min_cluster_size_spin.setValue(2)        # Settings

        self.run_button.setEnabled(False)

        self.progress_bar.setVisible(True)        self.min_cluster_size_spin.setSuffix(" terms")

        self.progress_bar.setValue(0)

                self.min_cluster_size_spin.setToolTip("Minimum number of terms in a cluster")        button_layout = self._create_buttons()

        # Create worker thread

        self.worker = ClusteringWorker(self.dataset, similarity_threshold)        

        self.worker.finished.connect(self._on_clustering_finished)

        self.worker.error.connect(self._on_clustering_error)        repr_layout.addRow("Filter:", self.show_repr_check)        main_layout.addLayout(button_layout)

        self.worker.progress.connect(self.progress_bar.setValue)

        self.worker.start()        repr_layout.addRow("Max Terms:", self.max_terms_spin)

        

    def _on_clustering_finished(self, clustered_df, clusters):        repr_layout.addRow("Min Cluster Size:", self.min_cluster_size_spin)    

        """Handle clustering completion"""

        self.clustered_df = clustered_df        

        self.clusters = clusters

                repr_group.setLayout(repr_layout)    def _create_settings_panel(self) -> QWidget:

        # Update UI

        self.run_button.setEnabled(True)        layout.addWidget(repr_group)

        self.progress_bar.setVisible(False)

                        """Create left settings panel"""

        # Update results

        self._update_results()        # Help

        

        # Enable tabs and buttons        help_label = QLabel(        panel = QWidget()

        self.tab_widget.setEnabled(True)

        self.export_button.setEnabled(True)            "<b>How to use:</b><br>"

        self.apply_button.setEnabled(True)

        self.refresh_button.setEnabled(True)            "1. Adjust similarity threshold<br>"        layout = QVBoxLayout(panel)

        

        # Update results label            "2. Click 'Run Clustering'<br>"

        n_clusters = len([c for c in clusters.values() if len(c) > 1])

        n_singletons = len([c for c in clusters.values() if len(c) == 1])            "3. Review results on the right<br>"        

        self.results_label.setText(

            f"Clustering complete: {n_clusters} clusters, {n_singletons} singletons"            "4. Click 'Apply' to create filtered dataset<br><br>"

        )

                    "<b>Network visualization:</b><br>"        # Dataset information

    def _on_clustering_error(self, error_message):

        """Handle clustering error"""            "• <b>Large nodes:</b> Representative terms<br>"

        self.run_button.setEnabled(True)

        self.progress_bar.setVisible(False)            "• <b>Small nodes:</b> Member terms<br>"        info_group = QGroupBox("📊 Dataset Information")

        

        QMessageBox.critical(            "• <b>Clusters:</b> Arranged in grid layout<br>"

            self,

            "Clustering Error",            "• <b>Edges:</b> Within-cluster connections only<br>"        info_layout = QFormLayout()

            f"An error occurred during clustering:\n\n{error_message}"

        )            "• <b>Hover:</b> Mouse over nodes for details<br>"

        

    def _update_results(self):            "• <b>Right gray area:</b> Singleton terms"        

        """Update all result displays"""

        if self.clustered_df is None:        )

            return

                    help_label.setWordWrap(True)        n_terms = len(self.dataset.dataframe) if self.dataset.dataframe is not None else 0

        self._update_network_graph()

        self._update_summary()        help_label.setStyleSheet("color: #444; font-size: 9pt; padding: 10px; background: #ffffcc; border-radius: 5px;")

        self._update_cluster_table()

        self._update_representative_table()        layout.addWidget(help_label)        info_layout.addRow("Dataset:", QLabel(self.dataset.name))

        

    def _update_network_graph(self):        

        """Update the network visualization with current settings"""

        if self.clustered_df is None or self.clusters is None:        layout.addStretch()        info_layout.addRow("Total Terms:", QLabel(f"<b>{n_terms:,}</b>"))

            return

                    

        # Get current settings

        self.top_n_labels = self.top_n_spin.value()        return panel        

        self.node_size = self.node_size_spin.value()

            

        # Clear figure

        self.figure.clear()    def _create_results_panel(self) -> QWidget:        info_group.setLayout(info_layout)

        ax = self.figure.add_subplot(111)

                """Create right results panel"""

        # Create graph

        G = nx.Graph()        panel = QWidget()        layout.addWidget(info_group)

        

        # Add nodes        layout = QVBoxLayout(panel)

        for idx, row in self.clustered_df.iterrows():

            G.add_node(idx, **row.to_dict())                

            

        # Add edges (based on gene overlap)        # Tab Widget

        gene_col = None

        for col in ['geneID', 'Genes', 'genes']:        self.result_tabs = QTabWidget()        # Settings

            if col in self.clustered_df.columns:

                gene_col = col        

                break

                        # Tab 1: Network Visualization        params_group = QGroupBox("")

        if gene_col:

            for i, row1 in self.clustered_df.iterrows():        self.network_tab = self._create_network_tab()

                genes1 = set(str(row1[gene_col]).split('/'))

                for j, row2 in self.clustered_df.iterrows():        self.result_tabs.addTab(self.network_tab, "🌐 Network")        params_layout = QFormLayout()

                    if i >= j:

                        continue        

                    genes2 = set(str(row2[gene_col]).split('/'))

                            # Tab 2: Summary        

                    # Calculate Jaccard similarity

                    intersection = len(genes1 & genes2)        self.summary_tab = self._create_summary_tab()

                    union = len(genes1 | genes2)

                    if union > 0:        self.result_tabs.addTab(self.summary_tab, "📊 Summary")        # Jaccard Similarity Threshold

                        similarity = intersection / union

                        if similarity > 0.3:  # Threshold for edge creation        

                            G.add_edge(i, j, weight=similarity)

                                    # Tab 3: Clusters        similarity_layout = QHBoxLayout()

        self.network_graph = G

                self.cluster_tab = self._create_cluster_tab()

        # Assign colors to clusters

        self.cluster_colors = {}        self.result_tabs.addTab(self.cluster_tab, "🗂️ Clusters")        self.similarity_slider = QSlider(Qt.Orientation.Horizontal)

        cluster_ids = sorted(set(self.clustered_df['cluster_id']))

        for i, cluster_id in enumerate(cluster_ids):        

            if cluster_id == -1:

                self.cluster_colors[cluster_id] = '#999999'  # Gray for singletons        # Tab 4: Representatives        self.similarity_slider.setMinimum(30)  # 0.3

            else:

                self.cluster_colors[cluster_id] = self.COLORS[i % len(self.COLORS)]        self.repr_tab = self._create_representative_tab()

                

        # Layout: Grid arrangement of clusters        self.result_tabs.addTab(self.repr_tab, "⭐ Representatives")        self.similarity_slider.setMaximum(90)  # 0.9

        cluster_positions = {}

        n_clusters = len([c for c in self.clusters.values() if len(c) > 1])        

        

        if n_clusters > 0:        layout.addWidget(self.result_tabs)        self.similarity_slider.setValue(70)  # ?0.7

            grid_cols = ceil(sqrt(n_clusters))

            grid_rows = ceil(n_clusters / grid_cols)        

            

            grid_spacing = 5.0        return panel        self.similarity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)

            

            cluster_idx = 0    

            for cluster_id, members in self.clusters.items():

                if len(members) == 1:    def _create_network_tab(self) -> QWidget:        self.similarity_slider.setTickInterval(10)

                    continue  # Handle singletons separately

                            """Create network visualization tab"""

                # Grid position

                row = cluster_idx // grid_cols        widget = QWidget()        

                col = cluster_idx % grid_cols

                center_x = col * grid_spacing        layout = QVBoxLayout(widget)

                center_y = row * grid_spacing

                                self.similarity_spin = QDoubleSpinBox()

                # Create subgraph for cluster

                subgraph = G.subgraph(members)        # Settings panel

                

                # Spring layout within cluster        settings_panel = QWidget()        self.similarity_spin.setRange(0.3, 0.9)

                if len(members) > 1:

                    sub_pos = nx.spring_layout(subgraph, k=0.5, iterations=50)        settings_layout = QHBoxLayout(settings_panel)

                else:

                    sub_pos = {members[0]: (0, 0)}        settings_layout.setContentsMargins(5, 5, 5, 5)        self.similarity_spin.setSingleStep(0.05)

                    

                # Offset to grid position        

                for node, (x, y) in sub_pos.items():

                    cluster_positions[node] = (center_x + x, center_y + y)        # Top N labels        self.similarity_spin.setValue(0.7)

                    

                cluster_idx += 1        settings_layout.addWidget(QLabel("Labels to show:"))

                

        # Position singletons        self.top_n_spin = QSpinBox()        self.similarity_spin.setDecimals(2)

        singleton_nodes = [idx for idx, row in self.clustered_df.iterrows() 

                          if row['cluster_id'] == -1]        self.top_n_spin.setRange(0, 50)

        if singleton_nodes:

            # Place singletons in bottom row        self.top_n_spin.setValue(10)        

            n_singletons = len(singleton_nodes)

            singleton_cols = ceil(sqrt(n_singletons))        self.top_n_spin.setSuffix(" terms")

            

            for i, node in enumerate(singleton_nodes):        self.top_n_spin.setToolTip("Number of top terms to label (by FDR)")        # Settings

                row = i // singleton_cols

                col = i % singleton_cols        settings_layout.addWidget(self.top_n_spin)

                cluster_positions[node] = (

                    col * 1.5,                self.similarity_slider.valueChanged.connect(

                    -(row + 1) * 1.5

                )        settings_layout.addSpacing(20)

                

        self.node_positions = cluster_positions                    lambda v: self.similarity_spin.setValue(v / 100.0)

        

        # Draw cluster hulls        # Node size

        for cluster_id, members in self.clusters.items():

            if len(members) < 3 or cluster_id == -1:        settings_layout.addWidget(QLabel("Node size:"))        )

                continue

                        self.node_size_spin = QSpinBox()

            points = np.array([cluster_positions[m] for m in members])

                    self.node_size_spin.setRange(100, 2000)        self.similarity_spin.valueChanged.connect(

            try:

                hull = ConvexHull(points)        self.node_size_spin.setValue(1000)

                hull_points = points[hull.vertices]

                        self.node_size_spin.setSingleStep(100)            lambda v: self.similarity_slider.setValue(int(v * 100))

                polygon = Polygon(

                    hull_points,        self.node_size_spin.setToolTip("Size of representative nodes")

                    alpha=0.2,

                    facecolor=self.cluster_colors[cluster_id],        settings_layout.addWidget(self.node_size_spin)        )

                    edgecolor=self.cluster_colors[cluster_id],

                    linewidth=2        

                )

                ax.add_patch(polygon)        settings_layout.addSpacing(20)        

            except:

                pass  # Skip if convex hull fails        

                

        # Draw edges        # Refresh button        similarity_layout.addWidget(self.similarity_slider, stretch=3)

        for edge in G.edges(data=True):

            n1, n2, data = edge        refresh_btn = QPushButton("🔄 Refresh Plot")

            if n1 in cluster_positions and n2 in cluster_positions:

                x1, y1 = cluster_positions[n1]        refresh_btn.setToolTip("Redraw network with current settings")        similarity_layout.addWidget(self.similarity_spin, stretch=1)

                x2, y2 = cluster_positions[n2]

                weight = data.get('weight', 0.5)        refresh_btn.clicked.connect(self._update_network_graph)

                ax.plot(

                    [x1, x2], [y1, y2],        refresh_btn.setStyleSheet("""        

                    color='gray',

                    alpha=0.3,            QPushButton {

                    linewidth=weight * 2,

                    zorder=1                background-color: #17a2b8;        params_layout.addRow("Similarity Threshold:", similarity_layout)

                )

                                color: white;

        # Draw nodes

        for node in G.nodes():                font-weight: bold;        

            if node not in cluster_positions:

                continue                padding: 5px 15px;

                

            x, y = cluster_positions[node]                border-radius: 3px;        # Threshold ?

            cluster_id = G.nodes[node]['cluster_id']

            is_rep = G.nodes[node].get('is_representative', False)            }

            

            color = self.cluster_colors.get(cluster_id, '#999999')            QPushButton:hover {        threshold_help = QLabel(

            

            # Node size based on representative status                background-color: #138496;

            if is_rep:

                size = self.node_size            }            "<small><i>"

                edge_color = 'black'

                edge_width = 2        """)

            else:

                size = self.node_size * 0.4        settings_layout.addWidget(refresh_btn)            "<b>Higher (0.8-0.9):</b> Fewer, very similar clusters<br>"

                edge_color = color

                edge_width = 1        

                

            ax.scatter(        settings_layout.addStretch()            "<b>Medium (0.6-0.7):</b> Balanced clustering<br>"

                x, y,

                s=size,        

                c=color,

                edgecolors=edge_color,        layout.addWidget(settings_panel)            "<b>Lower (0.3-0.5):</b> More, diverse clusters<br>"

                linewidths=edge_width,

                zorder=2        

            )

                    # Matplotlib Figure            "<b>Recommended:</b> 0.7"

        # Add labels for top N terms

        if self.top_n_labels > 0:        self.network_figure = Figure(figsize=(14, 10), facecolor='white')

            # Sort by FDR

            fdr_col = None        self.network_canvas = FigureCanvas(self.network_figure)            "</i></small>"

            for col in ['p.adjust', 'FDR', 'padj', 'qvalue']:

                if col in self.clustered_df.columns:        

                    fdr_col = col

                    break        # Navigation toolbar        )

                    

            if fdr_col:        self.network_toolbar = NavigationToolbar(self.network_canvas, widget)

                top_terms = self.clustered_df.nsmallest(self.top_n_labels, fdr_col)

                        layout.addWidget(self.network_toolbar)        threshold_help.setWordWrap(True)

                for idx, row in top_terms.iterrows():

                    if idx in cluster_positions:        

                        x, y = cluster_positions[idx]

                                # Canvas        threshold_help.setStyleSheet("color: #666; padding: 5px; background: #f0f0f0; border-radius: 3px;")

                        # Get term description

                        desc_col = None        layout.addWidget(self.network_canvas)

                        for col in ['Description', 'Term', 'term']:

                            if col in row.index:                params_layout.addRow("", threshold_help)

                                desc_col = col

                                break        # Initial message

                                

                        if desc_col:        ax = self.network_figure.add_subplot(111)        

                            label = row[desc_col]

                            if len(label) > 40:        ax.text(0.5, 0.5, 'Click "Run Clustering" to generate network visualization',

                                label = label[:37] + '...'

                                                ha='center', va='center', fontsize=14, color='gray',        # Method ? (? ?)

                            ax.text(

                                x, y,                transform=ax.transAxes)

                                label,

                                fontsize=8,        ax.axis('off')        method_label = QLabel("<b>Hierarchical Clustering</b> (Average Linkage)")

                                ha='center',

                                va='bottom',        self.network_canvas.draw()

                                bbox=dict(

                                    boxstyle='round,pad=0.3',                method_label.setStyleSheet("color: #0066cc;")

                                    facecolor='white',

                                    edgecolor='gray',        # Mouse hover event

                                    alpha=0.8

                                ),        self.network_canvas.mpl_connect('motion_notify_event', self._on_network_hover)        params_layout.addRow("Method:", method_label)

                                zorder=3

                            )        

                            

        # Set axis limits with 15% margin        # Hover info storage        

        if cluster_positions:

            x_coords = [pos[0] for pos in cluster_positions.values()]        self.hover_annotation = None

            y_coords = [pos[1] for pos in cluster_positions.values()]

                    self.node_positions = {}        params_group.setLayout(params_layout)

            x_min, x_max = min(x_coords), max(x_coords)

            y_min, y_max = min(y_coords), max(y_coords)        self.node_info_map = {}

            

            x_range = x_max - x_min                layout.addWidget(params_group)

            y_range = y_max - y_min

                    return widget

            x_margin = x_range * 0.15 if x_range > 0 else 1

            y_margin = y_range * 0.15 if y_range > 0 else 1            

            

            ax.set_xlim(x_min - x_margin, x_max + x_margin)    def _create_summary_tab(self) -> QWidget:

            ax.set_ylim(y_min - y_margin, y_max + y_margin)

                    """Create summary tab"""        # Preview button

        ax.set_aspect('equal')

        ax.axis('off')        widget = QWidget()

        

        self.canvas.draw()        layout = QVBoxLayout(widget)        self.preview_btn = QPushButton("? Run Clustering")

        

    def _on_network_hover(self, event):        

        """Handle mouse hover over network graph"""

        if event.inaxes is None or self.node_positions is None:        self.summary_label = QLabel(        self.preview_btn.setStyleSheet("""

            return

                        "<h3>📊 Clustering Summary</h3>"

        # Check if mouse is near any node

        mouse_x, mouse_y = event.xdata, event.ydata            "<p>Click 'Run Clustering' to start analysis.</p>"            QPushButton {

        

        closest_node = None        )

        min_distance = float('inf')

                self.summary_label.setWordWrap(True)                background-color: #0066cc;

        for node, (x, y) in self.node_positions.items():

            distance = sqrt((mouse_x - x)**2 + (mouse_y - y)**2)        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            

            # Threshold based on node size        self.summary_label.setStyleSheet("padding: 20px; color: #666;")                color: white;

            is_rep = self.clustered_df.loc[node, 'is_representative']

            threshold = 0.3 if is_rep else 0.15        

            

            if distance < threshold and distance < min_distance:        layout.addWidget(self.summary_label)                font-weight: bold;

                closest_node = node

                min_distance = distance        layout.addStretch()

                

        # Update tooltip                        padding: 10px;

        if closest_node is not None:

            row = self.clustered_df.loc[closest_node]        return widget

            

            # Get term description                    border-radius: 5px;

            desc_col = None

            for col in ['Description', 'Term', 'term']:    def _create_cluster_tab(self) -> QWidget:

                if col in row.index:

                    desc_col = col        """Create cluster details tab"""            }

                    break

                            widget = QWidget()

            # Get FDR

            fdr_col = None        layout = QVBoxLayout(widget)            QPushButton:hover {

            for col in ['p.adjust', 'FDR', 'padj', 'qvalue']:

                if col in row.index:        

                    fdr_col = col

                    break        # Cluster table                background-color: #0052a3;

                    

            # Get count        self.cluster_table = QTableWidget()

            count_col = None

            for col in ['Count', 'count', 'GeneRatio']:        self.cluster_table.setColumnCount(5)            }

                if col in row.index:

                    count_col = col        self.cluster_table.setHorizontalHeaderLabels([

                    break

                                "Cluster ID", "Term ID", "Description", "FDR", "Gene Count"            QPushButton:disabled {

            tooltip_text = ""

            if desc_col:        ])

                tooltip_text += f"{row[desc_col]}\n"

            if fdr_col:        header = self.cluster_table.horizontalHeader()                background-color: #cccccc;

                tooltip_text += f"FDR: {row[fdr_col]:.2e}\n"

            if count_col:        if header:

                tooltip_text += f"Count: {row[count_col]}\n"

            tooltip_text += f"Cluster: {row['cluster_id']}"            header.setStretchLastSection(True)            }

            

            self.canvas.setToolTip(tooltip_text)        

        else:

            self.canvas.setToolTip("")        self.cluster_table.setSortingEnabled(True)        """)

            

    def _update_summary(self):        

        """Update the summary statistics tab"""

        if self.clustered_df is None or self.clusters is None:        layout.addWidget(self.cluster_table)        self.preview_btn.clicked.connect(self._run_clustering)

            return

                    

        # Calculate statistics

        n_total = len(self.clustered_df)        return widget        layout.addWidget(self.preview_btn)

        n_clusters = len([c for c in self.clusters.values() if len(c) > 1])

        n_singletons = len([c for c in self.clusters.values() if len(c) == 1])    

        

        # Cluster sizes    def _create_representative_tab(self) -> QWidget:        

        cluster_sizes = [len(c) for c in self.clusters.values() if len(c) > 1]

        if cluster_sizes:        """Create representative terms tab"""

            avg_size = np.mean(cluster_sizes)

            max_size = max(cluster_sizes)        widget = QWidget()        # Progress bar

            min_size = min(cluster_sizes)

        else:        layout = QVBoxLayout(widget)

            avg_size = max_size = min_size = 0

                            self.progress_bar = QProgressBar()

        # Representative terms

        n_representatives = self.clustered_df['is_representative'].sum()        # Representative table

        

        # Build summary text        self.repr_table = QTableWidget()        self.progress_bar.setVisible(False)

        summary_html = f"""

        <html>        self.repr_table.setColumnCount(5)

        <head>

            <style>        self.repr_table.setHorizontalHeaderLabels([        self.progress_bar.setRange(0, 0)  # indeterminate

                body {{ font-family: Arial; font-size: 11pt; }}

                h2 {{ color: #2c3e50; }}            "Term ID", "Description", "FDR", "Gene Count", "Cluster Size"

                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}

                th {{ background-color: #3498db; color: white; padding: 8px; text-align: left; }}        ])        layout.addWidget(self.progress_bar)

                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}

                tr:nth-child(even) {{ background-color: #f2f2f2; }}        header = self.repr_table.horizontalHeader()

            </style>

        </head>        if header:        

        <body>

            <h2>Clustering Summary</h2>            header.setStretchLastSection(True)

            

            <table>                # Status label

                <tr>

                    <th>Metric</th>        self.repr_table.setSortingEnabled(True)

                    <th>Value</th>

                </tr>                self.status_label = QLabel("")

                <tr>

                    <td><b>Total GO Terms</b></td>        layout.addWidget(self.repr_table)

                    <td>{n_total}</td>

                </tr>                self.status_label.setWordWrap(True)

                <tr>

                    <td><b>Number of Clusters</b></td>        return widget

                    <td>{n_clusters}</td>

                </tr>            self.status_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")

                <tr>

                    <td><b>Singleton Terms</b></td>    def _create_buttons(self) -> QHBoxLayout:

                    <td>{n_singletons}</td>

                </tr>        """Create bottom button layout"""        layout.addWidget(self.status_label)

                <tr>

                    <td><b>Representative Terms</b></td>        button_layout = QHBoxLayout()

                    <td>{n_representatives}</td>

                </tr>                

                <tr>

                    <td><b>Average Cluster Size</b></td>        # Export button

                    <td>{avg_size:.1f}</td>

                </tr>        self.export_btn = QPushButton("📁 Export Clusters")        # Representative Terms ?

                <tr>

                    <td><b>Largest Cluster</b></td>        self.export_btn.setEnabled(False)

                    <td>{max_size} terms</td>

                </tr>        self.export_btn.clicked.connect(self._export_clusters)        repr_group = QGroupBox("")

                <tr>

                    <td><b>Smallest Cluster</b></td>        button_layout.addWidget(self.export_btn)

                    <td>{min_size} terms</td>

                </tr>                repr_layout = QFormLayout()

            </table>

                    button_layout.addStretch()

            <h2>Cluster Details</h2>

            <table>                

                <tr>

                    <th>Cluster ID</th>        # Apply button

                    <th>Size</th>

                    <th>Representative Term</th>        self.apply_btn = QPushButton("✅ Apply (Create Filtered Dataset)")        self.show_repr_check = QCheckBox("Show representative terms only")

                </tr>

        """        self.apply_btn.setEnabled(False)

        

        # Add cluster details        self.apply_btn.setStyleSheet("""        self.show_repr_check.setChecked(True)

        for cluster_id in sorted(self.clusters.keys()):

            members = self.clusters[cluster_id]            QPushButton {

            if len(members) == 1:

                continue  # Skip singletons                background-color: #28a745;        self.show_repr_check.setToolTip("Show only the most significant term from each cluster")

                

            # Find representative                color: white;

            cluster_df = self.clustered_df[self.clustered_df['cluster_id'] == cluster_id]

            rep_row = cluster_df[cluster_df['is_representative'] == True]                font-weight: bold;        

            

            if not rep_row.empty:                padding: 10px 20px;

                rep_row = rep_row.iloc[0]

                desc_col = None                border-radius: 5px;        self.max_terms_spin = QSpinBox()

                for col in ['Description', 'Term', 'term']:

                    if col in rep_row.index:            }

                        desc_col = col

                        break            QPushButton:hover {        self.max_terms_spin.setRange(5, 200)

                rep_term = rep_row[desc_col] if desc_col else "N/A"

            else:                background-color: #218838;

                rep_term = "N/A"

                            }        self.max_terms_spin.setValue(50)

            color = self.cluster_colors.get(cluster_id, '#999999')

                        QPushButton:disabled {

            summary_html += f"""

                <tr>                background-color: #cccccc;        self.max_terms_spin.setSuffix(" terms")

                    <td style="background-color: {color}; color: white; font-weight: bold;">

                        {cluster_id}            }

                    </td>

                    <td>{len(members)}</td>        """)        

                    <td>{rep_term}</td>

                </tr>        self.apply_btn.clicked.connect(self.accept)

            """

                    button_layout.addWidget(self.apply_btn)        self.min_cluster_size_spin = QSpinBox()

        summary_html += """

            </table>        

        </body>

        </html>        # Cancel button        self.min_cluster_size_spin.setRange(1, 20)

        """

                cancel_btn = QPushButton("Cancel")

        self.summary_text.setHtml(summary_html)

                cancel_btn.clicked.connect(self.reject)        self.min_cluster_size_spin.setValue(2)

    def _update_cluster_table(self):

        """Update the clustered terms table"""        button_layout.addWidget(cancel_btn)

        if self.clustered_df is None:

            return                self.min_cluster_size_spin.setSuffix(" terms")

            

        df = self.clustered_df.copy()        return button_layout

        

        # Sort by cluster and FDR            self.min_cluster_size_spin.setToolTip("Minimum number of terms in a cluster to be considered significant")

        fdr_col = None

        for col in ['p.adjust', 'FDR', 'padj', 'qvalue']:    def _run_clustering(self):

            if col in df.columns:

                fdr_col = col        """Execute clustering"""        

                break

                        # Disable button

        if fdr_col:

            df = df.sort_values(['cluster_id', fdr_col])        self.preview_btn.setEnabled(False)        repr_layout.addRow("Filter:", self.show_repr_check)

        else:

            df = df.sort_values('cluster_id')        self.progress_bar.setVisible(True)

            

        # Setup table        self.status_label.setText("Starting clustering...")        repr_layout.addRow("Max Terms:", self.max_terms_spin)

        self.cluster_table.setRowCount(len(df))

        self.cluster_table.setColumnCount(len(df.columns))        

        self.cluster_table.setHorizontalHeaderLabels(df.columns.tolist())

                # Start worker thread        repr_layout.addRow("Min Cluster Size:", self.min_cluster_size_spin)

        # Populate table

        for i, (idx, row) in enumerate(df.iterrows()):        threshold = self.similarity_spin.value()

            cluster_id = row['cluster_id']

            color = self.cluster_colors.get(cluster_id, '#999999')        self.worker = ClusteringWorker(self.dataset.dataframe.copy(), threshold)        

            

            for j, col in enumerate(df.columns):        self.worker.finished.connect(self._on_clustering_finished)

                value = row[col]

                        self.worker.progress.connect(self._on_progress_update)        repr_group.setLayout(repr_layout)

                # Format value

                if isinstance(value, float):        self.worker.error.connect(self._on_clustering_error)

                    if value < 0.001:

                        text = f"{value:.2e}"        self.worker.start()        layout.addWidget(repr_group)

                    else:

                        text = f"{value:.4f}"    

                else:

                    text = str(value)    def _on_progress_update(self, message: str):        

                    

                item = QTableWidgetItem(text)        """Progress update"""

                

                # Set background color alternating by cluster        self.status_label.setText(message)        # Settings

                if cluster_id != -1:

                    # Use lighter version of cluster color    

                    qcolor = QColor(color)

                    qcolor.setAlpha(50)    def _on_clustering_finished(self, clustered_df: pd.DataFrame, clusters: Dict):        help_label = QLabel(

                    item.setBackground(QBrush(qcolor))

                            """Clustering finished callback"""

                self.cluster_table.setItem(i, j, item)

                        self.clustered_df = clustered_df            "<b>How to use:</b><br>"

        # Resize columns

        self.cluster_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)        self.clusters = clusters

        

    def _update_representative_table(self):                    "1. Adjust similarity threshold<br>"

        """Update the representative terms table"""

        if self.clustered_df is None:        # Update UI

            return

                    self._update_results()            "2. Click 'Run Clustering'<br>"

        # Filter representatives

        df = self.clustered_df[self.clustered_df['is_representative'] == True].copy()        

        

        # Sort by FDR        # Enable buttons            "3. Review results on the right<br>"

        fdr_col = None

        for col in ['p.adjust', 'FDR', 'padj', 'qvalue']:        self.preview_btn.setEnabled(True)

            if col in df.columns:

                fdr_col = col        self.progress_bar.setVisible(False)            "4. Click 'Apply' to create filtered dataset<br><br>"

                break

                        self.apply_btn.setEnabled(True)

        if fdr_col:

            df = df.sort_values(fdr_col)        self.export_btn.setEnabled(True)            "<b>Network visualization:</b><br>"

            

        # Setup table        

        self.representative_table.setRowCount(len(df))

        self.representative_table.setColumnCount(len(df.columns))        n_clusters = len(clusters)            "<b>Large nodes:</b> Representative terms<br>"

        self.representative_table.setHorizontalHeaderLabels(df.columns.tolist())

                n_repr = len(clustered_df[clustered_df['is_representative'] == True]) if 'is_representative' in clustered_df.columns else 0

        # Populate table

        for i, (idx, row) in enumerate(df.iterrows()):                    "<b>Small nodes:</b> Member terms<br>"

            cluster_id = row['cluster_id']

            color = self.cluster_colors.get(cluster_id, '#999999')        self.status_label.setText(

            

            for j, col in enumerate(df.columns):            f"✅ Clustering complete! {n_clusters} clusters, {n_repr} representative terms"            "<b>Clusters:</b> Arranged in grid layout<br>"

                value = row[col]

                        )

                # Format value

                if isinstance(value, float):        self.status_label.setStyleSheet("color: #28a745; font-weight: bold; padding: 5px;")            "<b>Edges:</b> Within-cluster connections only<br>"

                    if value < 0.001:

                        text = f"{value:.2e}"    

                    else:

                        text = f"{value:.4f}"    def _on_clustering_error(self, error_msg: str):            "<b>Hover:</b> Mouse over nodes for details<br>"

                else:

                    text = str(value)        """Clustering error callback"""

                    

                item = QTableWidgetItem(text)        self.preview_btn.setEnabled(True)            "<b>Right gray area:</b> Singleton terms"

                

                # Set background color        self.progress_bar.setVisible(False)

                qcolor = QColor(color)

                qcolor.setAlpha(80)                )

                item.setBackground(QBrush(qcolor))

                        self.status_label.setText(f"❌ Error: {error_msg}")

                self.representative_table.setItem(i, j, item)

                        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold; padding: 5px;")        help_label.setWordWrap(True)

        # Resize columns

        self.representative_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)        

        

    def _export_clusters(self):        QMessageBox.critical(self, "Clustering Error", f"Failed to perform clustering:\n{error_msg}")        help_label.setStyleSheet("color: #444; font-size: 9pt; padding: 10px; background: #ffffcc; border-radius: 5px;")

        """Export clustering results to Excel file"""

        if self.clustered_df is None:    

            return

                def _update_results(self):        layout.addWidget(help_label)

        # Get save file path

        file_path, _ = QFileDialog.getSaveFileName(        """Update results UI"""

            self,

            "Export Clustering Results",        if self.clustered_df is None or self.clusters is None:        

            "",

            "Excel Files (*.xlsx)"            return

        )

                        layout.addStretch()

        if not file_path:

            return        # Update network graph (first)

            

        try:        self._update_network_graph()        

            # Create Excel writer

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:        

                # Export all terms

                self.clustered_df.to_excel(writer, sheet_name='All Terms', index=False)        # Update summary        return panel

                

                # Export representatives only        self._update_summary()

                representatives = self.clustered_df[

                    self.clustered_df['is_representative'] == True            

                ]

                representatives.to_excel(writer, sheet_name='Representatives', index=False)        # Update cluster table

                

                # Export cluster summary        self._update_cluster_table()    def _create_visualization_panel(self) -> QWidget:

                cluster_summary = []

                for cluster_id, members in self.clusters.items():        

                    if len(members) == 1:

                        continue        # Update representative table        """Create right results panel"""

                        

                    cluster_df = self.clustered_df[self.clustered_df['cluster_id'] == cluster_id]        self._update_representative_table()

                    rep_row = cluster_df[cluster_df['is_representative'] == True]

                            panel = QWidget()

                    if not rep_row.empty:

                        rep_row = rep_row.iloc[0]        layout = QVBoxLayout(panel)

                        desc_col = None

                        for col in ['Description', 'Term', 'term']:        

                            if col in rep_row.index:

                                desc_col = col        # Tab Widget (Network / Summary / Clusters / Representatives)

                                break

                        rep_term = rep_row[desc_col] if desc_col else "N/A"        self.result_tabs = QTabWidget()

                    else:

                        rep_term = "N/A"        

                        

                    cluster_summary.append({        # Tab 1: Network Visualization (NEW - Primary view)

                        'Cluster ID': cluster_id,

                        'Size': len(members),        self.network_tab = self._create_network_tab()

                        'Representative': rep_term,

                        'Color': self.cluster_colors.get(cluster_id, '#999999')        self.result_tabs.addTab(self.network_tab, "Network")

                    })

                            

                summary_df = pd.DataFrame(cluster_summary)

                summary_df.to_excel(writer, sheet_name='Cluster Summary', index=False)        # Tab 2: Summary Statistics

                

            QMessageBox.information(        self.summary_tab = self._create_summary_tab()

                self,

                "Export Successful",        self.result_tabs.addTab(self.summary_tab, "? Summary")

                f"Clustering results exported to:\n{file_path}"

            )        

            

        except Exception as e:        # Tab 3: Cluster Details

            QMessageBox.critical(

                self,        self.cluster_tab = self._create_cluster_tab()

                "Export Error",

                f"Failed to export clustering results:\n\n{str(e)}"        self.result_tabs.addTab(self.cluster_tab, "Clusters")

            )

                    

    def get_clustered_dataframe(self):

        """        # Tab 4: Representative Terms

        Get the clustered DataFrame for creating a filtered dataset.

                self.repr_tab = self._create_representative_tab()

        Returns:

            DataFrame with clustering information or None        self.result_tabs.addTab(self.repr_tab, "?Representatives")

        """

        return self.clustered_df        


        layout.addWidget(self.result_tabs)

        

        return panel

    

    def _create_network_tab(self) -> QWidget:

        """Create network visualization tab"""

        widget = QWidget()

        layout = QVBoxLayout(widget)

        

        # Settings

        settings_panel = QWidget()

        settings_layout = QHBoxLayout(settings_panel)

        settings_layout.setContentsMargins(5, 5, 5, 5)

        

        # Top N labels ?

        settings_layout.addWidget(QLabel("Labels to show:"))

        self.top_n_spin = QSpinBox()

        self.top_n_spin.setRange(0, 50)

        self.top_n_spin.setValue(10)

        self.top_n_spin.setSuffix(" terms")

        self.top_n_spin.setToolTip("Number of top terms to label (by FDR)")

        settings_layout.addWidget(self.top_n_spin)

        

        settings_layout.addSpacing(20)

        

        # Node size ?

        settings_layout.addWidget(QLabel("Node size:"))

        self.node_size_spin = QSpinBox()

        self.node_size_spin.setRange(100, 2000)

        self.node_size_spin.setValue(1000)

        self.node_size_spin.setSingleStep(100)

        self.node_size_spin.setToolTip("Size of representative nodes")

        settings_layout.addWidget(self.node_size_spin)

        

        settings_layout.addSpacing(20)

        

        # Refresh button

        refresh_btn = QPushButton("? Refresh Plot")

        refresh_btn.setToolTip("Redraw network with current settings")

        refresh_btn.clicked.connect(self._update_network_graph)

        refresh_btn.setStyleSheet("""

            QPushButton {

                background-color: #17a2b8;

                color: white;

                font-weight: bold;

                padding: 5px 15px;

                border-radius: 3px;

            }

            QPushButton:hover {

                background-color: #138496;

            }

        """)

        settings_layout.addWidget(refresh_btn)

        

        settings_layout.addStretch()

        

        layout.addWidget(settings_panel)

        

        # Matplotlib Figure

        self.network_figure = Figure(figsize=(14, 10), facecolor='white')

        self.network_canvas = FigureCanvas(self.network_figure)

        

        # Navigation toolbar ? (zoom, pan, home 

        self.network_toolbar = NavigationToolbar(self.network_canvas, widget)

        layout.addWidget(self.network_toolbar)

        

        # Canvas ?

        layout.addWidget(self.network_canvas)

        

        # Initial message

        ax = self.network_figure.add_subplot(111)

        ax.text(0.5, 0.5, 'Click "Run Clustering" to generate network visualization',

                ha='center', va='center', fontsize=14, color='gray',

                transform=ax.transAxes)

        ax.axis('off')

        self.network_canvas.draw()

        

        # Mouse hover event ?

        self.network_canvas.mpl_connect('motion_notify_event', self._on_network_hover)

        

        # Hover ? ?

        self.hover_annotation = None

        self.node_positions = {}

        self.node_info_map = {}

        

        return widget

    

    def _create_summary_tab(self) -> QWidget:

        """Create summary tab"""

        widget = QWidget()

        layout = QVBoxLayout(widget)

        

        self.summary_label = QLabel(

            "<h3>? Clustering Summary</h3>"

            "<p>Click 'Run Clustering' to start analysis.</p>"

        )

        self.summary_label.setWordWrap(True)

        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.summary_label.setStyleSheet("padding: 20px; color: #666;")

        

        layout.addWidget(self.summary_label)

        layout.addStretch()

        

        return widget

    

    def _create_cluster_tab(self) -> QWidget:

        """Create cluster details tab - show all terms"""

        widget = QWidget()

        layout = QVBoxLayout(widget)

        

        # All clustered terms table (representative ?)

        self.cluster_table = QTableWidget()

        self.cluster_table.setColumnCount(5)

        self.cluster_table.setHorizontalHeaderLabels([

            "Cluster ID", "Term ID", "Description", "FDR", "Gene Count"

        ])

        header = self.cluster_table.horizontalHeader()

        if header:

            header.setStretchLastSection(True)

        

        # Sorting ?

        self.cluster_table.setSortingEnabled(True)

        

        layout.addWidget(self.cluster_table)

        

        return widget

    

    def _create_representative_tab(self) -> QWidget:

        """Create representative terms tab"""

        widget = QWidget()

        layout = QVBoxLayout(widget)

        

        # Representative terms table

        self.repr_table = QTableWidget()

        self.repr_table.setColumnCount(5)

        self.repr_table.setHorizontalHeaderLabels([

            "Term ID", "Description", "FDR", "Gene Count", "Cluster Size"

        ])

        header = self.repr_table.horizontalHeader()

        if header:

            header.setStretchLastSection(True)

        

        # Sorting ?

        self.repr_table.setSortingEnabled(True)

        

        layout.addWidget(self.repr_table)

        

        return widget

    

    def _create_buttons(self) -> QHBoxLayout:

        """Create bottom button layout"""

        button_layout = QHBoxLayout()

        

        # Export button

        self.export_btn = QPushButton("? Export Clusters")

        self.export_btn.setEnabled(False)

        self.export_btn.clicked.connect(self._export_clusters)

        button_layout.addWidget(self.export_btn)

        

        button_layout.addStretch()

        

        # Apply button (  ?)

        self.apply_btn = QPushButton("Apply (Create Filtered Dataset)")

        self.apply_btn.setEnabled(False)

        self.apply_btn.setStyleSheet("""

            QPushButton {

                background-color: #28a745;

                color: white;

                font-weight: bold;

                padding: 8px 20px;

            }

            QPushButton:hover {

                background-color: #218838;

            }

            QPushButton:disabled {

                background-color: #cccccc;

            }

        """)

        self.apply_btn.clicked.connect(self.accept)

        button_layout.addWidget(self.apply_btn)

        

        # Cancel button

        cancel_btn = QPushButton("Cancel")

        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(cancel_btn)

        

        return button_layout

    

    def _run_clustering(self):

        """Execute clustering"""

        if self.worker and self.worker.isRunning():

            QMessageBox.warning(self, "In Progress", "Clustering is already running...")

            return

        

        if self.dataset.dataframe is None:

            QMessageBox.warning(self, "No Data", "No dataset available for clustering.")

            return

        

        # UI ?

        self.preview_btn.setEnabled(False)

        self.progress_bar.setVisible(True)

        self.status_label.setText("Starting clustering...")

        

        # Worker thread ?

        threshold = self.similarity_spin.value()

        self.worker = ClusteringWorker(self.dataset.dataframe.copy(), threshold)

        self.worker.finished.connect(self._on_clustering_finished)

        self.worker.progress.connect(self._on_progress_update)

        self.worker.error.connect(self._on_clustering_error)

        self.worker.start()

    

    def _on_progress_update(self, message: str):

        """Progress update"""

        self.status_label.setText(message)

    

    def _on_clustering_finished(self, clustered_df: pd.DataFrame, clusters: Dict):

        """Clustering finished callback"""

        self.clustered_df = clustered_df

        self.clusters = clusters

        

        # UI ??

        self._update_results()

        

        # UI ?

        self.preview_btn.setEnabled(True)

        self.progress_bar.setVisible(False)

        self.apply_btn.setEnabled(True)

        self.export_btn.setEnabled(True)

        

        n_clusters = len(clusters)

        n_repr = len(clustered_df[clustered_df['is_representative'] == True]) if 'is_representative' in clustered_df.columns else 0

        

        self.status_label.setText(

            f"Clustering complete! {n_clusters} clusters, {n_repr} representative terms"

        )

        self.status_label.setStyleSheet("color: #28a745; font-weight: bold; padding: 5px;")

    

    def _on_clustering_error(self, error_msg: str):

        """Clustering error callback"""

        self.preview_btn.setEnabled(True)

        self.progress_bar.setVisible(False)

        

        self.status_label.setText(f"Error: {error_msg}")

        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold; padding: 5px;")

        

        QMessageBox.critical(self, "Clustering Error", f"Failed to perform clustering:\n{error_msg}")

    

    def _update_results(self):

        """Update results UI"""

        if self.clustered_df is None or self.clusters is None:

            return

        

        # Network ?? (?)

        self._update_network_graph()

        

        # Summary ??

        self._update_summary()

        

        # Cluster table ??

        self._update_cluster_table()

        

        # Representative table ??

        self._update_representative_table()

    

    def _update_network_graph(self):

        """Update network graph (ClueGO style)"""

        if self.clustered_df is None or self.clusters is None:

            return

        

        # Figure 

        self.network_figure.clear()

        ax = self.network_figure.add_subplot(111)

        

        min_cluster_size = self.min_cluster_size_spin.value()

        

        # NetworkX ?

        G = nx.Graph()

        

        # Settings

        from matplotlib import colors as mcolors

        cluster_colors = {}

        color_palette = [

            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',

            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52BE80',

            '#EC7063', '#5DADE2', '#F39C12', '#48C9B0', '#AF7AC5',

            '#3498DB', '#E74C3C', '#1ABC9C', '#9B59B6', '#F1C40F'

        ]

        

        # Settings

        cluster_info = {}

        singleton_nodes = []

        

        for cluster_id, indices in self.clusters.items():

            cluster_size = len(indices)

            cluster_df = self.clustered_df.iloc[indices]

            

            # Representative term 

            repr_row = cluster_df[cluster_df['is_representative'] == True]

            if len(repr_row) > 0:

                repr_idx = repr_row.index[0]

            else:

                # Fallback: ? FDR

                if StandardColumns.FDR in cluster_df.columns:

                    repr_idx = cluster_df[StandardColumns.FDR].idxmin()

                else:

                    repr_idx = cluster_df.index[0]

            

            # Settings

            terms = []

            for idx in indices:

                row = self.clustered_df.iloc[idx]

                term_id = row.get(StandardColumns.TERM_ID, f"Term_{idx}")

                description = row.get(StandardColumns.DESCRIPTION, "")

                fdr = row.get(StandardColumns.FDR, 1.0)

                genes_str = row.get(StandardColumns.GENE_SYMBOLS, "")

                

                genes = set()

                if pd.notna(genes_str):

                    genes = set(str(genes_str).split('/'))

                

                terms.append({

                    'term_id': term_id,

                    'description': description,

                    'fdr': fdr,

                    'genes': genes,

                    'is_representative': (idx == repr_idx)

                })

            

            if cluster_size == 1:

                # Singleton

                singleton_nodes.append({

                    'cluster_id': cluster_id,

                    'terms': terms,

                    'size': 1

                })

            elif cluster_size >= min_cluster_size:

                # Large cluster

                cluster_info[cluster_id] = {

                    'terms': terms,

                    'size': cluster_size,

                    'color': color_palette[len(cluster_info) % len(color_palette)]

                }

                cluster_colors[cluster_id] = cluster_info[cluster_id]['color']

        

        # ? ? ? (large clusters only)

        node_to_cluster = {}

        for cluster_id, info in cluster_info.items():

            for term in info['terms']:

                term_id = term['term_id']

                G.add_node(term_id, 

                          description=term['description'],

                          fdr=term['fdr'],

                          genes=term['genes'],

                          cluster_id=cluster_id,

                          is_representative=term['is_representative'])

                node_to_cluster[term_id] = cluster_id

        

        # ?  ? (? ?? )

        nodes_list = list(G.nodes())

        for i, node1 in enumerate(nodes_list):

            for node2 in nodes_list[i+1:]:

                cluster1 = G.nodes[node1]['cluster_id']

                cluster2 = G.nodes[node2]['cluster_id']

                

                # ? ??  (inter-cluster edges ?)

                if cluster1 != cluster2:

                    continue

                

                genes1 = G.nodes[node1]['genes']

                genes2 = G.nodes[node2]['genes']

                

                if len(genes1) > 0 and len(genes2) > 0:

                    intersection = len(genes1 & genes2)

                    union = len(genes1 | genes2)

                    jaccard = intersection / union if union > 0 else 0

                    

                    # Settings

                    threshold = self.similarity_spin.value() * 0.3

                    

                    if jaccard >= threshold:

                        G.add_edge(node1, node2, weight=jaccard)

        

        # Settings

        pos = {}

        if len(cluster_info) > 0:

            n_clusters = len(cluster_info)

            

            # Grid ??  ( )

            grid_cols = int(np.ceil(np.sqrt(n_clusters)))

            grid_rows = int(np.ceil(n_clusters / grid_cols))

            

            cluster_spacing = 5.0  # Settings

            

            for idx, (cluster_id, info) in enumerate(cluster_info.items()):

                cluster_nodes = [n for n in G.nodes() if G.nodes[n]['cluster_id'] == cluster_id]

                

                if not cluster_nodes:

                    continue

                

                # ???spring layout

                cluster_G = G.subgraph(cluster_nodes).copy()

                if len(cluster_G.edges()) > 0:

                    cluster_pos = nx.spring_layout(cluster_G, k=0.5, iterations=100, seed=42)

                else:

                    # Settings

                    cluster_pos = {}

                    for i, node in enumerate(cluster_nodes):

                        angle = 2 * np.pi * i / len(cluster_nodes)

                        cluster_pos[node] = (0.3 * np.cos(angle), 0.3 * np.sin(angle))

                

                # Grid ? 

                grid_row = idx // grid_cols

                grid_col = idx % grid_cols

                center_x = grid_col * cluster_spacing

                center_y = -grid_row * cluster_spacing  # Settings

                

                # Settings

                for node in cluster_nodes:

                    local_x, local_y = cluster_pos[node]

                    pos[node] = (center_x + local_x * 0.8, center_y + local_y * 0.8)

        

        # Singleton ? ? (? ??

        singleton_pos = {}

        if len(singleton_nodes) > 0 and pos:

            x_offset = max([p[0] for p in pos.values()]) + 1.0 if pos else 1.5

            y_max = max([p[1] for p in pos.values()]) if pos else 1.0

            y_min = min([p[1] for p in pos.values()]) if pos else -1.0

            y_range = y_max - y_min

            y_spacing = y_range / max(len(singleton_nodes) - 1, 1)

            

            for i, node_info in enumerate(singleton_nodes):

                term = node_info['terms'][0]

                term_id = term['term_id']

                y_pos = y_max - i * y_spacing

                singleton_pos[term_id] = (x_offset, y_pos)

        

        # Node ? ?(hover -  ?

        self.node_positions = {**pos, **singleton_pos}

        self.node_info_map = {}  # 

        

        # ?

        if len(G.nodes()) > 0:

            # Settings

            top_n_labels = self.top_n_spin.value() if hasattr(self, 'top_n_spin') else 10

            representative_node_size = self.node_size_spin.value() if hasattr(self, 'node_size_spin') else 1000

            member_node_size = int(representative_node_size * 0.4)  # 40% ?

            

            # FDR? ? N

            node_fdr_list = [(node, G.nodes[node]['fdr'], G.nodes[node]['is_representative']) 

                           for node in G.nodes()]

            # Representative ?,  FDR

            node_fdr_list.sort(key=lambda x: (not x[2], x[1]))

            top_nodes = [item[0] for item in node_fdr_list[:top_n_labels]]

            

            # Settings

            for cluster_id, info in cluster_info.items():

                cluster_nodes = [n for n in G.nodes() if G.nodes[n]['cluster_id'] == cluster_id]

                cluster_pos = {n: pos[n] for n in cluster_nodes if n in pos}

                

                if len(cluster_nodes) == 0:

                    continue

                

                # Settings

                node_sizes = []

                for node in cluster_nodes:

                    if G.nodes[node]['is_representative']:

                        node_sizes.append(representative_node_size)

                    else:

                        node_sizes.append(member_node_size)

                    

                    # Node ? ?(hover

                    self.node_info_map[node] = {

                        'description': G.nodes[node]['description'],

                        'fdr': G.nodes[node]['fdr'],

                        'cluster_id': cluster_id,

                        'is_representative': G.nodes[node]['is_representative']

                    }

                

                # Settings

                nx.draw_networkx_nodes(G, cluster_pos, nodelist=cluster_nodes,

                                      node_size=node_sizes, 

                                      node_color=[info['color']] * len(cluster_nodes),

                                      alpha=0.85, ax=ax, edgecolors='white', linewidths=2.5)

            

            # Settings

            if len(G.edges()) > 0:

                nx.draw_networkx_edges(G, pos, alpha=0.5, width=2.5, 

                                      ax=ax, edge_color='gray')

            

            # Settings

            labels = {}

            for node in top_nodes:

                if node in pos:

                    desc = G.nodes[node]['description']

                    if len(desc) > 35:

                        desc = desc[:32] + '...'

                    labels[node] = desc

            

            if labels:

                nx.draw_networkx_labels(G, pos, labels, font_size=9, 

                                       font_weight='bold', ax=ax,

                                       bbox=dict(boxstyle='round,pad=0.4', 

                                               facecolor='white', alpha=0.8, edgecolor='gray'))

        

        # Singleton ? ?(?)

        if singleton_nodes:

            for node_info in singleton_nodes:

                term = node_info['terms'][0]

                term_id = term['term_id']

                if term_id in singleton_pos:

                    x, y = singleton_pos[term_id]

                    ax.scatter(x, y, s=250, c='lightgray', alpha=0.6, 

                              edgecolors='gray', linewidths=1.5, zorder=2)

                    

                    # Singleton ? ?

                    self.node_info_map[term_id] = {

                        'description': term['description'],

                        'fdr': term['fdr'],

                        'cluster_id': node_info['cluster_id'],

                        'is_representative': True

                    }

            

            # Singleton ? (?, italic)

            for node_info in singleton_nodes:

                term = node_info['terms'][0]

                term_id = term['term_id']

                if term_id in singleton_pos:

                    x, y = singleton_pos[term_id]

                    desc = term['description']

                    if len(desc) > 25:

                        desc = desc[:22] + '...'

                    ax.text(x + 0.08, y, desc, fontsize=7, va='center', ha='left',

                           color='gray', style='italic')

        

        # Settings

        for cluster_id, info in cluster_info.items():

            cluster_nodes = [n for n in G.nodes() if G.nodes[n]['cluster_id'] == cluster_id]

            if len(cluster_nodes) >= 3:  #  3 ?

                points = np.array([pos[n] for n in cluster_nodes])

                try:

                    from scipy.spatial import ConvexHull

                    hull = ConvexHull(points)

                    # Hull  ?

                    for simplex in hull.simplices:

                        ax.plot(points[simplex, 0], points[simplex, 1], 

                               color=info['color'], alpha=0.15, linewidth=1.5)

                    # Hull  ?( ??)

                    hull_points = points[hull.vertices]

                    ax.fill(hull_points[:, 0], hull_points[:, 1], 

                           color=info['color'], alpha=0.05)

                except:

                    pass  # ConvexHull ?

        

        ax.set_title(f"GO Term Clustering Network - ClueGO Style (Min Cluster Size: {min_cluster_size})", 

                    fontsize=13, fontweight='bold', pad=20)

        

        # Plot boundary ? ? (representative term? ??

        if pos:

            x_values = [p[0] for p in pos.values()]

            y_values = [p[1] for p in pos.values()]

            x_margin = (max(x_values) - min(x_values)) * 0.15  # 15% ?

            y_margin = (max(y_values) - min(y_values)) * 0.15

            ax.set_xlim(min(x_values) - x_margin, max(x_values) + x_margin)

            ax.set_ylim(min(y_values) - y_margin, max(y_values) + y_margin)

        

        ax.axis('off')

        

        # Legend (??) - ??? ?

        legend_elements = []

        for cluster_id, info in cluster_info.items():

            # Representative termdescription ?

            repr_term = [t for t in info['terms'] if t['is_representative']]

            if repr_term:

                label = repr_term[0]['description']

                if len(label) > 40:

                    label = label[:37] + '...'

                label = f"C{cluster_id}: {label} (n={info['size']})"

            else:

                label = f"C{cluster_id} (n={info['size']})"

            

            from matplotlib.patches import Patch

            legend_elements.append(Patch(facecolor=info['color'], alpha=0.8, label=label))

        

        if legend_elements:

            # Legend?plot ? ??

            # bbox_to_anchor=(1.05, 1): ? 

            # loc='upper left': legend? ?anchor ??

            ax.legend(handles=legend_elements, 

                     loc='upper left',

                     bbox_to_anchor=(1.02, 1.0),

                     fontsize=8, 

                     framealpha=0.95, 

                     title='Clusters', 

                     title_fontsize=9,

                     borderaxespad=0)

            

            # Figure??? legend ? ??

            self.network_figure.tight_layout(rect=(0, 0, 0.85, 1))  # Settings

        

        # Hover annotation ( ? ?)

        self.hover_annotation = ax.annotate("", xy=(0,0), xytext=(15,15),

                                           textcoords="offset points",

                                           bbox=dict(boxstyle="round,pad=0.5", 

                                                   facecolor="yellow", alpha=0.9, edgecolor='black'),

                                           fontsize=9, visible=False, zorder=1000)

        

        self.network_figure.tight_layout()

        self.network_canvas.draw()

    

    def _on_network_hover(self, event):

        """Handle network graph hover event"""

        if event.inaxes is None or not hasattr(self, 'node_positions') or not self.node_positions:

            if hasattr(self, 'hover_annotation') and self.hover_annotation:

                self.hover_annotation.set_visible(False)

                self.network_canvas.draw_idle()

            return

        

        # ?

        mouse_x, mouse_y = event.xdata, event.ydata

        if mouse_x is None or mouse_y is None:

            if hasattr(self, 'hover_annotation') and self.hover_annotation:

                self.hover_annotation.set_visible(False)

                self.network_canvas.draw_idle()

            return

        

        #  ? 

        min_dist = float('inf')

        closest_node = None

        hover_threshold = 0.3  # Settings

        

        for node, (x, y) in self.node_positions.items():

            dist = np.sqrt((x - mouse_x)**2 + (y - mouse_y)**2)

            if dist < min_dist and dist < hover_threshold:

                min_dist = dist

                closest_node = node

        

        # Settings

        if closest_node and hasattr(self, 'node_info_map') and closest_node in self.node_info_map:

            if hasattr(self, 'hover_annotation') and self.hover_annotation:

                info = self.node_info_map[closest_node]

                desc = info['description']

                fdr = info['fdr']

                cluster_id = info['cluster_id']

                is_repr = info['is_representative']

                

                hover_text = f"{desc}\n"

                hover_text += f"FDR: {fdr:.2e}\n"

                hover_text += f"Cluster: {cluster_id}\n"

                hover_text += f"{'Representative' if is_repr else 'Member term'}"

                

                x, y = self.node_positions[closest_node]

                self.hover_annotation.xy = (x, y)

                self.hover_annotation.set_text(hover_text)

                self.hover_annotation.set_visible(True)

                self.network_canvas.draw_idle()

        elif hasattr(self, 'hover_annotation') and self.hover_annotation:

            self.hover_annotation.set_visible(False)

            self.network_canvas.draw_idle()

    

    

    def _update_summary(self):

        """Update summary information"""

        if self.dataset.dataframe is None or self.clustered_df is None or self.clusters is None:

            return

        

        min_cluster_size = self.min_cluster_size_spin.value()

        

        n_original = len(self.dataset.dataframe)

        

        # Min cluster size ????

        large_clusters = {cid: indices for cid, indices in self.clusters.items() 

                         if len(indices) >= min_cluster_size}

        singleton_clusters = {cid: indices for cid, indices in self.clusters.items() 

                            if len(indices) == 1}

        

        n_clusters_total = len(self.clusters)

        n_clusters_large = len(large_clusters)

        n_clusters_singleton = len(singleton_clusters)

        

        n_repr = len(self.clustered_df[self.clustered_df['is_representative'] == True])

        

        # Cluster size ? (large clusters?

        if large_clusters:

            cluster_sizes = [len(indices) for indices in large_clusters.values()]

            avg_size = sum(cluster_sizes) / len(cluster_sizes)

            max_size = max(cluster_sizes)

            min_size_val = min(cluster_sizes)

        else:

            avg_size = 0

            max_size = 0

            min_size_val = 0

        

        # Redundancy reduction

        reduction_pct = (1 - n_repr / n_original) * 100 if n_original > 0 else 0

        

        summary_html = f"""

        <h3>? Clustering Summary</h3>

        <table style='width:100%; border-collapse: collapse;'>

            <tr style='background: #f0f0f0;'>

                <td style='padding: 8px; font-weight: bold;'>Original Terms:</td>

                <td style='padding: 8px;'>{n_original:,}</td>

            </tr>

            <tr>

                <td style='padding: 8px; font-weight: bold;'>Total Clusters:</td>

                <td style='padding: 8px;'>{n_clusters_total:,}</td>

            </tr>

            <tr style='background: #f0f0f0;'>

                <td style='padding: 8px; font-weight: bold;'>Large Clusters ({min_cluster_size}):</td>

                <td style='padding: 8px;'><b style='color: #0066cc;'>{n_clusters_large:,}</b></td>

            </tr>

            <tr>

                <td style='padding: 8px; font-weight: bold;'>Singleton Clusters:</td>

                <td style='padding: 8px;'><b style='color: #999;'>{n_clusters_singleton:,}</b></td>

            </tr>

            <tr style='background: #f0f0f0;'>

                <td style='padding: 8px; font-weight: bold;'>Representative Terms:</td>

                <td style='padding: 8px;'><b style='color: #28a745;'>{n_repr:,}</b></td>

            </tr>

            <tr>

                <td style='padding: 8px; font-weight: bold;'>Redundancy Reduction:</td>

                <td style='padding: 8px;'><b style='color: #dc3545;'>{reduction_pct:.1f}%</b></td>

            </tr>

            <tr style='background: #f0f0f0;'>

                <td style='padding: 8px;'>Large Cluster Size (Avg):</td>

                <td style='padding: 8px;'>{avg_size:.1f} terms</td>

            </tr>

            <tr>

                <td style='padding: 8px;'>Large Cluster Size (Range):</td>

                <td style='padding: 8px;'>{min_size_val} - {max_size} terms</td>

            </tr>

        </table>

        <br>

        <p style='background: #ffffcc; padding: 10px; border-radius: 5px;'>

            <b>? Tip:</b> The representative terms show the most significant GO term from each cluster,

            effectively reducing redundancy while preserving biological insight.

            <br><b>Min Cluster Size:</b> Clusters with fewer than {min_cluster_size} terms are shown separately as singletons.

        </p>

        """

        

        self.summary_label.setText(summary_html)

        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    

    def _update_cluster_table(self):

        """Update cluster table - show all terms with alternating backgrounds per cluster"""

        if self.clustered_df is None:

            return

        

        # Representative ?  term

        all_terms_df = self.clustered_df.copy()

        

        # Cluster ID

        if 'cluster_id' in all_terms_df.columns:

            all_terms_df = all_terms_df.sort_values(['cluster_id', StandardColumns.FDR])

        

        # Sorting ? (?? ?

        self.cluster_table.setSortingEnabled(False)

        self.cluster_table.setRowCount(len(all_terms_df))

        

        # ? (cluster??)

        from PyQt6.QtGui import QColor, QBrush, QFont

        color_white = QColor(255, 255, 255)  # White

        color_gray = QColor(245, 245, 245)   # Light gray

        

        prev_cluster_id = None

        current_color = color_white

        

        for row_idx, (_, row) in enumerate(all_terms_df.iterrows()):

            # Cluster ID (?)

            cluster_id = int(row.get('cluster_id', -1))

            

            # Settings

            if prev_cluster_id is not None and cluster_id != prev_cluster_id:

                current_color = color_gray if current_color == color_white else color_white

            prev_cluster_id = cluster_id

            

            # Cluster ID

            item = NumericTableWidgetItem(cluster_id, str(cluster_id))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setBackground(QBrush(current_color))

            self.cluster_table.setItem(row_idx, 0, item)

            

            # Term ID (?

            term_id = row.get(StandardColumns.TERM_ID, 'N/A')

            item = QTableWidgetItem(str(term_id))

            item.setBackground(QBrush(current_color))

            self.cluster_table.setItem(row_idx, 1, item)

            

            # Description (?

            desc = row.get(StandardColumns.DESCRIPTION, 'N/A')

            item = QTableWidgetItem(str(desc))

            # Representative term?  ?

            if row.get('is_representative', False):

                font = QFont()

                font.setBold(True)

                item.setFont(font)

            item.setBackground(QBrush(current_color))

            self.cluster_table.setItem(row_idx, 2, item)

            

            # FDR (?, scientific notation)

            if StandardColumns.FDR in row and pd.notna(row[StandardColumns.FDR]):

                fdr_value = float(row[StandardColumns.FDR])

                fdr_display = f"{fdr_value:.2e}"

                item = NumericTableWidgetItem(fdr_value, fdr_display)

            else:

                item = QTableWidgetItem("N/A")

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setBackground(QBrush(current_color))

            self.cluster_table.setItem(row_idx, 3, item)

            

            # Gene Count (?)

            if StandardColumns.GENE_COUNT in row and pd.notna(row[StandardColumns.GENE_COUNT]):

                gene_count = int(row[StandardColumns.GENE_COUNT])

                item = NumericTableWidgetItem(gene_count, str(gene_count))

            else:

                item = QTableWidgetItem("N/A")

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item.setBackground(QBrush(current_color))

            self.cluster_table.setItem(row_idx, 4, item)

        

        # Sorting ?

        self.cluster_table.setSortingEnabled(True)

        self.cluster_table.resizeColumnsToContents()

    

    def _update_representative_table(self):

        """Update representative terms table"""

        if self.clustered_df is None or self.clusters is None:

            return

        

        # Type assertion for type checker

        assert self.clustered_df is not None

        assert self.clusters is not None

        

        repr_df = self.clustered_df[self.clustered_df['is_representative'] == True].copy()

        

        # FDR

        if StandardColumns.FDR in repr_df.columns:

            repr_df = repr_df.sort_values(StandardColumns.FDR)

        

        # Sorting ? (?? ?

        self.repr_table.setSortingEnabled(False)

        self.repr_table.setRowCount(len(repr_df))

        

        for row_idx, (_, row) in enumerate(repr_df.iterrows()):

            # Term ID (?

            term_id = row.get(StandardColumns.TERM_ID, 'N/A')

            item = QTableWidgetItem(str(term_id))

            self.repr_table.setItem(row_idx, 0, item)

            

            # Description (?

            desc = row.get(StandardColumns.DESCRIPTION, 'N/A')

            item = QTableWidgetItem(str(desc))

            self.repr_table.setItem(row_idx, 1, item)

            

            # FDR (?, scientific notation)

            if StandardColumns.FDR in row and pd.notna(row[StandardColumns.FDR]):

                fdr_value = float(row[StandardColumns.FDR])

                fdr_display = f"{fdr_value:.2e}"

                item = NumericTableWidgetItem(fdr_value, fdr_display)

            else:

                item = QTableWidgetItem("N/A")

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.repr_table.setItem(row_idx, 2, item)

            

            # Gene Count (?)

            if StandardColumns.GENE_COUNT in row and pd.notna(row[StandardColumns.GENE_COUNT]):

                gene_count = int(row[StandardColumns.GENE_COUNT])

                item = NumericTableWidgetItem(gene_count, str(gene_count))

            else:

                item = QTableWidgetItem("N/A")

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.repr_table.setItem(row_idx, 3, item)

            

            # Cluster Size (?)

            cluster_id = row.get('cluster_id', -1)

            cluster_size = 1

            if self.clusters is not None and cluster_id in self.clusters:

                cluster_indices = self.clusters[cluster_id]

                cluster_size = len(cluster_indices) if cluster_indices else 1

            item = NumericTableWidgetItem(cluster_size, str(cluster_size))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.repr_table.setItem(row_idx, 4, item)

        

        # Sorting ?

        self.repr_table.setSortingEnabled(True)

        self.repr_table.resizeColumnsToContents()

    

    def _export_clusters(self):

        """Export cluster information to Excel"""

        if self.clustered_df is None:

            return

        

        from PyQt6.QtWidgets import QFileDialog

        

        file_path, _ = QFileDialog.getSaveFileName(

            self,

            "Export Cluster Results",

            "go_clusters.xlsx",

            "Excel Files (*.xlsx)"

        )

        

        if not file_path:

            return

        

        try:

            # Settings

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:

                # All clusters

                self.clustered_df.to_excel(writer, sheet_name='All Terms', index=False)

                

                # Representative terms only

                repr_df = self.clustered_df[self.clustered_df['is_representative'] == True]

                repr_df.to_excel(writer, sheet_name='Representatives', index=False)

                

                # Cluster statistics

                from utils.go_clustering import GOClustering

                clustering = GOClustering()

                stats_df = clustering.calculate_cluster_statistics(self.clustered_df)

                stats_df.to_excel(writer, sheet_name='Cluster Stats', index=False)

            

            QMessageBox.information(

                self,

                "Export Complete",

                f"Cluster results exported to:\n{file_path}"

            )

            

        except Exception as e:

            QMessageBox.critical(self, "Export Failed", f"Failed to export:\n{str(e)}")

    

    # === Public API ( ?) ===

    

    def get_similarity_threshold(self) -> float:

        """Return similarity threshold"""

        return self.similarity_spin.value()

    

    def use_representative_only(self) -> bool:

        """Return only representative terms"""

        return self.show_repr_check.isChecked()

    

    def get_max_terms(self) -> int:

        """?? term ""

        return self.max_terms_spin.value()

    

    def get_clustered_data(self) -> Optional[pd.DataFrame]:

        """Return clustered DataFrame"""

        if self.clustered_df is None:

            return None

        

        if self.use_representative_only():

            # Representative terms?

            repr_df = self.clustered_df[self.clustered_df['is_representative'] == True].copy()

            

            # FDR

            if StandardColumns.FDR in repr_df.columns:

                repr_df = repr_df.sort_values(StandardColumns.FDR)

            

            # Max terms ?

            max_terms = self.get_max_terms()

            if len(repr_df) > max_terms:

                repr_df = repr_df.head(max_terms)

            

            return repr_df

        else:

            # Settings

            return self.clustered_df.copy()

    

    # ===  API (deprecated, ?) ===

    

    def get_kappa_threshold(self) -> float:

        """Deprecated: Use get_similarity_threshold() instead"""

        return self.get_similarity_threshold()

    

    def get_total_genes(self) -> Optional[int]:

        """Deprecated: No longer used in Hierarchical Clustering"""

        return None


    
    def _update_network_graph(self):
        """Update network graph (ClueGO style)"""
        if self.clustered_df is None or self.clusters is None:
            return
        
        # Clear figure
        self.network_figure.clear()
        ax = self.network_figure.add_subplot(111)
        
        min_cluster_size = self.min_cluster_size_spin.value()
        
        # Create NetworkX graph
        G = nx.Graph()
        
        # Color palette (ClueGO style)
        color_palette = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52BE80',
            '#EC7063', '#5DADE2', '#F39C12', '#48C9B0', '#AF7AC5',
            '#3498DB', '#E74C3C', '#1ABC9C', '#9B59B6', '#F1C40F'
        ]
        
        # Prepare cluster data
        cluster_info = {}
        singleton_nodes = []
        
        for cluster_id, indices in self.clusters.items():
            cluster_size = len(indices)
            cluster_df = self.clustered_df.iloc[indices]
            
            # Find representative term
            repr_row = cluster_df[cluster_df['is_representative'] == True]
            if len(repr_row) > 0:
                repr_idx = repr_row.index[0]
            else:
                # Fallback: lowest FDR
                if StandardColumns.FDR in cluster_df.columns:
                    repr_idx = cluster_df[StandardColumns.FDR].idxmin()
                else:
                    repr_idx = cluster_df.index[0]
            
            # Collect all term info
            terms = []
            for idx in indices:
                row = self.clustered_df.iloc[idx]
                term_id = row.get(StandardColumns.TERM_ID, f"Term_{idx}")
                description = row.get(StandardColumns.DESCRIPTION, "")
                fdr = row.get(StandardColumns.FDR, 1.0)
                genes_str = row.get(StandardColumns.GENE_SYMBOLS, "")
                
                genes = set()
                if pd.notna(genes_str):
                    genes = set(str(genes_str).split('/'))
                
                terms.append({
                    'term_id': term_id,
                    'description': description,
                    'fdr': fdr,
                    'genes': genes,
                    'is_representative': (idx == repr_idx)
                })
            
            if cluster_size == 1:
                # Singleton
                singleton_nodes.append({
                    'cluster_id': cluster_id,
                    'terms': terms,
                    'size': 1
                })
            elif cluster_size >= min_cluster_size:
                # Large cluster
                cluster_info[cluster_id] = {
                    'terms': terms,
                    'size': cluster_size,
                    'color': color_palette[len(cluster_info) % len(color_palette)]
                }
        
        # Add nodes to graph
        for cluster_id, info in cluster_info.items():
            for term in info['terms']:
                term_id = term['term_id']
                G.add_node(term_id, 
                          description=term['description'],
                          fdr=term['fdr'],
                          genes=term['genes'],
                          cluster_id=cluster_id,
                          is_representative=term['is_representative'])
        
        # Add edges (within-cluster only)
        nodes_list = list(G.nodes())
        for i, node1 in enumerate(nodes_list):
            for node2 in nodes_list[i+1:]:
                cluster1 = G.nodes[node1]['cluster_id']
                cluster2 = G.nodes[node2]['cluster_id']
                
                # Only connect within same cluster
                if cluster1 != cluster2:
                    continue
                
                genes1 = G.nodes[node1]['genes']
                genes2 = G.nodes[node2]['genes']
                
                if len(genes1) > 0 and len(genes2) > 0:
                    intersection = len(genes1 & genes2)
                    union = len(genes1 | genes2)
                    jaccard = intersection / union if union > 0 else 0
                    
                    threshold = self.similarity_spin.value() * 0.3
                    
                    if jaccard >= threshold:
                        G.add_edge(node1, node2, weight=jaccard)
        
        # Layout calculation (grid-based cluster arrangement)
        pos = {}
        if len(cluster_info) > 0:
            n_clusters = len(cluster_info)
            
            # Grid layout
            grid_cols = int(np.ceil(np.sqrt(n_clusters)))
            cluster_spacing = 5.0
            
            for idx, (cluster_id, info) in enumerate(cluster_info.items()):
                cluster_nodes = [n for n in G.nodes() if G.nodes[n]['cluster_id'] == cluster_id]
                
                if not cluster_nodes:
                    continue
                
                # Spring layout per cluster
                cluster_G = G.subgraph(cluster_nodes).copy()
                if len(cluster_G.edges()) > 0:
                    cluster_pos = nx.spring_layout(cluster_G, k=0.5, iterations=100, seed=42)
                else:
                    # Circular layout if no edges
                    cluster_pos = {}
                    for i, node in enumerate(cluster_nodes):
                        angle = 2 * np.pi * i / len(cluster_nodes)
                        cluster_pos[node] = (0.3 * np.cos(angle), 0.3 * np.sin(angle))
                
                # Grid position
                grid_row = idx // grid_cols
                grid_col = idx % grid_cols
                center_x = grid_col * cluster_spacing
                center_y = -grid_row * cluster_spacing
                
                # Move cluster nodes to grid position
                for node in cluster_nodes:
                    local_x, local_y = cluster_pos[node]
                    pos[node] = (center_x + local_x * 0.8, center_y + local_y * 0.8)
        
        # Singleton positions (right side)
        singleton_pos = {}
        if len(singleton_nodes) > 0 and pos:
            x_offset = max([p[0] for p in pos.values()]) + 1.0 if pos else 1.5
            y_max = max([p[1] for p in pos.values()]) if pos else 1.0
            y_min = min([p[1] for p in pos.values()]) if pos else -1.0
            y_range = y_max - y_min
            y_spacing = y_range / max(len(singleton_nodes) - 1, 1) if len(singleton_nodes) > 1 else 0
            
            for i, node_info in enumerate(singleton_nodes):
                term = node_info['terms'][0]
                term_id = term['term_id']
                y_pos = y_max - i * y_spacing
                singleton_pos[term_id] = (x_offset, y_pos)
        
        # Store node info for hover (initialize first)
        self.node_positions = {**pos, **singleton_pos}
        self.node_info_map = {}
        
        # Draw graph
        if len(G.nodes()) > 0:
            # Get settings
            top_n_labels = self.top_n_spin.value() if hasattr(self, 'top_n_spin') else 10
            representative_node_size = self.node_size_spin.value() if hasattr(self, 'node_size_spin') else 1000
            member_node_size = int(representative_node_size * 0.4)
            
            # Sort nodes by FDR for labeling
            node_fdr_list = [(node, G.nodes[node]['fdr'], G.nodes[node]['is_representative']) 
                           for node in G.nodes()]
            node_fdr_list.sort(key=lambda x: (not x[2], x[1]))
            top_nodes = [item[0] for item in node_fdr_list[:top_n_labels]]
            
            # Draw nodes by cluster
            for cluster_id, info in cluster_info.items():
                cluster_nodes = [n for n in G.nodes() if G.nodes[n]['cluster_id'] == cluster_id]
                cluster_pos = {n: pos[n] for n in cluster_nodes if n in pos}
                
                if len(cluster_nodes) == 0:
                    continue
                
                # Node sizes
                node_sizes = []
                for node in cluster_nodes:
                    if G.nodes[node]['is_representative']:
                        node_sizes.append(representative_node_size)
                    else:
                        node_sizes.append(member_node_size)
                    
                    # Store node info for hover
                    self.node_info_map[node] = {
                        'description': G.nodes[node]['description'],
                        'fdr': G.nodes[node]['fdr'],
                        'cluster_id': cluster_id,
                        'is_representative': G.nodes[node]['is_representative']
                    }
                
                # Draw nodes
                nx.draw_networkx_nodes(G, cluster_pos, nodelist=cluster_nodes,
                                      node_size=node_sizes, 
                                      node_color=[info['color']] * len(cluster_nodes),
                                      alpha=0.85, ax=ax, edgecolors='white', linewidths=2.5)
            
            # Draw edges
            if len(G.edges()) > 0:
                nx.draw_networkx_edges(G, pos, alpha=0.5, width=2.5, 
                                      ax=ax, edge_color='gray')
            
            # Labels (top N only)
            labels = {}
            for node in top_nodes:
                if node in pos:
                    desc = G.nodes[node]['description']
                    if len(desc) > 35:
                        desc = desc[:32] + '...'
                    labels[node] = desc
            
            if labels:
                nx.draw_networkx_labels(G, pos, labels, font_size=9, 
                                       font_weight='bold', ax=ax,
                                       bbox=dict(boxstyle='round,pad=0.4', 
                                               facecolor='white', alpha=0.8, edgecolor='gray'))
        
        # Draw singletons
        if singleton_nodes:
            for node_info in singleton_nodes:
                term = node_info['terms'][0]
                term_id = term['term_id']
                if term_id in singleton_pos:
                    x, y = singleton_pos[term_id]
                    ax.scatter(x, y, s=250, c='lightgray', alpha=0.6, 
                              edgecolors='gray', linewidths=1.5, zorder=2)
                    
                    # Store singleton info for hover
                    self.node_info_map[term_id] = {
                        'description': term['description'],
                        'fdr': term['fdr'],
                        'cluster_id': node_info['cluster_id'],
                        'is_representative': True
                    }
            
            # Singleton labels
            for node_info in singleton_nodes:
                term = node_info['terms'][0]
                term_id = term['term_id']
                if term_id in singleton_pos:
                    x, y = singleton_pos[term_id]
                    desc = term['description']
                    if len(desc) > 25:
                        desc = desc[:22] + '...'
                    ax.text(x + 0.08, y, desc, fontsize=7, va='center', ha='left',
                           color='gray', style='italic')
        
        # Cluster areas (convex hull)
        for cluster_id, info in cluster_info.items():
            cluster_nodes = [n for n in G.nodes() if G.nodes[n]['cluster_id'] == cluster_id]
            if len(cluster_nodes) >= 3:
                points = np.array([pos[n] for n in cluster_nodes])
                try:
                    from scipy.spatial import ConvexHull
                    hull = ConvexHull(points)
                    for simplex in hull.simplices:
                        ax.plot(points[simplex, 0], points[simplex, 1], 
                               color=info['color'], alpha=0.15, linewidth=1.5)
                    hull_points = points[hull.vertices]
                    ax.fill(hull_points[:, 0], hull_points[:, 1], 
                           color=info['color'], alpha=0.05)
                except:
                    pass
        
        ax.set_title(f"GO Term Clustering Network - ClueGO Style (Min Cluster Size: {min_cluster_size})", 
                    fontsize=13, fontweight='bold', pad=20)
        
        # Add margin to prevent label clipping
        if pos:
            x_values = [p[0] for p in pos.values()]
            y_values = [p[1] for p in pos.values()]
            x_margin = (max(x_values) - min(x_values)) * 0.15
            y_margin = (max(y_values) - min(y_values)) * 0.15
            ax.set_xlim(min(x_values) - x_margin, max(x_values) + x_margin)
            ax.set_ylim(min(y_values) - y_margin, max(y_values) + y_margin)
        
        ax.axis('off')
        
        # Legend (right side)
        legend_elements = []
        for cluster_id, info in cluster_info.items():
            repr_term = [t for t in info['terms'] if t['is_representative']]
            if repr_term:
                label = repr_term[0]['description']
                if len(label) > 40:
                    label = label[:37] + '...'
                label = f"C{cluster_id}: {label} (n={info['size']})"
            else:
                label = f"C{cluster_id} (n={info['size']})"
            
            from matplotlib.patches import Patch
            legend_elements.append(Patch(facecolor=info['color'], alpha=0.8, label=label))
        
        if legend_elements:
            ax.legend(handles=legend_elements, 
                     loc='upper left',
                     bbox_to_anchor=(1.02, 1.0),
                     fontsize=8, 
                     framealpha=0.95, 
                     title='Clusters', 
                     title_fontsize=9,
                     borderaxespad=0)
            self.network_figure.tight_layout(rect=(0, 0, 0.85, 1))
        
        # Hover annotation
        self.hover_annotation = ax.annotate("", xy=(0,0), xytext=(15,15),
                                           textcoords="offset points",
                                           bbox=dict(boxstyle="round,pad=0.5", 
                                                   facecolor="yellow", alpha=0.9, edgecolor='black'),
                                           fontsize=9, visible=False, zorder=1000)
        
        self.network_figure.tight_layout()
        self.network_canvas.draw()
    
    def _on_network_hover(self, event):
        """Handle network graph hover event"""
        if event.inaxes is None or not hasattr(self, 'node_positions') or not self.node_positions:
            if hasattr(self, 'hover_annotation') and self.hover_annotation:
                self.hover_annotation.set_visible(False)
                self.network_canvas.draw_idle()
            return
        
        # Mouse position
        mouse_x, mouse_y = event.xdata, event.ydata
        if mouse_x is None or mouse_y is None:
            if hasattr(self, 'hover_annotation') and self.hover_annotation:
                self.hover_annotation.set_visible(False)
                self.network_canvas.draw_idle()
            return
        
        # Find closest node
        min_dist = float('inf')
        closest_node = None
        hover_threshold = 0.3
        
        for node, (x, y) in self.node_positions.items():
            dist = np.sqrt((x - mouse_x)**2 + (y - mouse_y)**2)
            if dist < min_dist and dist < hover_threshold:
                min_dist = dist
                closest_node = node
        
        # Show node info
        if closest_node and hasattr(self, 'node_info_map') and closest_node in self.node_info_map:
            if hasattr(self, 'hover_annotation') and self.hover_annotation:
                info = self.node_info_map[closest_node]
                desc = info['description']
                fdr = info['fdr']
                cluster_id = info['cluster_id']
                is_repr = info['is_representative']
                
                hover_text = f"{desc}\n"
                hover_text += f"FDR: {fdr:.2e}\n"
                hover_text += f"Cluster: {cluster_id}\n"
                hover_text += f"{'★ Representative' if is_repr else 'Member term'}"
                
                x, y = self.node_positions[closest_node]
                self.hover_annotation.xy = (x, y)
                self.hover_annotation.set_text(hover_text)
                self.hover_annotation.set_visible(True)
                self.network_canvas.draw_idle()
        elif hasattr(self, 'hover_annotation') and self.hover_annotation:
            self.hover_annotation.set_visible(False)
            self.network_canvas.draw_idle()
    
    def _update_summary(self):
        """Update summary information"""
        if self.clustered_df is None or self.clusters is None:
            return
        
        n_total = len(self.clustered_df)
        n_clusters = len(self.clusters)
        
        # Count representatives
        n_repr = len(self.clustered_df[self.clustered_df['is_representative'] == True])
        
        # Cluster sizes
        cluster_sizes = [len(indices) for indices in self.clusters.values()]
        avg_size = np.mean(cluster_sizes) if cluster_sizes else 0
        max_size = max(cluster_sizes) if cluster_sizes else 0
        min_size = min(cluster_sizes) if cluster_sizes else 0
        
        # Singletons
        n_singletons = sum(1 for size in cluster_sizes if size == 1)
        
        min_cluster_size = self.min_cluster_size_spin.value()
        large_clusters = sum(1 for size in cluster_sizes if size >= min_cluster_size)
        
        summary_html = f"""
        <h3>📊 Clustering Summary</h3>
        <table style='width: 100%; border-collapse: collapse;'>
            <tr style='background: #f0f0f0;'>
                <td style='padding: 8px; font-weight: bold;'>Total Terms:</td>
                <td style='padding: 8px;'>{n_total}</td>
            </tr>
            <tr>
                <td style='padding: 8px; font-weight: bold;'>Number of Clusters:</td>
                <td style='padding: 8px;'>{n_clusters}</td>
            </tr>
            <tr style='background: #f0f0f0;'>
                <td style='padding: 8px; font-weight: bold;'>Representative Terms:</td>
                <td style='padding: 8px;'>{n_repr}</td>
            </tr>
            <tr>
                <td style='padding: 8px; font-weight: bold;'>Large Clusters (≥{min_cluster_size}):</td>
                <td style='padding: 8px;'>{large_clusters}</td>
            </tr>
            <tr style='background: #f0f0f0;'>
                <td style='padding: 8px; font-weight: bold;'>Singleton Terms:</td>
                <td style='padding: 8px;'>{n_singletons}</td>
            </tr>
            <tr>
                <td style='padding: 8px; font-weight: bold;'>Average Cluster Size:</td>
                <td style='padding: 8px;'>{avg_size:.1f}</td>
            </tr>
            <tr style='background: #f0f0f0;'>
                <td style='padding: 8px; font-weight: bold;'>Largest Cluster:</td>
                <td style='padding: 8px;'>{max_size} terms</td>
            </tr>
            <tr>
                <td style='padding: 8px; font-weight: bold;'>Smallest Cluster:</td>
                <td style='padding: 8px;'>{min_size} terms</td>
            </tr>
        </table>
        """
        
        self.summary_label.setText(summary_html)
    
    def _update_cluster_table(self):
        """Update cluster table - show all terms with alternating backgrounds per cluster"""
        if self.clustered_df is None:
            return
        
        # Disable sorting while updating
        self.cluster_table.setSortingEnabled(False)
        
        # Filter by min cluster size
        min_size = self.min_cluster_size_spin.value()
        filtered_df = self.clustered_df.copy()
        
        # Count cluster sizes
        cluster_sizes = {}
        for cluster_id, indices in self.clusters.items():
            cluster_sizes[cluster_id] = len(indices)
        
        # Filter out small clusters
        filtered_df = filtered_df[filtered_df['cluster_id'].apply(
            lambda cid: cluster_sizes.get(cid, 0) >= min_size
        )]
        
        # Sort by cluster_id, then by is_representative (desc), then by FDR
        filtered_df = filtered_df.sort_values([
            'cluster_id',
            'is_representative',
            StandardColumns.FDR
        ], ascending=[True, False, True])
        
        self.cluster_table.setRowCount(len(filtered_df))
        
        # Alternating colors
        color_white = QColor(255, 255, 255)
        color_gray = QColor(245, 245, 245)
        
        prev_cluster_id = None
        current_color = color_white
        use_white = True
        
        for row_idx, (_, row) in enumerate(filtered_df.iterrows()):
            cluster_id = row.get('cluster_id', -1)
            term_id = row.get(StandardColumns.TERM_ID, "")
            description = row.get(StandardColumns.DESCRIPTION, "")
            fdr = row.get(StandardColumns.FDR, 1.0)
            genes_str = row.get(StandardColumns.GENE_SYMBOLS, "")
            gene_count = len(genes_str.split('/')) if pd.notna(genes_str) else 0
            is_repr = row.get('is_representative', False)
            
            # Change color when cluster changes
            if cluster_id != prev_cluster_id:
                use_white = not use_white
                current_color = color_white if use_white else color_gray
                prev_cluster_id = cluster_id
            
            # Cluster ID
            cluster_item = NumericTableWidgetItem(str(cluster_id))
            cluster_item.setBackground(QBrush(current_color))
            if is_repr:
                font = QFont()
                font.setBold(True)
                cluster_item.setFont(font)
            self.cluster_table.setItem(row_idx, 0, cluster_item)
            
            # Term ID
            term_item = QTableWidgetItem(term_id)
            term_item.setBackground(QBrush(current_color))
            if is_repr:
                font = QFont()
                font.setBold(True)
                term_item.setFont(font)
            self.cluster_table.setItem(row_idx, 1, term_item)
            
            # Description
            desc_item = QTableWidgetItem(description)
            desc_item.setBackground(QBrush(current_color))
            if is_repr:
                font = QFont()
                font.setBold(True)
                desc_item.setFont(font)
            self.cluster_table.setItem(row_idx, 2, desc_item)
            
            # FDR
            fdr_item = NumericTableWidgetItem(f"{fdr:.2e}")
            fdr_item.setData(Qt.ItemDataRole.UserRole, fdr)
            fdr_item.setBackground(QBrush(current_color))
            if is_repr:
                font = QFont()
                font.setBold(True)
                fdr_item.setFont(font)
            self.cluster_table.setItem(row_idx, 3, fdr_item)
            
            # Gene Count
            count_item = NumericTableWidgetItem(str(gene_count))
            count_item.setBackground(QBrush(current_color))
            if is_repr:
                font = QFont()
                font.setBold(True)
                count_item.setFont(font)
            self.cluster_table.setItem(row_idx, 4, count_item)
        
        # Re-enable sorting
        self.cluster_table.setSortingEnabled(True)
        self.cluster_table.resizeColumnsToContents()
    
    def _update_representative_table(self):
        """Update representative terms table"""
        if self.clustered_df is None:
            return
        
        # Get representatives only
        repr_df = self.clustered_df[self.clustered_df['is_representative'] == True].copy()
        
        # Filter by min cluster size
        min_size = self.min_cluster_size_spin.value()
        cluster_sizes = {}
        for cluster_id, indices in self.clusters.items():
            cluster_sizes[cluster_id] = len(indices)
        
        repr_df = repr_df[repr_df['cluster_id'].apply(
            lambda cid: cluster_sizes.get(cid, 0) >= min_size
        )]
        
        # Sort by FDR
        repr_df = repr_df.sort_values(StandardColumns.FDR)
        
        self.repr_table.setRowCount(len(repr_df))
        self.repr_table.setSortingEnabled(False)
        
        for row_idx, (_, row) in enumerate(repr_df.iterrows()):
            cluster_id = row.get('cluster_id', -1)
            term_id = row.get(StandardColumns.TERM_ID, "")
            description = row.get(StandardColumns.DESCRIPTION, "")
            fdr = row.get(StandardColumns.FDR, 1.0)
            genes_str = row.get(StandardColumns.GENE_SYMBOLS, "")
            gene_count = len(genes_str.split('/')) if pd.notna(genes_str) else 0
            cluster_size = cluster_sizes.get(cluster_id, 0)
            
            # Term ID
            self.repr_table.setItem(row_idx, 0, QTableWidgetItem(term_id))
            
            # Description
            self.repr_table.setItem(row_idx, 1, QTableWidgetItem(description))
            
            # FDR
            fdr_item = NumericTableWidgetItem(f"{fdr:.2e}")
            fdr_item.setData(Qt.ItemDataRole.UserRole, fdr)
            self.repr_table.setItem(row_idx, 2, fdr_item)
            
            # Gene Count
            self.repr_table.setItem(row_idx, 3, NumericTableWidgetItem(str(gene_count)))
            
            # Cluster Size
            self.repr_table.setItem(row_idx, 4, NumericTableWidgetItem(str(cluster_size)))
        
        self.repr_table.setSortingEnabled(True)
        self.repr_table.resizeColumnsToContents()
    
    def _export_clusters(self):
        """Export cluster information to Excel"""
        if self.clustered_df is None:
            return
        
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Clusters", "", "Excel Files (*.xlsx)"
        )
        
        if filename:
            try:
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    # Sheet 1: All clustered terms
                    self.clustered_df.to_excel(writer, sheet_name='All Terms', index=False)
                    
                    # Sheet 2: Representatives only
                    repr_df = self.clustered_df[self.clustered_df['is_representative'] == True]
                    repr_df.to_excel(writer, sheet_name='Representatives', index=False)
                
                QMessageBox.information(self, "Export Successful", 
                                       f"Clusters exported to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")
    
    def get_similarity_threshold(self) -> float:
        """Return similarity threshold"""
        return self.similarity_spin.value()
    
    def get_show_representatives_only(self) -> bool:
        """Return only representative terms flag"""
        return self.show_repr_check.isChecked()
    
    def get_max_terms(self) -> int:
        """Return max terms"""
        return self.max_terms_spin.value()
    
    def get_clustered_dataframe(self) -> Optional[pd.DataFrame]:
        """Return clustered DataFrame"""
        if self.clustered_df is None:
            return None
        
        # Apply filters
        filtered_df = self.clustered_df.copy()
        
        if self.get_show_representatives_only():
            # Only representatives
            filtered_df = filtered_df[filtered_df['is_representative'] == True]
        
        # Limit by max terms
        max_terms = self.get_max_terms()
        if len(filtered_df) > max_terms:
            # Sort by FDR and take top N
            filtered_df = filtered_df.sort_values(StandardColumns.FDR).head(max_terms)
        
        return filtered_df
