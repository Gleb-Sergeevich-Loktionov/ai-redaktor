"""Загрузка данных конфига: правила стиля + словарь англицизмов.

Это ДАННЫЕ, не код — правятся в `config/` без изменения кода и подмешиваются в промпт.
Грузить один раз на старте, не на каждый запрос.
"""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_rules() -> str:
    return (CONFIG_DIR / "rules.md").read_text(encoding="utf-8")


def load_glossary() -> dict:
    data = json.loads((CONFIG_DIR / "anglicisms.json").read_text(encoding="utf-8"))
    for key in ("replace_always", "context_dependent"):
        if key not in data or not isinstance(data[key], list):
            raise RuntimeError(f"anglicisms.json: отсутствует или некорректен '{key}'")
    return data
