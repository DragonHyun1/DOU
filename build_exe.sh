#!/bin/bash
# DoU Auto Test Toolkit - Build Script for Linux/Mac
# This script builds the application into a standalone executable

set -e  # Exit on error

echo "========================================"
echo "DoU Auto Test Toolkit - Build Script"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[1/5] Checking/Installing PyInstaller..."
if ! python3 -m pip show pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    python3 -m pip install pyinstaller
else
    echo "PyInstaller is already installed"
fi

echo ""
echo "[2/5] Cleaning previous build..."
rm -rf build dist

echo ""
echo "[3/5] Building executable with PyInstaller..."
python3 -m PyInstaller build_exe.spec --clean --noconfirm

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Build failed!"
    exit 1
fi

echo ""
echo "[4/5] Verifying build..."
if [ -f "dist/DoU_Auto_Test_Toolkit/DoU_Auto_Test_Toolkit" ]; then
    echo "Build successful!"
    echo ""
    echo "Executable location: dist/DoU_Auto_Test_Toolkit/"
else
    echo "ERROR: Executable was not created!"
    exit 1
fi

echo ""
echo "[5/5] Creating README for distribution..."
cat > "dist/DoU_Auto_Test_Toolkit/README.txt" << 'EOF'
DoU Auto Test Toolkit - Standalone Application
================================================

REQUIREMENTS:
- NI-DAQmx drivers must be installed separately
  Download from: https://www.ni.com/en-us/support/downloads/drivers/download.ni-daqmx.html

- ADB (Android Debug Bridge) for Android device control
  Usually included with Android SDK Platform Tools

RUNNING THE APPLICATION:
1. Make sure NI-DAQmx drivers are installed
2. Run ./DoU_Auto_Test_Toolkit
3. Connect your devices (Power Monitor, DAQ, Android device)
4. Start testing!

TROUBLESHOOTING:
- If the application doesn't start, run it from terminal to see error messages
- Make sure all hardware drivers are properly installed
- Check that devices are properly connected

For more information, see the docs folder in the source repository.
EOF

echo ""
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo ""
echo "The executable and required files are in:"
echo "  dist/DoU_Auto_Test_Toolkit/"
echo ""
echo "You can now distribute this entire folder."
echo ""
echo "IMPORTANT NOTES:"
echo "- Users must install NI-DAQmx drivers separately"
echo "- The entire folder must be distributed together"
echo "- Do not separate the executable from the other files"
echo ""
