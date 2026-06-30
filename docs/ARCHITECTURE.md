# Архитектура V1 (MVP) — «redactor»

## Принцип: ядро + тонкий адаптер + репозиторий хранения
Ядро редактуры не знает ни про Telegram, ни про БД. Telegram-адаптер принимает запрос,
через репозиторий достаёт контекст проекта («библию») и зовёт ядро. Новый канал (Notion,
веб) или другое хранилище (Postgres) = ещё один тонкий адаптер/репозиторий за тем же
контрактом, ядро не меняется (Separation of Concerns, DIP, Optimize for Change, DRY).

## Потоки

```
Редактор (Telegram)
 → Бот-адаптер (① сразу «Обрабатываю…»)
   ├─ Команды проекта ──────────────→ store (SQLite): create / select / update bible
   │
   ├─ Редактура:
   │    → скачать файл + проверка типа/размера → extract(file) -> str
   │    → store.get_active_project(chat) -> bible_text
   │    → ЯДРО edit(text, rules, glossary, bible) → один вызов Claude → JSON
   │    → render: файл + саммари + перечень правок → ② ответ
   │
   └─ Клиентские правки (ConversationHandler):
        шаг 1: исходный текст; шаг 2: версия с правками клиента
        → ЯДРО apply_client_edits(original, client_edits, ...) → сведённый текст + перечень
```
Состояние ограничено контекстом проекта в БД: истории правок, очередей и Notion нет.

## Компоненты и ответственность

| Компонент | Ответственность / обоснование |
|---|---|
| Бот-адаптер (`bot.py`) | Принимает текст/файл и команды, качает, валидирует, зовёт store и ядро, возвращает результат, ведёт UX (статусы, ошибки), держит диалог клиентских правок. **Тонкий** — логики редактуры здесь нет. |
| Извлечение (`extract.py`) | Узкий интерфейс `extract(file) -> str` (Law of Demeter). Плоские форматы — чтением; офисные — через pandoc. `.pdf` добавится здесь же. |
| Ядро (`core.py`) | Сердце. Две операции: `edit(...)` и `apply_client_edits(...)`. Собирает промпт (правила + словарь + «библия») и делает один вызов Claude → структурный JSON. Не знает про Telegram и БД. |
| Хранилище (`store.py`) | Репозиторий проектов поверх SQLite: CRUD проектов, активный проект чата, чтение/запись `bible_text`. Шов — меняем БД, не трогая ядро/адаптер. |
| БД (`db.py`) | Подключение к SQLite, инициализация схемы, WAL. Единственное место, знающее про `sqlite3`. |
| Глобальные данные (`config/`) | `anglicisms.json` и `rules.md` — **данные**, правятся без кода, подмешиваются в промпт. |
| Сборка ответа (`render.py`) | JSON → выходной файл + саммари + **перечень правок**. Отделена от анализа, чтобы менять формат вывода независимо. |
| Настройки (`settings.py`) | `.env`: токены, модель, лимиты, путь к файлу БД. Health-check pandoc на старте. |

## Контракты ядра (стабильные швы)

```
edit(client, model, text, *, rules, glossary, bible="") -> EditResult {
  edited_text: str,
  summary: { fixes_total: int, anglicisms_replaced: [str], style_notes: [str] },
  comments: [ { type, fragment, change, reason } ]   # ОБЯЗАТЕЛЬНЫ (перечень правок — выдача)
}

apply_client_edits(client, model, original, client_edits, *, rules, glossary, bible="")
  -> ReconcileResult {
       merged_text: str,
       summary: { ... },
       comments: [ { type, fragment, change, reason } ]
     }
```
`type` ∈ { ortho, punct, grammar, anglicism, style }. Канал и хранилище меняются — контракт нет.
Детали промптов и формата — `PROMPT.md`.

## Модель данных (SQLite)

```sql
projects (
  id         INTEGER PRIMARY KEY,
  chat_id    INTEGER NOT NULL,
  name       TEXT    NOT NULL,
  bible_text TEXT    NOT NULL DEFAULT '',
  created_at TEXT,
  updated_at TEXT,
  UNIQUE (chat_id, name)
);

chat_state (
  chat_id           INTEGER PRIMARY KEY,
  active_project_id INTEGER REFERENCES projects(id)
);
```
Минимум, достаточный для контекста проекта. Без истории правок (V2). Режим WAL.

## Целевая раскладка `src/` (ориентир, не догма)

```
src/
  bot.py            # адаптер: команды проекта + редактура + клиентские правки
  extract.py        # extract(file) -> str
  core.py           # edit(...) и apply_client_edits(...)
  prompts.py        # сборка промптов (вкл. «библию» и шаблон клиентских правок)
  models.py         # EditResult, ReconcileResult, Project
  store.py          # репозиторий проектов поверх SQLite (CRUD + активный проект)
  db.py             # подключение/инициализация SQLite (схема, WAL)
  config_loader.py  # глобальные rules + glossary
  render.py         # текст + саммари + перечень правок
  settings.py       # .env (токены, модель, лимиты, путь к БД)
```
Это **модули одного сервиса**, а не микросервисы. Модуль без обоснования на текущем скоупе — не создаём.

## Стек (boring, обоснован)

| Слой | Выбор | Почему |
|---|---|---|
| Язык | Python | Стандарт для ТГ-ботов и LLM. |
| Telegram | python-telegram-bot, long-polling, `ConversationHandler` | Конвенциональная библиотека; диалог клиентских правок — штатным механизмом. |
| Извлечение | pandoc + прямое чтение | Один зрелый конвертер; плоские форматы — напрямую. |
| Модель | Claude Sonnet (`claude-sonnet-4-6`) | Баланс качество/стоимость; имя из `.env`. |
| Хранилище | **SQLite** (`sqlite3` stdlib, без ORM) | Per-project «библия» при нуле инфраструктуры; репозиторий-шов под Postgres позже. |
| Хостинг | один контейнер на PaaS/VPS + volume под БД | Без Kubernetes; БД переживает рестарт. |
| Очереди / Notion / память | нет | YAGNI на текущем скоупе (V2). |

## Долгая обработка
LLM-вызов занимает секунды. Бот сразу отвечает «Обрабатываю…», затем шлёт результат
отдельным сообщением (блокирующие вызовы — в `asyncio.to_thread`). Очередь не нужна, пока
объём мал.

## Состояние и конкурентность
Один инстанс, низкий объём записи → SQLite в режиме WAL достаточно. Мульти-инстанс и
внешняя БД — при росте, за тем же репозиторием.

## Стоимость
Линейна по длине текста (вход + выход). Кап символов на запрос (`MAX_CHARS`).
Клиентские правки — дополнительный вызов только при использовании потока.

> Синхронизация: `PROMPT.md`, `CLAUDE.md`, `README.md` описывают прежний stateless-скоуп V0
> и должны быть приведены к этой архитектуре (БД, «библия», клиентские правки, перечень правок).
