import pandas as pd, re
go = pd.read_csv("docs/planning/generated/phase0_poc/enrichr_go_bp_2023.csv")
kg = pd.read_csv("docs/planning/generated/phase0_poc/enrichr_kegg_2021_human.csv")

print("=== (a) exact column names (GO) ===")
print(list(go.columns))
print("shape GO:", go.shape, "| shape KEGG:", kg.shape)

print("\n=== (b) Overlap format, 3 sample rows (GO) ===")
for _, r in go.head(3).iterrows():
    print(repr(r["Overlap"]))
print("=== (b) Overlap format, 3 sample rows (KEGG) ===")
for _, r in kg.head(3).iterrows():
    print(repr(r["Overlap"]))

print("\n=== (c) Genes separator, 3 sample rows (GO) ===")
for _, r in go.head(3).iterrows():
    g = str(r["Genes"])
    print("sep ';' in genes:", ";" in g, "| sample:", g[:120])
print("=== (c) Genes separator, 3 sample rows (KEGG) ===")
for _, r in kg.head(3).iterrows():
    g = str(r["Genes"])
    print("sep ';' in genes:", ";" in g, "| sample:", g[:120])

print("\n=== (d) KEGG Term content — 3 verbatim ===")
for _, r in kg.head(3).iterrows():
    print(repr(str(r["Term"])))
kegg_hsa = kg["Term"].astype(str).str.contains(r"^hsa\d+", regex=True).sum()
kegg_hsa_any = kg["Term"].astype(str).str.contains(r"hsa\d+", regex=True).sum()
print("KEGG terms starting with hsa\\d+:", kegg_hsa, "/", len(kg), "| containing hsa\\d+ anywhere:", kegg_hsa_any)

print("\n=== (e) GO Term content — 3 verbatim ===")
for _, r in go.head(3).iterrows():
    print(repr(str(r["Term"])))
go_id_paren = go["Term"].astype(str).str.contains(r"GO:\d{7}", regex=True).sum()
print("GO Terms containing GO:\\d{7}:", go_id_paren, "/", len(go))
go_none = go["Term"].astype(str).str.contains(r"GO:\d{7}", regex=True).sum() == 0
print("all GO Terms have GO id embedded:", go_none is False and go_id_paren == len(go))
