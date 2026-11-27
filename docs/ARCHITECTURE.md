# Архитектура — `ai-redaktor`

Stateless Telegram-бот для корректуры и лёгкой стилевой редактуры русскоязычных текстов.
Состояние между запросами не хранится: БД и пользовательских сессий нет.

## Принцип: ядро + тонкий адаптер

Ядро (`src/core.py`) ничего не знает про Telegram и файловую систему: принимает текст,
правила стиля и словарь англицизмов и возвращает структурированный `EditResult`.
Telegram-бот (`src/bot.py`) отвечает только за приём сообщений/файлов, проверку доступа,
валидацию лимитов и отправку результата.

## Поток обработки

```
Пользователь (Telegram)
  └─▶ src/bot.py (проверка ALLOWED_USER_IDS, лимиты MAX_CHARS / MAX_FILE_MB)
        ├─ текст ──────────────────────────────────────┐
        └─ файл (.txt/.md/.csv/.docx/.odt/.rtf)        │
             └─▶ src/extract.py (чтение / pandoc) ─────▼
                                                  src/core.py: edit(...)
                                                    ├─ src/prompts.py (SYSTEM + rules + glossary)
                                                    └─ Anthropic Claude (structured output / JSON)
                                                         │
                                                         ▼
                                                  src/render.py
                                                    ├─ corrected.md (документ)
                                                    ├─ саммари (текст)
                                                    └─ перечень изъянов (текст или flaws.md)
```

## Модули `src/`

| Модуль | Ответственность |
|---|---|
| `bot.py` | Async long-polling (`python-telegram-bot` v22), контроль доступа (`ALLOWED_USER_IDS`), валидация размеров, вынос blocking IO в `asyncio.to_thread` |
| `core.py` | Один вызов Claude (`messages.parse` с fallback на `messages.create` + `json_schema`), маппинг исключений SDK в `EditError` |
| `prompts.py` | Сборка системного и пользовательского промпта; стабильный префикс помечен `cache_control: ephemeral` |
| `models.py` | Контракт ядра (`frozen=True` Pydantic-модели: `EditResult`, `Summary`, `Comment`) |
| `extract.py` | Извлечение текста: UTF-8 для плоских форматов, `pypandoc` (системный `pandoc >= 2.14.2`) для `.docx`/`.odt`/`.rtf` |
| `render.py` | Рендер `corrected.md`, саммари и перечня изъянов (`flaws.md`, если длиннее лимита сообщения) |
| `config_loader.py` | Загрузка `config/rules.md` и `config/anglicisms.json` |
| `settings.py` | Загрузка переменных окружения (`.env`), парсинг `ALLOWED_USER_IDS`, проверка версии `pandoc` на старте |

## Контракт ядра

```python
edit(client, model, text, rules, glossary) -> EditResult(
    edited_text: str,
    summary: Summary(fixes_total: int, anglicisms_replaced: list[str], style_notes: list[str]),
    comments: list[Comment(type: CommentType, fragment: str, change: str, reason: str)],
)
```

`CommentType` ∈ `{"ortho", "punct", "grammar", "anglicism", "style", "logic"}`.
