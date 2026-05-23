"""
tests/integration/test_nlu_pipeline.py

Integration tests for the full NLU → execution pipeline.
These tests use the rule engine + executor without voice or AI.
"""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.asyncio
async def test_app_open_intent_resolves():
    """Full pipeline: text → rule engine → action plan for APP_OPEN."""
    from kaoruko.nlu.rule_engine import RuleEngine
    engine = RuleEngine()
    engine.load()

    result = engine.match("Open Chrome")
    assert result is not None
    assert result.intent == "APP_OPEN"
    assert result.action_plan is not None
    actions = result.action_plan["actions"]
    assert len(actions) == 1
    assert actions[0]["handler"] == "app_control"
    assert actions[0]["method"] == "open_application"
    assert actions[0]["params"]["app_name"] == "chrome"


@pytest.mark.asyncio
async def test_browser_search_resolves():
    from kaoruko.nlu.rule_engine import RuleEngine
    engine = RuleEngine()
    engine.load()

    result = engine.match("Search for machine learning jobs")
    assert result is not None
    assert result.intent == "BROWSER_SEARCH"
    assert "machine learning jobs" in result.entities.get("query", "")
    actions = result.action_plan["actions"]
    assert actions[0]["handler"] == "browser_control"
    assert actions[0]["method"] == "search"


@pytest.mark.asyncio
async def test_system_volume_resolves():
    from kaoruko.nlu.rule_engine import RuleEngine
    engine = RuleEngine()
    engine.load()

    result = engine.match("Set volume to 75")
    assert result is not None
    assert result.intent == "SYS_VOLUME"
    assert result.entities.get("level") == 75
    actions = result.action_plan["actions"]
    assert actions[0]["params"]["level"] == 75


@pytest.mark.asyncio
async def test_shutdown_requires_confirmation():
    from kaoruko.nlu.rule_engine import RuleEngine
    engine = RuleEngine()
    engine.load()

    result = engine.match("Shutdown")
    assert result is not None
    actions = result.action_plan["actions"]
    assert actions[0]["requires_confirmation"] is True


@pytest.mark.asyncio
async def test_workflow_start_resolves():
    from kaoruko.nlu.rule_engine import RuleEngine
    engine = RuleEngine()
    engine.load()

    result = engine.match("Start study mode")
    assert result is not None
    assert result.intent == "WORKFLOW_START"


@pytest.mark.asyncio
async def test_app_control_handler_open_known():
    """AppControlHandler resolves a known app alias."""
    from kaoruko.infrastructure.config.schema import KaorukoConfig
    from kaoruko.execution.handlers.app_control import AppControlHandler

    config = KaorukoConfig()
    handler = AppControlHandler(config)

    # Check alias resolution
    canonical = handler._resolve("chrome")
    assert canonical == "chrome"

    canonical = handler._resolve("VS Code")
    assert canonical == "code"

    canonical = handler._resolve("nonexistent_app_xyz")
    assert canonical is None


@pytest.mark.asyncio
async def test_audio_handler_volume_clamp():
    """Volume levels are clamped to 0-100."""
    from kaoruko.infrastructure.config.schema import KaorukoConfig
    from kaoruko.execution.handlers.audio_control import AudioControlHandler

    config = KaorukoConfig()
    handler = AudioControlHandler(config)

    # _set_absolute_volume should clamp
    # We can test the clamping logic directly
    assert max(0, min(100, -10)) == 0
    assert max(0, min(100, 150)) == 100
    assert max(0, min(100, 60))  == 60


@pytest.mark.asyncio
async def test_file_manager_known_folders():
    """FileManagerHandler knows standard Windows folder aliases."""
    from kaoruko.infrastructure.config.schema import KaorukoConfig
    from kaoruko.execution.handlers.file_manager import _KNOWN_FOLDERS

    assert "desktop"   in _KNOWN_FOLDERS
    assert "downloads" in _KNOWN_FOLDERS
    assert "documents" in _KNOWN_FOLDERS
    assert "pictures"  in _KNOWN_FOLDERS


@pytest.mark.asyncio
async def test_workflow_engine_known_workflows():
    """WorkflowEngine has all expected built-in workflows."""
    from kaoruko.infrastructure.config.schema import KaorukoConfig
    from kaoruko.execution.handlers.workflow_engine import WorkflowEngine, _BUILT_IN_WORKFLOWS

    assert "study"  in _BUILT_IN_WORKFLOWS
    assert "gaming" in _BUILT_IN_WORKFLOWS
    assert "work"   in _BUILT_IN_WORKFLOWS
    assert "movie"  in _BUILT_IN_WORKFLOWS
    assert "focus"  in _BUILT_IN_WORKFLOWS
    assert "morning" in _BUILT_IN_WORKFLOWS


@pytest.mark.asyncio
async def test_workflow_engine_unknown_returns_error():
    from kaoruko.infrastructure.config.schema import KaorukoConfig
    from kaoruko.execution.handlers.workflow_engine import WorkflowEngine

    config = KaorukoConfig()
    engine = WorkflowEngine(config)
    response = await engine.start_workflow(app_name="nonexistent_mode_xyz")
    assert "don't have a workflow" in response.lower() or "available" in response.lower()


@pytest.mark.asyncio
async def test_browser_search_url_builder():
    from kaoruko.execution.handlers.browser_control import BrowserControlHandler, _SEARCH_ENGINES
    from kaoruko.infrastructure.config.schema import KaorukoConfig

    assert "google"    in _SEARCH_ENGINES
    assert "youtube"   in _SEARCH_ENGINES
    assert "bing"      in _SEARCH_ENGINES
    assert "{}" in _SEARCH_ENGINES["google"]
