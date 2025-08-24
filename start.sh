
#!/bin/bash

# 🚀 Script de inicio completo para Thunderrol
# Ejecuta backend y frontend en modo desarrollo

set -e  # Salir si hay algún error

echo "🚀 Iniciando Thunderrol - Sistema de Trazabilidad de Inventario"
echo "============================================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con colores
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar PostgreSQL
print_status "Verificando PostgreSQL..."
if ! pg_isready -h localhost -p 5432 -U thunderrol -q; then
    print_error "PostgreSQL no está corriendo o no es accesible"
    echo "Intenta iniciar PostgreSQL:"
    echo "  sudo systemctl start postgresql  # Linux"
    echo "  brew services start postgresql  # macOS"
    exit 1
fi
print_success "PostgreSQL está corriendo"

# Verificar que existe el directorio del proyecto
PROJECT_ROOT="/home/ubuntu/thunderrol"
if [ ! -d "$PROJECT_ROOT" ]; then
    print_error "Directorio del proyecto no encontrado: $PROJECT_ROOT"
    exit 1
fi

cd "$PROJECT_ROOT"

# Verificar y activar entorno virtual del backend
print_status "Configurando backend..."
cd backend

if [ ! -d "venv" ]; then
    print_warning "Entorno virtual no encontrado. Creándolo..."
    python3 -m venv venv
fi

source venv/bin/activate

# Verificar dependencias del backend
if [ ! -f "venv/pyvenv.cfg" ] || [ ! -f "venv/lib/python*/site-packages/fastapi/__init__.py" ]; then
    print_warning "Instalando dependencias del backend..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Verificar migración de base de datos
print_status "Verificando migraciones de base de datos..."
if ! alembic current &>/dev/null; then
    print_warning "Ejecutando migraciones..."
    alembic upgrade head
fi

# Iniciar backend en segundo plano
print_status "Iniciando servidor backend en puerto 8000..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Esperar a que el backend inicie
sleep 5

# Verificar que el backend esté corriendo
if ! curl -s http://localhost:8000/health >/dev/null; then
    print_error "El backend no pudo iniciarse correctamente"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
print_success "Backend iniciado correctamente"

# Configurar frontend
print_status "Configurando frontend..."
cd ../frontend/app

# Verificar dependencias del frontend
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/next" ]; then
    print_warning "Instalando dependencias del frontend..."
    if command -v yarn >/dev/null 2>&1; then
        yarn install
    else
        npm install
    fi
fi

# Generar cliente de Prisma
print_status "Generando cliente de Prisma..."
if command -v yarn >/dev/null 2>&1; then
    yarn prisma generate >/dev/null 2>&1
else
    npm run prisma generate >/dev/null 2>&1
fi

# Iniciar frontend en segundo plano
print_status "Iniciando servidor frontend en puerto 3000..."
if command -v yarn >/dev/null 2>&1; then
    yarn dev &
    FRONTEND_PID=$!
else
    npm run dev &
    FRONTEND_PID=$!
fi

# Esperar a que el frontend inicie
sleep 8

echo
print_success "🎉 Thunderrol iniciado correctamente!"
echo "=============================================="
echo -e "📱 ${GREEN}Frontend:${NC}  http://localhost:3000"
echo -e "🔧 ${GREEN}Backend:${NC}   http://localhost:8000" 
echo -e "📚 ${GREEN}API Docs:${NC}  http://localhost:8000/docs"
echo
echo -e "${YELLOW}Credenciales de prueba:${NC}"
echo "  admin@thunderrol.com / admin123 (ADMIN)"
echo "  inventario@thunderrol.com / inv123 (MANAGER)"
echo "  taller@thunderrol.com / taller123 (OPERATOR)"
echo "  ventas@thunderrol.com / ventas123 (VIEWER)"
echo
echo -e "${BLUE}Para detener los servicios:${NC} Presiona Ctrl+C"

# Función para limpiar procesos al salir
cleanup() {
    echo
    print_status "🛑 Deteniendo servicios..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    
    # Esperar a que los procesos terminen
    sleep 2
    
    # Forzar cierre si es necesario
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "next-server" 2>/dev/null || true
    
    print_success "Servicios detenidos"
    exit 0
}

# Capturar señales para limpiar correctamente
trap cleanup SIGINT SIGTERM EXIT

# Mantener el script corriendo
print_status "Servicios corriendo... (Ctrl+C para detener)"
wait
