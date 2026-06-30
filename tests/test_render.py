from __future__ import annotations

import pytest

from src import render
from src.models import Comment, EditResult, Summary


def _result() -> EditResult:
    return EditResult(
        edited_text="готовый текст",
        summary=Summary(
            fixes_total=3,
            anglicisms_replaced=["дедлайн → срок"],
            style_notes=["короче"],
        ),
        comments=[
            Comment(type="ortho", fragment="превет", change="привет", reason="орфография"),
            Comment(type="anglicism", fragment="дедлайн", change="срок", reason="англицизм"),
        ],
    )


def test_render_summary():
    text = render.render_summary(_result())
    assert "3" in text and "дедлайн → срок" in text and "короче" in text


def test_render_file():
    buf, name = render.render_file(_result())
    assert name.endswith(".md")
    assert buf.getvalue().decode("utf-8") == "готовый текст"
    assert buf.name == name


def test_render_comments_message():
    text, file = render.render_comments(_result())
    assert file is None
    # фрагмент → change и причина каждой правки
    assert "превет" in text and "привет" in text and "орфография" in text
    assert "дедлайн" in text and "срок" in text and "англицизм" in text
    # подписи групп по типам
    assert "Орфография" in text and "Англицизмы" in text


def test_render_comments_logic_group():
    result = EditResult(
        edited_text="готовый текст",
        summary=Summary(fixes_total=1, anglicisms_replaced=[], style_notes=[]),
        comments=[
            Comment(
                type="logic",
                fragment="сначала вывод, потом причина",
                change="сначала причина, потом вывод",
                reason="нарушена связность изложения",
            ),
        ],
    )
    text, file = render.render_comments(result)
    assert file is None
    # тип logic выводится в группе «Логика» с фрагментом/изменением/причиной
    assert "Логика" in text
    assert "сначала вывод, потом причина" in text
    assert "сначала причина, потом вывод" in text
    assert "нарушена связность изложения" in text


def test_render_comments_empty():
    result = EditResult(
        edited_text="ок",
        summary=Summary(fixes_total=0, anglicisms_replaced=[], style_notes=[]),
        comments=[],
    )
    text, file = render.render_comments(result)
    assert file is None and "Изъянов не найдено" in text


def test_render_comments_long_falls_back_to_file():
    many = [
        Comment(type="style", fragment="ф" * 50, change="и" * 50, reason="п" * 50)
        for _ in range(200)
    ]
    result = EditResult(
        edited_text="т",
        summary=Summary(fixes_total=len(many), anglicisms_replaced=[], style_notes=[]),
        comments=many,
    )
    text, file = render.render_comments(result)
    assert text is None
    assert file is not None
    buf, name = file
    assert name.endswith(".md")
    assert buf.name == name
    assert ("ф" * 50) in buf.getvalue().decode("utf-8")


def test_models_frozen():
    result = _result()
    with pytest.raises(Exception):
        result.edited_text = "изменено"
