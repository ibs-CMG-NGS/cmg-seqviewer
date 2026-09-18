#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P0-5: 4-dialog offscreen smoke + clustering merge acceptance.
Read-only w.r.t. src/ (uses product classes only as consumers, per Phase 0 plan).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "src"))
HERE = os.path.dirname(os.path.abspath(__file__))
STD_CSV = os.path.join(HERE, "phase0_poc_standardized.csv")

import logging, warnings
for _lm in ("matplotlib", "matplotlib.font_manager", "matplotlib.mathtext"):
    logging.getLogger(_lm).setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message="Glyph .* missing")
warnings.filterwarnings("ignore", message="findfont: Font family")
warnings.filterwarnings("ignore", message="This plugin does not support propagateSizeHints")

import numpy as np
import pandas as pd

# ---- build the standardized DataFrame exactly as the loader contract expects ----
df = pd.read_csv(STD_CSV)
# rebuild real python-set _gene_set from the canonical '/'-joined gene_symbols column
# (mirrors src/utils/go_kegg_loader.py:_parse_gene_symbols, which splits on '/')
df["term"] = df["description"]  # Dataset GO_ANALYSIS contract alias (== term of P0-5 spec)
df["_gene_set"] = df["gene_symbols"].apply(
    lambda x: {g.strip() for g in str(x).split("/") if g.strip()} if pd.notna(x) else set()
)
print(f"[smoke] standardized df: {df.shape}, columns={list(df.columns)}")

# ---- compatibility double-check: converted df in loader INPUT vocab -> product standardizer ----
from utils.go_kegg_loader import GOKEGGLoader
loader = GOKEGGLoader()
inp = df.rename(columns={
    "term_id": "ID", "description": "Description", "gene_count": "Gene Count",
    "bg_count": "Background Count", "fdr": "Adjusted P-value", "pvalue": "P-value",
    "gene_ratio": "Gene Ratio", "bg_ratio": "Background Ratio",
    "gene_symbols": "Genes", "gene_set": "Gene Set",
}).copy()
inp["_description_check"] = inp["Description"]
std = loader._standardize_columns(inp)
std = loader._parse_gene_symbols(std)  # loader applies this before building the Dataset
print("[smoke] GOKEGGLoader(converted, input-vocab) _standardize_columns+_parse_gene_symbols OK ->", std.shape)
print("[smoke] std columns:", sorted(std.columns))
required = {"term_id", "description", "gene_symbols", "gene_count", "fdr", "pvalue",
            "gene_ratio", "bg_ratio", "fold_enrichment", "gene_set", "direction", "ontology", "_gene_set"}
missing = required - set(std.columns)
assert not missing, f"standardizer output missing: {missing}"
assert std["fdr"].notna().sum() > 0 and std["gene_count"].notna().sum() > 0
a = std["description"].fillna("").astype(str).tolist()
b = std["_description_check"].fillna("").astype(str).tolist()
assert a == b, "description round-trip mismatch"
ns = int(std["_gene_set"].map(len).gt(0).sum())
print(f"[smoke] loader round-trip: {len(std)} rows, {ns} non-empty _gene_set")

# ---- Dataset wrapper (GO_ANALYSIS requires term/gene_count/fdr) ----
from models.data_models import Dataset, DatasetType
dataset = Dataset(name="Phase0PoC", dataset_type=DatasetType.GO_ANALYSIS,
                  dataframe=std, metadata={"source": "phase0_poc"})
assert dataset.is_valid, "Dataset.is_valid failed"
print("[smoke] Dataset.is_valid =", dataset.is_valid)

# ---- offscreen Qt smoke ----
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEventLoop
app = QApplication.instance() or QApplication([])

dialogs = []
for name, cls in [
    ("GOBarChartDialog", None),
    ("GODotPlotDialog", None),
    ("GONetworkDialog", None),
    ("GOClusteringDialog", None),
]:
    try:
        if name == "GOBarChartDialog":
            from gui.go_bar_chart_dialog import GOBarChartDialog
            dlg = GOBarChartDialog(dataset)
        elif name == "GODotPlotDialog":
            from gui.go_dot_plot_dialog import GODotPlotDialog
            dlg = GODotPlotDialog(dataset)
        elif name == "GONetworkDialog":
            from gui.go_network_dialog import GONetworkDialog
            dlg = GONetworkDialog(dataset)
        else:
            from gui.go_clustering_dialog import GOClusteringDialog
            dlg = GOClusteringDialog(dataset)
        dlg.show()
        for _ in range(5):
            app.processEvents()
        dlg.close()
        dlg.deleteLater()
        print(f"[smoke] {name}: PASS (instantiate+show+processEvents+close, no exception)")
        dialogs.append(name)
    except Exception as e:
        import traceback
        print(f"[smoke] {name}: FAIL")
        traceback.print_exc()
        raise

assert len(dialogs) == 4, dialogs

# ---- clustering merge acceptance: >=1 pair with Jaccard > 0.3 ----
from utils.go_clustering import GOClustering
from scipy.cluster.hierarchy import fcluster

gene_sets = [s if isinstance(s, set) else set() for s in std["_gene_set"]]
valid_idx = [i for i, gs in enumerate(gene_sets) if len(gs) > 0]
# product-path clustering at threshold 0.3 (= assignment acceptance threshold)
cl = GOClustering(similarity_threshold=0.3).fit(std)
clustered_df, clusters = cl.cut(0.3)
merged = {cid: idxs for cid, idxs in clusters.items() if len(idxs) >= 2}
print(f"[clustering] GOClustering(0.3) -> {len(clusters)} clusters, {len(merged)} non-singleton")
assert len(merged) >= 1, "no cluster pair merged at 0.3"

# independent direct Jaccard max-pair computation over _gene_set
sets = [gene_sets[i] for i in valid_idx]
max_jac, pair = -1.0, None
for a in range(len(sets)):
    for b in range(a + 1, len(sets)):
        inter = len(sets[a] & sets[b])
        if inter == 0:
            continue
        jac = inter / len(sets[a] | sets[b])
        if jac > max_jac:
            max_jac, pair = jac, (valid_idx[a], valid_idx[b])
terms = std.loc[list(pair), ["term_id", "term", "gene_set"]]
print(f"[clustering] max Jaccard pair = {max_jac:.4f} -> rows {pair}")
print(terms.to_string(index=False))
merged_any_gt03 = any(
    len(sets[i] & sets[j]) / len(sets[i] | sets[j]) > 0.3
    for i, j in ((pair,) if False else [])
) or max_jac > 0.3
assert merged_any_gt03, "max Jaccard <= 0.3"
print(f"[clustering] acceptance (max Jaccard {max_jac:.4f} > 0.3): PASS")
print("[P0-5] ALL PASS")