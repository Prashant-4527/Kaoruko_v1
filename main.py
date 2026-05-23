"""
╔══════════════════════════════════════════════════════════╗
║           KAORUKO — AI Desktop Voice Assistant           ║
║                    Entry Point                           ║
║                                                          ║
║  Version:  1.0.0                                         ║
║  Platform: Windows 10/11                                 ║
║  Python:   3.11+                                         ║
╚══════════════════════════════════════════════════════════╝
"""

import sys
import asyncio
import signal
import platform
from pathlib import Path

# ── Ensure project root is in path ─────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# ── Windows-specific: must be set before any Qt import ─────────────────────
if platform.system() == "Windows":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        pass
    import os
    os.system("")


def _check_python_version() -> None:
    if sys.version_info < (3, 11):
        print(
            f"[ERROR] Kaoruko requires Python 3.11+. "
            f"You are running Python {sys.version_info.major}.{sys.version_info.minor}."
        )
        sys.exit(1)


def _check_platform() -> None:
    if platform.system() != "Windows":
        print(
            "[WARNING] Kaoruko is designed for Windows. "
            "Some desktop-control features will be unavailable on this platform."
        )


def _bootstrap_environment() -> None:
    """Load .env file and validate critical environment variables."""
    from dotenv import load_dotenv
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _configure_asyncio() -> asyncio.AbstractEventLoop:
    """
    Create and configure the event loop.

    FIX: Was using deprecated asyncio.get_event_loop() which raises
    DeprecationWarning in Python 3.10+ and errors in 3.12+.
    Now explicitly creates a new loop with asyncio.new_event_loop().
    """
    if platform.system() == "Windows":
        # ProactorEventLoop for better subprocess + audio support
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def _handle_exception(exc_type, exc_value, exc_traceback) -> None:
    """Global unhandled exception handler — log before crash."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    try:
        from kaoruko.infrastructure.logging.logger import get_logger
        log = get_logger("main")
        log.critical(
            "Unhandled exception — Kaoruko is shutting down",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
    except Exception:
        import traceback
        traceback.print_exception(exc_type, exc_value, exc_traceback)


def main() -> int:
    """
    Kaoruko bootstrap sequence:
    1. Pre-flight checks
    2. Environment setup
    3. Event loop creation (explicit, not deprecated get_event_loop)
    4. Infrastructure init (logging, config, DB)
    5. Core systems init (event bus, assistant)
    6. UI launch (Qt application)
    """
    _check_python_version()
    _check_platform()
    _bootstrap_environment()

    # Create event loop BEFORE Qt (Qt may create its own threads)
    loop = _configure_asyncio()

    sys.excepthook = _handle_exception

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon

    app = QApplication(sys.argv)
    app.setApplicationName("Kaoruko")
    app.setApplicationDisplayName("Kaoruko — AI Assistant")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("KaorukoProject")
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    from kaoruko.infrastructure.logging.logger import setup_logging
    from kaoruko.infrastructure.config.config_manager import ConfigManager
    from kaoruko.infrastructure.telemetry.metrics import MetricsCollector

    setup_logging()
    from kaoruko.infrastructure.logging.logger import get_logger
    log = get_logger("bootstrap")

    log.info("kaoruko_starting", version="1.0.0", python=sys.version, platform=platform.system())

    config = ConfigManager.load(PROJECT_ROOT / "config" / "kaoruko.yaml")
    log.info("config_loaded", theme=config.ui.theme, ai_primary=config.ai.primary)

    metrics = MetricsCollector()
    metrics.start()

    # ── Initialise database (explicit loop, not deprecated get_event_loop) ──
    from kaoruko.memory.long_term import DatabaseManager
    db = DatabaseManager(PROJECT_ROOT / "data" / "kaoruko.db")
    loop.run_until_complete(db.initialize())
    log.info("database_ready")

    # ── Initialise core assistant ───────────────────────────────────────────
    from kaoruko.core.assistant import KaorukoAssistant
    assistant = KaorukoAssistant(
        config=config,
        db=db,
        metrics=metrics,
        project_root=PROJECT_ROOT,   # FIX: pass explicit root, no more Path.cwd()
    )

    # ── Launch UI ───────────────────────────────────────────────────────────
    from kaoruko.ui.app import KaorukoApp
    ui = KaorukoApp(assistant=assistant, config=config)
    ui.launch()

    # ── Setup graceful shutdown ─────────────────────────────────────────────
    def _shutdown(sig=None, frame=None):
        log.info("shutdown_requested", signal=str(sig))
        loop.run_until_complete(assistant.shutdown())
        metrics.stop()
        app.quit()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    log.info("kaoruko_ready", message="Hajimemashite~ I am ready.")
    exit_code = app.exec()

    log.info("kaoruko_stopped", exit_code=exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
