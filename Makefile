
# 🚀 Makefile para Thunderrol - Sistema de Trazabilidad de Inventario

.PHONY: help start stop status test reset-db install-deps dev-backend dev-frontend build lint clean

# Variables
PROJECT_ROOT := $(shell pwd)
BACKEND_DIR := $(PROJECT_ROOT)/backend
FRONTEND_DIR := $(PROJECT_ROOT)/frontend/app

# Colores
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Ayuda
help: ## Mostrar esta ayuda
	@echo "$(BLUE)🚀 Thunderrol - Comandos disponibles$(NC)"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Comandos principales
start: ## Iniciar todos los servicios (backend + frontend)
	@echo "$(BLUE)🚀 Iniciando Thunderrol...$(NC)"
	@./start.sh

stop: ## Detener todos los servicios
	@echo "$(YELLOW)🛑 Deteniendo servicios...$(NC)"
	@pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@pkill -f "next-server" 2>/dev/null || true
	@pkill -f "node.*next" 2>/dev/null || true
	@echo "$(GREEN)✅ Servicios detenidos$(NC)"

status: ## Verificar estado de todos los servicios
	@./status.sh

test: ## Ejecutar todos los tests
	@./test.sh

reset-db: ## Resetear completamente la base de datos
	@./reset_db.sh

# Instalación y configuración
install-deps: install-backend install-frontend ## Instalar todas las dependencias

install-backend: ## Instalar dependencias del backend
	@echo "$(BLUE)📦 Instalando dependencias del backend...$(NC)"
	@cd $(BACKEND_DIR) && python3 -m venv venv || true
	@cd $(BACKEND_DIR) && source venv/bin/activate && pip install --upgrade pip
	@cd $(BACKEND_DIR) && source venv/bin/activate && pip install -r requirements.txt
	@echo "$(GREEN)✅ Backend configurado$(NC)"

install-frontend: ## Instalar dependencias del frontend
	@echo "$(BLUE)📦 Instalando dependencias del frontend...$(NC)"
	@cd $(FRONTEND_DIR) && (yarn install || npm install)
	@cd $(FRONTEND_DIR) && (yarn prisma generate || npm run prisma generate)
	@echo "$(GREEN)✅ Frontend configurado$(NC)"

# Desarrollo individual
dev-backend: ## Ejecutar solo el backend en modo desarrollo
	@echo "$(BLUE)🔧 Iniciando backend...$(NC)"
	@cd $(BACKEND_DIR) && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Ejecutar solo el frontend en modo desarrollo  
	@echo "$(BLUE)⚛️ Iniciando frontend...$(NC)"
	@cd $(FRONTEND_DIR) && (yarn dev || npm run dev)

# Build y producción
build: build-frontend ## Construir para producción
	@echo "$(GREEN)✅ Build completado$(NC)"

build-frontend: ## Build del frontend
	@echo "$(BLUE)🏗️ Construyendo frontend...$(NC)"
	@cd $(FRONTEND_DIR) && (yarn build || npm run build)

# Linting y formateo
lint: lint-backend lint-frontend ## Ejecutar linting en todo el proyecto

lint-backend: ## Linting del backend
	@echo "$(BLUE)🔍 Linting backend...$(NC)"
	@cd $(BACKEND_DIR) && source venv/bin/activate && (ruff app/ || echo "Ruff no instalado, usando flake8 como fallback") && (black --check app/ || echo "Black no instalado")

lint-frontend: ## Linting del frontend
	@echo "$(BLUE)🔍 Linting frontend...$(NC)"
	@cd $(FRONTEND_DIR) && (yarn lint || npm run lint)

format: format-backend format-frontend ## Formatear código

format-backend: ## Formatear código del backend
	@echo "$(BLUE)🎨 Formateando backend...$(NC)"
	@cd $(BACKEND_DIR) && source venv/bin/activate && (black app/ || echo "Black no instalado")

format-frontend: ## Formatear código del frontend
	@echo "$(BLUE)🎨 Formateando frontend...$(NC)"
	@cd $(FRONTEND_DIR) && (yarn lint --fix || npm run lint -- --fix)

