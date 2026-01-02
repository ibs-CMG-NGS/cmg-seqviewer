# GitHub Repository Upload - Final Checklist

## 🔒 CRITICAL: Data Protection Verification

> **⚠️ BEFORE UPLOADING**: Verify that internal research data is NOT included in the public repository.

### Data Protection Checklist
- [x] `.gitignore` excludes `database/datasets/*.parquet` - ✅ **CONFIGURED**
- [x] `.gitignore` excludes `database/metadata.json` - ✅ **CONFIGURED**
- [x] `.gitkeep` files created for empty directory structure - ✅ **CREATED**
- [x] `database/README.md` - ✅ **CREATED** (Public usage guide)
- [x] `docs/INTERNAL_DISTRIBUTION.md` - ✅ **CREATED** (Internal distribution guide)

### Pre-Upload Data Verification

```powershell
# 1. Verify .parquet files are NOT staged
git status
# Should NOT see: database/datasets/*.parquet

# 2. Verify .gitkeep files ARE staged
git status
# Should see: database/.gitkeep, database/datasets/.gitkeep

# 3. Check git history (ensure no data was committed before)
git log --all --full-history --oneline -- "database/datasets/*.parquet"
# Should be EMPTY

# 4. Verify repository size (should be small without data)
git count-objects -vH
# size-pack should be < 50 MiB

# 5. Double-check what would be pushed
git diff --stat --cached origin/main
# Review output - NO .parquet files should appear
```

**🛑 STOP**: If any `.parquet` files appear above, DO NOT PROCEED. Remove them first:

```powershell
# Remove from staging
git reset HEAD database/datasets/*.parquet

# If accidentally committed
git filter-branch --force --index-filter \
  "git rm -rf --cached --ignore-unmatch database/datasets/" \
  HEAD
```

---

## ✅ Pre-Upload Status

### Essential Files
- [x] `README.md` - ✅ **UPDATED** with latest features + data protection note
- [x] `LICENSE` - ✅ **CREATED** (MIT License)
- [x] `.gitignore` - ✅ Configured (excludes venv, build, logs, **INTERNAL DATA**)
- [x] `requirements.txt` - ✅ Production dependencies
- [x] `requirements-dev.txt` - ✅ Development dependencies
- [x] `.github/workflows/build.yml` - ✅ CI/CD pipeline ready
- [x] `rna-seq-viewer.spec` - ✅ Windows build configuration
- [x] `cmg-seqviewer-macos.spec` - ✅ macOS build configuration
- [x] `create_icon.py` - ✅ Icon generation script

### Documentation Files
- [x] `docs/RECENT_UPDATES.md` - ✅ **CREATED** (Latest features & changelog)
- [x] `docs/GITHUB_SETUP.md` - ✅ **CREATED** (Comprehensive upload & CI/CD guide)
- [x] `docs/INTERNAL_DISTRIBUTION.md` - ✅ **CREATED** (Internal data distribution)
- [x] `docs/QUICK_START.md` - ✅ User quick start guide
- [x] `docs/DEVELOPMENT.md` - ✅ Developer setup guide
- [x] `docs/DATABASE_GUIDE.md` - ✅ Database schema
- [x] `database/README.md` - ✅ **CREATED** (Public/internal usage)
- [x] `PROJECT_SUMMARY.md` - ✅ Comprehensive overview
- [x] In-app Help (F1) - ✅ **UPDATED** with GO/KEGG section

### Code Quality
- [x] Debug prints removed (main_window.py scientific notation logs)
- [x] Encoding fixed (help_dialog.py UTF-8)
- [x] Autoscale bug fixed (visualization_dialog.py column names)
- [x] GO clustering fully functional
- [x] Menu structure updated (flattened GO/KEGG menus)

### Security & Data Protection
- [x] Internal research data excluded from repository
- [x] Database directory structure preserved (.gitkeep files)
- [x] Public/internal usage documentation complete
- [x] Internal distribution methods documented

---

## 🚀 Upload Procedure (Step-by-Step)

### Phase 1: Local Git Setup

```powershell
# 1. Navigate to project
cd C:\Users\USER\Documents\GitHub\rna-seq-data-view

# 2. Check git status (should already be initialized)
git status

# 3. ⚠️ CRITICAL: Verify NO .parquet files are staged
git status | Select-String "parquet"
# Should return NOTHING

# 4. Review what will be committed
git add .
git status

# 5. If any unwanted files appear, update .gitignore
# Then: git reset
#       (edit .gitignore)
#       git add .

# 5. Create initial commit
git commit -m "feat: Initial release v1.0.0 - CMG-SeqViewer with GO/KEGG clustering

Features:
- MVP architecture with FSM state management (12 states, 18 events)
- Multi-dataset comparison with Venn diagrams
- GO/KEGG clustering with ClueGO-style network visualization
- Interactive visualizations (Volcano, Heatmap, Dot Plot, Bar Chart, Network)
- Comprehensive help documentation with F1 support
- CI/CD pipeline for Windows and macOS builds

Technical:
- Python 3.9+ with PyQt6
- Async processing with QThread workers
- SQLite database for session management
- PyInstaller build configurations
- GitHub Actions workflow ready"
```

