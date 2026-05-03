
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Truck, CheckCircle, ArrowRight, Eye, Package, Plus } from 'lucide-react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Location {
  id: number;
  name: string;
}

interface AvailableUnit {
  id: number;
  brand: string;
  model: string;
  engine_number: string;
  color: string;
}

interface TransferUnit {
  id: number;
  unit_id: number;
  unit: {
    id: number;
    brand: string;
    model: string;
    engine_number: string;
    color: string;
  } | null;
}

interface Transfer {
  id: number;
  from_location_id: number;
  to_location_id: number;
  user_id: number;
  status: string;
  total_units: number;
  notes: string | null;
  transfer_date: string | null;
  completed_date: string | null;
  created_at: string;
  from_location: { name: string } | null;
  to_location: { name: string } | null;
  user: { email: string; first_name: string; last_name: string } | null;
  transfer_units: TransferUnit[] | null;
}

const statusColors: Record<string, string> = {
  'PENDING': 'bg-yellow-100 text-yellow-800',
  'IN_TRANSIT': 'bg-blue-100 text-blue-800',
  'RECEIVED': 'bg-green-100 text-green-800',
  'CANCELLED': 'bg-red-100 text-red-800',
};

const statusLabels: Record<string, string> = {
  'PENDING': 'Pendiente',
  'IN_TRANSIT': 'En Tránsito',
  'RECEIVED': 'Completada',
  'CANCELLED': 'Cancelada',
};

