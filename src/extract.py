"""Извлечение текста: плоские форматы — чтением, офисные — через pandoc."""
from __future__ import annotations

import os

import pypandoc

FLAT = {".txt", ".md", ".csv"}
OFFICE = {".docx", ".odt", ".rtf"}
ALLOWED_EXT = FLAT | OFFICE


class ExtractError(Exception):
    """User-facing русское сообщение; ловится адаптером."""


def extract(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in FLAT:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError) as exc:
            raise ExtractError("Не удалось прочитать файл: повреждён или не в кодировке UTF-8.") from exc
    elif ext in OFFICE:
        try:
            # 'markdown', не 'plain' — сохраняет структуру; формат по расширению.
            text = pypandoc.convert_file(path, "markdown")
        except RuntimeError as exc:
            raise ExtractError("Не удалось извлечь текст: файл повреждён или формат не поддерживается.") from exc
        except OSError as exc:
            raise ExtractError("Внутренняя ошибка обработки файла. Попробуйте позже.") from exc
    else:
        raise ExtractError("Формат файла не поддерживается.")

    if not text.strip():  # pandoc на пустом отдаёт "" с кодом 0 — проверяем сами
        raise ExtractError("Файл пустой — нет текста для обработки.")
    return text
