"""Сборка ответа: EditResult -> выходной файл + текст саммари + перечень изъянов."""
from __future__ import annotations

import io

from .models import EditResult

# Длиннее порога перечень уходит файлом: лимит текстового сообщения Telegram — 4096.
COMMENTS_TEXT_LIMIT = 3500

# Человеческие подписи групп; порядок задаёт вывод (от частого к логике).
_TYPE_LABELS = {
    "ortho": "Орфография",
    "punct": "Пунктуация",
    "grammar": "Грамматика",
    "anglicism": "Англицизмы",
    "style": "Стиль",
    "logic": "Логика",
}


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


def _format_comments(comments: list) -> str:
    by_type: dict = {}
    for c in comments:
        by_type.setdefault(c.type, []).append(c)

    lines = [f"Перечень изъянов ({len(comments)}):"]
    for key, label in _TYPE_LABELS.items():
        items = by_type.get(key)
        if not items:
            continue
        lines.append("")
        lines.append(f"{label}:")
        for c in items:
            lines.append(f"• «{c.fragment}» → «{c.change}» — {c.reason}")
    return "\n".join(lines)


def render_comments(result: EditResult, limit: int = COMMENTS_TEXT_LIMIT) -> tuple:
    """Перечень изъянов для пользователя -> (text, file).

    Ровно одно из двух не None: короткий перечень возвращаем текстом (file=None),
    длинный (> limit) — файлом (text=None), т.к. он не влезает в сообщение Telegram.
    file, если задан, имеет форму (buf, name) — как у render_file.
    """
    if not result.comments:
        return "Изъянов не найдено.", None

    report = _format_comments(result.comments)
    if len(report) > limit:
        buf = io.BytesIO(report.encode("utf-8"))
        buf.name = "flaws.md"
        return None, (buf, buf.name)
    return report, None
