"""
tests/unit/test_config.py
"""
import pytest
import tempfile
from pathlib import Path

from kaoruko.infrastructure.config.schema import KaorukoConfig
from kaoruko.infrastructure.config.config_manager import ConfigManager


def test_default_config():
    config = KaorukoConfig()
    assert config.assistant.name == "Kaoruko"
    assert config.ui.theme.value == "cyber_purple"
    assert config.voice.wake_word.enabled is True
    assert len(config.voice.wake_word.phrases) >= 1
    assert config.ai.primary.value == "claude"


def test_config_loads_from_yaml():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config" / "kaoruko.yaml"
        config = ConfigManager.load(path)
        assert isinstance(config, KaorukoConfig)
        assert config.assistant.name == "Kaoruko"


def test_config_to_safe_dict():
    config = KaorukoConfig()
    d = config.to_safe_dict()
    assert "security" in d
    # Pin hash should be masked
    if d["security"].get("pin_hash"):
        assert d["security"]["pin_hash"] == "***"


"""
tests/unit/test_state_machine.py
"""
import asyncio
import pytest
from kaoruko.core.state_machine import StateMachine, AssistantState


@pytest.mark.asyncio
async def test_initial_state():
    sm = StateMachine()
    assert sm.state == AssistantState.INITIALIZING


@pytest.mark.asyncio
async def test_valid_transition():
    sm = StateMachine()
    ok = await sm.transition(AssistantState.IDLE)
    assert ok is True
    assert sm.state == AssistantState.IDLE


@pytest.mark.asyncio
async def test_invalid_transition():
    sm = StateMachine()
    # Can't go from INITIALIZING directly to SPEAKING
    ok = await sm.transition(AssistantState.SPEAKING)
    assert ok is False
    assert sm.state == AssistantState.INITIALIZING


@pytest.mark.asyncio
async def test_full_pipeline_transitions():
    sm = StateMachine()
    assert await sm.transition(AssistantState.IDLE)
    assert await sm.transition(AssistantState.LISTENING)
    assert await sm.transition(AssistantState.PROCESSING)
    assert await sm.transition(AssistantState.SPEAKING)
    assert await sm.transition(AssistantState.IDLE)
    assert sm.state == AssistantState.IDLE


@pytest.mark.asyncio
async def test_is_busy():
    sm = StateMachine()
    await sm.transition(AssistantState.IDLE)
    assert sm.is_busy() is False
    await sm.transition(AssistantState.LISTENING)
    assert sm.is_busy() is True


@pytest.mark.asyncio
async def test_can_wake():
    sm = StateMachine()
    await sm.transition(AssistantState.IDLE)
    assert sm.can_wake() is True
    await sm.transition(AssistantState.LISTENING)
    assert sm.can_wake() is False


@pytest.mark.asyncio
async def test_callback_on_transition():
    sm = StateMachine()
    events = []
    sm.on_transition(lambda old, new: events.append((old, new)))
    await sm.transition(AssistantState.IDLE)
    assert len(events) == 1
    assert events[0] == (AssistantState.INITIALIZING, AssistantState.IDLE)


"""
tests/unit/test_session.py
"""
import pytest
from kaoruko.core.session import Session, SessionManager, Turn


def test_session_add_turn():
    s = Session()
    t = Turn(role="user", text="Open Chrome", intent="APP_OPEN",
             entities={"app_name": "chrome"})
    s.add_turn(t)
    assert len(s.turns) == 1
    assert s.active_intent == "APP_OPEN"
    assert s.last_app_mentioned == "chrome"


def test_session_context_browser():
    s = Session()
    s.add_turn(Turn(role="user", text="Open Chrome",
                    intent="APP_OPEN", entities={"app_name": "chrome"}))
    # Follow-up: search without specifying browser
    resolved = s.resolve_context("Search for jobs", {})
    assert resolved.get("_context_app") == "chrome"


def test_session_to_history_messages():
    s = Session()
    s.add_turn(Turn(role="user", text="Hello"))
    s.add_turn(Turn(role="assistant", text="Hi there~"))
    msgs = s.to_history_messages()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


def test_session_manager_lifecycle():
    mgr = SessionManager()
    s1 = mgr.start_session()
    assert mgr.current() == s1
    s2 = mgr.start_session()
    assert mgr.current() == s2
    assert s1 != s2


"""
tests/unit/test_secrets_manager.py
"""
import pytest
import tempfile
from pathlib import Path
from kaoruko.security.secrets_manager import SecretsManager


def test_store_and_get():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SecretsManager(Path(tmp))
        mgr.store("test_key", "test_value_12345")
        val = mgr.get("test_key")
        assert val == "test_value_12345"


def test_list_keys():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SecretsManager(Path(tmp))
        mgr.store("key_a", "value_a")
        mgr.store("key_b", "value_b")
        keys = mgr.list_keys()
        assert "key_a" in keys
        assert "key_b" in keys


def test_delete():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SecretsManager(Path(tmp))
        mgr.store("to_delete", "temporary")
        assert mgr.get("to_delete") == "temporary"
        mgr.delete("to_delete")
        assert mgr.get("to_delete") is None


def test_get_missing_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SecretsManager(Path(tmp))
        assert mgr.get("nonexistent") is None


def test_persistence_across_instances():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        mgr1 = SecretsManager(p)
        mgr1.store("persistent_key", "persistent_value")

        # New instance, same directory
        mgr2 = SecretsManager(p)
        assert mgr2.get("persistent_key") == "persistent_value"
