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


def test_load_settings_missing(monkeypatch):
    monkeypatch.setattr(settings, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        settings.load_settings()
