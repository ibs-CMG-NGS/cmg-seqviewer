import time, sys
import pandas as pd

# ---- build ~100 gene list ----
da = pd.read_parquet("examples/Acute_1D_vs_Control_DA.parquet")
col = "gene_name"
sym = da[col].dropna().astype(str).str.strip()
sym = sym[sym != ""]
uniq = []
seen = set()
for s in sym:
    u = s.upper()
    if u not in seen and u != "NAN":
        seen.add(u)
        uniq.append(u)
genes = uniq[:100]
print("parquet rows:", len(da), "| unique non-empty symbols:", len(uniq), "| first 100:", len(genes))
print("first 10 genes:", genes[:10])
print("gene count should be 100 ->", len(genes))

import gseapy
print("gseapy version:", gseapy.__version__)

# ---- real call: GO_Biological_Process_2023 ----
t0 = time.perf_counter()
res_go = gseapy.enrichr(gene_list=genes, gene_sets=["GO_Biological_Process_2023"],
                        organism="human", outdir=None, no_plot=True, verbose=False)
t_go = time.perf_counter() - t0
print("GO call wall-time: %.2fs" % t_go)
go_df = res_go.res2d
print("GO shape:", go_df.shape)
print("GO columns:", list(go_df.columns))
go_df.to_csv("docs/planning/generated/phase0_poc/enrichr_go_bp_2023.csv", index=False)

# ---- real call: KEGG_2021_Human ----
t0 = time.perf_counter()
res_kg = gseapy.enrichr(gene_list=genes, gene_sets=["KEGG_2021_Human"],
                        organism="human", outdir=None, no_plot=True, verbose=False)
t_kg = time.perf_counter() - t0
print("KEGG call wall-time: %.2fs" % t_kg)
kg_df = res_kg.res2d
print("KEGG shape:", kg_df.shape)
print("KEGG columns:", list(kg_df.columns))
kg_df.to_csv("docs/planning/generated/phase0_poc/enrichr_kegg_2021_human.csv", index=False)
