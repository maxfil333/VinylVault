![](https://github.com/maxfil333/VinylVault/blob/master/web/website/data/other/VVlogo_solo_cr.png)

VinylVault — коллекция любимых альбомов: поиск по Last.fm, личная страница с обложками и порядком альбомов, аватар в S3/CDN.

Стек: FastAPI + Uvicorn, MongoDB (motor), Selectel S3 для аватаров, Docker Compose.

## Локальный запуск

```bash
cp .env.example .env          # заполнить API_KEY, s3_* и пароли Mongo
docker compose up -d --build
```

Приложение слушает `http://127.0.0.1:8000`. Состояние сервисов: `docker compose ps` — у `app` должно быть `healthy`
(проба ходит в `/health`, который отвечает 200 только при живой базе).

Админка Mongo поднимается отдельным профилем и только на localhost:

```bash
docker compose --profile dev up -d mongo-express   # http://localhost:8081/mongo
```

Smoke-тесты против поднятого стека (создают временного пользователя и убирают его за собой):

```bash
.venv/bin/python scripts/docker_smoke_test.py      # Windows: .venv\Scripts\python.exe scripts\docker_smoke_test.py
```

## Переменные окружения

Обязательные: `API_KEY` (Last.fm), `s3_user`, `s3_password`, `s3_access_key`, `s3_secret_key`, `s3_endpoint`,
`s3_base_domain`, `MONGO_ROOT_USER`, `MONGO_ROOT_PASSWORD`.

Настройки развёртывания (значения по умолчанию — в `.env.example`):

| Переменная | Назначение |
| --- | --- |
| `COOKIE_SECURE` | Флаг `Secure` у cookie сессии. На HTTPS обязателен `true`, локально по HTTP — `false` |
| `FORWARDED_ALLOW_IPS` | Чьим `X-Forwarded-*` верим. От этого зависят схема запроса и IP клиента для rate limit |
| `APP_BIND_HOST` | Интерфейс хоста для порта 8000. На сервере оставить `127.0.0.1` |
| `ENABLE_DOCS` | Публиковать `/docs`, `/redoc`, `/openapi.json`. На проде `false` |
| `LOG_LEVEL`, `LOG_ROTATION`, `LOG_RETENTION` | Логи в `/app/__logs` (volume `app_logs`) |
| `SEARCH_CACHE_TTL_SEC` | Время жизни кэша ответов Last.fm |
| `SESSION_TTL_SEC` | Срок сессии: TTL-индекс в Mongo и `Max-Age` cookie |

## Деплой на сервер за nginx

Ниже — краткая версия. Подробная пошаговая инструкция с разбором каждой команды и аргумента: [READMEdeploy.md](READMEdeploy.md).

1. Скопировать проект на сервер, заполнить `.env`. Для прода: `COOKIE_SECURE=true`, `ENABLE_DOCS=false`,
   `APP_BIND_HOST=127.0.0.1`, `FORWARDED_ALLOW_IPS=*`.

   `FORWARDED_ALLOW_IPS=*` безопасен только вместе с `APP_BIND_HOST=127.0.0.1`: до приложения дотягивается
   лишь nginx, поэтому подделать `X-Forwarded-Proto` или `X-Forwarded-For` извне нельзя. Если оставить
   заголовки недоверенными, cookie сессии уйдёт без `Secure`, а лимиты запросов схлопнутся в одну общую
   корзину на всех пользователей (все запросы будут выглядеть как один IP прокси).

2. Поднять стек: `docker compose up -d --build`. Наружу не публикуется ничего, кроме порта на localhost;
   MongoDB доступна только внутри compose-сети.

3. Настроить nginx по образцу `deploy/nginx.conf.example` (обязательны `X-Forwarded-Proto` и
   `client_max_body_size` под аватары) и выпустить сертификат:

   ```bash
   sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/vinylvault
   sudo ln -s /etc/nginx/sites-available/vinylvault /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d example.com
   ```

4. Проверить: `curl -s https://example.com/health` → `{"status":"ok","database":"up"}`, а в ответе на логин
   присутствует `Set-Cookie: ...; Secure`.

### Обновление версии

```bash
git pull
docker compose up -d --build
docker compose ps           # дождаться healthy
```

### Логи

```bash
docker compose logs -f app                       # поток stdout
docker compose exec app ls -la /app/__logs       # файлы с ротацией и retention
```

### Бэкап MongoDB

```bash
scripts/mongo_backup.sh                          # дамп в ./backups, чистка архивов старше 14 дней
```

Восстановление:

```bash
docker compose exec -T mongo mongorestore \
  --username "$MONGO_ROOT_USER" --password "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin \
  --archive --gzip --drop < backups/vinylvault-20260819-030000.archive.gz
```

Регулярный запуск из cron на сервере:

```cron
30 3 * * * /srv/VinylVault/scripts/mongo_backup.sh >> /var/log/vv-backup.log 2>&1
```
