FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry-cache

RUN pip install --no-cache-dir poetry \
    && poetry --version

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main --no-root --no-ansi \
    && rm -rf "$POETRY_CACHE_DIR"

COPY . .

STOPSIGNAL SIGINT

CMD ["python", "main.py"]