### Phase 2: GitHub Repository Creation

**Via GitHub Web Interface:**

1. Go to https://github.com/new
2. **Repository name**: `rna-seq-data-view` or `cmg-seqviewer`
3. **Description**: "Desktop application for RNA-Seq differential expression analysis and GO/KEGG pathway enrichment visualization with ClueGO-style clustering"
4. **Visibility**: Choose Public or Private
5. **Important**: 
   - ❌ **DO NOT** check "Initialize this repository with a README"
   - ❌ **DO NOT** add .gitignore
   - ❌ **DO NOT** choose a license (we already have one)
6. Click "Create repository"

### Phase 3: Connect Local to Remote

```powershell
# 1. Add remote (replace YOUR_USERNAME with actual GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/rna-seq-data-view.git

# 2. Verify remote
git remote -v
# Should show:
# origin  https://github.com/YOUR_USERNAME/rna-seq-data-view.git (fetch)
# origin  https://github.com/YOUR_USERNAME/rna-seq-data-view.git (push)

# 3. Rename branch to main (if currently master)
git branch -M main

# 4. Push to GitHub
git push -u origin main

# First push may prompt for GitHub authentication
# Use Personal Access Token (classic) with 'repo' scope
# Create at: https://github.com/settings/tokens
```

### Phase 4: Repository Configuration (on GitHub)

1. **Topics/Tags**: Add relevant topics
   - Go to repository page
   - Click gear icon ⚙️ next to "About"
   - Add topics: `rna-seq`, `bioinformatics`, `data-visualization`, `pyqt6`, `go-analysis`, `python`, `genomics`, `clustering`, `network-visualization`

2. **Description**: 
   - "Desktop app for RNA-Seq analysis with GO/KEGG clustering & visualization"

3. **Website** (optional):
   - Add if you have documentation hosted elsewhere

### Phase 5: First Release

```powershell
# Create annotated tag
git tag -a v1.0.0 -m "Release v1.0.0: GO/KEGG Clustering & ClueGO-style Visualization

🆕 Major Features:
- GO term clustering with Jaccard & Kappa similarity
- Interactive network visualization with convex hulls
- Real-time hover tooltips and cluster legend
- Representative term selection per cluster
- Export clustered results with cluster_id column

📊 Visualizations:
- GO/KEGG Dot Plot
- GO/KEGG Bar Chart
- GO/KEGG Network Chart (cluster-based)
- Enhanced Volcano Plot with autoscale
- Heatmap with hierarchical clustering

🎨 UI/UX:
- Flattened GO/KEGG menu structure
- Gene Set vs Regulation filter labels
- Re-filtering support (Filtered:Filtered tabs)
- Comprehensive F1 help with GO section

🐛 Bug Fixes:
- Volcano plot autoscale column name handling
- Help dialog encoding issues resolved
- Debug log cleanup

📖 Documentation:
- Updated README with latest features
- GitHub setup guide with CI/CD details
- Recent updates changelog"

# Push tag (triggers GitHub Actions build)
git push origin v1.0.0
```

---

## ⚙️ GitHub Actions Workflow

### What Happens After Pushing Tag

1. **Workflow Triggered**: `.github/workflows/build.yml` activates
2. **Parallel Builds**:
   - **Job 1** (windows-latest): Builds Windows .exe + ZIP
   - **Job 2** (macos-latest): Builds macOS .app + DMG
3. **Release Creation** (ubuntu-latest):
   - Waits for both builds to complete
   - Creates GitHub Release with tag name (v1.0.0)
   - Uploads both artifacts as release assets
4. **Users Can Download**: Executables available on Releases page

### Monitoring Build Progress

1. Go to repository → **Actions** tab
2. Click on the workflow run (shows tag name)
3. View each job:
   - `build-windows`: ~15-20 minutes
   - `build-macos`: ~15-20 minutes
   - `create-release`: ~1 minute
4. Check logs if any step fails

### Expected Artifacts

**Windows Build** (~150-200 MB):
```
CMG-SeqViewer-Windows.zip
└── CMG-SeqViewer/
    ├── CMG-SeqViewer.exe
    ├── _internal/ (PyQt6, pandas, matplotlib, etc.)
    └── database/
```

**macOS Build** (~180-220 MB):
```
CMG-SeqViewer-macOS.dmg
└── CMG-SeqViewer.app/
    └── Contents/
        ├── MacOS/CMG-SeqViewer
        ├── Resources/
        └── Frameworks/
```

---

## 🔍 Post-Upload Verification

### 1. Repository Checklist
- [ ] All files visible on GitHub (no .gitignore issues)
- [ ] README renders correctly with images/badges
- [ ] LICENSE file present
- [ ] Topics/tags added
- [ ] Description set

### 2. Actions Checklist
- [ ] Workflow file appears in .github/workflows/
- [ ] No YAML syntax errors (check Actions tab)
- [ ] Secrets not required (GITHUB_TOKEN auto-provided)

