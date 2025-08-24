
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Edit, Truck, DollarSign, History } from 'lucide-react';
import { Label } from '@/components/ui/label';
import Link from 'next/link';
import { useParams } from 'next/navigation';

interface Unit {
  id: string;
  brand?: string;
  model?: string;
  color: string;
  engine_number?: string;
  chassis_number?: string;
  status: string;
  location: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

interface UnitEvent {
  id: string;
  event_type: string;
  before: any;
  after: any;
  who: string;
  reason?: string;
  timestamp: string;
}

const statusColors = {
  'EN_BODEGA_NO_IDENTIFICADA': 'bg-red-100 text-red-800',
  'IDENTIFICADA_EN_TALLER': 'bg-yellow-100 text-yellow-800',
  'EN_TRANSITO_TALLER_SUCURSAL': 'bg-blue-100 text-blue-800',
  'EN_SUCURSAL_DISPONIBLE': 'bg-green-100 text-green-800',
  'VENDIDA': 'bg-gray-100 text-gray-800',
};

const statusLabels = {
  'EN_BODEGA_NO_IDENTIFICADA': 'En Bodega (No Identificada)',
  'IDENTIFICADA_EN_TALLER': 'Identificada en Taller',
  'EN_TRANSITO_TALLER_SUCURSAL': 'En Tránsito a Sucursal',
  'EN_SUCURSAL_DISPONIBLE': 'Disponible en Sucursal',
  'VENDIDA': 'Vendida',
};

export default function UnitDetailPage() {
  const params = useParams();
  const unitId = params.id as string;
  
  const [unit, setUnit] = useState<Unit | null>(null);
  const [events, setEvents] = useState<UnitEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simular carga de datos
    const sampleUnit: Unit = {
      id: unitId,
      brand: 'Honda',
      model: 'PCX',
      color: 'red',
      engine_number: '20250823035825',
      chassis_number: 'HXY202507501',
      status: 'EN_SUCURSAL_DISPONIBLE',
      location: 'SUCURSAL:Centro',
      notes: 'Unidad en perfecto estado',
      created_at: '2025-08-20T10:00:00Z',
      updated_at: '2025-08-20T14:30:00Z'
    };

    const sampleEvents: UnitEvent[] = [
      {
        id: '1',
        event_type: 'CREATED',
        before: null,
        after: { status: 'EN_BODEGA_NO_IDENTIFICADA', location: 'BODEGA' },
        who: 'inventario@thunderrol.com',
        timestamp: '2025-08-20T10:00:00Z'
      },
      {
        id: '2',
        event_type: 'IDENTIFICATION',
        before: { engine_number: null, chassis_number: null },
        after: { engine_number: '20250823035825', chassis_number: 'HXY202507501' },
        who: 'taller@thunderrol.com',
        reason: 'Identificación en taller',
        timestamp: '2025-08-20T12:00:00Z'
      },
      {
        id: '3',
        event_type: 'TRANSFER',
        before: { location: 'TALLER', status: 'IDENTIFICADA_EN_TALLER' },
        after: { location: 'SUCURSAL:Centro', status: 'EN_SUCURSAL_DISPONIBLE' },
        who: 'inventario@thunderrol.com',
        reason: 'Transferencia a sucursal centro',
        timestamp: '2025-08-20T14:30:00Z'
      }
    ];

    setTimeout(() => {
      setUnit(sampleUnit);
      setEvents(sampleEvents);
      setLoading(false);
    }, 500);
  }, [unitId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div>Cargando detalle de unidad...</div>
      </div>
    );
  }

  if (!unit) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div>Unidad no encontrada</div>
      </div>
    );
  }

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
                    <Badge className={statusColors[unit.status as keyof typeof statusColors]}>
                      {statusLabels[unit.status as keyof typeof statusLabels]}
                    </Badge>
                  </div>
                </div>
                
                <div>
                  <Label className="text-sm font-medium text-gray-500">Ubicación</Label>
                  <div className="mt-1 text-sm">{unit.location}</div>
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
                    unit.color === 'red' ? 'bg-red-500' :
                    unit.color === 'black' ? 'bg-black' :
                    unit.color === 'green' ? 'bg-green-500' :
                    unit.color === 'pink' ? 'bg-pink-500' :
                    unit.color === 'grey' ? 'bg-gray-500' :
                    unit.color === 'blue' ? 'bg-blue-500' :
                    'bg-gray-300'
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

              <div className="grid grid-cols-2 gap-4 text-xs text-gray-500">
                <div>
                  <Label className="text-sm font-medium text-gray-500">Creado</Label>
                  <div className="mt-1">20/08/2025</div>
                </div>
                
                <div>
                  <Label className="text-sm font-medium text-gray-500">Actualizado</Label>
                  <div className="mt-1">20/08/2025</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Historial de Eventos */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <History className="mr-2 h-5 w-5" />
                Historial de Eventos
              </CardTitle>
              <CardDescription>Cronología completa de la unidad</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {events.map((event, index) => (
                  <div key={event.id} className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <div className={`w-3 h-3 rounded-full ${
                        index === 0 ? 'bg-green-500' : 'bg-gray-300'
                      }`}></div>
                      {index < events.length - 1 && (
                        <div className="w-0.5 h-8 bg-gray-200 mx-auto mt-1"></div>
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900">
                        {event.event_type === 'CREATED' ? 'Unidad Creada' :
                         event.event_type === 'IDENTIFICATION' ? 'Identificación Completada' :
                         event.event_type === 'TRANSFER' ? 'Transferencia' :
                         event.event_type}
                      </div>
                      
                      {event.reason && (
                        <div className="text-sm text-gray-600 mt-1">{event.reason}</div>
                      )}
                      
                      <div className="text-xs text-gray-500 mt-1">
                        20/08/2025 • {event.who}
                      </div>
                      
                      {event.before && event.after && (
                        <div className="text-xs text-gray-400 mt-1">
                          Cambios: {JSON.stringify(event.after, null, 2)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
