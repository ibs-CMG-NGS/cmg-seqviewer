# macOS Installation & Troubleshooting Guide

## 📦 Installation

### Method 1: Download from Releases (Recommended)

1. Go to [Releases](https://github.com/ibs-CMG-NGS/cmg-seqviewer/releases)
2. Download `CMG-SeqViewer-macOS.dmg`
3. Double-click the DMG file to mount it
4. **Drag `CMG-SeqViewer.app` to the `Applications` folder** (shortcut visible in DMG window)
   - If you don't see an Applications shortcut, manually copy to `/Applications`

#### If DMG only shows the app icon (v1.0.3 and earlier):

**Temporary workaround** until v1.0.5 is released:

```bash
# 1. Mount the DMG (double-click or use command)
hdiutil attach ~/Downloads/CMG-SeqViewer-macOS.dmg

# 2. Copy app to Applications
sudo cp -R "/Volumes/CMG-SeqViewer/CMG-SeqViewer.app" /Applications/

# 3. Unmount DMG
hdiutil detach /Volumes/CMG-SeqViewer

# 4. Remove quarantine
xattr -cr /Applications/CMG-SeqViewer.app
```

Or simply run from the mounted DMG:
```bash
# Remove quarantine from mounted app
xattr -cr "/Volumes/CMG-SeqViewer/CMG-SeqViewer.app"

# Run directly
open "/Volumes/CMG-SeqViewer/CMG-SeqViewer.app"
```

---

## 🚀 First Launch

### If you see "cannot be opened because the developer cannot be verified"

This is normal for unsigned applications. Follow these steps:

#### Option 1: Right-Click Method (Easiest)
1. **Right-click** (or Control+Click) on `CMG-SeqViewer.app`
2. Select **"Open"** from the menu
3. Click **"Open"** in the security dialog
4. The app will now launch (only needed once)

#### Option 2: Security & Privacy Settings
1. Try to open the app (double-click)
2. Go to **System Preferences** → **Security & Privacy** → **General**
3. You'll see a message: *"CMG-SeqViewer.app was blocked"*
4. Click **"Open Anyway"**
5. Confirm by clicking **"Open"**

#### Option 3: Terminal Command (Advanced)
```bash
# Remove quarantine attribute
xattr -cr /Applications/CMG-SeqViewer.app

# Or if in Downloads
xattr -cr ~/Downloads/CMG-SeqViewer.app
```

---

## 🐛 Troubleshooting

### App doesn't respond when double-clicked

**Symptoms**: No window appears, no error message

**Solutions**:

1. **Check Console for errors**:
   - Open **Console.app** (in Applications → Utilities)
   - Search for "CMG-SeqViewer"
   - Look for error messages

2. **Run from Terminal to see errors**:
   ```bash
   # Navigate to the app
   cd /Applications/CMG-SeqViewer.app/Contents/MacOS
   
   # Run executable directly
   ./CMG-SeqViewer
   ```
   
   This will show error messages in the terminal.

3. **Check Python dependencies**:
   ```bash
   # The app is self-contained, but verify
   /Applications/CMG-SeqViewer.app/Contents/MacOS/CMG-SeqViewer --version
   ```

4. **Verify app permissions**:
   ```bash
   # Check if executable has proper permissions
   ls -l /Applications/CMG-SeqViewer.app/Contents/MacOS/CMG-SeqViewer
   
   # Should show: -rwxr-xr-x (executable permissions)
   ```

5. **Reset quarantine flags**:
   ```bash
   # Remove all extended attributes
   xattr -cr /Applications/CMG-SeqViewer.app
   
   # Verify removal
   xattr -l /Applications/CMG-SeqViewer.app
   # Should show no output
   ```

---

### "damaged and can't be opened" error

**Cause**: macOS Gatekeeper blocking unsigned apps

**Solution**:
```bash
# Remove quarantine
xattr -cr /Applications/CMG-SeqViewer.app

# If that doesn't work, bypass Gatekeeper temporarily
sudo spctl --master-disable  # Disable Gatekeeper
# Then open the app
sudo spctl --master-enable   # Re-enable Gatekeeper
```

**Note**: Only disable Gatekeeper temporarily and re-enable immediately after.

---

### Console shows "Library not loaded" errors

**Symptom**: Error messages about missing `.dylib` files

**Cause**: PyInstaller missed some dependencies

**Solution**: Run from source instead:
```bash
# Clone repository
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python src/main.py
```

---

### App opens but crashes immediately

**Check logs**:
```bash
# System logs
log show --predicate 'process == "CMG-SeqViewer"' --last 5m

# Or application logs (if app creates them)
ls ~/Library/Logs/CMG-SeqViewer/
```

**Common issues**:
1. **Missing database folder**: Download internal build from organization
2. **Qt platform plugin error**: Reinstall from DMG
3. **Permission issues**: Check file permissions

---

## 🔧 Advanced Debugging

### Enable Debug Mode

If the app has a console version:
```bash
# Run with debug output
/Applications/CMG-SeqViewer.app/Contents/MacOS/CMG-SeqViewer --debug
```

### Check App Bundle Structure

```bash
# Verify app structure
ls -R /Applications/CMG-SeqViewer.app/Contents/

# Should contain:
# MacOS/CMG-SeqViewer (executable)
# Resources/ (icons, etc.)
# Frameworks/ (Qt libraries)
# _internal/ (Python packages)
```

### Inspect Info.plist

```bash
# View bundle info
plutil -p /Applications/CMG-SeqViewer.app/Contents/Info.plist
```

---

## 🍎 macOS Compatibility

### Minimum Requirements
- **macOS**: 10.14 (Mojave) or later
- **Architecture**: Intel (x86_64) or Apple Silicon (arm64)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Disk Space**: 500 MB

### Tested Versions
- ✅ macOS 14 Sonoma
- ✅ macOS 13 Ventura
- ✅ macOS 12 Monterey
- ✅ macOS 11 Big Sur
- ⚠️ macOS 10.15 Catalina (may require Rosetta 2 on M1)
- ⚠️ macOS 10.14 Mojave (minimum supported)

---

## 📝 Reporting Issues

If the app still doesn't work, please report an issue with:

1. **macOS version**: `sw_vers`
2. **Architecture**: `uname -m`
3. **Console output**: From Terminal run method above
4. **System logs**: `log show --predicate 'process == "CMG-SeqViewer"' --last 5m`
5. **Error screenshot** (if any)

**Report at**: https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues

---

## 🔒 Security Notes

### Why is the app unsigned?

This is an open-source academic tool. Code signing requires:
- Apple Developer account ($99/year)
- Notarization process with Apple

For trusted environments (research labs), unsigned apps are acceptable.

### Is it safe?

- ✅ Source code is publicly available
- ✅ Built via GitHub Actions (transparent process)
- ✅ No network access required
- ✅ Works offline

You can verify by:
1. Checking the source code on GitHub
2. Building from source yourself
3. Scanning with antivirus (should be clean)

---

## 🆘 Still Having Issues?

### Alternative: Run from Source

Most reliable method for macOS:

```bash
# 1. Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python
brew install python@3.11

# 3. Clone and run
git clone https://github.com/ibs-CMG-NGS/cmg-seqviewer.git
cd cmg-seqviewer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

### Create Launcher

Make a simple launcher script:

```bash
#!/bin/bash
# Save as ~/cmg-seqviewer-launcher.sh

cd ~/cmg-seqviewer
source venv/bin/activate
python src/main.py
```

Make it executable:
```bash
chmod +x ~/cmg-seqviewer-launcher.sh
```

Run:
```bash
~/cmg-seqviewer-launcher.sh
```

---

## 📞 Support

- **Documentation**: [docs/](../docs/)
- **Issues**: [GitHub Issues](https://github.com/ibs-CMG-NGS/cmg-seqviewer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ibs-CMG-NGS/cmg-seqviewer/discussions)
