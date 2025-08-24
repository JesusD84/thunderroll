
#!/bin/bash

# 🗄️ Script para resetear completamente la base de datos de Thunderrol
# CUIDADO: Esto eliminará todos los datos existentes

set -e

# Colores para output
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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🗄️ Reset de Base de Datos - Thunderrol"
echo "======================================"
print_warning "⚠️  ADVERTENCIA: Esto eliminará TODOS los datos existentes"
echo

# Confirmar con el usuario
read -p "¿Estás seguro de que quieres continuar? (escriba 'SI' para confirmar): " confirm

if [ "$confirm" != "SI" ]; then
    echo "Operación cancelada."
    exit 0
fi

PROJECT_ROOT="/home/ubuntu/thunderrol"
cd "$PROJECT_ROOT"

# Verificar PostgreSQL
print_status "Verificando PostgreSQL..."
if ! pg_isready -h localhost -p 5432 -U thunderrol -q; then
    print_error "PostgreSQL no está corriendo o no es accesible"
    exit 1
fi

# Backend - Resetear con Alembic
print_status "Reseteando tablas del backend (Alembic)..."
cd backend

if [ ! -d "venv" ]; then
    print_error "Entorno virtual no encontrado. Ejecuta el script de inicio primero."
    exit 1
fi

source venv/bin/activate

# Eliminar todas las migraciones (downgrade a base)
print_status "Eliminando todas las tablas..."
alembic downgrade base

# Recrear todas las migraciones (upgrade a head)
print_status "Recreando todas las tablas..."
alembic upgrade head

# Ejecutar seeds del backend
print_status "Poblando con datos iniciales del backend..."
python -m app.db.seed

print_success "Backend reseteado correctamente"

# Frontend - Resetear Prisma
print_status "Reseteando configuración de NextAuth (Prisma)..."
cd ../frontend/app

# Push del schema de Prisma (recrear tablas de NextAuth)
print_status "Sincronizando schema de Prisma..."
if command -v yarn >/dev/null 2>&1; then
    yarn prisma db push --force-reset
    yarn prisma generate
    
    # Ejecutar seeds de Prisma
    print_status "Poblando con datos iniciales de NextAuth..."
    yarn prisma db seed
else
    npm run prisma db push -- --force-reset
    npm run prisma generate
    
    # Ejecutar seeds de Prisma
    print_status "Poblando con datos iniciales de NextAuth..."
    npm run prisma db seed
fi

print_success "Frontend reseteado correctamente"

# Verificar datos creados
print_status "Verificando usuarios creados..."
psql -h localhost -U thunderrol -d thunderrol -c "
SELECT 
    email, 
    role, 
    status,
    created_at::date as created
FROM users 
ORDER BY role;
"

echo
print_success "🎉 Base de datos reseteada correctamente!"
echo "========================================"
echo -e "${YELLOW}Credenciales disponibles:${NC}"
echo "  admin@thunderrol.com / admin123 (ADMIN)"
echo "  inventario@thunderrol.com / inv123 (MANAGER)" 
echo "  taller@thunderrol.com / taller123 (OPERATOR)"
echo "  ventas@thunderrol.com / ventas123 (VIEWER)"
echo
echo "Para iniciar la aplicación, ejecuta: ./start.sh"
