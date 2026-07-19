# Dockerfile — образ для продового сервера
#
# Отличие от dev:
#   Dev использует volumes (./src:/app) — код берётся с хоста
#   Прод копирует код внутрь образа (COPY src/ .) — образ самодостаточный

FROM python:3.12-slim

# Системные зависимости
# libpq-dev нужен для psycopg2 (PostgreSQL драйвер)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала копируем только requirements.txt — слой кешируется
# и не пересобирается если код изменился но зависимости нет
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY src/ .

# Создаём непривилегированного пользователя — не запускаем от root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser