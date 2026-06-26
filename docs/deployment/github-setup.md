# GitHub Repository Setup & Upload Guide

## 📋 Pre-Upload Checklist

### 1. Essential Files ✅
- [x] `.gitignore` - Configured to exclude build artifacts, venv, logs
- [x] `README.md` - Project overview and quick start
- [x] `requirements.txt` - Python dependencies
- [x] `LICENSE` - ⚠️ **MISSING** - Add appropriate license
- [x] `.github/workflows/build.yml` - CI/CD configuration
- [x] `rna-seq-viewer.spec` - Windows build spec
- [x] `cmg-seqviewer-macos.spec` - macOS build spec

### 2. Documentation Files ✅
- [x] `docs/RECENT_UPDATES.md` - Latest features and changes
- [x] `docs/QUICK_START.md` - User quick start guide
- [x] `docs/DEVELOPMENT.md` - Developer setup guide
- [x] `PROJECT_SUMMARY.md` - Comprehensive project overview
- [x] In-app Help (F1) - Updated with GO/KEGG content

### 3. Code Quality
- [x] Remove debug print statements
- [x] Encoding issues resolved (UTF-8)
- [x] No hardcoded file paths
- [x] Environment variables in `.env.example`
- [x] Proper error handling

---

## 🚀 GitHub Upload Steps

### Step 1: Create LICENSE File

Choose an appropriate license. For academic/research software, MIT or GPL are common:

```bash
# Create MIT License (permissive)
# Visit https://choosealicense.com/licenses/mit/ and copy content
# OR use GitHub's license template when creating repository
```

### Step 2: Initialize Git (if not already done)

```powershell
# Navigate to project directory
cd C:\Users\USER\Documents\GitHub\rna-seq-data-view

# Initialize git (skip if already initialized)
git init

# Check current status
git status
```

### Step 3: Review .gitignore

Ensure the following are excluded:
```gitignore
# Python
__pycache__/
*.pyc
venv/
*.egg-info/

# Build artifacts
build/
dist/
*.spec (except committed ones)

# IDE
.vscode/
.idea/

# Data
logs/
*.log
final_go_results_diagnostic.csv

# OS
.DS_Store
Thumbs.db

# Sensitive
.env
*.db (except example databases)
```

### Step 4: Stage and Commit Files

```powershell
# Add all files (respects .gitignore)
git add .

# Check what will be committed
git status

# First commit
git commit -m "Initial commit: CMG-SeqViewer v1.0.0 with GO/KEGG clustering"

# OR more detailed commit
git commit -m "feat: Complete RNA-Seq analysis tool with GO clustering

- MVP architecture with FSM state management
- Multi-dataset comparison and visualization
- GO/KEGG clustering with ClueGO-style network viz
- Comprehensive help documentation
- GitHub Actions CI/CD pipeline"
```

### Step 5: Create GitHub Repository

1. **Via GitHub Web**:
   - Go to https://github.com/new
   - Repository name: `rna-seq-data-view` or `cmg-seqviewer`
   - Description: "Desktop application for RNA-Seq differential expression analysis and GO/KEGG pathway enrichment visualization"
   - Choose Public or Private
   - **DO NOT** initialize with README (we already have one)
   - **DO NOT** add .gitignore (we already have one)
   - Click "Create repository"

2. **Note the repository URL**: `https://github.com/YOUR_USERNAME/rna-seq-data-view.git`

### Step 6: Connect Local to Remote

```powershell
# Add remote origin
git remote add origin https://github.com/YOUR_USERNAME/rna-seq-data-view.git

# Verify remote
git remote -v

# Rename branch to main (if currently master)
git branch -M main

# Push to GitHub
git push -u origin main
```

### Step 7: Configure Repository Settings (on GitHub)

1. **Topics/Tags**: Add relevant topics
   - `rna-seq`, `bioinformatics`, `data-visualization`, `pyqt6`, `go-analysis`, `python`

2. **About Section**: Add description and website (if any)

3. **Branch Protection** (optional for solo dev):
   - Settings → Branches → Add rule for `main`
   - Require status checks before merging (when CI is ready)

---

## ⚙️ GitHub Actions Setup

### Understanding the Workflow

Your `.github/workflows/build.yml` defines a CI/CD pipeline that:

1. **Triggers on**:
   - Version tags (e.g., `v1.0.0`)
   - Manual dispatch (workflow_dispatch)

