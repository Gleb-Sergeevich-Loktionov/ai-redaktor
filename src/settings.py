"""Чтение окружения и health-check на старте."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    anthropic_key: str
    model: str
    max_chars: int
    max_file_mb: int


def load_settings() -> Settings:
    load_dotenv()

    def req(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            raise RuntimeError(f"Не задана переменная окружения {name} (.env)")
        return value

    return Settings(
        telegram_token=req("TELEGRAM_BOT_TOKEN"),
        anthropic_key=req("ANTHROPIC_API_KEY"),
        model=os.environ.get("MODEL", "claude-sonnet-4-6"),
        max_chars=int(os.environ.get("MAX_CHARS", "20000")),
        max_file_mb=int(os.environ.get("MAX_FILE_MB", "10")),
    )


def check_pandoc() -> None:
    """Fail-fast на старте: RTF на вход требует pandoc >= 2.14.2."""
    import pypandoc  # импорт здесь, чтобы settings были импортируемы без pypandoc

    try:
        version = pypandoc.get_pandoc_version()
    except OSError as exc:
        raise RuntimeError("pandoc не установлен в системе") from exc
    try:
        parts = tuple(int(x) for x in version.split(".")[:3])
    except ValueError:
        parts = (0,)
    if parts < (2, 14, 2):
        raise RuntimeError(
            f"pandoc {version} не читает RTF на вход; нужен >= 2.14.2"
        )
