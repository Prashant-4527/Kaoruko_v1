"""
tests/conftest.py

Shared pytest fixtures and configuration.
"""
import asyncio
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def default_config():
    from kaoruko.infrastructure.config.schema import KaorukoConfig
    return KaorukoConfig()


@pytest.fixture
def rule_engine():
    from kaoruko.nlu.rule_engine import RuleEngine
    engine = RuleEngine()
    engine.load()
    return engine


@pytest.fixture
def lang_detector():
    from kaoruko.nlu.language_detector import LanguageDetector
    d = LanguageDetector()
    d.initialize()
    return d


@pytest.fixture
def fresh_bus():
    """Isolated EventBus for each test — not the global singleton."""
    from kaoruko.core.event_bus import EventBus
    return EventBus()


@pytest.fixture
def tmp_project_root(tmp_path):
    """Temporary project-like directory with data/ subdirectory."""
    (tmp_path / "data").mkdir()
    return tmp_path


@pytest.fixture
def mock_ai_router(default_config):
    """AIRouter with all network calls mocked out."""
    from kaoruko.intelligence.ai_router import AIRouter
    router = AIRouter(config=default_config, project_root=Path("/tmp"))
    router._internet_available = False  # force offline by default
    router._classify_with_ollama = AsyncMock(return_value={
        "intent": "CONV_CHAT",
        "entities": {},
        "confidence": 0.8,
        "action_plan": None,
        "response_text": "Hai~",
    })
    return router
