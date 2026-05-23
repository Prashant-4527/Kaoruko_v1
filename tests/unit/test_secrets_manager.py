"""
tests/unit/test_secrets_manager.py

Tests for the encrypted secrets storage.
Covers: round-trip encrypt/decrypt, missing key, delete, list_keys safety.
"""
import pytest
from pathlib import Path


@pytest.fixture
def secrets(tmp_path):
    """SecretsManager backed by a temporary directory."""
    from kaoruko.security.secrets_manager import SecretsManager
    return SecretsManager(tmp_path)


def test_store_and_retrieve(secrets):
    secrets.store("anthropic_api_key", "sk-ant-test-1234")
    result = secrets.get("anthropic_api_key")
    assert result == "sk-ant-test-1234"


def test_missing_key_returns_none(secrets):
    result = secrets.get("nonexistent_key")
    assert result is None


def test_overwrite_key(secrets):
    secrets.store("my_key", "value_v1")
    secrets.store("my_key", "value_v2")
    assert secrets.get("my_key") == "value_v2"


def test_delete_key(secrets):
    secrets.store("temp_key", "temp_value")
    assert secrets.get("temp_key") == "temp_value"
    secrets.delete("temp_key")
    assert secrets.get("temp_key") is None


def test_list_keys_does_not_expose_values(secrets):
    secrets.store("key_a", "secret_value_a")
    secrets.store("key_b", "secret_value_b")
    keys = secrets.list_keys()
    assert "key_a" in keys
    assert "key_b" in keys
    # Values must NOT appear in the keys list
    assert "secret_value_a" not in keys
    assert "secret_value_b" not in keys


def test_separate_instances_share_encrypted_store(tmp_path):
    """Two SecretsManager instances on same directory can read each other's data."""
    from kaoruko.security.secrets_manager import SecretsManager
    mgr1 = SecretsManager(tmp_path)
    mgr1.store("shared_key", "shared_value")

    mgr2 = SecretsManager(tmp_path)
    assert mgr2.get("shared_key") == "shared_value"


def test_store_empty_string(secrets):
    """Empty string is a valid secret value."""
    secrets.store("empty_key", "")
    assert secrets.get("empty_key") == ""


def test_store_unicode_key_and_value(secrets):
    secrets.store("api_香子", "value_🌸")
    assert secrets.get("api_香子") == "value_🌸"
