"""Сборка ответа: EditResult -> выходной файл + текст саммари."""
from __future__ import annotations

import io

from .models import EditResult


def render_summary(result: EditResult) -> str:
    lines = [f"Готово. Исправлений: {result.summary.fixes_total}."]
    if result.summary.anglicisms_replaced:
        lines.append("Англицизмы: " + "; ".join(result.summary.anglicisms_replaced))
    if result.summary.style_notes:
        lines.append("Стиль: " + "; ".join(result.summary.style_notes))
    return "\n".join(lines)


def render_file(result: EditResult, filename: str = "corrected.md") -> tuple:
    buf = io.BytesIO(result.edited_text.encode("utf-8"))
    buf.name = filename
    return buf, filename
