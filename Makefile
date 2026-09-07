.DEFAULT_GOAL := help
.PHONY: help run worker beat mig makemig seed superuser test lint fmt up down logs

PY := uv run
MANAGE := $(PY) manage.py

help: ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# --- приложение ---

run: ## Dev-сервер Django
	$(MANAGE) runserver

worker: ## Celery worker
	$(PY) celery -A config worker -l info

beat: ## Celery beat
	$(PY) celery -A config beat -l info

# --- база данных ---

mig: ## Применить миграции
	$(MANAGE) migrate

makemig: ## Сгенерировать миграции
	$(MANAGE) makemigrations

seed: ## Загрузить справочник валют
	$(MANAGE) loaddata currencies

superuser: ## Создать суперпользователя
	$(MANAGE) createsuperuser

# --- качество ---

test: ## Прогнать тесты
	$(PY) pytest

lint: ## Линтеры и типы
	$(PY) ruff check .
	$(PY) mypy .

fmt: ## Форматирование и автофиксы
	$(PY) ruff format .
	$(PY) ruff check . --fix

# --- docker ---

up: ## Поднять docker compose
	docker compose up --build -d

down: ## Остановить docker compose
	docker compose down

logs: ## Логи web и worker
	docker compose logs -f web worker