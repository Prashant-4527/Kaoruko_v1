"""
tests/unit/test_event_bus.py

Tests for EventBus — subscribe, publish, unsubscribe, wildcards,
once-subscriptions, clear_subscriptions, publish_sync, and wait_for.
"""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def bus():
    from kaoruko.core.event_bus import EventBus
    return EventBus()


# ── Basic subscribe / publish ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_handler_receives_event(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    received = []
    bus.subscribe(KaorukoEvent.ASSISTANT_READY, lambda e: received.append(e))
    await bus.publish(KaorukoEvent.ASSISTANT_READY, data={"version": "1.0"})
    assert len(received) == 1
    assert received[0].data["version"] == "1.0"


@pytest.mark.asyncio
async def test_async_handler_receives_event(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(KaorukoEvent.VOICE_WAKE_DETECTED, handler)
    await bus.publish(KaorukoEvent.VOICE_WAKE_DETECTED, data={"phrase": "hey kaoruko"})
    assert len(received) == 1


@pytest.mark.asyncio
async def test_multiple_handlers_all_called(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    calls = []
    bus.subscribe(KaorukoEvent.SYSTEM_ERROR, lambda e: calls.append("h1"))
    bus.subscribe(KaorukoEvent.SYSTEM_ERROR, lambda e: calls.append("h2"))
    await bus.publish(KaorukoEvent.SYSTEM_ERROR)
    assert set(calls) == {"h1", "h2"}


# ── Priority ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_priority_ordering(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    order = []
    bus.subscribe(KaorukoEvent.NLU_INTENT_RESOLVED, lambda e: order.append("low"),  priority=0)
    bus.subscribe(KaorukoEvent.NLU_INTENT_RESOLVED, lambda e: order.append("high"), priority=10)
    bus.subscribe(KaorukoEvent.NLU_INTENT_RESOLVED, lambda e: order.append("mid"),  priority=5)
    await bus.publish(KaorukoEvent.NLU_INTENT_RESOLVED)
    assert order == ["high", "mid", "low"]


# ── Unsubscribe ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    calls = []
    handler = lambda e: calls.append(e)
    bus.subscribe(KaorukoEvent.MEMORY_UPDATED, handler)
    await bus.publish(KaorukoEvent.MEMORY_UPDATED)
    assert len(calls) == 1

    bus.unsubscribe(KaorukoEvent.MEMORY_UPDATED, handler)
    await bus.publish(KaorukoEvent.MEMORY_UPDATED)
    assert len(calls) == 1  # Still 1 — not called again


# ── One-shot ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_once_subscription_fires_once(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    calls = []
    bus.subscribe(KaorukoEvent.TTS_SPEAKING_END, lambda e: calls.append(1), once=True)
    await bus.publish(KaorukoEvent.TTS_SPEAKING_END)
    await bus.publish(KaorukoEvent.TTS_SPEAKING_END)
    assert len(calls) == 1


# ── Wildcards ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wildcard_subscription(bus):
    received = []
    bus.subscribe("voice.*", lambda e: received.append(e.type.value))
    from kaoruko.core.event_bus import KaorukoEvent
    await bus.publish(KaorukoEvent.VOICE_WAKE_DETECTED)
    await bus.publish(KaorukoEvent.VOICE_TRANSCRIPT_READY)
    await bus.publish(KaorukoEvent.EXEC_ACTION_SUCCESS)  # should NOT match
    assert "voice.wake_detected" in received
    assert "voice.transcript_ready" in received
    assert "execution.action_success" not in received


# ── Clear subscriptions ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clear_subscriptions_all(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    calls = []
    bus.subscribe(KaorukoEvent.ASSISTANT_READY, lambda e: calls.append(1))
    bus.subscribe(KaorukoEvent.SYSTEM_ERROR, lambda e: calls.append(2))

    removed = bus.clear_subscriptions()
    assert removed >= 2

    await bus.publish(KaorukoEvent.ASSISTANT_READY)
    await bus.publish(KaorukoEvent.SYSTEM_ERROR)
    assert calls == []  # Nothing fired


@pytest.mark.asyncio
async def test_clear_subscriptions_specific_event(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    calls_a = []
    calls_b = []
    bus.subscribe(KaorukoEvent.ASSISTANT_READY, lambda e: calls_a.append(1))
    bus.subscribe(KaorukoEvent.SYSTEM_ERROR,    lambda e: calls_b.append(1))

    bus.clear_subscriptions(KaorukoEvent.ASSISTANT_READY)

    await bus.publish(KaorukoEvent.ASSISTANT_READY)
    await bus.publish(KaorukoEvent.SYSTEM_ERROR)
    assert calls_a == []   # cleared
    assert calls_b == [1]  # still active


# ── Event history ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_history_stored(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    await bus.publish(KaorukoEvent.ASSISTANT_READY, data={"v": "1"})
    await bus.publish(KaorukoEvent.SYSTEM_ERROR, data={"err": "oops"})

    history = bus.get_recent_events(limit=10)
    assert len(history) >= 2


@pytest.mark.asyncio
async def test_event_history_filter_by_type(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    await bus.publish(KaorukoEvent.ASSISTANT_READY)
    await bus.publish(KaorukoEvent.SYSTEM_ERROR)
    await bus.publish(KaorukoEvent.ASSISTANT_READY)

    ready_events = bus.get_recent_events(KaorukoEvent.ASSISTANT_READY)
    assert all(e.type == KaorukoEvent.ASSISTANT_READY for e in ready_events)
    assert len(ready_events) == 2


# ── wait_for ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wait_for_event_resolves(bus):
    from kaoruko.core.event_bus import KaorukoEvent

    async def fire_after_delay():
        await asyncio.sleep(0.05)
        await bus.publish(KaorukoEvent.EXEC_CONFIRM_RECEIVED, data={"confirmed": True})

    asyncio.create_task(fire_after_delay())
    event = await bus.wait_for(KaorukoEvent.EXEC_CONFIRM_RECEIVED, timeout=1.0)
    assert event is not None
    assert event.data["confirmed"] is True


@pytest.mark.asyncio
async def test_wait_for_event_times_out(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    event = await bus.wait_for(KaorukoEvent.EXEC_CONFIRM_RECEIVED, timeout=0.05)
    assert event is None


# ── publish_sync ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_publish_sync_from_running_loop(bus):
    """publish_sync should not raise when called from a running loop."""
    from kaoruko.core.event_bus import KaorukoEvent
    calls = []
    bus.subscribe(KaorukoEvent.SYSTEM_WARNING, lambda e: calls.append(1))
    bus.publish_sync(KaorukoEvent.SYSTEM_WARNING)
    await asyncio.sleep(0.05)
    assert len(calls) == 1


# ── subscriber_count ──────────────────────────────────────────────────────────

def test_subscriber_count(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    assert bus.subscriber_count(KaorukoEvent.ASSISTANT_READY) == 0
    bus.subscribe(KaorukoEvent.ASSISTANT_READY, lambda e: None)
    bus.subscribe(KaorukoEvent.ASSISTANT_READY, lambda e: None)
    assert bus.subscriber_count(KaorukoEvent.ASSISTANT_READY) == 2


def test_total_subscriber_count(bus):
    from kaoruko.core.event_bus import KaorukoEvent
    assert bus.total_subscriber_count == 0
    bus.subscribe(KaorukoEvent.ASSISTANT_READY, lambda e: None)
    bus.subscribe(KaorukoEvent.SYSTEM_ERROR,    lambda e: None)
    assert bus.total_subscriber_count == 2
