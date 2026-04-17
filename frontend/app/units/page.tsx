
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
  sold_date: string | null;
  created_at: string;
}

interface Location {
  id: number;
  name: string;
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
  'black': 'bg-black',
  'red': 'bg-red-500',
  'blue': 'bg-blue-500',
  'white': 'bg-white border border-gray-300',
  'green': 'bg-green-500',
  'grey': 'bg-gray-500',
  'pink': 'bg-pink-500',
};

const colorLabels: Record<string, string> = {
  'negro': 'Negro', 'rojo': 'Rojo', 'azul': 'Azul', 'blanco': 'Blanco',
  'verde': 'Verde', 'gris': 'Gris', 'amarillo': 'Amarillo', 'naranja': 'Naranja',
  'rosa': 'Rosa', 'black': 'Negro', 'red': 'Rojo', 'blue': 'Azul',
  'white': 'Blanco', 'green': 'Verde', 'grey': 'Gris', 'pink': 'Rosa',
};

export default function UnitsPage() {
  const { data: session } = useSession();
  const [units, setUnits] = useState<Unit[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [locationFilter, setLocationFilter] = useState('all');

  useEffect(() => {
    const fetchData = async () => {
      const token = (session as any)?.accessToken;
      if (!token) return;

      try {
        const [unitsRes, locationsRes] = await Promise.all([
          fetch(`${API_URL}/api/v1/units/`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
          fetch(`${API_URL}/api/v1/locations/`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
        ]);

        if (unitsRes.ok) {
          const unitsData = await unitsRes.json();
          setUnits(unitsData);
        }
        if (locationsRes.ok) {
          const locationsData = await locationsRes.json();
          setLocations(locationsData);
        }
      } catch (err) {
        console.error('Error fetching units:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [session]);

  const filteredUnits = units.filter(unit => {
    const matchesSearch = !searchTerm || 
      unit.engine_number?.includes(searchTerm) ||
      unit.chassis_number?.includes(searchTerm) ||
      unit.brand?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      unit.model?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || unit.status === statusFilter;
    const matchesLocation = locationFilter === 'all' || String(unit.current_location_id) === locationFilter;
    
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
                  {Object.entries(statusLabels).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={locationFilter} onValueChange={setLocationFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Ubicación" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las Ubicaciones</SelectItem>
                  {locations.map((loc) => (
                    <SelectItem key={loc.id} value={String(loc.id)}>{loc.name}</SelectItem>
                  ))}
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
                            colorMap[unit.color.toLowerCase()] || 'bg-gray-300'
                          }`}></div>
                          {colorLabels[unit.color.toLowerCase()] || unit.color}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {unit.engine_number || '-'}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {unit.chassis_number || '-'}
                      </TableCell>
                      <TableCell>
                        <Badge className={statusColors[unit.status] || 'bg-gray-100 text-gray-800'}>
                          {statusLabels[unit.status] || unit.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{unit.current_location?.name || '-'}</TableCell>
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
