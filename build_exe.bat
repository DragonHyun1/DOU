@echo off
REM DoU Auto Test Toolkit - Build Script for Windows
REM This script builds the application into a standalone executable

echo ========================================
echo DoU Auto Test Toolkit - Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo [1/5] Checking/Installing PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
) else (
    echo PyInstaller is already installed
)

echo.
echo [2/5] Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

echo.
echo [3/5] Building executable with PyInstaller...
pyinstaller build_exe.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo [4/5] Verifying build...
if exist "dist\DoU_Auto_Test_Toolkit\DoU_Auto_Test_Toolkit.exe" (
    echo Build successful!
    echo.
    echo Executable location: dist\DoU_Auto_Test_Toolkit\
) else (
    echo ERROR: Executable was not created!
    pause
    exit /b 1
)

echo.
echo [5/5] Creating README for distribution...
(
echo DoU Auto Test Toolkit - Standalone Application
echo ================================================
echo.
echo REQUIREMENTS:
echo - NI-DAQmx drivers must be installed separately
echo   Download from: https://www.ni.com/en-us/support/downloads/drivers/download.ni-daqmx.html
echo.
echo - ADB (Android Debug Bridge) for Android device control
echo   Usually included with Android SDK Platform Tools
echo.
echo RUNNING THE APPLICATION:
echo 1. Make sure NI-DAQmx drivers are installed
echo 2. Double-click DoU_Auto_Test_Toolkit.exe
echo 3. Connect your devices (Power Monitor, DAQ, Android device)
echo 4. Start testing!
echo.
echo TROUBLESHOOTING:
echo - If the application doesn't start, run it from command line to see error messages
echo - Make sure all hardware drivers are properly installed
echo - Check that devices are properly connected
echo.
echo For more information, see the docs folder in the source repository.
) > "dist\DoU_Auto_Test_Toolkit\README.txt"

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo The executable and required files are in:
echo   dist\DoU_Auto_Test_Toolkit\
echo.
echo You can now distribute this entire folder.
echo.
echo IMPORTANT NOTES:
echo - Users must install NI-DAQmx drivers separately
echo - The entire folder must be distributed together
echo - Do not separate the .exe from the other files
echo.
pause