2. **Builds**:
   - Windows executable (`.exe` + dependencies in folder)
   - macOS application (`.app` bundle in `.dmg`)

3. **Releases**:
   - Automatically creates GitHub Release when tagged
   - Uploads build artifacts as release assets

### Workflow Breakdown

#### Job 1: `build-windows` (runs on `windows-latest`)

```yaml
steps:
  1. Checkout code (actions/checkout@v4)
  2. Setup Python 3.11 (actions/setup-python@v4)
  3. Install dependencies (requirements.txt + pyinstaller + pillow)
  4. Create icon (create_icon.py → cmg-seqviewer.ico)
  5. Build executable (pyinstaller --clean --noconfirm rna-seq-viewer.spec)
  6. Create ZIP (Compress-Archive dist/CMG-SeqViewer → CMG-SeqViewer-Windows.zip)
  7. Upload artifact (actions/upload-artifact@v3)
```

**Output**: `CMG-SeqViewer-Windows.zip` containing:
```
CMG-SeqViewer/
├── CMG-SeqViewer.exe
├── _internal/ (dependencies)
└── database/ (pre-loaded datasets)
```

#### Job 2: `build-macos` (runs on `macos-latest`)

```yaml
steps:
  1. Checkout code
  2. Setup Python 3.11
  3. Install dependencies
  4. Create icon PNG (create_icon.py)
  5. Convert PNG to ICNS:
     - Create .iconset directory
     - Generate multiple resolutions (16x16 to 512x512@2x)
     - Use iconutil to create .icns
  6. Build .app bundle (pyinstaller cmg-seqviewer-macos.spec)
  7. Create DMG (hdiutil create → CMG-SeqViewer-macOS.dmg)
  8. Upload artifact
```

**Output**: `CMG-SeqViewer-macOS.dmg` containing:
```
CMG-SeqViewer.app/
├── Contents/
│   ├── MacOS/
│   │   └── CMG-SeqViewer (executable)
│   ├── Resources/
│   │   ├── cmg-seqviewer.icns
│   │   └── database/
│   └── Info.plist
```

#### Job 3: `create-release` (runs on `ubuntu-latest`)

```yaml
needs: [build-windows, build-macos]  # Wait for builds
if: startsWith(github.ref, 'refs/tags/')  # Only on tags

steps:
  1. Download Windows artifact
  2. Download macOS artifact
  3. Create GitHub Release (softprops/action-gh-release@v1):
     - Reads tag name (v1.0.0)
     - Creates release with that version
     - Uploads both ZIP and DMG as assets
     - Uses GITHUB_TOKEN for authentication
```

---

## 🏷️ Creating a Release

### Method 1: Git Tag + Push (Triggers CI)

```powershell
# Create annotated tag
git tag -a v1.0.0 -m "Release v1.0.0: GO/KEGG Clustering Support

Features:
- GO term clustering with ClueGO-style visualization
- Interactive network dialog with real-time updates
- Multiple similarity metrics (Jaccard, Kappa)
- Export clustered results with cluster_id column
- Updated help documentation

Bug Fixes:
- Volcano plot autoscale functionality
- Column name normalization for compatibility
- Encoding issues in help dialog"

# Push tag to GitHub (triggers workflow)
git push origin v1.0.0

# Or push all tags
git push --tags
```

### Method 2: GitHub Web Interface

1. Go to repository → Releases → "Draft a new release"
2. Click "Choose a tag" → Create new tag `v1.0.0`
3. Set target branch: `main`
4. Release title: `CMG-SeqViewer v1.0.0`
5. Description: Copy from tag message above
6. Click "Publish release"

This will:
- Create the tag
- Trigger the GitHub Actions workflow
- Workflow builds Windows + macOS versions
- Workflow uploads them to the release automatically

### Method 3: Manual Workflow Dispatch (Test Builds)

For testing without creating a release:

1. Go to repository → Actions → "Build CMG-SeqViewer"
2. Click "Run workflow" dropdown
3. Select branch `main`
4. Click "Run workflow"

This builds both platforms but does NOT create a release (artifacts available in Actions tab for 90 days).

---

## 🔍 Monitoring Builds

### Viewing Workflow Runs

1. Repository → Actions tab
2. Click on a workflow run to see details
3. Each job (build-windows, build-macos, create-release) shows:
   - Step-by-step execution
   - Logs for each step
   - Success/failure status

### Common Issues & Solutions

