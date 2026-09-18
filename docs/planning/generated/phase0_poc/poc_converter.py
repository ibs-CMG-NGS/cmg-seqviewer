#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P0-4: GO/KEGG enrichment converter contract asserts (standalone, no src/ imports).

Implements plan ON_GO_ENRICHMENT_IMPLEMENTATION_PLAN.md v1.1 sections 6.3-6.6:
  - labels '{direction}_{ontology}'                  (G5)
  - _gene_set from Genes strings via re.split(r'[;/,]') rejoin '/'  (G4/A5)
  - gene_ratio 'k/n', bg_ratio 'M/N'                 (G6)
  - fold_enrichment with 0-denominator protection    (mirror src/utils/go_kegg_loader.py:423-478)
  - term_id: GO -> first GO:\\d{7} in Term string; KEGG -> '' unless defensive ^hsa\\d+  (G7/A1/ADR-4)
  - description canonical: obo name > GMT name > Enrichr Term  (A4)

Asserts A-G run against enrichr GO, enrichr KEGG (where applicable) and GOATOOLS outputs.

Reads only small precomputed artifacts under this directory (survives deletion of
the heavyweight raw downloads).
"""
import json
import math
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- inputs ----------------
f_go = os.path.join(HERE, "enrichr_go_bp_2023.csv")
f_kg = os.path.join(HERE, "enrichr_kegg_2021_human.csv")
f_gt = os.path.join(HERE, "goatools_human_results.csv")
obo_names = json.load(open(os.path.join(HERE, "obo_names.json")))
gt_sizes = json.load(open(os.path.join(HERE, "goatools_term_sizes.json")))
gmt_go = json.load(open(os.path.join(HERE, "gmt_go_sizes.json")))
gmt_kg = json.load(open(os.path.join(HERE, "gmt_kegg_sizes.json")))
esym = json.load(open(os.path.join(HERE, "entrez2sym_human.json")))
DEG_N = len(json.load(open(os.path.join(HERE, "p0-3_genes.json"))))  # 100
GOATOOLS_N = len(esym)  # 63 mapped entrez

# ---------------- helpers (plan 6.4 / 6.5 / 6.6) ----------------
SPLIT_RE = re.compile(r"[;/,]")
GO_ID_RE = re.compile(r"\bGO:\d{7}\b")
HSA_RE = re.compile(r"^hsa\d+")


def normalize_genes(gene_str):
    """Multi-delimiter normalization: split [;/,], strip, drop empties. (A5)"""
    if pd.isna(gene_str) or gene_str == "" or str(gene_str).strip() == "":
        return set()
    return {g.strip().upper() for g in SPLIT_RE.split(str(gene_str)) if g.strip()}


def join_genes(gene_set):
    return "/".join(sorted(gene_set))


def parse_ratio(val):
    """'10/100' -> float (mirror _compute_fold_enrichment._parse_ratio)."""
    try:
        if pd.isna(val):
            return float("nan")
        if isinstance(val, (int, float)):
            return float(val)
        parts = str(val).split("/")
        if len(parts) == 2:
            num, den = float(parts[0]), float(parts[1])
            return num / den if den > 0 else float("nan")
    except Exception:
        pass
    return float("nan")


def fold_from_ratios(gr, br):
    """gene_ratio/bg_ratio with 0-denominator protection (loader mirror)."""
    grf, brf = parse_ratio(gr), parse_ratio(br)
    if math.isnan(brf) or brf == 0:
        return float("nan")
    return round(grf / brf, 4)


def extract_go_id(text):
    m = GO_ID_RE.search(str(text))
    return m.group(0) if m else ""


def canonical_description(go_id, gmt_name, enrichr_term):
    """obo name > GMT name > Enrichr Term. (A4)"""
    def _strip(text):
        return re.sub(r"\s*\(GO:\d{7}\)\s*$", "", str(text)).strip()
    if go_id and go_id in obo_names:
        return obo_names[go_id]
    if gmt_name and str(gmt_name).strip():
        return _strip(gmt_name)
    return _strip(enrichr_term)


def parse_label(label):
    """Mirror of src/utils/go_kegg_loader.py:_extract_direction_ontology.parse_gene_set."""
    s = str(label).strip().upper()
    ontology = "UNKNOWN"
    if "KEGG" in s:
        ontology = "KEGG"
    elif "_BP" in s or s.endswith("BP"):
        ontology = "BP"
    elif "_MF" in s or s.endswith("MF"):
        ontology = "MF"
    elif "_CC" in s or s.endswith("CC"):
        ontology = "CC"
    direction = "UNKNOWN"
    if "KEGG" in s:
        if "_UP" in s or s.endswith("UP"):
            direction = "UP"
        elif "_DOWN" in s or s.endswith("DOWN"):
            direction = "DOWN"
        elif "_TOTAL" in s or s.endswith("TOTAL"):
            direction = "TOTAL"
        else:
            direction = "TOTAL"
    elif s.startswith("UP"):
        direction = "UP"
    elif s.startswith("DOWN"):
        direction = "DOWN"
    elif s.startswith("TOTAL"):
        direction = "TOTAL"
    return direction, ontology


# ---------------- engine converters (plan 6.3-6.6) ----------------
def convert_enrichr_go(df):
    out = []
    uni = int(gmt_go["universe"])
    for _, r in df.iterrows():
        term = str(r["Term"])
        go_id = extract_go_id(term)
        genes = normalize_genes(r["Genes"])
        gr = str(r["Overlap"])
        k = int(str(r["Overlap"]).split("/")[0])
        M = int(gmt_go["sizes_by_go"].get(go_id, len(genes)))  # GMT size (fallback: overlap)
        out.append({
            "term_id": go_id, "term": canonical_description(go_id, term, term),
            "gene_count": k, "bg_count": M,
            "fdr": float(r["Adjusted P-value"]), "pvalue": float(r["P-value"]),
            "gene_ratio": gr, "bg_ratio": f"{M}/{uni}",
            "gene_symbols": join_genes(genes), "gene_set": "TOTAL_BP",
            "direction": "TOTAL", "ontology": "BP", "engine": "enrichr:GO_Biological_Process_2023",
        })
    return pd.DataFrame(out)


def convert_enrichr_kegg(df):
    out = []
    uni = int(gmt_kg["universe"])
    for _, r in df.iterrows():
        term = str(r["Term"])
        m = HSA_RE.match(term)
        term_id = m.group(0) if m else ""          # ADR-4 4A: online KEGG Term has no hsa id
        genes = normalize_genes(r["Genes"])
        gr = str(r["Overlap"])
        k = int(str(r["Overlap"]).split("/")[0])
        M = int(gmt_kg["sizes_by_name"].get(term, len(genes)))
        out.append({
            "term_id": term_id, "term": canonical_description("", term, term),
            "gene_count": k, "bg_count": M,
            "fdr": float(r["Adjusted P-value"]), "pvalue": float(r["P-value"]),
            "gene_ratio": gr, "bg_ratio": f"{M}/{uni}",
            "gene_symbols": join_genes(genes), "gene_set": "TOTAL_KEGG",
            "direction": "TOTAL", "ontology": "KEGG", "engine": "enrichr:KEGG_2021_Human",
        })
    return pd.DataFrame(out)


def convert_goatools(df):
    out = []
    for _, r in df.iterrows():
        go_id = str(r["GO"])
        ents = [int(x) for x in str(r["study_items"]).strip("[]").replace(" ", "").split(",") if x.strip()]
        syms = {esym.get(str(e)) for e in ents if esym.get(str(e))}
        syms = {s for s in syms if s}
        M = int(gt_sizes.get(go_id, r["pop_count"]))     # assoc (genome-wide) term size
        out.append({
            "term_id": go_id, "term": canonical_description(go_id, "", r["name"]),
            "gene_count": int(r["study_count"]), "bg_count": M,
            "fdr": float(r["p_fdr_bh"]), "pvalue": float(r["p_uncorrected"]),
            "gene_ratio": f"{int(r['study_count'])}/{int(r['study_n'])}",
            "bg_ratio": f"{M}/{GOATOOLS_N}",
            "gene_symbols": join_genes(syms), "gene_set": f"TOTAL_{r['NS']}",
            "direction": "TOTAL", "ontology": str(r["NS"]), "engine": "goatools:gene2go_9606",
        })
    return pd.DataFrame(out)


# ---------------- run converters ----------------
go_df = pd.read_csv(f_go)
kg_df = pd.read_csv(f_kg)
gt_df = pd.read_csv(f_gt)

c_go = convert_enrichr_go(go_df)
c_kg = convert_enrichr_kegg(kg_df)
c_gt = convert_goatools(gt_df)

merged = pd.concat([c_go, c_kg, c_gt], ignore_index=True)

# fold_enrichment (computed last, after ratios; loader computes from gene_ratio/bg_ratio)
merged["fold_enrichment"] = [
    fold_from_ratios(gr, br) for gr, br in zip(merged["gene_ratio"], merged["bg_ratio"])
]
merged["_gene_set"] = merged["gene_symbols"].apply(lambda s: normalize_genes(s))

merged["description"] = merged["term"]  # StandardColumns.DESCRIPTION label (term = Dataset GO_ANALYSIS contract)
merged.drop(columns=["_br_num", "_pdir", "_pont"], errors="ignore").to_csv(
    os.path.join(HERE, "phase0_poc_standardized.csv"), index=False)
print(f"[converter] merged standardized rows: {len(merged)} "
      f"(enrichr_GO={len(c_go)}, enrichr_KEGG={len(c_kg)}, goatools={len(c_gt)})")

# ---------------- asserts (A-G) ----------------
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(f"  {name}: {'PASS' if cond else 'FAIL'}" + (f"  ({detail})" if detail else ""))


# (A) _gene_set
nz_go = int((merged["engine"].str.contains("enrichr:GO") & (merged["_gene_set"].map(len) > 0)).sum())
nz_gt = int((merged["engine"].str.contains("goatools") & (merged["_gene_set"].map(len) > 0)).sum())
check("A1 _gene_set non-empty (enrichr GO)", nz_go >= 1, f"{nz_go} rows non-empty")
check("A2 _gene_set non-empty (GOATOOLS)", nz_gt >= 1, f"{nz_gt} rows non-empty")
multi = normalize_genes("GENE1;GENE2/GENE3,GENE4")
check("A3 multi-delimiter unit", len(multi) == 4 and join_genes(multi) == "GENE1/GENE2/GENE3/GENE4",
      f"parsed={sorted(multi)}")

# (B) gene_ratio 'k/n'
bad_gr = merged[~merged["gene_ratio"].astype(str).str.fullmatch(r"\d+/\d+")]
check("B gene_ratio ^\\d+/\\d+$", len(bad_gr) == 0, f"{len(bad_gr)} bad rows")

# (C) bg_ratio 'M/N'
bad_br = merged[~merged["bg_ratio"].astype(str).str.fullmatch(r"\d+/\d+")]
check("C bg_ratio ^\\d+/\\d+$", len(bad_br) == 0, f"{len(bad_br)} bad rows")

# (D) fold finite where denominator>0
merged["_br_num"] = merged["bg_ratio"].apply(lambda v: int(str(v).split("/")[0]))
den_zero = merged["_br_num"] == 0
nonfinite = merged[~den_zero & ~merged["fold_enrichment"].apply(math.isfinite)]
check("D fold finite (non-zero denom)", len(nonfinite) == 0,
      f"{len(nonfinite)} non-finite with M>0; NaN-fold rows={int(den_zero.sum())} (M=0)")

# (E) label parse contract
merged["_pdir"], merged["_pont"] = zip(*merged["gene_set"].apply(parse_label))
bad_dir = merged[~merged["direction"].isin(["UP", "DOWN", "TOTAL"])]
bad_ont = merged[~merged["ontology"].isin(["BP", "CC", "MF", "KEGG"])]
mismatch = merged[(merged["_pdir"] != merged["direction"]) | (merged["_pont"] != merged["ontology"])]
check("E1 direction in {UP,DOWN,TOTAL}", len(bad_dir) == 0)
check("E2 ontology in {BP,CC,MF,KEGG}", len(bad_ont) == 0)
check("E3 label parse mirrors loader", len(mismatch) == 0, f"{len(mismatch)} mismatches")

# (F) term_id policy
go_rows = merged[merged["ontology"] != "KEGG"]
kegg_rows = merged[merged["ontology"] == "KEGG"]
go_ok = go_rows["term_id"].astype(str).str.fullmatch(r"GO:\d{7}")
kegg_hsa = kegg_rows["term_id"].astype(str).str.fullmatch(r"hsa\d+")
kegg_empty = kegg_rows["term_id"].astype(str).str.fullmatch(r"")
check("F1 GO rows have GO:\\d{7}", bool(go_ok.all()),
      f"{int(go_ok.sum())}/{len(go_rows)}")
check("F2 KEGG term_id empty unless ^hsa\\d+",
      bool((kegg_hsa | kegg_empty).all()),
      f"observed: hsa={int(kegg_hsa.sum())}, empty={int(kegg_empty.sum())} of {len(kegg_rows)}")

# (G) description canonical: shared term_id across engines -> single description
shared = set(c_go["term_id"]) & set(c_gt["term_id"])
conflicts = []
for tid in shared:
    descs = set(merged[merged["term_id"] == tid]["term"].astype(str))
    if len(descs) > 1:
        conflicts.append((tid, descs))
check("G description canonical (no conflict on shared term_ids)", len(conflicts) == 0,
      f"{len(shared)} shared ids; conflicts={len(conflicts)}")
# count how many shared ids had differing RAW texts that canonicalization resolved
raw_diff = 0
enr_term_by_id = {}
for _, r in go_df.iterrows():
    tid = extract_go_id(r["Term"])
    if tid:
        enr_term_by_id[tid] = str(r["Term"])
raw_diff = sum(1 for tid in shared if tid in enr_term_by_id
               and enr_term_by_id[tid] != obo_names.get(tid, ""))
print(f"  (G detail) shared ids={len(shared)}; raw enrichr Term differed from obo name for {raw_diff} "
      f"-> canonicalized to obo name; example conflict terms: "
      f"{[(tid, enr_term_by_id[tid], obo_names.get(tid)) for tid in list(shared)[:2] if tid in enr_term_by_id]}")

# ---- summary ----
print("\n==== P0-4 CONVERTER SUMMARY ====")
print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")
for name, detail in FAIL:
    print(f"  FAILED ASSERT: {name} {detail}")
# sample standardized rows
print("\nSample standardized rows (3):")
print(merged[["term_id", "term", "gene_ratio", "bg_ratio", "fold_enrichment", "gene_set",
              "gene_count", "bg_count", "fdr", "engine"]].head(3).to_string(index=False))
print("\nFold distribution (inspect non-trivial):")
print(merged["fold_enrichment"].describe().to_string())
sys.exit(1 if FAIL else 0)