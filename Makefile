UV ?= uv
PYTHON ?= $(UV) run python
DJANGO_MANAGE = $(PYTHON) src/manage.py

.PHONY: setup fmt lint test runserver migrate makemigrations shell collectstatic compose-up compose-down

setup:
	$(UV) sync --dev

fmt:
	$(UV) run black src
	$(UV) run isort src

lint:
	$(UV) run ruff check src
	$(UV) run black --check src
	$(UV) run isort --check-only src

test:
	$(UV) run pytest -q

runserver:
	$(DJANGO_MANAGE) runserver 0.0.0.0:8000

migrate:
	$(DJANGO_MANAGE) migrate

makemigrations:
	$(DJANGO_MANAGE) makemigrations

shell:
	$(DJANGO_MANAGE) shell

collectstatic:
	$(DJANGO_MANAGE) collectstatic --noinput

compose-up:
	docker compose up -d

compose-down:
	docker compose down
