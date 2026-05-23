"""
tests/unit/test_executor.py

Tests for the Executor — action dispatch, sequential/parallel modes,
empty plans, missing handlers, confirmation gate bypass, and response building.
All actual handlers are mocked.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_bus():
    from kaoruko.core.event_bus import EventBus, KaorukoEvent
    bus = MagicMock(spec=EventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def mock_config(default_config):
    default_config.security.confirm_destructive = True
    return default_config


@pytest.fixture
def executor(mock_config, mock_bus, tmp_path):
    """Executor with a real registry, but all handlers stubbed."""
    from kaoruko.execution.executor import Executor
    from kaoruko.memory.memory_manager import MemoryManager

    memory = MagicMock(spec=MemoryManager)
    memory.remember = AsyncMock()

    with patch("kaoruko.execution.registry.HandlerRegistry.register_all"):
        exc = Executor(config=mock_config, bus=mock_bus, memory=memory)

    # Inject a mock handler
    mock_handler = MagicMock()
    mock_handler.open_app = AsyncMock(return_value="Opening Chrome~")
    mock_handler.shutdown = AsyncMock(return_value="Shutting down~")
    exc._registry.register("app_control", mock_handler)

    return exc


@pytest.mark.asyncio
async def test_empty_action_plan_is_no_op(executor, mock_bus):
    await executor.execute({"actions": [], "execution_mode": "sequential"})
    # Should not publish any action events for empty plan
    for call in mock_bus.publish.call_args_list:
        args = call[0]
        assert "action_started" not in str(args[0])


@pytest.mark.asyncio
async def test_sequential_single_action_success(executor, mock_bus):
    from kaoruko.core.event_bus import KaorukoEvent
    plan = {
        "actions": [{"handler": "app_control", "method": "open_app", "params": {"app_name": "chrome"}}],
        "execution_mode": "sequential",
    }
    await executor.execute(plan)

    published_events = [call[0][0] for call in mock_bus.publish.call_args_list]
    assert KaorukoEvent.EXEC_ACTION_SUCCESS in published_events


@pytest.mark.asyncio
async def test_handler_not_found_publishes_failure(executor, mock_bus):
    from kaoruko.core.event_bus import KaorukoEvent
    plan = {
        "actions": [{"handler": "nonexistent_handler", "method": "do_thing", "params": {}}],
        "execution_mode": "sequential",
    }
    await executor.execute(plan)

    published_events = [call[0][0] for call in mock_bus.publish.call_args_list]
    assert KaorukoEvent.EXEC_ACTION_FAILED in published_events


@pytest.mark.asyncio
async def test_method_not_found_publishes_failure(executor, mock_bus):
    from kaoruko.core.event_bus import KaorukoEvent
    plan = {
        "actions": [{"handler": "app_control", "method": "nonexistent_method", "params": {}}],
        "execution_mode": "sequential",
    }
    await executor.execute(plan)

    published_events = [call[0][0] for call in mock_bus.publish.call_args_list]
    assert KaorukoEvent.EXEC_ACTION_FAILED in published_events


@pytest.mark.asyncio
async def test_confirmation_required_and_denied_cancels(executor, mock_bus):
    from kaoruko.core.event_bus import KaorukoEvent

    executor._confirmation.ask = AsyncMock(return_value=False)

    plan = {
        "actions": [{
            "handler": "app_control", "method": "shutdown",
            "params": {}, "requires_confirmation": True,
        }],
        "execution_mode": "sequential",
    }
    await executor.execute(plan)

    published_events = [call[0][0] for call in mock_bus.publish.call_args_list]
    assert KaorukoEvent.EXEC_ACTION_CANCELLED in published_events

    # Handler was NOT called
    executor._registry.get("app_control").shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_confirmation_required_and_confirmed_proceeds(executor, mock_bus):
    from kaoruko.core.event_bus import KaorukoEvent

    executor._confirmation.ask = AsyncMock(return_value=True)

    plan = {
        "actions": [{
            "handler": "app_control", "method": "shutdown",
            "params": {}, "requires_confirmation": True,
        }],
        "execution_mode": "sequential",
    }
    await executor.execute(plan)

    executor._registry.get("app_control").shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_parallel_execution(executor, mock_bus):
    """Parallel mode launches all actions and waits for all to complete."""
    from kaoruko.core.event_bus import KaorukoEvent

    mock_handler = executor._registry.get("app_control")
    mock_handler.open_app = AsyncMock(return_value="opened")

    plan = {
        "actions": [
            {"handler": "app_control", "method": "open_app", "params": {"app_name": "chrome"}},
            {"handler": "app_control", "method": "open_app", "params": {"app_name": "vscode"}},
        ],
        "execution_mode": "parallel",
    }
    await executor.execute(plan)
    assert mock_handler.open_app.call_count == 2

    published_events = [call[0][0] for call in mock_bus.publish.call_args_list]
    assert KaorukoEvent.EXEC_ACTION_SUCCESS in published_events


def test_build_response_all_success(executor):
    from kaoruko.execution.executor import ActionResult
    results = [
        ActionResult(True, "h1", "m1", {}, response_text="Done alpha~"),
        ActionResult(True, "h2", "m2", {}, response_text="Done beta~"),
    ]
    resp = executor._build_response(results, all_success=True)
    assert "Done alpha~" in resp
    assert "Done beta~" in resp


def test_build_response_failure_uses_error(executor):
    from kaoruko.execution.executor import ActionResult
    results = [ActionResult(False, "h1", "m1", {}, error="Device not found")]
    resp = executor._build_response(results, all_success=False)
    assert "Device not found" in resp
