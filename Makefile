BACKEND_DIR := backend
FRONTEND_DIR := frontend
PYTHON := python3

.PHONY: install backend-install frontend-install run-backend run-frontend lint backend-lint frontend-lint

install: backend-install frontend-install

backend-install:
	cd $(BACKEND_DIR) && pip install -r requirements.dev.txt

frontend-install:
	cd $(FRONTEND_DIR) && npm install

run-backend:
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

run-frontend:
	cd $(FRONTEND_DIR) && npm run dev

lint: backend-lint frontend-lint

backend-lint:
	cd $(BACKEND_DIR) && ruff check app

frontend-lint:
	cd $(FRONTEND_DIR) && npm run lint
