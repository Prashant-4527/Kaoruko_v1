"""
build_hooks/hook-kaoruko.py

PyInstaller hook for the kaoruko package.
Ensures all subpackages and data files are collected.
"""
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("kaoruko")
datas = collect_data_files("kaoruko")
