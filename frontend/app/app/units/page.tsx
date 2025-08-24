
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Search, Filter } from 'lucide-react';
import Link from 'next/link';

interface Unit {
  id: string;
  brand?: string;
  model?: string;
  color: string;
  engine_number?: string;
  chassis_number?: string;
  status: string;
  location: string;
  created_at: string;
}

const statusColors = {
  'EN_BODEGA_NO_IDENTIFICADA': 'bg-red-100 text-red-800',
  'IDENTIFICADA_EN_TALLER': 'bg-yellow-100 text-yellow-800',
  'EN_TRANSITO_TALLER_SUCURSAL': 'bg-blue-100 text-blue-800',
  'EN_SUCURSAL_DISPONIBLE': 'bg-green-100 text-green-800',
  'VENDIDA': 'bg-gray-100 text-gray-800',
};

const statusLabels = {
  'EN_BODEGA_NO_IDENTIFICADA': 'En Bodega (No ID)',
  'IDENTIFICADA_EN_TALLER': 'Identificada en Taller',
  'EN_TRANSITO_TALLER_SUCURSAL': 'En Tránsito',
  'EN_SUCURSAL_DISPONIBLE': 'En Sucursal',
  'VENDIDA': 'Vendida',
};

export default function UnitsPage() {
  const [units, setUnits] = useState<Unit[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [locationFilter, setLocationFilter] = useState('all');

  useEffect(() => {
    // Simular datos mientras conectamos con el backend
    const sampleUnits: Unit[] = [
      {
        id: '1',
        brand: 'Honda',
        model: 'PCX',
        color: 'red',
        engine_number: '20250823035825',
        chassis_number: 'HXY202507501',
        status: 'EN_SUCURSAL_DISPONIBLE',
        location: 'SUCURSAL:Centro',
        created_at: '2025-08-20T10:00:00Z'
      },
      {
        id: '2',
        brand: 'Yamaha',
        model: 'NMAX',
        color: 'black',
        engine_number: '20250823035826',
        chassis_number: 'HXY202507502',
        status: 'IDENTIFICADA_EN_TALLER',
        location: 'TALLER',
        created_at: '2025-08-20T09:00:00Z'
      },
      {
        id: '3',
        color: 'green',
        status: 'EN_BODEGA_NO_IDENTIFICADA',
        location: 'BODEGA',
        created_at: '2025-08-20T08:00:00Z'
      }
    ];
    
    setTimeout(() => {
      setUnits(sampleUnits);
      setLoading(false);
    }, 1000);
  }, []);

  const filteredUnits = units.filter(unit => {
    const matchesSearch = !searchTerm || 
      unit.engine_number?.includes(searchTerm) ||
      unit.chassis_number?.includes(searchTerm) ||
      unit.brand?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      unit.model?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || unit.status === statusFilter;
    const matchesLocation = locationFilter === 'all' || unit.location === locationFilter;
    
    return matchesSearch && matchesStatus && matchesLocation;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Gestión de Unidades</h1>
              <p className="text-gray-600">Administra el inventario de motos y scooters</p>
            </div>
            <Link href="/units/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Agregar Unidad
              </Button>
            </Link>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Filtros */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Filtros</CardTitle>
            <CardDescription>Busca y filtra las unidades del inventario</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <Input
                  placeholder="Buscar por # motor, chasis, marca..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full"
                />
              </div>
              
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los Estados</SelectItem>
                  <SelectItem value="EN_BODEGA_NO_IDENTIFICADA">En Bodega (No ID)</SelectItem>
                  <SelectItem value="IDENTIFICADA_EN_TALLER">Identificada en Taller</SelectItem>
                  <SelectItem value="EN_TRANSITO_TALLER_SUCURSAL">En Tránsito</SelectItem>
                  <SelectItem value="EN_SUCURSAL_DISPONIBLE">En Sucursal</SelectItem>
                  <SelectItem value="VENDIDA">Vendida</SelectItem>
                </SelectContent>
              </Select>

              <Select value={locationFilter} onValueChange={setLocationFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Ubicación" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las Ubicaciones</SelectItem>
                  <SelectItem value="BODEGA">Bodega</SelectItem>
                  <SelectItem value="TALLER">Taller</SelectItem>
                  <SelectItem value="SUCURSAL:Centro">Sucursal Centro</SelectItem>
                  <SelectItem value="SUCURSAL:Norte">Sucursal Norte</SelectItem>
                  <SelectItem value="SUCURSAL:Sur">Sucursal Sur</SelectItem>
                </SelectContent>
              </Select>

              <Button variant="outline" onClick={() => {
                setSearchTerm('');
                setStatusFilter('all');
                setLocationFilter('all');
              }}>
                <Filter className="mr-2 h-4 w-4" />
                Limpiar Filtros
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tabla de Unidades */}
        <Card>
          <CardHeader>
            <CardTitle>Unidades ({filteredUnits.length})</CardTitle>
            <CardDescription>Lista de todas las unidades en el sistema</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">Cargando unidades...</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Marca/Modelo</TableHead>
                    <TableHead>Color</TableHead>
                    <TableHead># Motor</TableHead>
                    <TableHead># Chasis</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Ubicación</TableHead>
                    <TableHead>Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUnits.map((unit) => (
                    <TableRow key={unit.id}>
                      <TableCell className="font-mono text-sm">{unit.id}</TableCell>
                      <TableCell>
                        {unit.brand && unit.model ? `${unit.brand} ${unit.model}` : 'No especificado'}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          <div className={`w-4 h-4 rounded-full mr-2 ${
                            unit.color === 'red' ? 'bg-red-500' :
                            unit.color === 'black' ? 'bg-black' :
                            unit.color === 'green' ? 'bg-green-500' :
                            unit.color === 'pink' ? 'bg-pink-500' :
                            unit.color === 'grey' ? 'bg-gray-500' :
                            unit.color === 'blue' ? 'bg-blue-500' :
                            'bg-gray-300'
                          }`}></div>
                          {unit.color}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {unit.engine_number || '-'}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {unit.chassis_number || '-'}
                      </TableCell>
                      <TableCell>
                        <Badge className={statusColors[unit.status as keyof typeof statusColors]}>
                          {statusLabels[unit.status as keyof typeof statusLabels]}
                        </Badge>
                      </TableCell>
                      <TableCell>{unit.location}</TableCell>
                      <TableCell>
                        <Link href={`/units/${unit.id}`}>
                          <Button variant="outline" size="sm">Ver Detalle</Button>
                        </Link>
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
