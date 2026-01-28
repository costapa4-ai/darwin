.PHONY: help build up down restart logs clean test health

help: ## Show this help message
	@echo '🧬 Darwin System - Commands'
	@echo ''
	@echo 'Usage:'
	@echo '  make [command]'
	@echo ''
	@echo 'Commands:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

build: ## Build all containers
	docker-compose build

up: ## Start all services
	docker-compose up -d
	@echo ''
	@echo '✅ Darwin System is starting...'
	@echo ''
	@echo 'Frontend: http://localhost:3000'
	@echo 'Backend:  http://localhost:8000'
	@echo 'API Docs: http://localhost:8000/docs'
	@echo ''
	@echo 'Run "make logs" to see logs'

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Show logs (all services)
	docker-compose logs -f

logs-backend: ## Show backend logs only
	docker-compose logs -f backend

logs-frontend: ## Show frontend logs only
	docker-compose logs -f frontend

clean: ## Stop and remove all containers, volumes, and data
	docker-compose down -v
	rm -rf data/*.db logs/*.log
	@echo '✅ Cleaned all data and logs'

test: ## Run health checks
	@echo 'Testing backend health...'
	@curl -s http://localhost:8000/api/health | json_pp || echo '❌ Backend not responding'
	@echo ''
	@echo 'Testing frontend...'
	@curl -s http://localhost:3000 > /dev/null && echo '✅ Frontend OK' || echo '❌ Frontend not responding'

health: ## Check system health
	@curl -s http://localhost:8000/api/health

metrics: ## Get system metrics
	@curl -s http://localhost:8000/api/metrics | json_pp

setup: ## Initial setup (copy .env.example to .env)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo '✅ Created .env file'; \
		echo '⚠️  Please edit .env and add your API keys!'; \
	else \
		echo '.env already exists'; \
	fi

dev: ## Start in development mode with logs
	docker-compose up --build

prod: ## Start in production mode (detached)
	docker-compose up -d --build

ps: ## Show running containers
	docker-compose ps

stats: ## Show container stats
	docker stats

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend /bin/sh

install: setup build ## Complete installation (setup + build)
	@echo ''
	@echo '✅ Installation complete!'
	@echo ''
	@echo 'Next steps:'
	@echo '1. Edit .env and add your API keys'
	@echo '2. Run: make up'
	@echo '3. Open: http://localhost:3000'

start: up ## Alias for 'up'

stop: down ## Alias for 'down'

rebuild: ## Rebuild and restart everything
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

# Development helpers
format-backend: ## Format backend Python code
	docker-compose exec backend black .

lint-backend: ## Lint backend Python code
	docker-compose exec backend flake8 .

format-frontend: ## Format frontend code
	docker-compose exec frontend npm run format

# Database
db-reset: ## Reset database
	docker-compose down
	rm -rf data/*.db
	docker-compose up -d
	@echo '✅ Database reset complete'

# Backup
backup: ## Backup database
	mkdir -p backups
	cp data/darwin.db backups/darwin_$(shell date +%Y%m%d_%H%M%S).db
	@echo '✅ Backup created in backups/'

# Task testing
create-test-task: ## Create a test task via API
	curl -X POST http://localhost:8000/api/tasks \
		-H "Content-Type: application/json" \
		-d '{"description": "criar função que calcula fatorial", "type": "algorithm"}'

list-tasks: ## List all tasks
	curl -s http://localhost:8000/api/tasks | json_pp
