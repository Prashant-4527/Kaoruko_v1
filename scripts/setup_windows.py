"""
scripts/setup_windows.py

One-click Windows setup script for Kaoruko.
Handles:
  - Python version check
  - Virtual environment creation
  - Dependency installation
  - Playwright browser installation
  - spaCy model download
  - Directory structure verification
  - API key configuration
  - Desktop shortcut creation  (FIX: paths with spaces now quoted correctly)
  - First-run health check
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"{GREEN}  ✓  {msg}{RESET}")
def warn(msg): print(f"{YELLOW}  ⚠  {msg}{RESET}")
def err(msg):  print(f"{RED}  ✗  {msg}{RESET}")
def info(msg): print(f"{CYAN}  →  {msg}{RESET}")
def hdr(msg):  print(f"\n{BOLD}{CYAN}{msg}{RESET}")


def _run(cmd: list, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def _get_venv_python(venv_path: Path) -> Path:
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def main() -> int:
    os.system("")  # Enable ANSI on Windows

    print(f"""
{BOLD}{CYAN}
╔══════════════════════════════════════════════════════════╗
║       KAORUKO  —  Windows Setup Script                   ║
║       Elite AI Desktop Voice Assistant                   ║
╚══════════════════════════════════════════════════════════╝
{RESET}""")

    # 1. Platform check
    hdr("Step 1 · Platform Check")
    if platform.system() != "Windows":
        warn("Designed for Windows. Continuing anyway — some features will be limited.")
    else:
        ok(f"Windows {platform.version()}")

    # 2. Python version
    hdr("Step 2 · Python Version")
    if sys.version_info < (3, 11):
        err(f"Python 3.11+ required. Found: {sys.version}")
        err("Download from: https://www.python.org/downloads/")
        return 1
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # 3. Virtual environment
    hdr("Step 3 · Virtual Environment")
    venv_path = PROJECT_ROOT / ".venv"
    if not venv_path.exists():
        info("Creating virtual environment...")
        _run([sys.executable, "-m", "venv", str(venv_path)])
        ok("Virtual environment created")
    else:
        ok("Virtual environment already exists")

    python = _get_venv_python(venv_path)
    pip    = str(python)

    # 4. Upgrade pip
    hdr("Step 4 · Upgrade pip")
    _run([str(python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    ok("pip up to date")

    # 5. Install dependencies
    hdr("Step 5 · Install Dependencies")
    info("Installing from pyproject.toml (this may take 5–10 minutes)...")
    result = _run(
        [str(python), "-m", "pip", "install", "--quiet", "-e", f"{PROJECT_ROOT}[dev]"],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        warn(f"Some packages failed to install. Error: {result.stderr[:200]}")
        warn("You can retry manually: .venv\\Scripts\\pip install -e .[dev]")
    else:
        ok("All dependencies installed")

    # 6. Playwright browsers
    hdr("Step 6 · Playwright Browser")
    info("Installing Chromium for browser automation...")
    result = _run(
        [str(python), "-m", "playwright", "install", "chromium"],
        check=False, capture=True,
    )
    if result.returncode == 0:
        ok("Chromium installed")
    else:
        warn("Playwright install failed — browser control will be limited")

    # 7. spaCy model
    hdr("Step 7 · spaCy Language Model")
    result = _run(
        [str(python), "-m", "spacy", "download", "en_core_web_sm"],
        check=False, capture=True,
    )
    if result.returncode == 0:
        ok("spaCy English model installed")
    else:
        warn("spaCy model download failed — NLU may be degraded")

    # 8. Data directories
    hdr("Step 8 · Directory Structure")
    for subdir in ["data", "data/logs", "data/cache", "data/memory", "data/user"]:
        d = PROJECT_ROOT / subdir.replace("/", os.sep)
        d.mkdir(parents=True, exist_ok=True)
    ok("All directories ready")

    # 9. .env file
    hdr("Step 9 · Environment File")
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        env_content = (
            "# Kaoruko Environment Variables\n"
            "# API keys are stored encrypted via the secrets manager.\n\n"
            "LOG_LEVEL=INFO\n"
            "LOG_JSON=true\n"
            "LOG_CONSOLE=true\n"
            "KAORUKO_DEV=false\n"
        )
        env_path.write_text(env_content, encoding="utf-8")
        ok(".env created")
    else:
        ok(".env already exists")

    # 10. Desktop shortcut (Windows only) — FIX: paths with spaces quoted correctly
    if platform.system() == "Windows":
        hdr("Step 10 · Desktop Shortcut")
        try:
            import winshell
            from win32com.client import Dispatch

            desktop = Path(winshell.desktop())
            shortcut_path = desktop / "Kaoruko.lnk"

            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))

            # FIX: Targetpath and Arguments must handle paths containing spaces.
            # Previously: shortcut.Targetpath = str(python)  ← breaks with spaces
            # Now: use quoted string only when embedded in Arguments; Targetpath
            # itself does NOT need quotes in the COM API (it's a raw path property),
            # but WorkingDirectory must be the unquoted resolved root.
            shortcut.Targetpath       = str(python.resolve())  # raw path, no quotes
            shortcut.Arguments        = f'"{PROJECT_ROOT / "main.py"}"'  # quoted argument
            shortcut.WorkingDirectory = str(PROJECT_ROOT.resolve())       # no quotes
            shortcut.Description      = "Kaoruko AI Desktop Assistant"
            shortcut.save()
            ok(f"Desktop shortcut created → {shortcut_path}")
        except ImportError:
            info("Install 'winshell' to create a desktop shortcut (optional)")
        except Exception as e:
            warn(f"Shortcut creation failed: {e}")

    # 11. Health check
    hdr("Step 11 · Health Check")
    checks = [
        ("PyQt6",           "from PyQt6.QtWidgets import QApplication"),
        ("faster-whisper",  "import faster_whisper"),
        ("edge-tts",        "import edge_tts"),
        ("SQLAlchemy",      "import sqlalchemy"),
        ("pydantic",        "import pydantic"),
        ("structlog",       "import structlog"),
        ("sounddevice",     "import sounddevice"),
        ("anthropic",       "import anthropic"),
        ("cryptography",    "from cryptography.fernet import Fernet"),
    ]
    for name, stmt in checks:
        res = _run([str(python), "-c", stmt], check=False, capture=True)
        if res.returncode == 0:
            ok(name)
        else:
            warn(f"{name} — not installed (some features may be limited)")

    # Summary
    main_py = PROJECT_ROOT / "main.py"
    print(f"""
{BOLD}{GREEN}
╔══════════════════════════════════════════════════════════╗
║               Setup Complete!                            ║
╚══════════════════════════════════════════════════════════╝
{RESET}
  To start Kaoruko:

    {CYAN}.venv\\Scripts\\python main.py{RESET}

  Or double-click the Desktop shortcut (if created).

  First run will download the Whisper model (~140MB for 'base').
  This only happens once.

  Wake words: {CYAN}"Hey Kaoruko"{RESET}  or  {CYAN}"Kaoruko"{RESET}
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
