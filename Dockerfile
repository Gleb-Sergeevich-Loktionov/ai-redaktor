# Один контейнер на PaaS/VPS (не Kubernetes).
# Базовый образ — Debian bookworm, в нём pandoc 2.17 (>= 2.14.2 → RTF на вход работает).
FROM python:3.12-slim

# Системный pandoc — единственный путь установки (не дублировать pypandoc_binary).
RUN apt-get update \
    && apt-get install -y --no-install-recommends pandoc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запуск не от root.
RUN useradd --create-home app && chown -R app /app
USER app

# Токены — из окружения контейнера (.env не копировать в образ; см. .dockerignore).
CMD ["python", "-m", "src.bot"]
