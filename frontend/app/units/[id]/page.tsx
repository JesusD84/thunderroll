
'use client';

import { apiFetch, ApiError } from '@/lib/api';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Edit, Truck, DollarSign, History, Save, X } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useAuth } from '@/lib/auth';

interface Unit {
  id: number;
  brand: string;
  model: string;
  color: string;
  engine_number: string | null;
  chassis_number: string | null;
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
  dispatched_by_id: number | null;
  received_by_id: number | null;
  origin_location_id: number | null;
  destination_location_id: number | null;
  status: string;
  dispatched_at: string | null;
  received_at: string | null;
}

const statusColors: Record<string, string> = {
  'AVAILABLE': 'bg-green-100 text-green-800',
  'WAREHOUSE_UNIDENTIFIED': 'bg-yellow-100 text-yellow-800',
  'SOLD': 'bg-gray-100 text-gray-800',
  'IN_TRANSIT': 'bg-blue-100 text-blue-800',
};

const statusLabels: Record<string, string> = {
  'AVAILABLE': 'Disponible',
  'WAREHOUSE_UNIDENTIFIED': 'Sin Identificar',
  'SOLD': 'Vendida',
  'IN_TRANSIT': 'En Tránsito',
};

const transferStatusLabels: Record<string, string> = {
  'PENDING': 'Pendiente',
  'IN_TRANSIT': 'En Tránsito',
  'RECEIVED': 'Recibida',
  'CANCELLED': 'Cancelada',
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

const colorOptions = [
  { value: 'ROJO', label: 'Rojo' },
  { value: 'NEGRO', label: 'Negro' },
  { value: 'AZUL', label: 'Azul' },
  { value: 'BLANCO', label: 'Blanco' },
  { value: 'VERDE', label: 'Verde' },
  { value: 'GRIS', label: 'Gris' },
  { value: 'ROSA', label: 'Rosa' },
  { value: 'AMARILLO', label: 'Amarillo' },
];

// Names the import may store in English (any casing) -> Spanish key.
const englishColorKeys: Record<string, string> = {
  black: 'negro', red: 'rojo', blue: 'azul', white: 'blanco', green: 'verde',
  grey: 'gris', gray: 'gris', yellow: 'amarillo', orange: 'naranja', pink: 'rosa',
};

// Returns the edit-form option value for a stored color, or '' if none matches.
function toColorOptionValue(color: string | null | undefined): string {
  const key = (color ?? '').trim().toLowerCase();
  const spanishKey = englishColorKeys[key] ?? key;
  return colorOptions.find(c => c.value.toLowerCase() === spanishKey)?.value ?? '';
}

interface Location {
  id: number;
  name: string;
}

export default function UnitDetailPage() {
  const params = useParams();
  const unitId = params.id as string;
  const { data: session } = useSession();
  const { manageUnits } = useAuth();
  
  const [unit, setUnit] = useState<Unit | null>(null);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    brand: '', model: '', color: '', engine_number: '', chassis_number: '',
    current_location_id: '', notes: '',
  });
  const [showTransfer, setShowTransfer] = useState(false);
  const [transferTo, setTransferTo] = useState('');
  const [transferNotes, setTransferNotes] = useState('');
  const [showSell, setShowSell] = useState(false);
  const [sellNotes, setSellNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeTransferId, setActiveTransferId] = useState<number | null>(null);

  const parseError = (err: unknown): string => {
    const detail = err instanceof ApiError ? err.detail : undefined;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((d: unknown) => {
          if (d && typeof d === 'object' && 'msg' in d) {
            const msg = (d as { msg?: unknown }).msg;
            return typeof msg === 'string' ? msg : String(msg ?? '');
          }
          return '';
        })
        .filter((m) => m !== '');
      if (messages.length > 0) return messages.join(', ');
    }
    return 'Error realizando operación';
  };

  const refreshData = async () => {
    const [unitData, movementsData] = await Promise.all([
      apiFetch<Unit>(`/api/v1/units/${unitId}`).catch(() => null),
      apiFetch<Movement[]>(`/api/v1/transfers/?unit_id=${unitId}`).catch(() => null),
    ]);
    if (unitData) setUnit(unitData);
    if (movementsData) setMovements(movementsData);
    // Check for active transfer
    try {
      const active = await apiFetch<{ id: number }>(`/api/v1/transfers/unit/${unitId}/active`);
      setActiveTransferId(active?.id ?? null);
    } catch { setActiveTransferId(null); }
  };

  const handleTransfer = async (toLocationId: number, notes?: string) => {
    if (!session || !unit) return;
    setActionLoading(true);
    setActionError(null);
    try {
      await apiFetch('/api/v1/transfers/', {
        method: 'POST',
        json: {
          unit_id: unit.id,
          origin_location_id: unit.current_location_id,
          destination_location_id: toLocationId,
        },
      });
      await refreshData();
      setShowTransfer(false);
      setTransferTo('');
      setTransferNotes('');
    } catch (err) {
      setActionError(err instanceof ApiError ? parseError(err) : 'Error de conexión');
    }
    finally { setActionLoading(false); }
  };

  const handleConfirmArrival = async () => {
    if (!session || !unit) return;
    setActionLoading(true);
    setActionError(null);
    try {
      if (!activeTransferId) {
        // The state of a unit comes from its transfer: a unit that is on the
        // road always has an active transfer, so there is nothing to close
        // here. Say it instead of pretending the unit can be edited.
        setActionError('Esta unidad no tiene una transferencia activa. Pide a un administrador que revise la unidad.');
        return;
      }
      // Complete the Transfer record: the unit becomes AVAILABLE at the
      // destination.
      await apiFetch(`/api/v1/transfers/${activeTransferId}`, {
        method: 'PUT',
        json: { status: 'RECEIVED' },
      });
      await refreshData();
    } catch (err) {
      setActionError(err instanceof ApiError ? parseError(err) : 'Error de conexión');
    }
    finally { setActionLoading(false); }
  };

  const handleSell = async (notes?: string) => {
    if (!session || !unit) return;
    setActionLoading(true);
    setActionError(null);
    try {
      await apiFetch(`/api/v1/units/${unitId}/sell`, {
        method: 'POST',
        json: { notes: notes?.trim() || null },
      });
      await refreshData();
      setShowSell(false);
      setSellNotes('');
    } catch (err) {
      setActionError(err instanceof ApiError ? parseError(err) : 'Error de conexión');
    }
    finally { setActionLoading(false); }
  };

  useEffect(() => {
    const fetchData = async () => {
      if (!session) return;

      try {
        const [unitData, movementsData] = await Promise.all([
          apiFetch<Unit>(`/api/v1/units/${unitId}`),
          // The history is optional: the unit itself is what must load.
          apiFetch<Movement[]>(`/api/v1/transfers/?unit_id=${unitId}`).catch(() => null),
        ]);
        setUnit(unitData);
        if (movementsData) setMovements(movementsData);

        try {
          setLocations(await apiFetch<Location[]>('/api/v1/locations/'));
        } catch {
          // Without the locations the modal cannot be filled in.
        }

        // Check for active transfer if unit is in transit
        if (unitData.status === 'IN_TRANSIT') {
          try {
            const active = await apiFetch<{ id: number }>(`/api/v1/transfers/unit/${unitId}/active`);
            setActiveTransferId(active?.id ?? null);
          } catch {
            setActiveTransferId(null);
          }
        }
      } catch (err) {
        console.error('Error fetching unit:', err);
        if (err instanceof ApiError && err.status === 404) {
          setError(`Unidad no encontrada (${err.status})`);
        } else {
          setError(err instanceof Error ? err.message : 'Unidad no encontrada');
        }
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

  const getLocName = (id: number | null) => {
    if (!id) return '-';
    return locations.find(l => l.id === id)?.name || `Loc #${id}`;
  };

  const formatMovementDesc = (m: Movement) => {
    const from = getLocName(m.origin_location_id);
    const to = getLocName(m.destination_location_id);
    if (m.origin_location_id && m.destination_location_id) {
      return `${from} → ${to}`;
    }
    if (m.destination_location_id) {
      return `Recibida en ${to}`;
    }
    return 'Transferencia';
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
              {manageUnits && (
                <Button variant="outline" onClick={() => {
                  setEditing(true);
                  setEditError(null);
                  setEditForm({
                    brand: unit.brand || '',
                    model: unit.model || '',
                    color: toColorOptionValue(unit.color),
                    engine_number: unit.engine_number || '',
                    chassis_number: unit.chassis_number || '',
                    current_location_id: unit.current_location_id ? String(unit.current_location_id) : '',
                    notes: unit.notes || '',
                  });
                }}>
                  <Edit className="mr-2 h-4 w-4" />
                  Editar
                </Button>
              )}
              {unit.status === 'IN_TRANSIT' ? (
                <Button className="bg-green-600 hover:bg-green-700" onClick={handleConfirmArrival}
                  disabled={actionLoading}>
                  <Truck className="mr-2 h-4 w-4" />
                  {actionLoading ? 'Confirmando...' : 'Confirmar Llegada'}
                </Button>
              ) : (
                <>
                  <Button variant="outline" onClick={() => { setShowTransfer(true); setActionError(null); }}
                    disabled={unit.status === 'SOLD' || unit.status === 'IN_TRANSIT'}>
                    <Truck className="mr-2 h-4 w-4" />
                    Transferir
                  </Button>
                  <Button onClick={() => { setShowSell(true); setActionError(null); }}
                    disabled={unit.status === 'SOLD' || unit.status === 'IN_TRANSIT'}>
                    <DollarSign className="mr-2 h-4 w-4" />
                    Vender
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Transfer Modal */}
      {showTransfer && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle>Transferir Unidad</CardTitle>
              <CardDescription>Mover unidad {unit.engine_number || `#${unit.id}`} a otra ubicación</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 bg-gray-50 rounded-lg text-sm">
                <span className="text-gray-500">Ubicación actual:</span>{' '}
                <span className="font-medium">{locations.find(l => l.id === unit.current_location_id)?.name || unit.current_location?.name || 'Sin ubicación'}</span>
              </div>
              <div>
                <Label>Ubicación Destino *</Label>
                <Select value={transferTo} onValueChange={setTransferTo}>
                  <SelectTrigger><SelectValue placeholder="Selecciona destino" /></SelectTrigger>
                  <SelectContent>
                    {locations.filter(l => l.id !== unit.current_location_id).map(l =>
                      <SelectItem key={l.id} value={String(l.id)}>{l.name}</SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Notas</Label>
                <Input value={transferNotes} onChange={(e) => setTransferNotes(e.target.value)} placeholder="Notas opcionales" />
              </div>
              {actionError && <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{actionError}</div>}
              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setShowTransfer(false)} disabled={actionLoading}>
                  Cancelar
                </Button>
                <Button onClick={() => handleTransfer(parseInt(transferTo), transferNotes)}
                  disabled={actionLoading || !transferTo}>
                  <Truck className="mr-2 h-4 w-4" />
                  {actionLoading ? 'Transfiriendo...' : 'Transferir'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Sell Modal */}
      {showSell && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle>Vender Unidad</CardTitle>
              <CardDescription>Registrar venta de {unit.engine_number || `#${unit.id}`}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 bg-yellow-50 text-yellow-800 rounded-lg text-sm">
                Esta acción marcará la unidad como vendida. Esta operación no se puede deshacer fácilmente.
              </div>
              <div>
                <Label>Notas de venta</Label>
                <Input value={sellNotes} onChange={(e) => setSellNotes(e.target.value)} placeholder="Detalles de la venta" />
              </div>
              {actionError && <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{actionError}</div>}
              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setShowSell(false)} disabled={actionLoading}>
                  Cancelar
                </Button>
                <Button variant="destructive" onClick={() => handleSell(sellNotes)}
                  disabled={actionLoading}>
                  <DollarSign className="mr-2 h-4 w-4" />
                  {actionLoading ? 'Procesando...' : 'Confirmar Venta'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Información de la Unidad */}
          <Card>
            <CardHeader>
              <CardTitle>{editing ? 'Editar Unidad' : 'Información de la Unidad'}</CardTitle>
              <CardDescription>{editing ? 'Modifica los datos de la unidad' : 'Datos actuales de la unidad'}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
            {editing ? (
              <form onSubmit={async (e) => {
                e.preventDefault();
                setSaving(true);
                setEditError(null);
                if (!session) return;
                try {
                  const updated = await apiFetch<Unit>(`/api/v1/units/${unitId}`, {
                    method: 'PUT',
                    json: {
                      brand: editForm.brand || undefined,
                      model: editForm.model || undefined,
                      color: editForm.color || undefined,
                      engine_number: editForm.engine_number || null,
                      chassis_number: editForm.chassis_number || null,
                      notes: editForm.notes || null,
                    },
                  });
                  setUnit(updated);
                  setEditing(false);
                } catch (err) {
                  if (err instanceof ApiError) {
                    setEditError(typeof err.detail === 'string' ? err.detail : 'Error actualizando unidad');
                  } else {
                    setEditError('Error de conexión');
                  }
                } finally {
                  setSaving(false);
                }
              }} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Marca</Label>
                    <Input value={editForm.brand} onChange={(e) => setEditForm(p => ({...p, brand: e.target.value}))} />
                  </div>
                  <div>
                    <Label>Modelo</Label>
                    <Input value={editForm.model} onChange={(e) => setEditForm(p => ({...p, model: e.target.value}))} />
                  </div>
                </div>
                <div>
                  <Label>Color</Label>
                  <Select value={editForm.color} onValueChange={(v) => setEditForm(p => ({...p, color: v}))}>
                    <SelectTrigger><SelectValue placeholder="Selecciona color" /></SelectTrigger>
                    <SelectContent>
                      {colorOptions.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label># Motor</Label>
                    <Input value={editForm.engine_number} onChange={(e) => setEditForm(p => ({...p, engine_number: e.target.value}))} />
                  </div>
                  <div>
                    <Label># Chasis</Label>
                    <Input value={editForm.chassis_number} onChange={(e) => setEditForm(p => ({...p, chassis_number: e.target.value}))} />
                  </div>
                </div>
                <div>
                  <Label>Notas</Label>
                  <Input value={editForm.notes} onChange={(e) => setEditForm(p => ({...p, notes: e.target.value}))} placeholder="Observaciones" />
                </div>
                {editError && <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{editError}</div>}
                <div className="flex justify-end space-x-2">
                  <Button type="button" variant="outline" onClick={() => setEditing(false)} disabled={saving}>
                    <X className="mr-2 h-4 w-4" /> Cancelar
                  </Button>
                  <Button type="submit" disabled={saving}>
                    <Save className="mr-2 h-4 w-4" /> {saving ? 'Guardando...' : 'Guardar'}
                  </Button>
                </div>
              </form>
            ) : (
            <>
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
            </>
            )}
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
                        Transferencia — {transferStatusLabels[movement.status] || movement.status}
                      </div>
                      
                      <div className="text-sm text-gray-600 mt-1">
                        {formatMovementDesc(movement)}
                      </div>
                      
                      <div className="text-xs text-gray-500 mt-1">
                        {formatDateTime(movement.dispatched_at || movement.received_at || '')}
                      </div>
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
