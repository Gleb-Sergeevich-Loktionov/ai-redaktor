"""Ядро редактуры: один вызов Claude, структурный вывод. Telegram-агностично, sync."""
from __future__ import annotations

import logging

import anthropic

from .models import EditResult
from .prompts import SYSTEM, build_messages

logger = logging.getLogger(__name__)

MAX_TOKENS = 16000  # потолок, безопасный для non-streaming; кириллица токеноёмкая


class EditError(Exception):
    """Дружелюбное русское сообщение для адаптера."""


def _force_no_additional(node) -> None:
    """Рекурсивно проставить additionalProperties:false (требование structured output)."""
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            node["additionalProperties"] = False
        for value in node.values():
            _force_no_additional(value)
    elif isinstance(node, list):
        for value in node:
            _force_no_additional(value)


def _strict_schema() -> dict:
    schema = EditResult.model_json_schema()
    _force_no_additional(schema)
    return schema


def _log_usage(resp) -> None:
    usage = getattr(resp, "usage", None)
    if usage is None:
        return
    logger.info(
        "anthropic usage in=%s out=%s cache_read=%s",
        getattr(usage, "input_tokens", None),
        getattr(usage, "output_tokens", None),
        getattr(usage, "cache_read_input_tokens", None),
    )


def _first_text(resp) -> str:
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            return block.text
    raise EditError("Пустой ответ модели.")


def _invoke(client, model: str, messages: list) -> EditResult:
    # Предпочтительно messages.parse + output_format (валидированный Pydantic).
    parse = getattr(client.messages, "parse", None)
    if callable(parse):
        resp = parse(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=messages,
            output_format=EditResult,
            output_config={"effort": "low"},  # дешёвая детерминированная редактура
        )
        _log_usage(resp)
        out = getattr(resp, "parsed_output", None)
        if out is None:
            raise EditError("Модель вернула некорректный ответ. Попробуйте ещё раз.")
        return out

    # Fallback: raw json_schema (для SDK без messages.parse).
    resp = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=messages,
        output_config={"format": {"type": "json_schema", "schema": _strict_schema()}},
    )
    _log_usage(resp)
    return EditResult.model_validate_json(_first_text(resp))


def edit(client, model: str, text: str, rules: str, glossary: dict) -> EditResult:
    """Один вызов Claude. `client` инжектится снаружи (один на процесс)."""
    messages = build_messages(text, rules, glossary)
    try:
        return _invoke(client, model, messages)
    # Порядок: от частного к общему (RateLimit/BadRequest — подклассы APIStatusError).
    except anthropic.RateLimitError as exc:
        raise EditError("Сервис перегружен, попробуйте через минуту.") from exc
    except anthropic.BadRequestError as exc:
        raise EditError("Текст не удалось обработать (возможно, слишком длинный).") from exc
    except anthropic.APIConnectionError as exc:
        raise EditError("Не удалось связаться с сервисом редактуры. Попробуйте позже.") from exc
    except anthropic.APIStatusError as exc:
        raise EditError("Сервис редактуры недоступен. Попробуйте позже.") from exc


def count_tokens(client, model: str, text: str, rules: str, glossary: dict) -> int:
    """Калибровка MAX_CHARS (этап 3): сколько входных токенов даёт текст."""
    resp = client.messages.count_tokens(
        model=model, system=SYSTEM, messages=build_messages(text, rules, glossary)
    )
    return resp.input_tokens
