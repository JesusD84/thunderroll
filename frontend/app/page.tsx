
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

interface DashboardStats {
  total_units: number;
  by_status: Record<string, number>;
  by_location: Record<string, number>;
  recent_sales: number;
  pending_transfers: number;
  unidentified_units: number;
}

interface RecentActivity {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  user: string;
}

const statusLabels = {
  'EN_BODEGA_NO_IDENTIFICADA': 'En Bodega (No ID)',
  'IDENTIFICADA_EN_TALLER': 'Identificada en Taller',
  'EN_TRANSITO_TALLER_SUCURSAL': 'En Tránsito',
  'EN_SUCURSAL_DISPONIBLE': 'En Sucursal',
  'VENDIDA': 'Vendida',
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simular carga de estadísticas
    const mockStats: DashboardStats = {
      total_units: 156,
      by_status: {
        'EN_BODEGA_NO_IDENTIFICADA': 25,
        'IDENTIFICADA_EN_TALLER': 18,
        'EN_TRANSITO_TALLER_SUCURSAL': 4,
        'EN_SUCURSAL_DISPONIBLE': 89,
        'VENDIDA': 20
      },
      by_location: {
        'BODEGA': 25,
        'TALLER': 18,
        'SUCURSAL:Centro': 45,
        'SUCURSAL:Norte': 32,
        'SUCURSAL:Sur': 12
      },
      recent_sales: 5,
      pending_transfers: 7,
      unidentified_units: 25
    };

    const mockActivity: RecentActivity[] = [
      {
        id: '1',
        type: 'SALE',
        description: 'Honda PCX Red vendida en Sucursal Centro',
        timestamp: '2025-08-20T14:30:00Z',
        user: 'ventas@thunderrol.com'
      },
      {
        id: '2',
        type: 'TRANSFER',
        description: 'Yamaha NMAX transferida de Taller a Sucursal Norte',
        timestamp: '2025-08-20T13:45:00Z',
        user: 'inventario@thunderrol.com'
      },
      {
        id: '3',
        type: 'IDENTIFICATION',
        description: 'Unidad identificada con motor #20250823035830',
        timestamp: '2025-08-20T12:15:00Z',
        user: 'taller@thunderrol.com'
      },
      {
        id: '4',
        type: 'IMPORT',
        description: 'Importadas 15 unidades del lote BATCH_202508_003',
        timestamp: '2025-08-20T10:00:00Z',
        user: 'inventario@thunderrol.com'
      }
    ];

    setTimeout(() => {
      setStats(mockStats);
      setRecentActivity(mockActivity);
      setLoading(false);
    }, 1000);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div>Cargando dashboard...</div>
      </div>
    );
  }

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
                <div className="text-2xl font-bold text-gray-900">{stats?.total_units || 0}</div>
                <div className="text-sm text-gray-600">Total de Unidades</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center p-6">
              <Warehouse className="h-8 w-8 text-yellow-600" />
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">{stats?.by_location?.['BODEGA'] || 0}</div>
                <div className="text-sm text-gray-600">En Bodega</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center p-6">
              <Building className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">
                  {(stats?.by_location?.['SUCURSAL:Centro'] || 0) + 
                   (stats?.by_location?.['SUCURSAL:Norte'] || 0) + 
                   (stats?.by_location?.['SUCURSAL:Sur'] || 0)}
                </div>
                <div className="text-sm text-gray-600">En Sucursales</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center p-6">
              <DollarSign className="h-8 w-8 text-purple-600" />
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">{stats?.by_status?.['VENDIDA'] || 0}</div>
                <div className="text-sm text-gray-600">Vendidas</div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Estados de Unidades */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Activity className="mr-2 h-5 w-5" />
                Estados de Unidades
              </CardTitle>
              <CardDescription>Distribución actual por estado</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {stats && Object.entries(stats.by_status).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline">
                        {statusLabels[status as keyof typeof statusLabels] || status}
                      </Badge>
                    </div>
                    <div className="text-2xl font-bold">{count}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Ubicaciones */}
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
                {stats && Object.entries(stats.by_location).map(([location, count]) => (
                  <div key={location} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {location === 'BODEGA' && <Warehouse className="h-4 w-4 text-yellow-600" />}
                      {location === 'TALLER' && <Wrench className="h-4 w-4 text-blue-600" />}
                      {location.startsWith('SUCURSAL') && <Building className="h-4 w-4 text-green-600" />}
                      <span className="text-sm">{location}</span>
                    </div>
                    <div className="text-xl font-bold">{count}</div>
                  </div>
                ))}
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
                <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                  <div>
                    <div className="font-medium text-red-900">Unidades sin Identificar</div>
                    <div className="text-sm text-red-700">{stats?.unidentified_units || 0} unidades en bodega</div>
                  </div>
                  <Link href="/units?status=EN_BODEGA_NO_IDENTIFICADA">
                    <Button size="sm" variant="outline">Ver</Button>
                  </Link>
                </div>

                <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                  <div>
                    <div className="font-medium text-yellow-900">Transferencias Pendientes</div>
                    <div className="text-sm text-yellow-700">{stats?.pending_transfers || 0} transferencias</div>
                  </div>
                  <Link href="/transfers">
                    <Button size="sm" variant="outline">Ver</Button>
                  </Link>
                </div>
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
                {recentActivity.map((activity) => (
                  <div key={activity.id} className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      {activity.type === 'SALE' && <DollarSign className="h-5 w-5 text-green-600" />}
                      {activity.type === 'TRANSFER' && <Truck className="h-5 w-5 text-blue-600" />}
                      {activity.type === 'IDENTIFICATION' && <Wrench className="h-5 w-5 text-purple-600" />}
                      {activity.type === 'IMPORT' && <Package className="h-5 w-5 text-orange-600" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900">
                        {activity.description}
                      </div>
                      <div className="text-xs text-gray-500">
                        Hace 2 horas • {activity.user}
                      </div>
                    </div>
                  </div>
                ))}
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
