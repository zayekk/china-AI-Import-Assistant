# ===========================================
# China AI Import Assistant - Makefile
# ===========================================

.PHONY: help install-backend install-frontend dev-backend dev-frontend test docker-up docker-down migrate

help:
	@echo "Commandes disponibles :"
	@echo "  make install-backend   - Installe les dépendances Python + Playwright"
	@echo "  make install-frontend  - Installe les dépendances npm"
	@echo "  make dev-backend       - Démarre l'API FastAPI en mode développement"
	@echo "  make dev-frontend      - Démarre le frontend Vite en mode développement"
	@echo "  make test              - Lance tous les tests (pytest)"
	@echo "  make migrate           - Applique les migrations Alembic"
	@echo "  make docker-up         - Démarre tous les services via docker-compose"
	@echo "  make docker-down       - Arrête tous les services docker"

install-backend:
	cd backend && python3 -m venv venv && \
	. venv/bin/activate && \
	pip install -r requirements.txt && \
	python -m playwright install --with-deps chromium

install-frontend:
	cd frontend && npm install

dev-backend:
	cd backend && . venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	pytest tests/ -v

migrate:
	cd backend && . venv/bin/activate && alembic upgrade head

docker-up:
	docker compose up --build

docker-down:
	docker compose down
