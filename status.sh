
#!/bin/bash

# 📊 Script para verificar el estado de todos los servicios de Thunderrol

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "$(echo "$1" | sed 's/./=/g')"
}

check_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    if curl -s "$url" | grep -q "$expected"; then
        echo -e "  ✅ ${GREEN}$name${NC}: Funcionando correctamente"
        return 0
    else
        echo -e "  ❌ ${RED}$name${NC}: No responde o error"
        return 1
    fi
}

check_port() {
    local name=$1
    local port=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        echo -e "  ✅ ${GREEN}$name${NC}: Puerto $port está en uso"
        return 0
    else
        echo -e "  ❌ ${RED}$name${NC}: Puerto $port no está en uso"
        return 1
    fi
}

check_postgres() {
    if pg_isready -h localhost -p 5432 -U thunderrol -q 2>/dev/null; then
        echo -e "  ✅ ${GREEN}PostgreSQL${NC}: Conectado correctamente"
        
        # Verificar datos
        local user_count=$(psql -h localhost -U thunderrol -d thunderrol -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
        if [ "$user_count" -gt 0 ]; then
            echo -e "  ✅ ${GREEN}Base de Datos${NC}: $user_count usuarios encontrados"
        else
            echo -e "  ⚠️  ${YELLOW}Base de Datos${NC}: Sin datos (ejecuta ./reset_db.sh)"
        fi
        return 0
    else
        echo -e "  ❌ ${RED}PostgreSQL${NC}: No conectado"
        return 1
    fi
}

echo "📊 Estado de Thunderrol - Sistema de Trazabilidad"
echo "=================================================="

# Verificar PostgreSQL
print_header "🗄️ Base de Datos"
check_postgres
echo

# Verificar servicios por puerto
print_header "🚀 Servicios"
check_port "Backend (FastAPI)" 8000
check_port "Frontend (Next.js)" 3000
echo

# Verificar endpoints
print_header "🌐 Endpoints"
check_service "Backend Health" "http://localhost:8000/health" "ok"
check_service "Frontend" "http://localhost:3000" "html"
check_service "API Docs" "http://localhost:8000/docs" "swagger"
echo

# Verificar procesos
print_header "⚙️ Procesos"
if pgrep -f "uvicorn app.main:app" >/dev/null; then
    echo -e "  ✅ ${GREEN}Backend Process${NC}: Ejecutándose (PID: $(pgrep -f 'uvicorn app.main:app'))"
else
    echo -e "  ❌ ${RED}Backend Process${NC}: No está ejecutándose"
fi

if pgrep -f "next-server" >/dev/null || pgrep -f "node.*next" >/dev/null; then
    echo -e "  ✅ ${GREEN}Frontend Process${NC}: Ejecutándose (PID: $(pgrep -f 'next-server\|node.*next' | head -1))"
else
    echo -e "  ❌ ${RED}Frontend Process${NC}: No está ejecutándose"
fi
echo

# Verificar archivos de configuración
print_header "📁 Configuración"
if [ -f "/home/ubuntu/thunderrol/backend/.env" ]; then
    echo -e "  ✅ ${GREEN}Backend .env${NC}: Encontrado"
else
    echo -e "  ❌ ${RED}Backend .env${NC}: No encontrado"
fi

if [ -f "/home/ubuntu/thunderrol/frontend/app/.env.local" ]; then
    echo -e "  ✅ ${GREEN}Frontend .env.local${NC}: Encontrado"
else
    echo -e "  ❌ ${RED}Frontend .env.local${NC}: No encontrado"
fi

if [ -d "/home/ubuntu/thunderrol/backend/venv" ]; then
    echo -e "  ✅ ${GREEN}Python venv${NC}: Configurado"
else
    echo -e "  ❌ ${RED}Python venv${NC}: No encontrado"
fi

if [ -d "/home/ubuntu/thunderrol/frontend/app/node_modules" ]; then
    echo -e "  ✅ ${GREEN}Node modules${NC}: Instalado"
else
    echo -e "  ❌ ${RED}Node modules${NC}: No instalado"
fi

echo
print_header "🎯 Accesos Rápidos"
echo "  🌐 Frontend:  http://localhost:3000"
echo "  🔧 Backend:   http://localhost:8000"
echo "  📚 API Docs:  http://localhost:8000/docs"
echo "  🗄️ DB Admin:  yarn prisma studio (en frontend/app/)"
echo

print_header "🔑 Credenciales de Prueba"
echo "  admin@thunderrol.com / admin123 (ADMIN)"
echo "  inventario@thunderrol.com / inv123 (MANAGER)"
echo "  taller@thunderrol.com / taller123 (OPERATOR)"
echo "  ventas@thunderrol.com / ventas123 (VIEWER)"
