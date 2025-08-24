
#!/bin/bash

# 🧪 Script para ejecutar todos los tests de Thunderrol

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🧪 Ejecutando Tests - Thunderrol"
echo "==============================="

PROJECT_ROOT="/home/ubuntu/thunderrol"
cd "$PROJECT_ROOT"

BACKEND_PASSED=true
FRONTEND_PASSED=true

# Tests del Backend
print_status "Ejecutando tests del backend..."
cd backend

if [ ! -d "venv" ]; then
    print_error "Entorno virtual no encontrado"
    BACKEND_PASSED=false
else
    source venv/bin/activate
    
    # Instalar dependencias de testing si no están
    pip install -q pytest pytest-asyncio httpx pytest-mock
    
    # Ejecutar tests
    if pytest tests/ -v --tb=short; then
        print_success "Tests del backend: PASARON"
    else
        print_error "Tests del backend: FALLARON"
        BACKEND_PASSED=false
    fi
fi

# Tests del Frontend
print_status "Ejecutando verificaciones del frontend..."
cd ../frontend/app

if [ ! -d "node_modules" ]; then
    print_error "Dependencias del frontend no instaladas"
    FRONTEND_PASSED=false
else
    # Linting
    print_status "Ejecutando linting..."
    if command -v yarn >/dev/null 2>&1; then
        if yarn lint; then
            print_success "Linting: PASÓ"
        else
            print_error "Linting: FALLÓ"
            FRONTEND_PASSED=false
        fi
        
        # Type checking
        print_status "Verificando tipos TypeScript..."
        if yarn type-check; then
            print_success "Type checking: PASÓ"
        else
            print_error "Type checking: FALLÓ" 
            FRONTEND_PASSED=false
        fi
        
        # Build test
        print_status "Probando build de producción..."
        if yarn build; then
            print_success "Build: PASÓ"
        else
            print_error "Build: FALLÓ"
            FRONTEND_PASSED=false
        fi
    else
        if npm run lint; then
            print_success "Linting: PASÓ"
        else
            print_error "Linting: FALLÓ"
            FRONTEND_PASSED=false
        fi
        
        if npm run type-check; then
            print_success "Type checking: PASÓ"
        else
            print_error "Type checking: FALLÓ"
            FRONTEND_PASSED=false
        fi
        
        if npm run build; then
            print_success "Build: PASÓ"
        else
            print_error "Build: FALLÓ"
            FRONTEND_PASSED=false
        fi
    fi
fi

# Resumen
echo
echo "📊 Resumen de Tests"
echo "=================="

if [ "$BACKEND_PASSED" = true ]; then
    print_success "✅ Backend: Todos los tests pasaron"
else
    print_error "❌ Backend: Algunos tests fallaron"
fi

if [ "$FRONTEND_PASSED" = true ]; then
    print_success "✅ Frontend: Todas las verificaciones pasaron"
else
    print_error "❌ Frontend: Algunas verificaciones fallaron"
fi

if [ "$BACKEND_PASSED" = true ] && [ "$FRONTEND_PASSED" = true ]; then
    echo
    print_success "🎉 ¡Todos los tests pasaron!"
    exit 0
else
    echo
    print_error "❌ Algunos tests fallaron. Revisar los errores arriba."
    exit 1
fi
