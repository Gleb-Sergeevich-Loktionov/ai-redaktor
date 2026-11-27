from __future__ import annotations

import pytest

from src import settings


def test_load_settings_defaults(monkeypatch):
    monkeypatch.setattr(settings, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    monkeypatch.delenv("MODEL", raising=False)
    monkeypatch.delenv("MAX_CHARS", raising=False)
    monkeypatch.delenv("MAX_FILE_MB", raising=False)

    s = settings.load_settings()
    assert s.telegram_token == "tok" and s.anthropic_key == "key"
    assert s.model == "claude-sonnet-4-6"
    assert s.max_chars == 20000 and s.max_file_mb == 10
    assert s.allowed_user_ids == frozenset()


def test_parse_allowed_user_ids():
    assert settings.parse_allowed_user_ids(None) == frozenset()
    assert settings.parse_allowed_user_ids("") == frozenset()
    assert settings.parse_allowed_user_ids("  ") == frozenset()
    assert settings.parse_allowed_user_ids("123, 456, ,789") == frozenset({123, 456, 789})

    with pytest.raises(RuntimeError):
        settings.parse_allowed_user_ids("123,not-an-id")


def test_load_settings_allowed_user_ids(monkeypatch):
    monkeypatch.setattr(settings, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    monkeypatch.setenv("ALLOWED_USER_IDS", "101, 202")

    s = settings.load_settings()
    assert s.allowed_user_ids == frozenset({101, 202})


def test_load_settings_missing(monkeypatch):
    monkeypatch.setattr(settings, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        settings.load_settings()