export default function TransfersPage() {
  const { data: session } = useSession();
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  // New transfer form state
  const [showNewTransfer, setShowNewTransfer] = useState(false);
  const [fromLocationId, setFromLocationId] = useState('');
  const [toLocationId, setToLocationId] = useState('');
  const [selectedUnitId, setSelectedUnitId] = useState('');
  const [transferNotes, setTransferNotes] = useState('');
  const [availableUnits, setAvailableUnits] = useState<AvailableUnit[]>([]);
  const [unitsLoading, setUnitsLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const token = (session as any)?.accessToken;
      if (!token) return;

      try {
        const [tRes, lRes] = await Promise.all([
          fetch(`${API_URL}/api/v1/transfers/`, { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch(`${API_URL}/api/v1/locations/`, { headers: { 'Authorization': `Bearer ${token}` } }),
        ]);
        if (tRes.ok) setTransfers(await tRes.json());
        if (lRes.ok) setLocations(await lRes.json());
      } catch (err) {
        console.error('Error fetching transfers:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [session]);

  // Fetch available units when origin location changes
  useEffect(() => {
    const fetchUnits = async () => {
      const token = (session as any)?.accessToken;
      if (!token || !fromLocationId) { setAvailableUnits([]); return; }
      setUnitsLoading(true);
      setSelectedUnitId('');
      try {
        const res = await fetch(
          `${API_URL}/api/v1/units/?status=AVAILABLE&location_id=${fromLocationId}`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        );
        if (res.ok) setAvailableUnits(await res.json());
      } catch (err) {
        console.error('Error fetching units:', err);
      } finally {
        setUnitsLoading(false);
      }
    };
    fetchUnits();
  }, [fromLocationId, session]);

  const handleCreateTransfer = async () => {
    const token = (session as any)?.accessToken;
    if (!token || !selectedUnitId || !fromLocationId || !toLocationId) return;
    setCreateLoading(true);
    setCreateError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/transfers/`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          unit_ids: [parseInt(selectedUnitId)],
          from_location_id: parseInt(fromLocationId),
          to_location_id: parseInt(toLocationId),
          notes: transferNotes || null,
        }),
      });
      if (res.ok) {
        // Refresh list and reset form
        const listRes = await fetch(`${API_URL}/api/v1/transfers/`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (listRes.ok) setTransfers(await listRes.json());
        setShowNewTransfer(false);
        setFromLocationId(''); setToLocationId(''); setSelectedUnitId(''); setTransferNotes('');
        setAvailableUnits([]);
      } else {
        const err = await res.json();
        const detail = err.detail;
        setCreateError(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ') : 'Error creando transferencia');
      }
    } catch { setCreateError('Error de conexión'); }
    finally { setCreateLoading(false); }
  };

  const handleConfirmArrival = async (transferId: number) => {
    const token = (session as any)?.accessToken;
    if (!token) return;
    setActionLoading(transferId);

    try {
      const res = await fetch(`${API_URL}/api/v1/transfers/${transferId}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'RECEIVED' }),
      });

      if (res.ok) {
        // Refresh transfers list
        const listRes = await fetch(`${API_URL}/api/v1/transfers/`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (listRes.ok) setTransfers(await listRes.json());
      }
    } catch (err) {
      console.error('Error completing transfer:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('es-MX', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
  };

  const getUnitLabel = (transfer: Transfer) => {
    const units = transfer.transfer_units;
    if (!units || units.length === 0) return '-';
    const u = units[0].unit;
    if (!u) return `ID: ${units[0].unit_id}`;
    return `${u.brand} ${u.model}`;
  };

  const getUnitId = (transfer: Transfer): number | null => {
    const units = transfer.transfer_units;
    if (!units || units.length === 0) return null;
    return units[0].unit_id;
  };

  const filteredTransfers = statusFilter === 'all'
    ? transfers
    : transfers.filter(t => t.status === statusFilter);

  const pendingCount = transfers.filter(t => t.status === 'PENDING' || t.status === 'IN_TRANSIT').length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Transferencias</h1>
              <p className="text-gray-600">Control de movimientos entre ubicaciones</p>
            </div>
            <div className="flex items-center space-x-3">
              {pendingCount > 0 && (
                <Badge className="bg-blue-100 text-blue-800 text-sm px-3 py-1">
                  <Truck className="mr-1 h-4 w-4" />
                  {pendingCount} en tránsito
                </Badge>
              )}
              <Button onClick={() => { setShowNewTransfer(true); setCreateError(null); }}>
                <Plus className="mr-2 h-4 w-4" />
                Nueva Transferencia
              </Button>
            </div>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* New Transfer Form */}
        {showNewTransfer && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Nueva Transferencia</CardTitle>
              <CardDescription>Selecciona origen, unidad y destino</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>1. Ubicación Origen *</Label>
                  <Select value={fromLocationId} onValueChange={setFromLocationId}>
                    <SelectTrigger><SelectValue placeholder="¿De dónde sale?" /></SelectTrigger>
                    <SelectContent>
                      {locations.map(l => <SelectItem key={l.id} value={String(l.id)}>{l.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>2. Unidad a Transferir *</Label>
                  <Select value={selectedUnitId} onValueChange={setSelectedUnitId} disabled={!fromLocationId || unitsLoading}>
                    <SelectTrigger>
                      <SelectValue placeholder={unitsLoading ? 'Cargando unidades...' : !fromLocationId ? 'Selecciona origen primero' : availableUnits.length === 0 ? 'Sin unidades disponibles' : 'Selecciona unidad'} />
                    </SelectTrigger>
                    <SelectContent>
                      {availableUnits.map(u => (
                        <SelectItem key={u.id} value={String(u.id)}>
                          {u.brand} {u.model} — {u.engine_number}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>3. Ubicación Destino *</Label>
                  <Select value={toLocationId} onValueChange={setToLocationId}>
                    <SelectTrigger><SelectValue placeholder="¿A dónde va?" /></SelectTrigger>
                    <SelectContent>
                      {locations.filter(l => String(l.id) !== fromLocationId).map(l =>
                        <SelectItem key={l.id} value={String(l.id)}>{l.name}</SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Notas (opcional)</Label>
                  <Input value={transferNotes} onChange={(e) => setTransferNotes(e.target.value)} placeholder="Motivo de la transferencia" />
                </div>
              </div>
              {createError && <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{createError}</div>}
              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => {
                  setShowNewTransfer(false); setFromLocationId(''); setToLocationId('');
                  setSelectedUnitId(''); setTransferNotes(''); setAvailableUnits([]);
                }}>Cancelar</Button>
                <Button onClick={handleCreateTransfer}
                  disabled={createLoading || !selectedUnitId || !fromLocationId || !toLocationId}>
                  <Truck className="mr-2 h-4 w-4" />
                  {createLoading ? 'Creando...' : 'Crear Transferencia'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Lista de Transferencias */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Historial de Transferencias</CardTitle>
                <CardDescription>Movimientos entre ubicaciones</CardDescription>
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Filtrar por estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="PENDING">Pendiente</SelectItem>
                  <SelectItem value="IN_TRANSIT">En Tránsito</SelectItem>
                  <SelectItem value="RECEIVED">Completada</SelectItem>
                  <SelectItem value="CANCELLED">Cancelada</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">Cargando transferencias...</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Unidad</TableHead>
                    <TableHead>Ruta</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Completada</TableHead>
                    <TableHead>Creado Por</TableHead>
                    <TableHead>Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTransfers.map((transfer) => {
                    const unitId = getUnitId(transfer);
                    return (
                      <TableRow key={transfer.id}>
                        <TableCell className="font-mono text-sm">{transfer.id}</TableCell>
                        <TableCell>
                          {unitId ? (
                            <Link href={`/units/${unitId}`} className="text-blue-600 hover:underline text-sm font-medium">
                              {getUnitLabel(transfer)}
                            </Link>
                          ) : (
                            <span className="text-sm text-gray-500">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm">{transfer.from_location?.name || '-'}</span>
                            <ArrowRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                            <span className="text-sm">{transfer.to_location?.name || '-'}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={statusColors[transfer.status] || 'bg-gray-100 text-gray-800'}>
                            {statusLabels[transfer.status] || transfer.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatDate(transfer.transfer_date || transfer.created_at)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatDate(transfer.completed_date)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {transfer.user ? `${transfer.user.first_name} ${transfer.user.last_name}` : '-'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            {(transfer.status === 'PENDING' || transfer.status === 'IN_TRANSIT') && (
                              <Button
                                size="sm"
                                className="bg-green-600 hover:bg-green-700"
                                onClick={() => handleConfirmArrival(transfer.id)}
                                disabled={actionLoading === transfer.id}
                              >
                                <CheckCircle className="mr-1 h-4 w-4" />
                                {actionLoading === transfer.id ? 'Confirmando...' : 'Confirmar Llegada'}
                              </Button>
                            )}
                            {transfer.status === 'RECEIVED' && (
                              <Badge variant="outline" className="text-green-700 border-green-300">
                                <CheckCircle className="mr-1 h-3 w-3" />
                                Completada
                              </Badge>
                            )}
                            {unitId && (
                              <Link href={`/units/${unitId}`}>
                                <Button size="sm" variant="ghost">
                                  <Eye className="h-4 w-4" />
                                </Button>
                              </Link>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {filteredTransfers.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-sm text-gray-500 py-8">
                        No hay transferencias {statusFilter !== 'all' ? `con estado "${statusLabels[statusFilter]}"` : 'registradas'}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
