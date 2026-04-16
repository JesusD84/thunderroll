
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
import { useSession } from 'next-auth/react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Location {
  id: number;
  name: string;
  address: string | null;
  created_at: string;
}

interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export default function SettingsPage() {
  const { data: session } = useSession();
  const [locations, setLocations] = useState<Location[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'locations' | 'users'>('locations');
  const [showNewLocation, setShowNewLocation] = useState(false);
  const [newLocation, setNewLocation] = useState({ name: '', address: '' });

  useEffect(() => {
    const fetchData = async () => {
      const token = (session as any)?.accessToken;
      if (!token) return;

      try {
        const [locRes, usersRes] = await Promise.all([
          fetch(`${API_URL}/api/v1/locations/`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
          fetch(`${API_URL}/api/v1/user/`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
        ]);

        if (locRes.ok) {
          setLocations(await locRes.json());
        }
        if (usersRes.ok) {
          setUsers(await usersRes.json());
        }
      } catch (err) {
        console.error('Error fetching settings data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [session]);

  const handleCreateLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = (session as any)?.accessToken;
    if (!token) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/locations/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newLocation.name,
          address: newLocation.address || null,
        }),
      });

      if (res.ok) {
        const created = await res.json();
        setLocations(prev => [...prev, created]);
        setShowNewLocation(false);
        setNewLocation({ name: '', address: '' });
      }
    } catch (err) {
      console.error('Error creating location:', err);
    }
  };

  const handleDeleteLocation = async (locationId: number) => {
    const token = (session as any)?.accessToken;
    if (!token) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/locations/${locationId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (res.ok) {
        setLocations(prev => prev.filter(loc => loc.id !== locationId));
      }
    } catch (err) {
      console.error('Error deleting location:', err);
    }
  };

  const roleColors: Record<string, string> = {
    'admin': 'bg-red-100 text-red-800',
    'manager': 'bg-blue-100 text-blue-800',
    'operator': 'bg-green-100 text-green-800',
    'viewer': 'bg-purple-100 text-purple-800',
  };

  const roleLabels: Record<string, string> = {
    'admin': 'ADMIN',
    'manager': 'MANAGER',
    'operator': 'OPERADOR',
    'viewer': 'VIEWER',
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('es-MX', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
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
                        <Label htmlFor="location_address">Dirección</Label>
                        <Input
                          id="location_address"
                          value={newLocation.address}
                          onChange={(e) => setNewLocation(prev => ({ ...prev, address: e.target.value }))}
                          placeholder="ej. Av. Vallarta 1234"
                        />
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
                        <TableHead>ID</TableHead>
                        <TableHead>Nombre</TableHead>
                        <TableHead>Dirección</TableHead>
                        <TableHead>Creado</TableHead>
                        <TableHead>Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {locations.map((location) => (
                        <TableRow key={location.id}>
                          <TableCell className="font-mono text-sm">{location.id}</TableCell>
                          <TableCell className="font-medium">{location.name}</TableCell>
                          <TableCell className="text-sm">{location.address || '-'}</TableCell>
                          <TableCell className="text-sm">
                            {formatDate(location.created_at)}
                          </TableCell>
                          <TableCell>
                            <div className="flex space-x-2">
                              <Button variant="outline" size="sm">
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button 
                                variant="outline" 
                                size="sm"
                                onClick={() => handleDeleteLocation(location.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                      {locations.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center text-sm text-gray-500">
                            No hay ubicaciones registradas
                          </TableCell>
                        </TableRow>
                      )}
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
                      <TableHead>Creado</TableHead>
                      <TableHead>Estado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium">{user.first_name} {user.last_name}</TableCell>
                        <TableCell>{user.email}</TableCell>
                        <TableCell>
                          <Badge className={roleColors[user.role] || 'bg-gray-100 text-gray-800'}>
                            {roleLabels[user.role] || user.role.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatDate(user.created_at)}
                        </TableCell>
                        <TableCell>
                          <Badge variant={user.is_active ? 'default' : 'secondary'}>
                            {user.is_active ? 'Activo' : 'Inactivo'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                    {users.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-sm text-gray-500">
                          No hay usuarios o no tienes permisos para verlos
                        </TableCell>
                      </TableRow>
                    )}
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
                <h4 className="font-medium">Manager</h4>
                <p className="text-sm text-gray-600">Email: manager@thunderrol.com</p>
                <p className="text-sm text-gray-600">Password: manager123</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium">Operador</h4>
                <p className="text-sm text-gray-600">Email: operator@thunderrol.com</p>
                <p className="text-sm text-gray-600">Password: operator123</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium">Viewer</h4>
                <p className="text-sm text-gray-600">Email: viewer@thunderrol.com</p>
                <p className="text-sm text-gray-600">Password: viewer123</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
