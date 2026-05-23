"""
tests/unit/test_ai_router.py

Tests for AIRouter — internet TTL cache, retry, fallback, message building.
All network I/O is mocked.
"""
import asyncio
import time
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def router(default_config):
    from kaoruko.intelligence.ai_router import AIRouter
    r = AIRouter(config=default_config, project_root=Path("/tmp"))
    return r


@pytest.mark.asyncio
async def test_uses_ollama_when_no_internet(router):
    router._internet_available = False
    router._internet_last_checked = time.monotonic()

    ollama_result = {
        "intent": "APP_OPEN", "entities": {"app_name": "chrome"},
        "confidence": 0.9, "action_plan": None, "response_text": "Opening Chrome~",
    }
    router._classify_with_ollama = AsyncMock(return_value=ollama_result)
    router._classify_with_claude = AsyncMock()

    result = await router.classify_intent("open chrome")

    router._classify_with_claude.assert_not_called()
    router._classify_with_ollama.assert_called_once()
    assert result["intent"] == "APP_OPEN"


@pytest.mark.asyncio
async def test_internet_cache_expires_after_ttl(router):
    """Stale cache should trigger a new network check."""
    router._internet_available = True
    # Make the cache look stale
    router._internet_last_checked = time.monotonic() - router._INTERNET_CACHE_TTL - 1

    check_call_count = 0

    async def fake_http_check():
        nonlocal check_call_count
        check_call_count += 1

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.head = AsyncMock(return_value=MagicMock(status_code=200))
        mock_client.return_value = mock_instance

        result = await router._check_internet()

    # A fresh network check was made (not the cached value)
    mock_instance.head.assert_called_once()


@pytest.mark.asyncio
async def test_internet_cache_valid_within_ttl(router):
    """Fresh cache should NOT trigger a new network check."""
    router._internet_available = True
    router._internet_last_checked = time.monotonic()  # Just checked

    with patch("httpx.AsyncClient") as mock_client:
        result = await router._check_internet()
        mock_client.assert_not_called()

    assert result is True


@pytest.mark.asyncio
async def test_invalidate_cache_on_api_error(router):
    router._internet_available = True
    router._internet_last_checked = time.monotonic()

    router._invalidate_internet_cache()

    assert router._internet_available is None
    assert router._internet_last_checked == 0.0


@pytest.mark.asyncio
async def test_retry_on_rate_limit(router):
    """Should retry up to _MAX_RETRIES times on a 429 error."""
    router._internet_available = True
    router._internet_last_checked = time.monotonic()

    from kaoruko.intelligence.ai_router import _with_retry

    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("429 rate limit exceeded")
        return {"intent": "CONV_CHAT", "confidence": 0.9, "response_text": "ok", "entities": {}, "action_plan": None}

    result = await _with_retry(flaky, max_retries=3)
    assert result["intent"] == "CONV_CHAT"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_raises_non_retriable_immediately(router):
    """Non-rate-limit errors should surface immediately without retrying."""
    from kaoruko.intelligence.ai_router import _with_retry

    call_count = 0

    async def bad_auth():
        nonlocal call_count
        call_count += 1
        raise Exception("Authentication error: invalid API key")

    with pytest.raises(Exception, match="Authentication error"):
        await _with_retry(bad_auth, max_retries=3)

    assert call_count == 1  # Did NOT retry


def test_build_messages_no_history(router):
    msgs = router._build_messages("hello", None)
    assert msgs == [{"role": "user", "content": "hello"}]


def test_build_messages_with_history(router):
    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "response"},
    ]
    msgs = router._build_messages("second", history)
    assert msgs[-1] == {"role": "user", "content": "second"}
    assert len(msgs) == 3


def test_project_root_injected(default_config):
    from kaoruko.intelligence.ai_router import AIRouter
    root = Path("/custom/root")
    router = AIRouter(config=default_config, project_root=root)
    assert router._project_root == root
