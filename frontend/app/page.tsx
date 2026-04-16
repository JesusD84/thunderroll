
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Package, 
  Warehouse, 
  Wrench, 
  Building, 
  DollarSign, 
  TrendingUp,
  AlertTriangle,
  Activity,
  Plus,
  Truck
} from 'lucide-react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface DashboardData {
  units: {
    total: number;
    available: number;
    sold: number;
    in_transit: number;
  };
  locations: { total: number };
  transfers: { active: number };
  recent_movements: {
    id: number;
    unit_engine: string | null;
    movement_type: string;
    from_location: string | null;
    to_location: string | null;
    user: string | null;
    date: string;
  }[];
  inventory_by_location: { location: string; count: number }[];
  inventory_by_brand: { brand: string; count: number }[];
  sales_by_month: { month: string | null; count: number }[];
  recent_imports: {
    id: number;
    filename: string;
    total_records: number;
    successful: number;
    failed: number;
    date: string;
    user: string | null;
  }[];
}

const movementTypeLabels: Record<string, string> = {
  'import': 'Importación',
  'sale': 'Venta',
  'transfer': 'Transferencia',
  'return': 'Devolución',
  'adjustment': 'Ajuste',
};

const movementTypeIcons: Record<string, string> = {
  'import': 'IMPORT',
  'sale': 'SALE',
  'transfer': 'TRANSFER',
  'return': 'TRANSFER',
  'adjustment': 'IDENTIFICATION',
};