#### Issue 1: Icon Creation Fails
```
Error: PIL.Image not found
```
**Solution**: Ensure `pillow` is in `requirements.txt` and installed in workflow

#### Issue 2: PyInstaller Missing Modules
```
ModuleNotFoundError: No module named 'xxx'
```
**Solution**: Add to `hiddenimports` in `.spec` file:
```python
hiddenimports=[
    'PyQt6',
    'networkx',  # Add missing module
    # ...
],
```

#### Issue 3: macOS ICNS Conversion Fails
```
iconutil: error: missing required file
```
**Solution**: Check `create_icon.py` creates PNG at correct size (512x512 minimum)

#### Issue 4: Database Not Included in Build
```
FileNotFoundError: database directory
```
**Solution**: Verify `datas` in `.spec` file:
```python
datas=[
    ('database', 'database'),  # (source, destination)
],
```

---

## 📦 Artifact Structure

### Windows Build
```
CMG-SeqViewer-Windows.zip (uploaded to release)
└── CMG-SeqViewer/
    ├── CMG-SeqViewer.exe           # Main executable
    ├── _internal/                  # PyInstaller dependencies
    │   ├── PyQt6/
    │   ├── pandas/
    │   ├── matplotlib/
    │   └── ... (all Python packages)
    └── database/                   # Pre-loaded datasets
        ├── dataset1.parquet
        └── dataset2.parquet
```

### macOS Build
```
CMG-SeqViewer-macOS.dmg (uploaded to release)
└── CMG-SeqViewer.app/
    └── Contents/
        ├── MacOS/
        │   └── CMG-SeqViewer       # Executable binary
        ├── Resources/
        │   ├── cmg-seqviewer.icns  # App icon
        │   ├── database/           # Pre-loaded datasets
        │   └── (dependencies)
        ├── Info.plist              # macOS app metadata
        └── Frameworks/             # Bundled libraries
```

---

## 🔒 Security Considerations

### Secrets Management

GitHub Actions uses `GITHUB_TOKEN` automatically for:
- Uploading release assets
- Creating releases
- Accessing repository

**No manual secret setup needed** for basic workflow.

### If Adding External Services

For services like code signing, deployment:

1. Go to Repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add secret (e.g., `SIGNING_CERTIFICATE`)
4. Use in workflow: `${{ secrets.SIGNING_CERTIFICATE }}`

---

## 📊 Download Statistics

After releases are created, view download stats:

1. Repository → Insights → Traffic
2. Check release downloads in Release page

---

## 🎯 Next Steps After Upload

1. **Add Badge to README**:
```markdown
[![Build Status](https://github.com/YOUR_USERNAME/rna-seq-data-view/workflows/Build%20CMG-SeqViewer/badge.svg)](https://github.com/YOUR_USERNAME/rna-seq-data-view/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Latest Release](https://img.shields.io/github/v/release/YOUR_USERNAME/rna-seq-data-view)](https://github.com/YOUR_USERNAME/rna-seq-data-view/releases)
```

2. **Enable GitHub Pages** (optional):
   - Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main`, folder: `/docs`
   - Allows hosting documentation at `https://YOUR_USERNAME.github.io/rna-seq-data-view/`

3. **Set Up Issue Templates**:
   - .github/ISSUE_TEMPLATE/bug_report.md
   - .github/ISSUE_TEMPLATE/feature_request.md

4. **Add CONTRIBUTING.md**:
   - Guidelines for contributors
   - Code style conventions
   - Testing requirements

5. **Create Project Board** (optional):
   - Track features, bugs, enhancements
   - Kanban-style workflow

---

## 🆘 Troubleshooting

### Build Fails on GitHub But Works Locally

**Cause**: Environment differences (Python version, dependencies)

**Solution**:
1. Check Python version in workflow matches local: `python-version: '3.11'`
2. Ensure `requirements.txt` is complete
3. Test with fresh venv locally:
   ```powershell
   python -m venv test-venv
   test-venv\Scripts\activate
   pip install -r requirements.txt
   pyinstaller rna-seq-viewer.spec
   ```

### Workflow YAML Syntax Errors

**Tool**: Use VS Code with YAML extension or online validator
- https://www.yamllint.com/
- Indentation is critical (2 spaces, not tabs)

### Need to Debug Workflow

Add debug step:
```yaml
- name: Debug environment
  run: |
    python --version
    pip list
    ls -la
    pwd
```

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [GitHub Releases Guide](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [Semantic Versioning](https://semver.org/)
