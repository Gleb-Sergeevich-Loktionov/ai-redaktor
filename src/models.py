"""Контракт ядра редактуры (стабильный шов).

Модели — `frozen` (правило иммутабельности проекта). `EditResult` служит и типом
возврата `core.edit`, и схемой структурного вывода Claude (`output_format`).
"""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict

CommentType = Literal["ortho", "punct", "grammar", "anglicism", "style", "logic"]


class Comment(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: CommentType
    fragment: str   # исходный фрагмент
    change: str     # что стало
    reason: str     # коротко почему


class Summary(BaseModel):
    model_config = ConfigDict(frozen=True)
    fixes_total: int
    anglicisms_replaced: List[str]   # ["инсайт → вывод", ...]
    style_notes: List[str]


class EditResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    edited_text: str
    summary: Summary
    comments: List[Comment]   # перечень изъянов — обязательная выдача
