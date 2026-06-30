"""Тонкий Telegram-адаптер (python-telegram-bot v22, async, long-polling).

Логики редактуры здесь нет. Блокирующие вызовы (core.edit — Claude; extract — pandoc)
уходят в asyncio.to_thread, чтобы не блокировать единственный event loop.
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass
from functools import partial

import anthropic
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import config_loader, core, extract, render
from .settings import Settings, check_pandoc, load_settings

logger = logging.getLogger(__name__)

START_MSG = (
    "Пришлите текст или файл (.txt .md .csv .docx .odt .rtf) — "
    "отредактирую и верну исправленный текст + краткое саммари."
)


@dataclass(frozen=True)
class Deps:
    settings: Settings
    client: anthropic.Anthropic
    rules: str
    glossary: dict


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(START_MSG)


async def _process_and_reply(update: Update, text: str, deps: Deps) -> None:
    if not text.strip():
        await update.message.reply_text("Пустой текст — нечего редактировать.")
        return
    if len(text) > deps.settings.max_chars:
        await update.message.reply_text(
            f"Слишком длинный текст (> {deps.settings.max_chars} символов). "
            "Пришлите меньшую часть."
        )
        return

    status = await update.message.reply_text("Обрабатываю…")
    try:
        # core.edit — синхронный и блокирующий; в поток, иначе фриз всего бота.
        result = await asyncio.to_thread(
            core.edit, deps.client, deps.settings.model, text, deps.rules, deps.glossary
        )
    except core.EditError as exc:
        await update.message.reply_text(str(exc))
        return
    finally:
        try:
            await status.delete()  # снимаем статус и на ошибке
        except TelegramError:
            pass

    buf, name = render.render_file(result)
    await update.message.reply_document(document=buf, filename=name)
    await update.message.reply_text(render.render_summary(result))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE, deps: Deps) -> None:
    await _process_and_reply(update, update.message.text or "", deps)


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE, deps: Deps) -> None:
    doc = update.message.document
    if doc.file_size and doc.file_size > deps.settings.max_file_mb * 1024 * 1024:
        await update.message.reply_text(
            f"Файл слишком большой (> {deps.settings.max_file_mb} МБ)."
        )
        return

    ext = os.path.splitext(doc.file_name or "")[1].lower()
    if ext not in extract.ALLOWED_EXT:
        await update.message.reply_text(
            "Неподдерживаемый формат. Пришлите .txt .md .csv .docx .odt .rtf."
        )
        return

    # tempfile + только расширение от клиента (против path-traversal/коллизий).
    fd, path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        tg_file = await doc.get_file()
        await tg_file.download_to_drive(path)
        text = await asyncio.to_thread(extract.extract, path)
    except extract.ExtractError as exc:
        await update.message.reply_text(str(exc))
        return
    except TelegramError:
        await update.message.reply_text("Не удалось скачать файл. Попробуйте ещё раз.")
        return
    finally:
        try:
            os.remove(path)  # stateless — чистим временный файл
        except OSError:
            pass

    await _process_and_reply(update, text, deps)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("Произошла ошибка, попробуйте позже.")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = load_settings()
    check_pandoc()  # fail-fast: pandoc >= 2.14.2 для RTF

    # Клиент и конфиг — один раз на старте, не на каждый запрос.
    client = anthropic.Anthropic(api_key=settings.anthropic_key)
    deps = Deps(
        settings=settings,
        client=client,
        rules=config_loader.load_rules(),
        glossary=config_loader.load_glossary(),
    )

    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, partial(on_text, deps=deps)))
    app.add_handler(MessageHandler(filters.Document.ALL, partial(on_document, deps=deps)))
    app.add_error_handler(error_handler)

    logger.info("Bot started (long-polling)")
    app.run_polling()  # владеет event loop; НЕ оборачивать в asyncio.run


if __name__ == "__main__":
    main()
