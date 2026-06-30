"""Этап 3: калибровка MAX_CHARS. Считает входные токены для текста из stdin.

Запуск из корня проекта (нужен заполненный .env):
    python -m scripts.calibrate < sample.txt
"""
from __future__ import annotations

import sys

import anthropic

from src import config_loader, core
from src.settings import load_settings


def main() -> None:
    settings = load_settings()
    text = sys.stdin.read()
    client = anthropic.Anthropic(api_key=settings.anthropic_key)
    tokens = core.count_tokens(
        client, settings.model, text, config_loader.load_rules(), config_loader.load_glossary()
    )
    print(
        f"chars={len(text)} input_tokens={tokens} model={settings.model} "
        f"out_cap(MAX_TOKENS)={core.MAX_TOKENS}"
    )


if __name__ == "__main__":
    main()
