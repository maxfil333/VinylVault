# Версия uv зафиксирована для воспроизводимой сборки
ARG UV_VERSION=0.12.5
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_NO_DEV=1

# Зеркало PyPI переопределяется при сборке: --build-arg UV_INDEX_URL=...
ARG UV_INDEX_URL=https://pypi.org/simple/

WORKDIR /app

# 1. Копируем бинарный файл uv из официального образа
COPY --from=uv /uv /usr/local/bin/uv

# 2. Создаем виртуальное окружение и добавляем его в PATH
RUN uv venv /opt/venv --python python3.13
ENV PATH="/opt/venv/bin:$PATH"

# 3. Сначала копируем только файлы зависимостей (для оптимизации кэша Docker)
COPY pyproject.toml uv.lock /app/

# 4. Устанавливаем зависимости
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --python python3.13

COPY . /app

# 5. Непривилегированный пользователь; каталог логов должен быть ему доступен на запись
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /app/__logs \
    && chown -R app:app /app
USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"

CMD ["python", "-m", "main"]