### 3. Release Checklist
- [ ] Tag created (v1.0.0)
- [ ] Release created automatically
- [ ] Windows ZIP attached
- [ ] macOS DMG attached
- [ ] Release notes populated
- [ ] Download links work

### 4. Documentation Checklist
- [ ] README links work (relative paths correct)
- [ ] docs/ folder accessible
- [ ] GITHUB_SETUP.md guide accurate
- [ ] RECENT_UPDATES.md complete

---

## 🎯 Next Steps After Upload

### Immediate (Day 1)
1. **Test Downloads**:
   - Download Windows ZIP → Extract → Run .exe
   - Download macOS DMG → Install → Run .app
   - Verify both versions work correctly

2. **Add Badges to README** (optional):
   ```markdown
   [![Build Status](https://github.com/YOUR_USERNAME/rna-seq-data-view/workflows/Build%20CMG-SeqViewer/badge.svg)](https://github.com/YOUR_USERNAME/rna-seq-data-view/actions)
   ```

3. **Create Issue Templates**:
   - `.github/ISSUE_TEMPLATE/bug_report.md`
   - `.github/ISSUE_TEMPLATE/feature_request.md`

### Short-term (Week 1)
1. **Social Sharing**:
   - Share on Twitter/LinkedIn with hashtags: #bioinformatics #RNASeq #opensource
   - Post on relevant forums/Slack channels (if applicable)

2. **Documentation Review**:
   - Proofread all docs for typos
   - Add screenshots to README/docs
   - Record demo video

3. **Community Setup**:
   - Enable GitHub Discussions
   - Create FAQ.md based on anticipated questions
   - Set up CONTRIBUTING.md with guidelines

### Medium-term (Month 1)
1. **User Feedback**:
   - Monitor issues for bug reports
   - Track feature requests
   - Respond to community questions

2. **Analytics**:
   - Check download statistics (Insights → Traffic)
   - Monitor star/fork growth
   - Review Actions usage limits

3. **Iteration**:
   - Plan v1.0.1 bug fix release
   - Prioritize v1.1 features based on feedback

---

## 📝 Important Notes

### GitHub Username Placeholder
All documentation uses `YOUR_USERNAME` as placeholder. **Find and replace** with actual GitHub username:

```powershell
# Find all occurrences
Select-String -Path "*.md", "docs/*.md" -Pattern "YOUR_USERNAME" -CaseSensitive

# Manual replacement needed in:
# - README.md
# - docs/GITHUB_SETUP.md  
# - docs/RECENT_UPDATES.md
```

### Repository Naming Options
1. `rna-seq-data-view` (current folder name)
2. `cmg-seqviewer` (product name, shorter)
3. `seqviewer` (very short, may be taken)

Recommendation: **`cmg-seqviewer`** (matches product branding)

### GitHub Actions Costs
- **Free tier**: 2,000 minutes/month for private repos
- **Public repos**: Unlimited minutes
- Recommendation: Make repository **public** to avoid costs

### Pre-loaded Database Handling
The `database/` folder contains pre-loaded datasets:
- **Included in builds**: Users get example data
- **Size**: ~5-10 MB total
- **If too large**: Add `database/*.parquet` to .gitignore, regenerate on first run

---

## 🆘 Common Issues & Solutions

### Issue: Git push rejected
**Cause**: Remote has commits you don't have locally
**Solution**:
```powershell
git pull origin main --rebase
git push origin main
```

### Issue: Actions workflow not triggering
**Cause**: YAML syntax error or wrong trigger condition
**Solution**:
1. Check Actions tab for error messages
2. Validate YAML: https://www.yamllint.com/
3. Ensure tag starts with 'v': `v1.0.0` not `1.0.0`

### Issue: Build fails on specific platform
**Cause**: Platform-specific dependency issue
**Solution**:
1. Check workflow logs for error details
2. Add missing dependency to requirements.txt
3. Update hiddenimports in .spec file if needed

### Issue: Release not created despite successful builds
**Cause**: `if: startsWith(github.ref, 'refs/tags/')` condition not met
**Solution**:
- Ensure tag was pushed: `git push origin v1.0.0`
- Check that tag starts with 'v'
- Verify workflow permissions (Settings → Actions → General → Workflow permissions: Read and write)

---

## 📞 Getting Help

If issues arise during upload:
1. **Check GitHub Docs**: https://docs.github.com/
2. **Actions Troubleshooting**: https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows
3. **Community Forum**: https://github.community/
4. **Stack Overflow**: Tag `github-actions` or `pyinstaller`

---

## ✨ Success Criteria

Repository successfully uploaded when:
- ✅ All source code visible on GitHub
- ✅ README renders with correct formatting
- ✅ GitHub Actions workflow completes successfully
- ✅ Release v1.0.0 created with Windows + macOS executables
- ✅ Download links functional and executables run correctly
- ✅ Documentation accessible and links work

**Congratulations! Your project is now open source! 🎉**
