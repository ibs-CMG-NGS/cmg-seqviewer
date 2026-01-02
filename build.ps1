# RNA-Seq Data Viewer - Build Script
# This script creates an executable file using PyInstaller

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "CMG-SeqViewer - Build Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 1. Clean previous build
Write-Host "[1/4] Cleaning previous build..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "  - Removed build directory" -ForegroundColor Green
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
    Write-Host "  - Removed dist directory" -ForegroundColor Green
}
Write-Host ""

# 2. Check dependencies
Write-Host "[2/4] Checking dependencies..." -ForegroundColor Yellow
$packages = @("PyQt6", "pandas", "numpy", "scipy", "openpyxl", "pyarrow", "matplotlib", "seaborn", "pyinstaller")
foreach ($package in $packages) {
    $installed = pip show $package 2>$null
    if ($installed) {
        Write-Host "  ✓ $package" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $package (NOT INSTALLED)" -ForegroundColor Red
        $missing = $true
    }
}

if ($missing) {
    Write-Host ""
    Write-Host "Some packages are missing. Install them first:" -ForegroundColor Red
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Check database folder
if (Test-Path "database") {
    $datasetCount = (Get-ChildItem "database\datasets\*.parquet" -ErrorAction SilentlyContinue).Count
    Write-Host "  ✓ database folder ($datasetCount datasets)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ database folder not found (no pre-loaded datasets)" -ForegroundColor Yellow
}
Write-Host ""

# 3. Build executable
Write-Host "[3/4] Building executable..." -ForegroundColor Yellow
Write-Host "  This may take several minutes..." -ForegroundColor Gray
pyinstaller --clean --noconfirm rna-seq-viewer.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Build FAILED!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 4. Check output
Write-Host "[4/4] Checking output..." -ForegroundColor Yellow
if (Test-Path "dist\CMG-SeqViewer") {
    Write-Host "  ✓ Build successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Output location:" -ForegroundColor Cyan
    Write-Host "  dist\CMG-SeqViewer\" -ForegroundColor White
    Write-Host ""
    Write-Host "To run the program:" -ForegroundColor Cyan
    Write-Host "  .\dist\CMG-SeqViewer\CMG-SeqViewer.exe" -ForegroundColor White
    Write-Host "======================================" -ForegroundColor Cyan
} else {
    Write-Host "  ✗ Build failed - output not found" -ForegroundColor Red
    exit 1
}
