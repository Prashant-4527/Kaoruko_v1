@echo off
:: ============================================================
::  Kaoruko — Windows EXE Builder
::  Run this from the project root on Windows.
::  Output: dist\Kaoruko\Kaoruko.exe
:: ============================================================
setlocal enabledelayedexpansion

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  KAORUKO  -  Windows EXE Build                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: Check for virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo  [ERROR] Virtual environment not found.
    echo  Run:  python scripts\setup_windows.py
    exit /b 1
)

set PYTHON=.venv\Scripts\python.exe
set PIP=.venv\Scripts\pip.exe

:: Install PyInstaller if not present
echo  [1/5] Checking PyInstaller...
%PYTHON% -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo  Installing PyInstaller...
    %PIP% install --quiet pyinstaller pyinstaller-hooks-contrib
)
echo  PyInstaller ready.

:: Install UPX (optional, compresses EXE)
echo  [2/5] Checking UPX (optional compression)...
where upx >nul 2>&1
if errorlevel 1 (
    echo  UPX not found - skipping compression (EXE will be larger but still works)
) else (
    echo  UPX found - will compress output
)

:: Clean previous build
echo  [3/5] Cleaning previous build...
if exist "dist\Kaoruko" rmdir /s /q "dist\Kaoruko"
if exist "build\Kaoruko"  rmdir /s /q "build\Kaoruko"
echo  Clean done.

:: Build
echo  [4/5] Building EXE (this may take 3-8 minutes)...
%PYTHON% -m PyInstaller kaoruko.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed. Check the output above for details.
    exit /b 1
)

:: Verify output
echo  [5/5] Verifying output...
if not exist "dist\Kaoruko\Kaoruko.exe" (
    echo  [ERROR] Kaoruko.exe not found in dist\Kaoruko\
    exit /b 1
)

:: Print bundle size
for /f "tokens=*" %%A in ('dir /s /b "dist\Kaoruko\" ^| find /c /v ""') do set FILE_COUNT=%%A
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  Build Successful!                                       ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Output:  dist\Kaoruko\Kaoruko.exe
echo  Files:   !FILE_COUNT! total
echo.
echo  To run:  dist\Kaoruko\Kaoruko.exe
echo  To distribute: zip the entire dist\Kaoruko\ folder
echo.

endlocal
