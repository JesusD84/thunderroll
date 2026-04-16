
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Edit, Truck, DollarSign, History } from 'lucide-react';
import { Label } from '@/components/ui/label';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useSession } from 'next-auth/react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Unit {
  id: number;
  brand: string;
  model: string;
  color: string;
  engine_number: string;
  chassis_number: string;
  status: string;
  current_location_id: number;
  current_location: { name: string; id: number } | null;
  notes: string | null;
  sold_date: string | null;
  created_at: string;
  updated_at: string | null;
}

interface Movement {
  id: number;
  unit_id: number;
  movement_type: string;
  from_location_id: number | null;
  to_location_id: number | null;
  quantity: number;
  notes: string | null;
  movement_date: string;
  created_at: string;
  user: {
    email: string;
    first_name: string;
    last_name: string;
  } | null;
  from_location: { name: string } | null;
  to_location: { name: string } | null;
}

const statusColors: Record<string, string> = {
  'available': 'bg-green-100 text-green-800',
  'sold': 'bg-gray-100 text-gray-800',
  'in_transit': 'bg-blue-100 text-blue-800',
  'reserved': 'bg-yellow-100 text-yellow-800',
};

const statusLabels: Record<string, string> = {
  'available': 'Disponible',
  'sold': 'Vendida',
  'in_transit': 'En Tránsito',
  'reserved': 'Reservada',
};

const movementTypeLabels: Record<string, string> = {
  'import': 'Importación',
  'sale': 'Venta',
  'transfer': 'Transferencia',
  'return': 'Devolución',
  'adjustment': 'Ajuste',
};

const colorMap: Record<string, string> = {
  'negro': 'bg-black',
  'rojo': 'bg-red-500',
  'azul': 'bg-blue-500',
  'blanco': 'bg-white border border-gray-300',
  'verde': 'bg-green-500',
  'gris': 'bg-gray-500',
  'amarillo': 'bg-yellow-500',
  'naranja': 'bg-orange-500',
  'rosa': 'bg-pink-500',
};

