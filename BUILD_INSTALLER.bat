@echo off
:: ============================================================
::  Kaoruko — Inno Setup Installer Builder
::  Requires: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
::  Run AFTER BUILD.bat has completed successfully.
:: ============================================================

if not exist "dist\Kaoruko\Kaoruko.exe" (
    echo [ERROR] Run BUILD.bat first to create dist\Kaoruko\Kaoruko.exe
    exit /b 1
)

where iscc >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Inno Setup compiler (iscc.exe) not found in PATH.
    echo Download from: https://jrsoftware.org/isdl.php
    exit /b 1
)

echo Building installer...
iscc kaoruko_installer.iss
if errorlevel 1 (
    echo [ERROR] Installer build failed.
    exit /b 1
)
echo.
echo Installer created: dist\Kaoruko_Setup_1.0.0.exe
