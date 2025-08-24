
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Plus, Edit, Trash2, MapPin } from 'lucide-react';

interface Location {
  id: string;
  name: string;
  type: 'BODEGA' | 'TALLER' | 'SUCURSAL';
  active: boolean;
  created_at: string;
}

interface User {
  id: string;
  name: string;
  email: string;
  role: 'ADMIN' | 'INVENTARIO' | 'TALLER' | 'VENTAS';
  created_at: string;
  last_login_at?: string;
}

export default function SettingsPage() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'locations' | 'users'>('locations');
  const [showNewLocation, setShowNewLocation] = useState(false);
  const [newLocation, setNewLocation] = useState<{
    name: string;
    type: 'BODEGA' | 'TALLER' | 'SUCURSAL';
  }>({
    name: '',
    type: 'SUCURSAL'
  });

  useEffect(() => {
    // Simular carga de datos
    const mockLocations: Location[] = [
      {
        id: '1',
        name: 'Bodega Principal',
        type: 'BODEGA',
        active: true,
        created_at: '2025-01-01T00:00:00Z'
      },
      {
        id: '2',
        name: 'Taller Central',
        type: 'TALLER',
        active: true,
        created_at: '2025-01-01T00:00:00Z'
      },
      {
        id: '3',
        name: 'Sucursal Centro',
        type: 'SUCURSAL',
        active: true,
        created_at: '2025-01-01T00:00:00Z'
      },
      {
        id: '4',
        name: 'Sucursal Norte',
        type: 'SUCURSAL',
        active: true,
        created_at: '2025-01-01T00:00:00Z'
      },
      {
        id: '5',
        name: 'Sucursal Sur',
        type: 'SUCURSAL',
        active: true,
        created_at: '2025-01-01T00:00:00Z'
      }
    ];

    const mockUsers: User[] = [
      {
        id: '1',
        name: 'Admin Usuario',
        email: 'admin@thunderrol.com',
        role: 'ADMIN',
        created_at: '2025-01-01T00:00:00Z',
        last_login_at: '2025-08-20T14:00:00Z'
      },
      {
        id: '2',
        name: 'Inventario Usuario',
        email: 'inventario@thunderrol.com',
        role: 'INVENTARIO',
        created_at: '2025-01-01T00:00:00Z',
        last_login_at: '2025-08-20T13:30:00Z'
      },
      {
        id: '3',
        name: 'Taller Usuario',
        email: 'taller@thunderrol.com',
        role: 'TALLER',
        created_at: '2025-01-01T00:00:00Z',
        last_login_at: '2025-08-20T12:00:00Z'
      },
      {
        id: '4',
        name: 'Ventas Usuario',
        email: 'ventas@thunderrol.com',
        role: 'VENTAS',
        created_at: '2025-01-01T00:00:00Z',
        last_login_at: '2025-08-20T11:00:00Z'
      }
    ];

    setTimeout(() => {
      setLocations(mockLocations);
      setUsers(mockUsers);
      setLoading(false);
    }, 500);
  }, []);

  const handleCreateLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const newLocationRecord: Location = {
      id: Date.now().toString(),
      name: newLocation.name,
      type: newLocation.type,
      active: true,
      created_at: new Date().toISOString()
    };

    setLocations(prev => [...prev, newLocationRecord]);
    setShowNewLocation(false);
    setNewLocation({ name: '', type: 'SUCURSAL' });
  };

  const handleToggleLocation = (locationId: string) => {
    setLocations(prev => prev.map(loc => 
      loc.id === locationId ? { ...loc, active: !loc.active } : loc
    ));
  };

  const roleColors = {
    'ADMIN': 'bg-red-100 text-red-800',
    'INVENTARIO': 'bg-blue-100 text-blue-800',
    'TALLER': 'bg-green-100 text-green-800',
    'VENTAS': 'bg-purple-100 text-purple-800',
  };

  const locationTypeColors = {
    'BODEGA': 'bg-yellow-100 text-yellow-800',
    'TALLER': 'bg-blue-100 text-blue-800',
    'SUCURSAL': 'bg-green-100 text-green-800',
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Configuración</h1>
          <p className="text-gray-600">Gestiona ubicaciones y usuarios del sistema</p>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Tabs */}
        <div className="flex space-x-1 mb-6">
          <Button
            variant={activeTab === 'locations' ? 'default' : 'outline'}
            onClick={() => setActiveTab('locations')}
          >
            <MapPin className="mr-2 h-4 w-4" />
            Ubicaciones
          </Button>
          <Button
            variant={activeTab === 'users' ? 'default' : 'outline'}
            onClick={() => setActiveTab('users')}
          >
            Usuarios
          </Button>
        </div>

        {/* Ubicaciones */}
        {activeTab === 'locations' && (
          <div>
            {/* Formulario Nueva Ubicación */}
            {showNewLocation && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>Nueva Ubicación</CardTitle>
                  <CardDescription>Agregar una nueva ubicación al sistema</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleCreateLocation} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="location_name">Nombre *</Label>
                        <Input
                          id="location_name"
                          value={newLocation.name}
                          onChange={(e) => setNewLocation(prev => ({ ...prev, name: e.target.value }))}
                          placeholder="ej. Sucursal Este"
                          required
                        />
                      </div>

                      <div>
                        <Label>Tipo *</Label>
                        <Select 
                          value={newLocation.type} 
                          onValueChange={(value) => 
                            setNewLocation(prev => ({ ...prev, type: value as 'BODEGA' | 'TALLER' | 'SUCURSAL' }))
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="BODEGA">Bodega</SelectItem>
                            <SelectItem value="TALLER">Taller</SelectItem>
                            <SelectItem value="SUCURSAL">Sucursal</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="flex justify-end space-x-2">
                      <Button type="button" variant="outline" onClick={() => setShowNewLocation(false)}>
                        Cancelar
                      </Button>
                      <Button type="submit" disabled={!newLocation.name}>
                        Crear Ubicación
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            )}

            {/* Lista de Ubicaciones */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Ubicaciones</CardTitle>
                    <CardDescription>Gestiona las ubicaciones del sistema</CardDescription>
                  </div>
                  <Button onClick={() => setShowNewLocation(true)}>
                    <Plus className="mr-2 h-4 w-4" />
                    Nueva Ubicación
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="text-center py-8">Cargando ubicaciones...</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Nombre</TableHead>
                        <TableHead>Tipo</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Creado</TableHead>
                        <TableHead>Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {locations.map((location) => (
                        <TableRow key={location.id}>
                          <TableCell className="font-medium">{location.name}</TableCell>
                          <TableCell>
                            <Badge className={locationTypeColors[location.type]}>
                              {location.type}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={location.active ? 'default' : 'secondary'}>
                              {location.active ? 'Activa' : 'Inactiva'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm">
                            01/01/2025
                          </TableCell>
                          <TableCell>
                            <div className="flex space-x-2">
                              <Button variant="outline" size="sm">
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button 
                                variant="outline" 
                                size="sm"
                                onClick={() => handleToggleLocation(location.id)}
                              >
                                {location.active ? 'Desactivar' : 'Activar'}
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Usuarios */}
        {activeTab === 'users' && (
          <Card>
            <CardHeader>
              <CardTitle>Usuarios del Sistema</CardTitle>
              <CardDescription>Lista de usuarios con acceso al sistema</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-8">Cargando usuarios...</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Rol</TableHead>
                      <TableHead>Último Acceso</TableHead>
                      <TableHead>Estado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium">{user.name}</TableCell>
                        <TableCell>{user.email}</TableCell>
                        <TableCell>
                          <Badge className={roleColors[user.role]}>
                            {user.role}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          20/08/2025
                        </TableCell>
                        <TableCell>
                          <Badge variant="default">Activo</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        )}

        {/* Credenciales Demo */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Credenciales Demo</CardTitle>
            <CardDescription>Usuarios de demostración para testing</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <h4 className="font-medium">Administrador</h4>
                <p className="text-sm text-gray-600">Email: admin@thunderrol.com</p>
                <p className="text-sm text-gray-600">Password: admin123</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium">Inventario</h4>
                <p className="text-sm text-gray-600">Email: inventario@thunderrol.com</p>
                <p className="text-sm text-gray-600">Password: inv123</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium">Taller</h4>
                <p className="text-sm text-gray-600">Email: taller@thunderrol.com</p>
                <p className="text-sm text-gray-600">Password: taller123</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium">Ventas</h4>
                <p className="text-sm text-gray-600">Email: ventas@thunderrol.com</p>
                <p className="text-sm text-gray-600">Password: ventas123</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
