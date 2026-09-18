"""Re-run GOATOOLS from saved artifacts to persist pop_count/pop_n (term sizes) into the results CSV."""
import os, json, time, resource
import pandas as pd
DATA = "docs/planning/generated/phase0_poc/data"
OUT = "docs/planning/generated/phase0_poc"
import statsmodels.sandbox.stats.multicomp as _sm_mc
from statsmodels.stats.multitest import multipletests as _mp
_sm_mc.multipletests = _mp
from goatools.obo_parser import GODag
from goatools.anno.genetogo_reader import Gene2GoReader
from goatools.goea.go_enrichment_ns import GOEnrichmentStudyNS

genes = json.load(open(os.path.join(OUT, "p0-3_genes.json")))
esym = json.load(open(os.path.join(OUT, "entrez2sym_human.json")))
entrez = [int(e) for e in esym.keys()]
print("genes:", len(genes), "entrez:", len(entrez))

t0 = time.perf_counter()
obo_dag = GODag(os.path.join(DATA, "go-basic.obo"), optional_attrs=["relationship"])
g2r = Gene2GoReader(os.path.join(DATA, "gene2go_human.tsv"), taxids=[9606])
ns2assoc = g2r.get_ns2assc()
goea = GOEnrichmentStudyNS(entrez, ns2assoc, obo_dag, propagate_counts=True, alpha=0.05, methods=["fdr_bh"])
results = goea.run_study(entrez)
print(f"prep+run wall={time.perf_counter()-t0:.2f}s n_results={len(results)}")

rows = []
for r in results:
    rows.append({"GO": r.GO, "NS": r.NS, "name": r.name,
                 "p_uncorrected": r.p_uncorrected, "p_fdr_bh": r.p_fdr_bh,
                 "study_count": r.study_count, "study_n": r.study_n,
                 "pop_count": getattr(r, "pop_count", ""), "pop_n": getattr(r, "pop_n", ""),
                 "ratio_in_study": str(r.ratio_in_study),
                 "study_items": sorted(r.study_items)})
res_df = pd.DataFrame(rows)
res_df.to_csv(os.path.join(OUT, "goatools_human_results.csv"), index=False)
sig = res_df[res_df["p_fdr_bh"] < 0.05]
print("rows saved:", len(res_df), "| significant:", len(sig))
print(res_df[["GO","NS","name","p_fdr_bh","study_count","pop_count","pop_n"]].head(5).to_string())
print("P0-3c DONE")
