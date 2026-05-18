.PHONY: help install dev test backend frontend openapi kb-update lint build deploy down logs migrate

SHELL := /bin/bash

help:
	@echo "Remote GTNH Control — Make targets"
	@echo "  install       — backend venv + npm install"
	@echo "  dev           — docker compose up -d"
	@echo "  test          — pytest in server/"
	@echo "  backend       — uvicorn dev server (foreground)"
	@echo "  frontend      — vite dev server"
	@echo "  openapi       — regenerate website/src/api/generated/schema.d.ts"
	@echo "  kb-update     — re-fetch wiki/docs into kb/"
	@echo "  migrate       — alembic upgrade head"
	@echo "  build         — docker compose build"
	@echo "  deploy        — git pull + docker compose up -d --build"
	@echo "  down          — docker compose down"
	@echo "  logs          — docker compose logs -f backend"

install:
	cd server && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
	cd website && npm install
	cd tools/kb-fetch && pip install -r requirements.txt

dev:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f backend

build:
	docker compose build

deploy:
	git pull --ff-only
	docker compose up -d --build
	@echo "Done. Check: make logs"

test:
	cd server && . .venv/bin/activate && pytest

backend:
	cd server && . .venv/bin/activate && python run.py --reload

frontend:
	cd website && npm run dev

openapi:
	cd server && . .venv/bin/activate && SERVER_TOKEN=$${SERVER_TOKEN:-dev} python scripts/dump_openapi.py
	cd website && npm run openapi:generate

kb-update:
	cd tools/kb-fetch && python fetch.py --config sources.yaml

migrate:
	cd server && . .venv/bin/activate && alembic upgrade head

lint:
	cd website && npm run lint
