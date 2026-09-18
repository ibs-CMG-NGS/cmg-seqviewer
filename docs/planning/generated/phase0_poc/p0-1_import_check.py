import sys
print("python:", sys.version)
import pandas as pd, numpy as np, scipy
print("pandas:", pd.__version__, "| numpy:", np.__version__, "| scipy:", scipy.__version__)
import gseapy, goatools, mygene, statsmodels, requests
print("gseapy:", gseapy.__version__)
print("goatools:", getattr(goatools, "__version__", "n/a"))
import importlib.metadata as im
for pkg in ("goatools", "mygene", "statsmodels", "requests"):
    print(f"{pkg} (metadata):", im.version(pkg))
# deep imports
from goatools.obo_parser import GODag
try:
    from goatools.goea_go_enrich_nss import GOEnrichmentStudyNS
    print("goatools.goea_go_enrich_nss import: OK (legacy path)")
except ModuleNotFoundError as e:
    print("goatools.goea_go_enrich_nss import: FAIL ->", e)
from goatools.goea.go_enrichment_ns import GOEnrichmentStudyNS
print("goatools.goea.go_enrichment_ns import: OK")
from goatools.anno.genetogo_reader import Gene2GoReader
from gseapy import enrichr, enrich, prerank, get_library_name
from statsmodels.stats.multitest import multipletests
print("all deep imports: OK")
