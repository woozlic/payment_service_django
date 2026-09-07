# Payment Service

REST-сервис для управления заявками на выплату средств. Заявка создаётся через API, обрабатывается асинхронно Celery-воркером.

**Стек:** Python 3.12, Django 6, DRF, Celery + Redis, PostgreSQL, uv.

---

## Быстрый старт (Docker)

```bash
cp .env.example .env          # заполнить POSTGRES_* и DJANGO_SECRET_KEY
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata currencies
docker compose exec web python manage.py createsuperuser
```

Поднимаются пять сервисов: `db` (Postgres), `redis` (брокер + result backend), `web` (Django), `worker` (Celery), `beat`.

API доступно на http://localhost:8000/api/, админка — на http://localhost:8000/admin/.

Сгенерировать `DJANGO_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Локальный запуск (без Docker)

Нужны запущенные локально PostgreSQL и Redis, либо только они из compose:
`docker compose up -d db redis`.

### 1. Зависимости

Проект использует [uv](https://docs.astral.sh/uv/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

### 2. Переменные окружения

```bash
cp .env.example .env
```

| Переменная | Назначение | Пример |
|---|---|---|
| `DJANGO_SECRET_KEY` | ключ подписи Django | `<random 50 chars>` |
| `DJANGO_DEBUG` | режим отладки | `1` локально, `0` в проде |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | доступ к БД | `payments` / `payments` / `...` |
| `POSTGRES_HOST` / `POSTGRES_PORT` | адрес БД | `127.0.0.1` / `5432` |
| `REDIS_URL` | брокер Celery | `redis://127.0.0.1:6379` |

### 3. Миграции и стартовые данные

```bash
make mig          # uv run manage.py migrate
make seed         # справочник валют
make superuser    # пользователь для админки и получения токена
```

### 4. Приложение

```bash
make run          # uv run manage.py runserver
```

### 5. Celery

В отдельных терминалах:

```bash
make worker       # uv run celery -A config worker -l info
make beat         # uv run celery -A config beat -l info   (опционально)
```

`worker` обрабатывает заявки. `beat` раз в минуту подбирает «зависшие» в `pending` заявки — страховка на случай, если воркер был недоступен в момент создания.

### 6. Тесты и линтеры

```bash
make test         # uv run pytest
make lint         # uv run ruff check . && uv run mypy .
```

---

## Команды Makefile

| Команда | Действие |
|---|---|
| `make run` | dev-сервер Django |
| `make worker` | Celery worker |
| `make beat` | Celery beat |
| `make mig` | применить миграции |
| `make makemig` | сгенерировать миграции |
| `make seed` | загрузить справочник валют |
| `make superuser` | создать суперпользователя |
| `make test` | pytest |
| `make lint` | ruff + mypy |
| `make up` / `make down` | поднять / остановить docker compose |

---

## API

Аутентификация — JWT. Все эндпоинты выплат требуют авторизации; пользователь видит только свои заявки.

```bash
# получить токен
curl -X POST http://localhost:8000/api/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username": "tester", "password": "pass12345"}'

export TOKEN=<access>
```

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/api/payouts/` | список своих заявок (пагинация) |
| `GET` | `/api/payouts/{id}/` | заявка по идентификатору |
| `POST` | `/api/payouts/` | создать заявку |
| `PATCH` | `/api/payouts/{id}/` | частичное обновление (прежде всего — статус) |
| `DELETE` | `/api/payouts/{id}/` | удаление (soft delete) |
| `POST` | `/api/token/` | получить пару access/refresh |
| `POST` | `/api/token/refresh/` | обновить access |

### Создание заявки

```bash
curl -X POST http://localhost:8000/api/payouts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"amount": "100.50", "currency": "EUR", "receiver_wallet": "0x1234567890", "comment": "invoice #42"}'
```

```json
{
  "id": 1,
  "amount": "100.50",
  "currency": "EUR",
  "status": "pending",
  "receiver_wallet": "0x1234567890",
  "comment": "invoice #42",
  "created_at": "2026-09-07T10:15:00Z",
  "updated_at": "2026-09-07T10:15:00Z"
}
```

Заявка всегда создаётся в статусе `pending` — переданный клиентом `status` игнорируется. После коммита транзакции (`transaction.on_commit`) в очередь ставится задача `process_payout`, которая имитирует обработку и переводит заявку в `paid` или `failed`.

### Статусы и переходы

```
pending ──▶ paid      (терминальный)
   └────▶ failed ──▶ pending   (ручной ретрай)
```

Недопустимый переход отклоняется с 400. Заявка в терминальном статусе не редактируется и не удаляется.

### Формат ошибок

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input.",
    "details": {"amount": ["Amount must be positive"]}
  }
}
```

| Код | Когда |
|---|---|
| `400` | ошибка валидации, недопустимый переход статуса |
| `401` | нет или истёк токен |
| `403` | доступ к чужой заявке запрещён |
| `404` | заявки нет или она удалена |

### Валидация

- `amount` — Decimal > 0, до 2 знаков после запятой, ограничение продублировано `CheckConstraint` на уровне БД;
- `currency` — код из справочника валют;
- `receiver_wallet` — обязательное, 4–64 символа после `strip()`;
- `comment` — необязательное;
- `status` — read-only при создании, при обновлении проверяется по таблице переходов.

---


## Деплой в прод

### Необходимые сервисы

| Компонент | Роль 
|---|---|
| PostgreSQL |
| Redis | брокер и result backend Celery |
| Приложение Django | обработка HTTP |
| Celery worker | фоновая обработка выплат |
| Celery beat | периодические задачи |
| Nginx / ALB | TLS-терминация, статика, rate limiting |
| Sentry + Prometheus/Grafana | ошибки и метрики |

### Запуск процессов

Web — gunicorn, число воркеров ≈ `2 × CPU + 1`, за реверс-прокси:

```bash
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 --workers 5 --timeout 60 --access-logfile -
```

Celery — отдельный процесс/контейнер, никогда не в одном контейнере с web:

```bash
celery -A config worker -l info --concurrency 4 --max-tasks-per-child 500
celery -A config beat -l info
```

### Подготовка окружения — минимальные шаги

1. Создать managed PostgreSQL и Redis, закрыть их в приватную сеть.
2. Завести секреты (`DJANGO_SECRET_KEY`, доступы к БД) в vault / secret manager — не в образе и не в репозитории.
3. Собрать образ из `Dockerfile`, запушить в реестр, тег = git sha.
4. Прогнать `python manage.py migrate` отдельным шагом до выкатки нового кода. Миграции пишутся обратно совместимыми, чтобы старая и новая версии приложения могли работать на одной схеме во время раскатки.
5. `python manage.py collectstatic`, статика — на Nginx или в S3/CDN.
6. Выкатить `web` и `worker`, проверить `/health/` и что воркер виден в `celery -A config inspect ping`.

### Настройки продакшн-окружения

`DEBUG=0`, заполненный `ALLOWED_HOSTS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, логи в JSON в stdout. Проверяется командой `python manage.py check --deploy`.

### CI/CD

На каждый PR: `ruff check`, `mypy`, `pytest` на сервисном Postgres + Redis. На merge в `main`: сборка и пуш образа, применение миграций, rolling update. Откат — на предыдущий тег образа.

---
