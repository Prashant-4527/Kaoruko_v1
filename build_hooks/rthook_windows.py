"""
build_hooks/rthook_windows.py

PyInstaller runtime hook — runs before any app code at startup.
Sets up the correct working directory, DLL search paths,
and asyncio policy for the bundled .exe.
"""
import os
import sys
import asyncio
import platform

# Set working directory to the bundle root
# (sys._MEIPASS for onefile, sys.executable dir for onedir)
if getattr(sys, "frozen", False):
    bundle_dir = os.path.dirname(sys.executable)
    os.chdir(bundle_dir)
    # Ensure bundled DLLs are found (sounddevice, ctranslate2, etc.)
    os.add_dll_directory(bundle_dir)

# Windows asyncio ProactorEventLoop is required for subprocess + audio I/O
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
