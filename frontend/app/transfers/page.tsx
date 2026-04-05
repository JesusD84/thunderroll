
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

interface Transfer {
  id: string;
  unit_id: string;
  unit_info: string;
  from_location: string;
  to_location: string;
  status: 'PENDING' | 'IN_TRANSIT' | 'RECEIVED';
  created_by: string;
  created_at: string;
  eta?: string;
  received_by?: string;
  received_at?: string;
}

const transferStatusColors = {
  'PENDING': 'bg-yellow-100 text-yellow-800',
  'IN_TRANSIT': 'bg-blue-100 text-blue-800', 
  'RECEIVED': 'bg-green-100 text-green-800',
};

const transferStatusLabels = {
  'PENDING': 'Pendiente',
  'IN_TRANSIT': 'En Tránsito',
  'RECEIVED': 'Recibida',
};

export default function TransfersPage() {
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewTransfer, setShowNewTransfer] = useState(false);
  const [newTransfer, setNewTransfer] = useState({
    unit_id: '',
    from_location: '',
    to_location: '',
    eta: '',
    reason: ''
  });

  useEffect(() => {
    // Simular datos de transferencias
    const sampleTransfers: Transfer[] = [
      {
        id: '1',
        unit_id: 'UNIT_001',
        unit_info: 'Honda PCX - Red - HXY202507501',
        from_location: 'TALLER',
        to_location: 'SUCURSAL:Centro',
        status: 'IN_TRANSIT',
        created_by: 'inventario@thunderrol.com',
        created_at: '2025-08-20T09:00:00Z',
        eta: '2025-08-20T16:00:00Z'
      },
      {
        id: '2',
        unit_id: 'UNIT_002',
        unit_info: 'Yamaha NMAX - Black - HXY202507502',
        from_location: 'SUCURSAL:Centro',
        to_location: 'SUCURSAL:Norte',
        status: 'PENDING',
        created_by: 'ventas@thunderrol.com',
        created_at: '2025-08-20T11:00:00Z',
        eta: '2025-08-21T10:00:00Z'
      },
      {
        id: '3',
        unit_id: 'UNIT_003',
        unit_info: 'Honda PCX - Blue - HXY202507503',
        from_location: 'BODEGA',
        to_location: 'TALLER',
        status: 'RECEIVED',
        created_by: 'inventario@thunderrol.com',
        created_at: '2025-08-19T14:00:00Z',
        received_by: 'taller@thunderrol.com',
        received_at: '2025-08-19T15:30:00Z'
      }
    ];

    setTimeout(() => {
      setTransfers(sampleTransfers);
      setLoading(false);
    }, 500);
  }, []);

  const handleCreateTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Aquí iría la llamada al API
    console.log('Creando transferencia:', newTransfer);
    
    // Simular creación
    const newTransferRecord: Transfer = {
      id: Date.now().toString(),
      unit_id: newTransfer.unit_id,
      unit_info: `Unidad ${newTransfer.unit_id}`,
      from_location: newTransfer.from_location,
      to_location: newTransfer.to_location,
      status: 'PENDING',
      created_by: 'current_user@thunderrol.com',
      created_at: new Date().toISOString(),
      eta: newTransfer.eta || undefined
    };

    setTransfers(prev => [newTransferRecord, ...prev]);
    setShowNewTransfer(false);
    setNewTransfer({
      unit_id: '',
      from_location: '',
      to_location: '',
      eta: '',
      reason: ''
    });
  };

  const handleReceiveTransfer = async (transferId: string) => {
    // Simular recepción
    setTransfers(prev => prev.map(transfer => 
      transfer.id === transferId 
        ? { 
            ...transfer, 
            status: 'RECEIVED' as const,
            received_by: 'current_user@thunderrol.com',
            received_at: new Date().toISOString()
          }
        : transfer
    ));
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
              <CardDescription>Crear una nueva transferencia de unidad</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateTransfer} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="unit_id">ID de Unidad *</Label>
                    <Input
                      id="unit_id"
                      value={newTransfer.unit_id}
                      onChange={(e) => setNewTransfer(prev => ({ ...prev, unit_id: e.target.value }))}
                      placeholder="UNIT_001"
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="eta">Fecha/Hora Estimada</Label>
                    <Input
                      id="eta"
                      type="datetime-local"
                      value={newTransfer.eta}
                      onChange={(e) => setNewTransfer(prev => ({ ...prev, eta: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Ubicación Origen *</Label>
                    <Select value={newTransfer.from_location} onValueChange={(value) => setNewTransfer(prev => ({ ...prev, from_location: value }))}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona origen" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="BODEGA">Bodega</SelectItem>
                        <SelectItem value="TALLER">Taller</SelectItem>
                        <SelectItem value="SUCURSAL:Centro">Sucursal Centro</SelectItem>
                        <SelectItem value="SUCURSAL:Norte">Sucursal Norte</SelectItem>
                        <SelectItem value="SUCURSAL:Sur">Sucursal Sur</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Ubicación Destino *</Label>
                    <Select value={newTransfer.to_location} onValueChange={(value) => setNewTransfer(prev => ({ ...prev, to_location: value }))}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona destino" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="BODEGA">Bodega</SelectItem>
                        <SelectItem value="TALLER">Taller</SelectItem>
                        <SelectItem value="SUCURSAL:Centro">Sucursal Centro</SelectItem>
                        <SelectItem value="SUCURSAL:Norte">Sucursal Norte</SelectItem>
                        <SelectItem value="SUCURSAL:Sur">Sucursal Sur</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <Label htmlFor="reason">Motivo</Label>
                  <Input
                    id="reason"
                    value={newTransfer.reason}
                    onChange={(e) => setNewTransfer(prev => ({ ...prev, reason: e.target.value }))}
                    placeholder="Motivo de la transferencia"
                  />
                </div>

                <div className="flex justify-end space-x-2">
                  <Button type="button" variant="outline" onClick={() => setShowNewTransfer(false)}>
                    Cancelar
                  </Button>
                  <Button 
                    type="submit" 
                    disabled={!newTransfer.unit_id || !newTransfer.from_location || !newTransfer.to_location}
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
            <CardTitle>Transferencias Activas</CardTitle>
            <CardDescription>Movimientos pendientes y en tránsito</CardDescription>
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
                    <TableHead>ETA</TableHead>
                    <TableHead>Creado Por</TableHead>
                    <TableHead>Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transfers.map((transfer) => (
                    <TableRow key={transfer.id}>
                      <TableCell className="font-mono text-sm">{transfer.id}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{transfer.unit_id}</div>
                          <div className="text-sm text-gray-500">{transfer.unit_info}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm">{transfer.from_location}</span>
                          <ArrowRight className="h-4 w-4 text-gray-400" />
                          <span className="text-sm">{transfer.to_location}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={transferStatusColors[transfer.status]}>
                          {transferStatusLabels[transfer.status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {transfer.eta ? '21/08/2025' : '-'}
                      </TableCell>
                      <TableCell className="text-sm">{transfer.created_by}</TableCell>
                      <TableCell>
                        {transfer.status === 'IN_TRANSIT' && (
                          <Button 
                            size="sm" 
                            onClick={() => handleReceiveTransfer(transfer.id)}
                          >
                            <CheckCircle className="mr-2 h-4 w-4" />
                            Recibir
                          </Button>
                        )}
                        {transfer.status === 'PENDING' && (
                          <Badge variant="outline">
                            <Clock className="mr-1 h-3 w-3" />
                            Pendiente
                          </Badge>
                        )}
                        {transfer.status === 'RECEIVED' && (
                          <Badge variant="default">
                            <CheckCircle className="mr-1 h-3 w-3" />
                            Completada
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
