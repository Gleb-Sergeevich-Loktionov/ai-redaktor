from __future__ import annotations

import asyncio
from types import SimpleNamespace

from src import bot
from src.settings import Settings


class _ExplodingClient:
    class messages:
        @staticmethod
        def parse(**kwargs):
            raise AssertionError("Anthropic API should not be called for unauthorized users")

        @staticmethod
        def create(**kwargs):
            raise AssertionError("Anthropic API should not be called for unauthorized users")


class _StubMessage:
    def __init__(self, text: str = "привет", document=None):
        self.text = text
        self.document = document
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs):
        self.replies.append(text)
        return self

    async def delete(self):
        return None


def _make_update(user_id: int | None, text: str = "тест текст"):
    msg = _StubMessage(text=text)
    user = SimpleNamespace(id=user_id) if user_id is not None else None
    return SimpleNamespace(
        effective_user=user,
        effective_message=msg,
        message=msg,
    ), msg


def _make_deps(allowed_user_ids: frozenset[int]) -> bot.Deps:
    return bot.Deps(
        settings=Settings(
            telegram_token="tok",
            anthropic_key="key",
            model="claude-sonnet-4-6",
            max_chars=20000,
            max_file_mb=10,
            allowed_user_ids=allowed_user_ids,
        ),
        client=_ExplodingClient(),  # type: ignore[arg-type]
        rules="rules",
        glossary={"replace_always": [], "context_dependent": []},
    )


def test_is_user_allowed():
    update_100, _ = _make_update(100)
    update_none, _ = _make_update(None)

    assert bot.is_user_allowed(update_100, frozenset()) is True
    assert bot.is_user_allowed(update_none, frozenset()) is True
    assert bot.is_user_allowed(update_100, frozenset({100, 200})) is True
    assert bot.is_user_allowed(update_100, frozenset({200})) is False
    assert bot.is_user_allowed(update_none, frozenset({100})) is False


def test_handlers_reject_unauthorized_without_calling_api():
    deps = _make_deps(frozenset({42}))
    update, msg = _make_update(999, "Отредактируй этот текст")

    async def scenario():
        await bot.start(update, None, deps=deps)  # type: ignore[arg-type]
        await bot.on_text(update, None, deps=deps)  # type: ignore[arg-type]
        await bot.on_document(update, None, deps=deps)  # type: ignore[arg-type]

    asyncio.run(scenario())
    assert msg.replies == ["Доступ запрещён.", "Доступ запрещён.", "Доступ запрещён."]


def test_start_allows_listed_and_unrestricted_users():
    update_allowed, msg_allowed = _make_update(42)
    asyncio.run(bot.start(update_allowed, None, deps=_make_deps(frozenset({42}))))  # type: ignore[arg-type]
    assert msg_allowed.replies == [bot.START_MSG]

    update_open, msg_open = _make_update(777)
    asyncio.run(bot.start(update_open, None, deps=_make_deps(frozenset())))  # type: ignore[arg-type]
    assert msg_open.replies == [bot.START_MSG]