export default function UnitDetailPage() {
  const params = useParams();
  const unitId = params.id as string;
  const { data: session } = useSession();
  
  const [unit, setUnit] = useState<Unit | null>(null);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const token = (session as any)?.accessToken;
      if (!token) return;

      try {
        const [unitRes, movementsRes] = await Promise.all([
          fetch(`${API_URL}/api/v1/units/${unitId}`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
          fetch(`${API_URL}/api/v1/units/${unitId}/movements`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
        ]);

        if (!unitRes.ok) throw new Error(`Unidad no encontrada (${unitRes.status})`);

        const unitData = await unitRes.json();
        setUnit(unitData);

        if (movementsRes.ok) {
          const movementsData = await movementsRes.json();
          setMovements(movementsData);
        }
      } catch (err: any) {
        console.error('Error fetching unit:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [unitId, session]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div>Cargando detalle de unidad...</div>
      </div>
    );
  }

  if (error || !unit) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-600">{error || 'Unidad no encontrada'}</div>
      </div>
    );
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('es-MX', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('es-MX', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const formatMovementDesc = (m: Movement) => {
    const type = movementTypeLabels[m.movement_type] || m.movement_type;
    if (m.movement_type === 'import') {
      return m.to_location ? `Importada a ${m.to_location.name}` : 'Importada al sistema';
    }
    if (m.movement_type === 'sale') {
      return 'Unidad vendida';
    }
    if (m.movement_type === 'transfer') {
      const from = m.from_location?.name || '?';
      const to = m.to_location?.name || '?';
      return `${from} → ${to}`;
    }
    return type;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Link href="/units">
                <Button variant="ghost" size="sm" className="mr-4">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Volver a Unidades
                </Button>
              </Link>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Unidad {unit.id}</h1>
                <p className="text-gray-600">
                  {unit.brand && unit.model ? `${unit.brand} ${unit.model}` : 'Detalle de unidad'}
                </p>
              </div>
            </div>
            <div className="flex space-x-2">
              <Button variant="outline">
                <Edit className="mr-2 h-4 w-4" />
                Editar
              </Button>
              <Button variant="outline">
                <Truck className="mr-2 h-4 w-4" />
                Transferir
              </Button>
              <Button>
                <DollarSign className="mr-2 h-4 w-4" />
                Vender
              </Button>
            </div>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Información de la Unidad */}
          <Card>
            <CardHeader>
              <CardTitle>Información de la Unidad</CardTitle>
              <CardDescription>Datos actuales de la unidad</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium text-gray-500">Estado</Label>
                  <div className="mt-1">
                    <Badge className={statusColors[unit.status] || 'bg-gray-100 text-gray-800'}>
                      {statusLabels[unit.status] || unit.status}
                    </Badge>
                  </div>
                </div>
                
                <div>
                  <Label className="text-sm font-medium text-gray-500">Ubicación</Label>
                  <div className="mt-1 text-sm">{unit.current_location?.name || '-'}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium text-gray-500">Marca</Label>
                  <div className="mt-1 text-sm">{unit.brand || 'No especificada'}</div>
                </div>
                
                <div>
                  <Label className="text-sm font-medium text-gray-500">Modelo</Label>
                  <div className="mt-1 text-sm">{unit.model || 'No especificado'}</div>
                </div>
              </div>

              <div>
                <Label className="text-sm font-medium text-gray-500">Color</Label>
                <div className="mt-1 flex items-center">
                  <div className={`w-4 h-4 rounded-full mr-2 ${
                    colorMap[unit.color.toLowerCase()] || 'bg-gray-300'
                  }`}></div>
                  <span className="text-sm capitalize">{unit.color}</span>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4">
                <div>
                  <Label className="text-sm font-medium text-gray-500">Número de Motor</Label>
                  <div className="mt-1 text-sm font-mono">{unit.engine_number || 'No identificado'}</div>
                </div>
                
                <div>
                  <Label className="text-sm font-medium text-gray-500">Número de Chasis</Label>
                  <div className="mt-1 text-sm font-mono">{unit.chassis_number || 'No identificado'}</div>
                </div>
              </div>

              {unit.notes && (
                <div>
                  <Label className="text-sm font-medium text-gray-500">Notas</Label>
                  <div className="mt-1 text-sm">{unit.notes}</div>
                </div>
              )}

              {unit.sold_date && (
                <div>
                  <Label className="text-sm font-medium text-gray-500">Fecha de Venta</Label>
                  <div className="mt-1 text-sm">{formatDate(unit.sold_date)}</div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 text-xs text-gray-500">
                <div>
                  <Label className="text-sm font-medium text-gray-500">Creado</Label>
                  <div className="mt-1">{formatDate(unit.created_at)}</div>
                </div>
                
                <div>
                  <Label className="text-sm font-medium text-gray-500">Actualizado</Label>
                  <div className="mt-1">{formatDate(unit.updated_at)}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Historial de Movimientos */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <History className="mr-2 h-5 w-5" />
                Historial de Movimientos
              </CardTitle>
              <CardDescription>Cronología completa de la unidad</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {movements.map((movement: Movement, index: number) => (
                  <div key={movement.id} className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <div className={`w-3 h-3 rounded-full ${
                        index === 0 ? 'bg-green-500' : 'bg-gray-300'
                      }`}></div>
                      {index < movements.length - 1 && (
                        <div className="w-0.5 h-8 bg-gray-200 mx-auto mt-1"></div>
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900">
                        {movementTypeLabels[movement.movement_type] || movement.movement_type}
                      </div>
                      
                      <div className="text-sm text-gray-600 mt-1">
                        {formatMovementDesc(movement)}
                      </div>
                      
                      <div className="text-xs text-gray-500 mt-1">
                        {formatDateTime(movement.movement_date || movement.created_at)}
                        {movement.user && ` • ${movement.user.first_name} ${movement.user.last_name}`}
                      </div>
                      
                      {movement.notes && (
                        <div className="text-xs text-gray-400 mt-1">
                          {movement.notes}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {movements.length === 0 && (
                  <div className="text-sm text-gray-500">No hay movimientos registrados</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