# Base de datos
migrate: ## Ejecutar migraciones de base de datos
	@echo "$(BLUE)🗄️ Ejecutando migraciones...$(NC)"
	@cd $(BACKEND_DIR) && source venv/bin/activate && alembic upgrade head

create-migration: ## Crear nueva migración (usar: make create-migration DESC="descripción")
	@echo "$(BLUE)📝 Creando migración: $(DESC)...$(NC)"
	@cd $(BACKEND_DIR) && source venv/bin/activate && alembic revision --autogenerate -m "$(DESC)"

seed-db: ## Poblar base de datos con datos iniciales
	@echo "$(BLUE)🌱 Poblando base de datos...$(NC)"
	@cd $(BACKEND_DIR) && source venv/bin/activate && python -m app.db.seed
	@cd $(FRONTEND_DIR) && (yarn prisma db seed || npm run prisma db seed)

# Herramientas de desarrollo
prisma-studio: ## Abrir Prisma Studio para administrar la base de datos
	@echo "$(BLUE)🗄️ Abriendo Prisma Studio...$(NC)"
	@cd $(FRONTEND_DIR) && (yarn prisma studio || npm run prisma studio)

logs-backend: ## Mostrar logs del backend
	@tail -f $(BACKEND_DIR)/logs/*.log 2>/dev/null || echo "No hay archivos de log encontrados"

logs-frontend: ## Mostrar logs del frontend
	@echo "$(YELLOW)Los logs del frontend aparecen en la consola donde se ejecuta$(NC)"

# Limpieza
clean: ## Limpiar archivos temporales y caches
	@echo "$(BLUE)🧹 Limpiando archivos temporales...$(NC)"
	@cd $(BACKEND_DIR) && find . -name "*.pyc" -delete
	@cd $(BACKEND_DIR) && find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@cd $(FRONTEND_DIR) && rm -rf .next
	@echo "$(GREEN)✅ Limpieza completada$(NC)"

clean-all: clean ## Limpieza completa incluyendo node_modules y venv
	@echo "$(YELLOW)⚠️ Limpieza completa (eliminará node_modules y venv)...$(NC)"
	@cd $(BACKEND_DIR) && rm -rf venv
	@cd $(FRONTEND_DIR) && rm -rf node_modules yarn.lock package-lock.json
	@echo "$(GREEN)✅ Limpieza completa realizada$(NC)"

# Verificaciones de salud
health-check: ## Verificar que todos los servicios estén funcionando
	@echo "$(BLUE)🏥 Verificando salud de servicios...$(NC)"
	@curl -s http://localhost:8000/health | jq '.' || echo "$(RED)Backend no responde$(NC)"
	@curl -s http://localhost:3000 >/dev/null && echo "$(GREEN)Frontend OK$(NC)" || echo "$(RED)Frontend no responde$(NC)"

# Docker (alternativo)
docker-start: ## Iniciar con Docker Compose
	@echo "$(BLUE)🐳 Iniciando con Docker...$(NC)"
	@docker-compose up --build

docker-stop: ## Detener Docker Compose
	@echo "$(BLUE)🐳 Deteniendo Docker...$(NC)"
	@docker-compose down

docker-logs: ## Ver logs de Docker
	@docker-compose logs -f

# Información útil
info: ## Mostrar información del sistema
	@echo "$(BLUE)ℹ️ Información del Sistema$(NC)"
	@echo "=========================="
	@echo "Node.js: $$(node --version 2>/dev/null || echo 'No instalado')"
	@echo "Python: $$(python3 --version 2>/dev/null || echo 'No instalado')"  
	@echo "PostgreSQL: $$(psql --version 2>/dev/null | head -1 || echo 'No instalado')"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'No instalado')"
	@echo ""
	@echo "$(GREEN)Puertos utilizados:$(NC)"
	@echo "  Frontend: 3000"
	@echo "  Backend:  8000"
	@echo "  PostgreSQL: 5432"

# Atajos útiles
up: start ## Alias para start
down: stop ## Alias para stop
restart: stop start ## Reiniciar servicios
rebuild: clean install-deps start ## Reconstruir y reiniciar todo
