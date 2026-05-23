"""
tests/unit/test_plugin_manager.py

Tests for the PluginManager — loading, intent dispatch, enable/disable,
and the async handle_intent() contract.
"""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock


def _make_plugin_dir(tmp_path: Path, name: str, intent: str, response: str, manifest: bool = True):
    """Helper: create a minimal plugin package on disk."""
    plugin_dir = tmp_path / name
    plugin_dir.mkdir()

    init_code = f'''
from kaoruko.plugins.plugin_base import KaorukoPlugin
from typing import Any, Optional

class Plugin(KaorukoPlugin):
    name = "{name}"
    version = "1.0.0"
    intents = ["{intent}"]

    async def handle_intent(self, intent: str, entities: dict, session=None) -> Optional[str]:
        return "{response}"
'''
    (plugin_dir / "__init__.py").write_text(init_code)

    if manifest:
        import json
        manifest_data = {"name": name, "version": "1.0.0", "intents": [intent]}
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest_data))

    return plugin_dir


@pytest.fixture
def plugin_dir(tmp_path):
    return tmp_path / "plugins"


@pytest.fixture
def manager(plugin_dir, default_config, fresh_bus):
    from kaoruko.plugins.plugin_base import PluginManager
    plugin_dir.mkdir(exist_ok=True)
    return PluginManager(plugins_dir=plugin_dir, config=default_config, bus=fresh_bus)


@pytest.mark.asyncio
async def test_load_valid_plugin(manager, plugin_dir, default_config, fresh_bus):
    _make_plugin_dir(plugin_dir, "test_plugin", "TEST_INTENT", "test response")
    count = await manager.discover_and_load()
    assert count == 1
    assert len(manager) == 1


@pytest.mark.asyncio
async def test_get_handler_for_intent(manager, plugin_dir):
    _make_plugin_dir(plugin_dir, "weather_plugin", "GET_WEATHER", "It is sunny~")
    await manager.discover_and_load()

    plugin = manager.get_handler_for_intent("GET_WEATHER")
    assert plugin is not None
    assert plugin.name == "weather_plugin"


@pytest.mark.asyncio
async def test_get_handler_returns_none_for_unknown_intent(manager, plugin_dir):
    _make_plugin_dir(plugin_dir, "weather_plugin", "GET_WEATHER", "sunny")
    await manager.discover_and_load()

    plugin = manager.get_handler_for_intent("NON_EXISTENT")
    assert plugin is None


@pytest.mark.asyncio
async def test_async_handle_intent(manager, plugin_dir):
    _make_plugin_dir(plugin_dir, "cpu_plugin", "GET_CPU", "CPU is at 42%")
    await manager.discover_and_load()

    plugin = manager.get_handler_for_intent("GET_CPU")
    assert plugin is not None

    response = await manager.call_handle_intent(plugin, "GET_CPU", {})
    assert response == "CPU is at 42%"


@pytest.mark.asyncio
async def test_disable_plugin(manager, plugin_dir):
    _make_plugin_dir(plugin_dir, "disableable", "DISABLE_ME", "response")
    await manager.discover_and_load()

    manager.disable("disableable")
    plugin = manager.get_handler_for_intent("DISABLE_ME")
    assert plugin is None  # disabled plugin not returned


@pytest.mark.asyncio
async def test_enable_plugin_after_disable(manager, plugin_dir):
    _make_plugin_dir(plugin_dir, "toggle_plugin", "TOGGLE_INTENT", "toggled")
    await manager.discover_and_load()

    manager.disable("toggle_plugin")
    assert manager.get_handler_for_intent("TOGGLE_INTENT") is None

    manager.enable("toggle_plugin")
    assert manager.get_handler_for_intent("TOGGLE_INTENT") is not None


@pytest.mark.asyncio
async def test_get_all_intents(manager, plugin_dir):
    _make_plugin_dir(plugin_dir, "plugin_a", "INTENT_A", "a")
    _make_plugin_dir(plugin_dir, "plugin_b", "INTENT_B", "b")
    await manager.discover_and_load()

    intents = manager.get_all_intents()
    assert "INTENT_A" in intents
    assert "INTENT_B" in intents


@pytest.mark.asyncio
async def test_plugin_without_manifest_still_loads(manager, plugin_dir):
    _make_plugin_dir(plugin_dir, "no_manifest", "NO_MANIFEST_INTENT", "works", manifest=False)
    count = await manager.discover_and_load()
    assert count == 1


@pytest.mark.asyncio
async def test_list_plugins(manager, plugin_dir):
    _make_plugin_dir(plugin_dir, "list_me", "LIST_INTENT", "listed")
    await manager.discover_and_load()

    plugins = manager.list_plugins()
    assert len(plugins) == 1
    assert plugins[0]["name"] == "list_me"
    assert plugins[0]["enabled"] is True