export default function DashboardPage() {
  const { data: session } = useSession();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboard = async () => {
      const token = (session as any)?.accessToken;
      if (!token) return;

      try {
        const res = await fetch(`${API_URL}/api/v1/reports/dashboard`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });

        if (!res.ok) throw new Error(`Error ${res.status}`);

        const data: DashboardData = await res.json();
        setDashboardData(data);
      } catch (err: any) {
        console.error('Error fetching dashboard:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, [session]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div>Cargando dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-600">Error cargando dashboard: {error}</div>
      </div>
    );
  }

  const units = dashboardData?.units;
  const locationData = dashboardData?.inventory_by_location || [];
  const brandData = dashboardData?.inventory_by_brand || [];
  const movements = dashboardData?.recent_movements || [];

  const formatMovementDescription = (m: DashboardData['recent_movements'][0]) => {
    const engine = m.unit_engine || 'Unidad';
    const type = movementTypeLabels[m.movement_type] || m.movement_type;
    if (m.movement_type === 'transfer' && m.from_location && m.to_location) {
      return `${engine} transferida de ${m.from_location} a ${m.to_location}`;
    }
    if (m.movement_type === 'sale') {
      return `${engine} vendida${m.from_location ? ` en ${m.from_location}` : ''}`;
    }
    if (m.movement_type === 'import') {
      return `${engine} importada${m.to_location ? ` a ${m.to_location}` : ''}`;
    }
    return `${type}: ${engine}`;
  };

  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays > 0) return `Hace ${diffDays} día${diffDays > 1 ? 's' : ''}`;
    if (diffHours > 0) return `Hace ${diffHours} hora${diffHours > 1 ? 's' : ''}`;
    if (diffMins > 0) return `Hace ${diffMins} min`;
    return 'Justo ahora';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-gray-600">Sistema de Trazabilidad de Inventario - Thunderrol</p>
            </div>
            <div className="flex space-x-2">
              <Link href="/imports">
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Importar Inventario
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* KPIs Principales */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          <Card>
            <CardContent className="flex items-center p-6">
              <Package className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">{units?.total || 0}</div>
                <div className="text-sm text-gray-600">Total de Unidades</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center p-6">
              <Warehouse className="h-8 w-8 text-yellow-600" />
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">{units?.available || 0}</div>
                <div className="text-sm text-gray-600">Disponibles</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center p-6">
              <Truck className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">{units?.in_transit || 0}</div>
                <div className="text-sm text-gray-600">En Tránsito</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center p-6">
              <DollarSign className="h-8 w-8 text-purple-600" />
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">{units?.sold || 0}</div>
                <div className="text-sm text-gray-600">Vendidas</div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Inventario por Ubicación */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Building className="mr-2 h-5 w-5" />
                Distribución por Ubicación
              </CardTitle>
              <CardDescription>Unidades por ubicación actual</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {locationData.map((item) => (
                  <div key={item.location} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {item.location.toLowerCase().includes('almac') && <Warehouse className="h-4 w-4 text-yellow-600" />}
                      {item.location.toLowerCase().includes('taller') && <Wrench className="h-4 w-4 text-blue-600" />}
                      {item.location.toLowerCase().includes('sucursal') && <Building className="h-4 w-4 text-green-600" />}
                      {!item.location.toLowerCase().includes('almac') && 
                       !item.location.toLowerCase().includes('taller') && 
                       !item.location.toLowerCase().includes('sucursal') && <Package className="h-4 w-4 text-gray-600" />}
                      <span className="text-sm">{item.location}</span>
                    </div>
                    <div className="text-xl font-bold">{item.count}</div>
                  </div>
                ))}
                {locationData.length === 0 && (
                  <div className="text-sm text-gray-500">No hay datos de ubicación</div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Inventario por Marca */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Activity className="mr-2 h-5 w-5" />
                Inventario por Marca
              </CardTitle>
              <CardDescription>Distribución actual por marca</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {brandData.map((item) => (
                  <div key={item.brand} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline">{item.brand}</Badge>
                    </div>
                    <div className="text-2xl font-bold">{item.count}</div>
                  </div>
                ))}
                {brandData.length === 0 && (
                  <div className="text-sm text-gray-500">No hay datos de marcas</div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Alertas y Notificaciones */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <AlertTriangle className="mr-2 h-5 w-5 text-orange-500" />
                Alertas
              </CardTitle>
              <CardDescription>Elementos que requieren atención</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {(units?.in_transit || 0) > 0 && (
                  <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                    <div>
                      <div className="font-medium text-blue-900">Unidades en Tránsito</div>
                      <div className="text-sm text-blue-700">{units?.in_transit} unidades en camino</div>
                    </div>
                    <Link href="/transfers">
                      <Button size="sm" variant="outline">Ver</Button>
                    </Link>
                  </div>
                )}

                {(dashboardData?.transfers?.active || 0) > 0 && (
                  <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                    <div>
                      <div className="font-medium text-yellow-900">Transferencias Activas</div>
                      <div className="text-sm text-yellow-700">{dashboardData?.transfers?.active} transferencias</div>
                    </div>
                    <Link href="/transfers">
                      <Button size="sm" variant="outline">Ver</Button>
                    </Link>
                  </div>
                )}

                {(units?.in_transit || 0) === 0 && (dashboardData?.transfers?.active || 0) === 0 && (
                  <div className="flex items-center p-3 bg-green-50 rounded-lg">
                    <div className="font-medium text-green-900">Todo en orden — sin alertas pendientes</div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Actividad Reciente */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <TrendingUp className="mr-2 h-5 w-5" />
                Actividad Reciente
              </CardTitle>
              <CardDescription>Últimos movimientos del sistema</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {movements.map((m) => {
                  const iconType = movementTypeIcons[m.movement_type] || 'IMPORT';
                  return (
                    <div key={m.id} className="flex items-start space-x-3">
                      <div className="flex-shrink-0">
                        {iconType === 'SALE' && <DollarSign className="h-5 w-5 text-green-600" />}
                        {iconType === 'TRANSFER' && <Truck className="h-5 w-5 text-blue-600" />}
                        {iconType === 'IDENTIFICATION' && <Wrench className="h-5 w-5 text-purple-600" />}
                        {iconType === 'IMPORT' && <Package className="h-5 w-5 text-orange-600" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900">
                          {formatMovementDescription(m)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatTimeAgo(m.date)} • {m.user || 'Sistema'}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {movements.length === 0 && (
                  <div className="text-sm text-gray-500">No hay movimientos recientes</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Acciones Rápidas */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Acciones Rápidas</CardTitle>
            <CardDescription>Accesos directos a las funciones más utilizadas</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Link href="/units/new">
                <Button variant="outline" className="h-20 w-full flex-col">
                  <Plus className="h-6 w-6 mb-2" />
                  <span>Agregar Unidad</span>
                </Button>
              </Link>

              <Link href="/imports">
                <Button variant="outline" className="h-20 w-full flex-col">
                  <Package className="h-6 w-6 mb-2" />
                  <span>Importar Excel</span>
                </Button>
              </Link>

              <Link href="/transfers">
                <Button variant="outline" className="h-20 w-full flex-col">
                  <Truck className="h-6 w-6 mb-2" />
                  <span>Nueva Transferencia</span>
                </Button>
              </Link>

              <Link href="/reports">
                <Button variant="outline" className="h-20 w-full flex-col">
                  <TrendingUp className="h-6 w-6 mb-2" />
                  <span>Generar Reporte</span>
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
