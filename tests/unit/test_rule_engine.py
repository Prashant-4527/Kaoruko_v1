"""
tests/unit/test_rule_engine.py
"""
import pytest
from kaoruko.nlu.rule_engine import RuleEngine


@pytest.fixture
def engine():
    e = RuleEngine()
    e.load()
    return e


class TestRuleEngineAppOpen:
    def test_open_chrome(self, engine):
        r = engine.match("Open Chrome")
        assert r is not None
        assert r.intent == "APP_OPEN"
        assert r.entities["app_name"] == "chrome"
        assert r.confidence >= 0.95

    def test_open_vscode(self, engine):
        r = engine.match("Open VS Code")
        assert r is not None
        assert r.intent == "APP_OPEN"

    def test_hinglish_open(self, engine):
        r = engine.match("Chrome kholo")
        assert r is not None
        assert r.intent == "APP_OPEN"
        assert r.entities["app_name"] == "chrome"

    def test_hinglish_open_karo(self, engine):
        r = engine.match("VS Code open karo")
        assert r is not None
        assert r.intent == "APP_OPEN"

    def test_launch_steam(self, engine):
        r = engine.match("Launch Steam")
        assert r is not None
        assert r.intent == "APP_OPEN"
        assert r.entities["app_name"] == "steam"


class TestRuleEngineAppClose:
    def test_close_discord(self, engine):
        r = engine.match("Close Discord")
        assert r is not None
        assert r.intent == "APP_CLOSE"
        assert r.entities["app_name"] == "discord"

    def test_quit_chrome(self, engine):
        r = engine.match("Quit Chrome")
        assert r is not None
        assert r.intent == "APP_CLOSE"

    def test_hinglish_close(self, engine):
        r = engine.match("Discord band karo")
        assert r is not None
        assert r.intent == "APP_CLOSE"


class TestRuleEngineBrowser:
    def test_search_google(self, engine):
        r = engine.match("Search for Python tutorials")
        assert r is not None
        assert r.intent == "BROWSER_SEARCH"
        assert "Python tutorials" in r.entities.get("query", "")

    def test_google_hinglish(self, engine):
        r = engine.match("Google me AI jobs search karo")
        assert r is not None
        assert r.intent == "BROWSER_SEARCH"

    def test_open_url(self, engine):
        r = engine.match("Open https://github.com")
        assert r is not None
        assert r.intent == "BROWSER_OPEN"
        assert "github.com" in r.entities.get("url", "")

    def test_open_domain(self, engine):
        r = engine.match("Open youtube.com")
        assert r is not None
        assert r.intent == "BROWSER_OPEN"


class TestRuleEngineSystem:
    def test_volume_absolute(self, engine):
        r = engine.match("Set volume to 60")
        assert r is not None
        assert r.intent == "SYS_VOLUME"
        assert r.entities.get("level") == 60

    def test_volume_percent(self, engine):
        r = engine.match("volume 80%")
        assert r is not None
        assert r.intent == "SYS_VOLUME"

    def test_volume_up(self, engine):
        r = engine.match("Turn up the volume")
        assert r is not None
        assert r.intent == "SYS_VOLUME"

    def test_mute(self, engine):
        r = engine.match("Mute")
        assert r is not None
        assert r.intent == "SYS_MUTE"
        assert r.entities.get("mute") is True

    def test_shutdown(self, engine):
        r = engine.match("Shutdown")
        assert r is not None
        assert r.intent == "SYS_SHUTDOWN"
        assert r.confidence >= 0.97

    def test_restart(self, engine):
        r = engine.match("Restart")
        assert r is not None
        assert r.intent == "SYS_RESTART"

    def test_sleep(self, engine):
        r = engine.match("Sleep")
        assert r is not None
        assert r.intent == "SYS_SLEEP"

    def test_lock(self, engine):
        r = engine.match("Lock screen")
        assert r is not None
        assert r.intent == "SYS_LOCK"

    def test_wifi_off(self, engine):
        r = engine.match("Turn off WiFi")
        assert r is not None
        assert r.intent == "SYS_WIFI"
        assert r.entities.get("enable") is False

    def test_wifi_on(self, engine):
        r = engine.match("Enable WiFi")
        assert r is not None
        assert r.intent == "SYS_WIFI"


class TestRuleEngineMeta:
    def test_help(self, engine):
        r = engine.match("help")
        assert r is not None
        assert r.intent == "META_HELP"

    def test_settings(self, engine):
        r = engine.match("Open settings")
        assert r is not None
        assert r.intent == "META_SETTINGS"

    def test_stop(self, engine):
        r = engine.match("Stop listening")
        assert r is not None
        assert r.intent == "META_STOP"


class TestRuleEngineEdgeCases:
    def test_empty_string(self, engine):
        r = engine.match("")
        assert r is None

    def test_whitespace_only(self, engine):
        r = engine.match("   ")
        assert r is None

    def test_unknown_command(self, engine):
        r = engine.match("xyzzy frobulate the glorp")
        assert r is None

    def test_action_plan_exists(self, engine):
        r = engine.match("Open Chrome")
        assert r is not None
        assert r.action_plan is not None
        assert len(r.action_plan["actions"]) > 0

    def test_shutdown_requires_confirmation(self, engine):
        r = engine.match("Shutdown")
        assert r is not None
        assert r.action_plan is not None
        actions = r.action_plan["actions"]
        assert any(a.get("requires_confirmation") for a in actions)
