#!/usr/bin/env python
"""gene2go sample fixture for the GOATOOLS local-path integration test (plan §12).

tax_id, GeneID, GO_id, Evidence, Qualifier, GO_term, PubMed, Category
(NCBI gene2go Category=Process/Function/Component — human 9606만, mini-obo GO 참조)
"""
import gzip

ROWS = [
    "9606\t101\tGO:0000004\tIDA\t\theart contraction\t\tProcess",
    "9606\t101\tGO:0000006\tIDA\t\tmuscle cell migration\t\tProcess",
    "9606\t102\tGO:0000004\tIDA\t\theart contraction\t\tProcess",
    "9606\t102\tGO:0000007\tIDA\t\tcell adhesion\t\tProcess",
    "9606\t103\tGO:0000007\tIDA\t\tcell adhesion\t\tProcess",
    "9606\t103\tGO:0000005\tIDA\t\timmune response\t\tProcess",
    "9606\t104\tGO:0000005\tIDA\t\timmune response\t\tProcess",
    "9606\t105\tGO:0000008\tIDA\t\treceptor binding\t\tFunction",
    "9606\t106\tGO:0000009\tIDA\t\tstructural molecule activity\t\tFunction",
    "9606\t107\tGO:0000010\tIDA\t\tmembrane component\t\tComponent",
    "9606\t108\tGO:0000011\tIDA\t\tcytosol\t\tComponent",
]

# Population (Entrez) — 101..108 (8 genes). Study(UP_BP case) — 101..104 (4 genes).
POPULATION = [101, 102, 103, 104, 105, 106, 107, 108]
STUDY = [101, 102, 103, 104]


def write_gene2go_sample(path) -> "Path":
    """gzipped gene2go 픽스처 작성 (참조 전용 — 테스트가 tmp에 사용)."""
    import gzip
    with gzip.open(str(path), "wt", encoding="utf-8") as fh:
        fh.write("\n".join(ROWS) + "\n")
    return path