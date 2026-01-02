#!/bin/bash
# CMG-SeqViewer - macOS Build Script

set -e  # 에러 발생 시 중단

echo "======================================"
echo "CMG-SeqViewer - macOS Build Script"
echo "======================================"
echo ""

# 1. Clean previous build
echo "[1/5] Cleaning previous build..."
if [ -d "build" ]; then
    rm -rf build
    echo "  - Removed build directory"
fi
if [ -d "dist" ]; then
    rm -rf dist
    echo "  - Removed dist directory"
fi
echo ""

# 2. Check Python version
echo "[2/5] Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  ✓ Python $PYTHON_VERSION"
echo ""

# 3. Check dependencies
echo "[3/5] Checking dependencies..."
REQUIRED_PACKAGES=("PyQt6" "pandas" "numpy" "scipy" "openpyxl" "pyarrow" "matplotlib" "seaborn" "pyinstaller")
MISSING=0

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import ${package}" 2>/dev/null; then
        echo "  ✓ $package"
    else
        echo "  ✗ $package (NOT INSTALLED)"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "Some packages are missing. Install them first:"
    echo "  pip3 install -r requirements.txt"
    exit 1
fi

# Check database folder
if [ -d "database" ]; then
    DATASET_COUNT=$(ls -1 database/datasets/*.parquet 2>/dev/null | wc -l)
    echo "  ✓ database folder ($DATASET_COUNT datasets)"
else
    echo "  ⚠ database folder not found (no pre-loaded datasets)"
fi
echo ""

# 4. Check/Create icon
echo "[4/5] Checking icon..."
if [ ! -f "cmg-seqviewer.icns" ]; then
    echo "  ⚠ cmg-seqviewer.icns not found"
    echo "  Creating icon from PNG..."
    if [ -f "cmg-seqviewer.png" ]; then
        # PNG를 ICNS로 변환 (macOS)
        mkdir -p cmg-seqviewer.iconset
        sips -z 16 16     cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_16x16.png
        sips -z 32 32     cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_16x16@2x.png
        sips -z 32 32     cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_32x32.png
        sips -z 64 64     cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_32x32@2x.png
        sips -z 128 128   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_128x128.png
        sips -z 256 256   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_128x128@2x.png
        sips -z 256 256   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_256x256.png
        sips -z 512 512   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_256x256@2x.png
        sips -z 512 512   cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_512x512.png
        sips -z 1024 1024 cmg-seqviewer.png --out cmg-seqviewer.iconset/icon_512x512@2x.png
        iconutil -c icns cmg-seqviewer.iconset
        rm -rf cmg-seqviewer.iconset
        echo "  ✓ Created cmg-seqviewer.icns"
    else
        echo "  ⚠ cmg-seqviewer.png not found, building without icon"
    fi
else
    echo "  ✓ cmg-seqviewer.icns found"
fi
echo ""

# 5. Build application
echo "[5/5] Building application..."
echo "  This may take several minutes..."
pyinstaller --clean --noconfirm cmg-seqviewer-macos.spec

if [ $? -ne 0 ]; then
    echo ""
    echo "Build FAILED!"
    exit 1
fi
echo ""

# 6. Check output
echo "Checking output..."
if [ -d "dist/CMG-SeqViewer.app" ]; then
    echo "  ✓ Build successful!"
    echo ""
    echo "======================================"
    echo "Output location:"
    echo "  dist/CMG-SeqViewer.app"
    echo ""
    echo "To run the program:"
    echo "  open dist/CMG-SeqViewer.app"
    echo ""
    echo "To create DMG (optional):"
    echo "  hdiutil create -volname CMG-SeqViewer -srcfolder dist/CMG-SeqViewer.app -ov -format UDZO CMG-SeqViewer.dmg"
    echo "======================================"
else
    echo "  ✗ Build failed - output not found"
    exit 1
fi
