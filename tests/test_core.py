from __future__ import annotations

import anthropic
import httpx
import pytest

from src import core
from src.models import EditResult, Summary

VALID = EditResult(
    edited_text="ок",
    summary=Summary(fixes_total=1, anglicisms_replaced=[], style_notes=[]),
)
GLOSSARY = {"replace_always": [], "context_dependent": []}


class _Usage:
    input_tokens = 10
    output_tokens = 5
    cache_read_input_tokens = 0


# --- happy path: messages.parse ---
class _ParseClient:
    class messages:
        @staticmethod
        def parse(**kwargs):
            return type("R", (), {"parsed_output": VALID, "usage": _Usage()})()


def test_parse_path():
    assert core.edit(_ParseClient(), "m", "txt", "rules", GLOSSARY) == VALID


# --- raw fallback: no .parse, only .create ---
class _TextBlock:
    type = "text"
    text = VALID.model_dump_json()


class _CreateClient:
    class messages:
        @staticmethod
        def create(**kwargs):
            return type("R", (), {"content": [_TextBlock()], "usage": _Usage()})()


def test_raw_fallback_path():
    result = core.edit(_CreateClient(), "m", "txt", "rules", GLOSSARY)
    assert result.edited_text == "ок"


# --- parsed_output None -> EditError ---
class _NoneClient:
    class messages:
        @staticmethod
        def parse(**kwargs):
            return type("R", (), {"parsed_output": None, "usage": _Usage()})()


def test_parse_none_raises():
    with pytest.raises(core.EditError):
        core.edit(_NoneClient(), "m", "t", "r", GLOSSARY)


# --- anthropic exception -> EditError ---
class _RaiseClient:
    class messages:
        @staticmethod
        def parse(**kwargs):
            raise anthropic.APIConnectionError(
                message="boom", request=httpx.Request("POST", "http://x")
            )


def test_connection_error_maps_to_editerror():
    with pytest.raises(core.EditError):
        core.edit(_RaiseClient(), "m", "t", "r", GLOSSARY)


def test_strict_schema_no_additional():
    schema = core._strict_schema()
    assert schema["additionalProperties"] is False
    for definition in schema.get("$defs", {}).values():
        if definition.get("type") == "object" or "properties" in definition:
            assert definition["additionalProperties"] is False
