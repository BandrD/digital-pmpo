FROM python:3.10.18-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Устанавливаем Poetry
RUN pip install --no-cache-dir poetry

# Копируем только конфиги
COPY pyproject.toml poetry.lock* /app/

# Устанавливаем зависимости
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# Копируем весь проект
COPY . /app

# Корень Минцифры нужен для https://platform-api2.max.ru. Проверку TLS не отключаем.
RUN cp /app/bot/certs/russian_trusted_root_ca.pem /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \
    && update-ca-certificates

# Запуск бота
CMD ["python", "-m", "bot.main"]
