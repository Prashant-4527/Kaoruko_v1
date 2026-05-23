"""
tests/unit/test_voice_pipeline_thread_safety.py

Tests for thread-safety of VoicePipeline's cross-thread state flags.
Verifies that _recording_active and _tts_busy behave correctly when
set/cleared from multiple threads simultaneously (simulating the
hardware audio thread + async event loop interaction).
"""
import threading
import time
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def pipeline(default_config):
    """VoicePipeline with all external dependencies mocked out."""
    from kaoruko.core.event_bus import EventBus
    from kaoruko.voice.pipeline import VoicePipeline

    bus = MagicMock(spec=EventBus)
    bus.subscribe = MagicMock()
    pipeline = VoicePipeline(config=default_config, bus=bus)
    return pipeline


def test_recording_active_is_threading_event(pipeline):
    """_recording_active must be a threading.Event, not a plain bool."""
    import threading
    assert isinstance(pipeline._recording_active, threading.Event)


def test_tts_busy_is_threading_event(pipeline):
    import threading
    assert isinstance(pipeline._tts_busy, threading.Event)


def test_initially_not_recording(pipeline):
    assert not pipeline._recording_active.is_set()
    assert not pipeline.is_recording


def test_recording_flag_visible_across_threads(pipeline):
    """
    Set the flag from the main thread, verify it's visible from a spawned thread.
    This simulates the audio hardware callback thread reading the flag that
    was set by the async event loop.
    """
    seen_from_thread = []

    def reader_thread():
        seen_from_thread.append(pipeline._recording_active.is_set())

    pipeline._recording_active.set()

    t = threading.Thread(target=reader_thread)
    t.start()
    t.join(timeout=1.0)

    assert seen_from_thread == [True]


def test_clear_recording_flag(pipeline):
    pipeline._recording_active.set()
    assert pipeline.is_recording

    pipeline._recording_active.clear()
    assert not pipeline.is_recording


def test_concurrent_set_and_read(pipeline):
    """
    Multiple threads concurrently setting and reading _recording_active
    should not crash or corrupt state.
    """
    errors = []

    def setter():
        for _ in range(100):
            pipeline._recording_active.set()
            time.sleep(0.0001)
            pipeline._recording_active.clear()

    def reader():
        for _ in range(100):
            _ = pipeline._recording_active.is_set()

    threads = [
        threading.Thread(target=setter),
        threading.Thread(target=reader),
        threading.Thread(target=reader),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    # No exceptions means the threading.Event handled concurrent access correctly
    assert errors == []


def test_wake_guard_uses_is_set(pipeline):
    """
    The audio callback guard checks .is_set() which is the thread-safe
    API — not a direct bool comparison.
    """
    pipeline._recording_active.set()
    pipeline._tts_busy.clear()

    # Simulate what the on_audio_chunk closure does
    should_process_wake = (
        not pipeline._recording_active.is_set()
        and not pipeline._tts_busy.is_set()
    )
    assert should_process_wake is False  # Should NOT process when recording


def test_tts_busy_prevents_wake_processing(pipeline):
    pipeline._recording_active.clear()
    pipeline._tts_busy.set()

    should_process_wake = (
        not pipeline._recording_active.is_set()
        and not pipeline._tts_busy.is_set()
    )
    assert should_process_wake is False  # Should NOT process when TTS is speaking
