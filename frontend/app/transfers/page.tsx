
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Plus, Truck, CheckCircle, Clock, ArrowRight } from 'lucide-react';
import { useSession } from 'next-auth/react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Location {
  id: number;
  name: string;
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
  updated_at: string | null;
  from_location: { name: string } | null;
  to_location: { name: string } | null;
  user: { email: string; first_name: string; last_name: string } | null;
}

const statusColors: Record<string, string> = {
  'pending': 'bg-yellow-100 text-yellow-800',
  'in_transit': 'bg-blue-100 text-blue-800',
  'completed': 'bg-green-100 text-green-800',
  'cancelled': 'bg-red-100 text-red-800',
};

const statusLabels: Record<string, string> = {
  'pending': 'Pendiente',
  'in_transit': 'En Tránsito',
  'completed': 'Completada',
  'cancelled': 'Cancelada',
};

export default function TransfersPage() {
  const { data: session } = useSession();
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewTransfer, setShowNewTransfer] = useState(false);
  const [newTransfer, setNewTransfer] = useState({
    unit_ids: '',
    from_location_id: '',
    to_location_id: '',
    notes: ''
  });

  useEffect(() => {
    const fetchData = async () => {
      const token = (session as any)?.accessToken;
      if (!token) return;

      try {
        const [transfersRes, locationsRes] = await Promise.all([
          fetch(`${API_URL}/api/v1/transfers/`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
          fetch(`${API_URL}/api/v1/locations/`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
        ]);

        if (transfersRes.ok) {
          setTransfers(await transfersRes.json());
        }
        if (locationsRes.ok) {
          setLocations(await locationsRes.json());
        }
      } catch (err) {
        console.error('Error fetching transfers:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [session]);

  const handleCreateTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = (session as any)?.accessToken;
    if (!token) return;

    const unitIds = newTransfer.unit_ids.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));

    try {
      const res = await fetch(`${API_URL}/api/v1/transfers/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          from_location_id: parseInt(newTransfer.from_location_id),
          to_location_id: parseInt(newTransfer.to_location_id),
          unit_ids: unitIds,
          notes: newTransfer.notes || null,
        }),
      });

      if (res.ok) {
        const created = await res.json();
        setTransfers(prev => [created, ...prev]);
        setShowNewTransfer(false);
        setNewTransfer({ unit_ids: '', from_location_id: '', to_location_id: '', notes: '' });
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail}`);
      }
    } catch (err) {
      console.error('Error creating transfer:', err);
    }
  };

  const handleCompleteTransfer = async (transferId: number) => {
    const token = (session as any)?.accessToken;
    if (!token) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/transfers/${transferId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: 'completed' }),
      });

      if (res.ok) {
        const updated = await res.json();
        setTransfers(prev => prev.map(t => t.id === transferId ? updated : t));
      }
    } catch (err) {
      console.error('Error completing transfer:', err);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('es-MX', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Transferencias</h1>
              <p className="text-gray-600">Gestiona movimientos entre ubicaciones</p>
            </div>
            <Button onClick={() => setShowNewTransfer(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Nueva Transferencia
            </Button>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Formulario Nueva Transferencia */}
        {showNewTransfer && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Nueva Transferencia</CardTitle>
              <CardDescription>Crear una nueva transferencia de unidades</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateTransfer} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="unit_ids">IDs de Unidades * (separados por coma)</Label>
                    <Input
                      id="unit_ids"
                      value={newTransfer.unit_ids}
                      onChange={(e) => setNewTransfer(prev => ({ ...prev, unit_ids: e.target.value }))}
                      placeholder="1, 2, 3"
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="notes">Notas</Label>
                    <Input
                      id="notes"
                      value={newTransfer.notes}
                      onChange={(e) => setNewTransfer(prev => ({ ...prev, notes: e.target.value }))}
                      placeholder="Motivo de la transferencia"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Ubicación Origen *</Label>
                    <Select value={newTransfer.from_location_id} onValueChange={(value) => setNewTransfer(prev => ({ ...prev, from_location_id: value }))}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona origen" />
                      </SelectTrigger>
                      <SelectContent>
                        {locations.map((loc) => (
                          <SelectItem key={loc.id} value={String(loc.id)}>{loc.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Ubicación Destino *</Label>
                    <Select value={newTransfer.to_location_id} onValueChange={(value) => setNewTransfer(prev => ({ ...prev, to_location_id: value }))}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona destino" />
                      </SelectTrigger>
                      <SelectContent>
                        {locations.map((loc) => (
                          <SelectItem key={loc.id} value={String(loc.id)}>{loc.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex justify-end space-x-2">
                  <Button type="button" variant="outline" onClick={() => setShowNewTransfer(false)}>
                    Cancelar
                  </Button>
                  <Button 
                    type="submit" 
                    disabled={!newTransfer.unit_ids || !newTransfer.from_location_id || !newTransfer.to_location_id}
                  >
                    Crear Transferencia
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Lista de Transferencias */}
        <Card>
          <CardHeader>
            <CardTitle>Transferencias</CardTitle>
            <CardDescription>Historial de movimientos entre ubicaciones</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">Cargando transferencias...</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Ruta</TableHead>
                    <TableHead>Unidades</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Creado Por</TableHead>
                    <TableHead>Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transfers.map((transfer) => (
                    <TableRow key={transfer.id}>
                      <TableCell className="font-mono text-sm">{transfer.id}</TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm">{transfer.from_location?.name || '-'}</span>
                          <ArrowRight className="h-4 w-4 text-gray-400" />
                          <span className="text-sm">{transfer.to_location?.name || '-'}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm font-medium">{transfer.total_units}</TableCell>
                      <TableCell>
                        <Badge className={statusColors[transfer.status] || 'bg-gray-100 text-gray-800'}>
                          {statusLabels[transfer.status] || transfer.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDate(transfer.transfer_date || transfer.created_at)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {transfer.user ? `${transfer.user.first_name} ${transfer.user.last_name}` : '-'}
                      </TableCell>
                      <TableCell>
                        {(transfer.status === 'pending' || transfer.status === 'in_transit') && (
                          <Button 
                            size="sm" 
                            onClick={() => handleCompleteTransfer(transfer.id)}
                          >
                            <CheckCircle className="mr-2 h-4 w-4" />
                            Completar
                          </Button>
                        )}
                        {transfer.status === 'completed' && (
                          <Badge variant="default">
                            <CheckCircle className="mr-1 h-3 w-3" />
                            Completada
                          </Badge>
                        )}
                        {transfer.status === 'cancelled' && (
                          <Badge variant="secondary">Cancelada</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  {transfers.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-sm text-gray-500">
                        No hay transferencias registradas
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
