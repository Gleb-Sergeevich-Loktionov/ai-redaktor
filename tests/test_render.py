from __future__ import annotations

import pytest

from src import render
from src.models import EditResult, Summary


def _result() -> EditResult:
    return EditResult(
        edited_text="готовый текст",
        summary=Summary(
            fixes_total=3,
            anglicisms_replaced=["дедлайн → срок"],
            style_notes=["короче"],
        ),
    )


def test_render_summary():
    text = render.render_summary(_result())
    assert "3" in text and "дедлайн → срок" in text and "короче" in text


def test_render_file():
    buf, name = render.render_file(_result())
    assert name.endswith(".md")
    assert buf.getvalue().decode("utf-8") == "готовый текст"
    assert buf.name == name


def test_models_frozen():
    result = _result()
    with pytest.raises(Exception):
        result.edited_text = "изменено"
