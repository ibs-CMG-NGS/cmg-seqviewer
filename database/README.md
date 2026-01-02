# Database Directory

## Overview

This directory stores pre-loaded RNA-Seq datasets in Parquet format for quick access within the application.

## Structure

```
database/
├── .gitkeep              # Ensures directory is tracked by git
├── README.md             # This file
├── datasets/             # Parquet data files
│   ├── .gitkeep          # Ensures subdirectory exists
│   └── *.parquet         # Dataset files (excluded from git)
└── metadata.json         # Dataset metadata (excluded from git)
```

## For Public Repository Users

**Note**: This repository does not include pre-loaded datasets to protect internal research data.

### Option 1: Use Without Pre-loaded Data (Recommended for External Users)

The application works perfectly without pre-loaded data:

1. Clone the repository (database folder will be empty)
2. Run the application: `python src/main.py`
3. Load your own datasets via:
   - `File → Open Dataset` (Ctrl+O)
   - Drag & drop Excel files
   - Recent files menu

### Option 2: Add Your Own Datasets

To pre-load your own datasets:

1. Place Excel files in a temporary folder
2. Load them via the application
3. They will be automatically saved to `database/datasets/` in Parquet format
4. Next time you run the app, they'll appear in "Database Browser"

## For Internal Distribution (Research Team)

### Creating Internal Release Package

For internal team members who need pre-loaded datasets:

#### Method 1: Manual Package Creation

```powershell
# 1. Build application with PyInstaller
pyinstaller --clean rna-seq-viewer.spec

# 2. Manually copy database folder to dist
Copy-Item -Recurse database dist/CMG-SeqViewer/database

# 3. Create internal ZIP
Compress-Archive -Path "dist\CMG-SeqViewer" -DestinationPath "CMG-SeqViewer-Internal-v1.0.0.zip"
```

#### Method 2: Separate Data Package

Keep code and data separate:

**Code Package** (from GitHub):
```powershell
# Users clone from GitHub
git clone https://github.com/YOUR_USERNAME/cmg-seqviewer.git
```

**Data Package** (internal file share):
```
CMG-SeqViewer-Data-v1.0.0.zip
└── database/
    ├── datasets/
    │   └── *.parquet
    └── metadata.json
```

**Installation**:
1. Clone repository from GitHub
2. Download data package from internal server
3. Extract data package into project root (merges with database/ folder)

#### Method 3: Private Data Repository

For larger teams, create a separate private repository:

```bash
# Main public repository
https://github.com/YOUR_ORG/cmg-seqviewer

# Private data repository (internal only)
https://github.com/YOUR_ORG/cmg-seqviewer-data
```

In main repository README:
```markdown
## Internal Team Setup

For internal team members with access to research data:

1. Clone main repository: `git clone https://github.com/YOUR_ORG/cmg-seqviewer.git`
2. Clone data repository: `git clone https://github.com/YOUR_ORG/cmg-seqviewer-data.git`
3. Copy data: `cp -r cmg-seqviewer-data/database/* cmg-seqviewer/database/`
```

## Data Format

### Parquet Files
- **Format**: Apache Parquet (columnar storage)
- **Naming**: UUID v4 format (e.g., `a307e148-e2ef-4748-aca6-dda1b404e6cc.parquet`)
- **Content**: Differential expression or GO/KEGG analysis results
- **Columns**: Standardized via `StandardColumns` class

### Metadata JSON
```json
{
  "datasets": [
    {
      "id": "a307e148-...",
      "name": "[Astrocyte] Acute1D_vs_Control",
      "type": "differential_expression",
      "loaded_at": "2025-01-02T10:30:00",
      "row_count": 15907,
      "columns": ["gene_id", "symbol", "log2fc", "adj_pvalue", ...]
    }
  ]
}
```

## Security Considerations

### What's Protected
- ✅ Actual research data (.parquet files)
- ✅ Dataset metadata (sample names, counts)
- ✅ Any identifying information

### What's Public
- ✅ Application source code
- ✅ Database schema/structure
- ✅ Example data format documentation
- ✅ Empty database directories

## Automated Builds

### GitHub Actions Behavior

The `.github/workflows/build.yml` includes database in spec file:

```python
# rna-seq-viewer.spec
datas=[
    ('database', 'database'),  # Includes database folder
],
```

**For Public Builds**: 
- Database folder exists but is empty (only .gitkeep files)
- Application runs normally without pre-loaded data

**For Internal Builds**:
1. Build locally with data: `pyinstaller rna-seq-viewer.spec`
2. Or use GitHub Actions with private data repo as submodule

## FAQ

**Q: Can users load their own data?**  
A: Yes! The application is fully functional without pre-loaded data. Users can load any Excel file with differential expression or GO/KEGG results.

**Q: How do I know if data is loaded?**  
A: Check the "Database Browser" dialog (`File → Database Browser`). If datasets appear, they're pre-loaded.

**Q: Can I delete pre-loaded datasets?**  
A: Yes, click "Remove" in Database Browser or manually delete `.parquet` files from this folder.

**Q: What's the difference between database and session data?**  
- **Database**: Persistent pre-loaded datasets (this folder)
- **Session**: Temporary datasets loaded during current session (not saved by default)

## Troubleshooting

### Database folder is missing
```powershell
# Create structure
mkdir database/datasets -Force
```

### Permission errors when writing
```powershell
# Check folder permissions (Windows)
icacls database

# Grant write access if needed
icacls database /grant Users:F /T
```

### Corrupted metadata.json
```powershell
# Backup first
Copy-Item database/metadata.json database/metadata.json.bak

# Delete and regenerate
Remove-Item database/metadata.json
# Restart application - it will regenerate from .parquet files
```

---

**For internal team support**: Contact [your-team-contact] for access to pre-loaded datasets.
