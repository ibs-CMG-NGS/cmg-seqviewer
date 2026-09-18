# 12. Gene Annotation

## 12.1 Overview

CMG-SeqViewer provides quick access to external gene annotation databases
 through convenient right-click context menus in data tables.

## 12.2 Accessing Gene Information

Right-click on any gene symbol or gene ID in the data table to access annotation resources:

### For Gene Symbols/IDs:

- **🔍 NCBI Gene** - Comprehensive gene information

 - Official gene names and symbols

 - Genomic locations and structure

 - Expression data and orthologs

 - References and pathways

- **🔍 GeneCards** - Human gene database

 - Integrated information from 150+ sources

 - Disease associations

 - Protein products and domains

 - Best for human genes

- **🔍 Ensembl** - Genome browser

 - Multi-species support

 - Detailed genomic annotations

 - Variant information

 - Comparative genomics

- **🔍 UniProt** - Protein database

 - Protein sequences and structures

 - Functional annotations

 - Post-translational modifications

 - Protein-protein interactions

- **📚 Google Scholar** - Literature search

 - Research publications about the gene

 - Citations and reviews

 - Recent discoveries

## 12.3 GO Term Annotation

Right-click on GO term IDs or descriptions in GO analysis results:

### For GO Terms (GO:XXXXXXX):

- **🔍 QuickGO (EBI)** - Primary GO resource

 - Detailed term definitions

 - Hierarchical relationships (parent/child terms)

 - Associated genes and proteins

 - Fast and comprehensive

- **🔍 AmiGO** - Official GO browser

 - Interactive ontology browser

 - Term relationships visualization

 - Gene product annotations

 - Official GO Consortium tool

- **🔍 Gene Ontology** - GO documentation

 - Official GO documentation

 - Ontology structure information

 - Best practices and guidelines

- **🔍 NCBI Gene** - Genes with this GO term

 - Find genes annotated with this term

 - Cross-reference with your results

## 12.4 KEGG Pathway Annotation

Right-click on KEGG pathway IDs or pathway names:

### For KEGG Pathways (e.g., hsa04110):

- **🔍 KEGG Pathway** - Interactive pathway maps

 - Visual pathway diagrams

 - Gene/protein relationships

 - Compound and reaction information

 - Links to related pathways

- **🔍 KEGG Search** - Search KEGG database

 - Find related pathways

 - Search by pathway name or description

 - Cross-species pathway information

- **🔍 Reactome** - Alternative pathway database

 - Curated biological pathways

 - Detailed molecular mechanisms

 - Pathway visualization tools

 - Cross-references to other databases

- **🔍 WikiPathways** - Community pathways

 - Open collaborative pathway database

 - Regularly updated by community

 - Integration with other tools

## 12.5 General Descriptions

Right-click on description columns for general searches:

- **📚 Google Scholar** - Academic literature search

- **📚 PubMed** - Biomedical literature database

 - Research articles and reviews

 - Clinical studies

 - Free full-text articles (PMC)

## 12.6 How It Works

1. **Auto-detection:** The tool automatically detects column types:

 - Gene columns: gene_id, symbol, gene_symbol

 - GO columns: term_id, go_id, or GO:XXXXXXX pattern

 - KEGG columns: pathway_id, kegg_id, or pathway names

 - Description columns: description, term_name, pathway_name

2. **ID Extraction:** Automatically extracts IDs from text:

 - GO:0008150 extracted from "GO:0008150 biological_process"

 - hsa04110 extracted from pathway descriptions

3. **One-click access:** Click any menu item to open in default browser

4. **Context-aware:** Shows relevant databases based on data type

## 12.7 Workflow Examples

### Example 1: Gene Function Research

1. Load DE analysis results

2. Filter for significant genes (padj < 0.05, |log2FC| > 1)

3. Right-click on interesting gene symbol

4. Select "🔍 GeneCards" for comprehensive overview

5. Select "📚 Google Scholar" for recent publications

### Example 2: GO Term Investigation

1. Load GO enrichment results

2. Filter top enriched terms (FDR < 0.01)

3. Right-click on GO term ID

4. Select "🔍 QuickGO" to see term hierarchy

5. Select "🔍 NCBI Gene" to find related genes

### Example 3: Pathway Analysis

1. Load KEGG enrichment results

2. Right-click on enriched pathway

3. Select "🔍 KEGG Pathway" to view pathway diagram

4. Select "🔍 Reactome" for alternative pathway view

5. Compare pathway information across databases

## 12.8 Tips

6. **Multiple Databases:** Check multiple databases for comprehensive information

7. **Species Consideration:**

 - GeneCards is best for human genes

 - Ensembl supports multiple species

 - NCBI Gene covers many organisms

8. **GO Hierarchy:** Use QuickGO or AmiGO to explore parent/child term relationships

9. **Pathway Context:** View KEGG pathways to understand gene interactions

10. **Literature Review:** Use Google Scholar and PubMed to find relevant research

11. **Quick Reference:** Right-click is faster than manual web searches

## 12.9 Benefits

12. ✅ **No local database needed** - Always up-to-date information

13. ✅ **One-click access** - Saves time compared to manual searches

14. ✅ **Multiple resources** - Compare information across databases

15. ✅ **Context-aware** - Shows relevant databases for each data type

16. ✅ **Auto ID extraction** - No need to copy-paste IDs manually

---
**See also**: [User Guide](../user-guide.md) · [FAQ](20-faq.md)
