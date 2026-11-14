
'use client';

import { sessionAwareFetch } from '@/lib/api';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Plus, Edit, Trash2, MapPin } from 'lucide-react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';

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

const emptyNewUser = {
  email: '',
  username: '',
  first_name: '',
  last_name: '',
  password: '',
  role: 'operator',
};

const emptyEditUser = {
  email: '',
  username: '',
  first_name: '',
  last_name: '',
  role: 'operator',
  is_active: 'true',
};

export default function SettingsPage() {
  const { data: session } = useSession();
  const { manageUsers, isAdmin } = useAuth();
  const router = useRouter();
  const [locations, setLocations] = useState<Location[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'locations' | 'users'>('locations');
  const [showNewLocation, setShowNewLocation] = useState(false);
  const [newLocation, setNewLocation] = useState({ name: '', address: '' });
  const [editingLocation, setEditingLocation] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: '', address: '' });
  const [editSaving, setEditSaving] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [showNewUser, setShowNewUser] = useState(false);
  const [newUser, setNewUser] = useState(emptyNewUser);
  const [userSaving, setUserSaving] = useState(false);
  const [userError, setUserError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editUserForm, setEditUserForm] = useState(emptyEditUser);
  const [editUserSaving, setEditUserSaving] = useState(false);
  const [editUserError, setEditUserError] = useState<string | null>(null);
  const [userActionError, setUserActionError] = useState<string | null>(null);

  useEffect(() => {
    if (session && !manageUsers) {
      router.replace('/');
    }
  }, [session, manageUsers, router]);

  const mapDeleteLocationErrorToSpanish = (detail: string): string => {
    const match = detail.match(/^Cannot delete: there (?:is|are) (\d+) units? at this location$/);
    if (match) {
      const unitCount = Number(match[1]);
      return `No se puede eliminar: hay ${unitCount} unidad${unitCount === 1 ? '' : 'es'} en esta ubicación`;
    }
    return detail;
  };

  useEffect(() => {
    const fetchData = async () => {
      const token = (session as any)?.accessToken;
      if (!token) return;

      try {
        const [locRes, usersRes] = await Promise.all([
          sessionAwareFetch(`${API_URL}/api/v1/locations/`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
          sessionAwareFetch(`${API_URL}/api/v1/user/`, {
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
      const res = await sessionAwareFetch(`${API_URL}/api/v1/locations/`, {
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

  const handleEditLocation = async (locationId: number) => {
    const token = (session as any)?.accessToken;
    if (!token) return;
    setEditSaving(true);
    setLocationError(null);
    try {
      const res = await sessionAwareFetch(`${API_URL}/api/v1/locations/${locationId}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editForm.name || undefined,
          address: editForm.address || null,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setLocations(prev => prev.map(l => l.id === locationId ? updated : l));
        setEditingLocation(null);
      } else {
        const err = await res.json();
        setLocationError(typeof err.detail === 'string' ? err.detail : 'Error actualizando ubicación');
      }
    } catch { setLocationError('Error de conexión'); }
    finally { setEditSaving(false); }
  };

  const handleDeleteLocation = async (locationId: number) => {
    if (!confirm('¿Seguro que deseas eliminar esta ubicación? Solo se puede eliminar si no tiene unidades asignadas.')) return;
    const token = (session as any)?.accessToken;
    if (!token) return;
    setLocationError(null);

    try {
      const res = await sessionAwareFetch(`${API_URL}/api/v1/locations/${locationId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (res.ok) {
        setLocations(prev => prev.filter(loc => loc.id !== locationId));
      } else {
        const err = await res.json();
        setLocationError(typeof err.detail === 'string' ? mapDeleteLocationErrorToSpanish(err.detail) : 'Error eliminando ubicación');
      }
    } catch {
      setLocationError('Error de conexión');
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = (session as any)?.accessToken;
    if (!token) return;
    setUserSaving(true);
    setUserError(null);

    try {
      const res = await sessionAwareFetch(`${API_URL}/api/v1/user/`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newUser,
          role: isAdmin ? newUser.role : 'operator',
        }),
      });

      if (res.ok) {
        const created = await res.json();
        setUsers(prev => [...prev, created]);
        setShowNewUser(false);
        setNewUser(emptyNewUser);
      } else {
        const err = await res.json();
        setUserError(typeof err.detail === 'string' ? err.detail : 'Error creando usuario');
      }
    } catch {
      setUserError('Error de conexión');
    } finally {
      setUserSaving(false);
    }
  };

  const isEditingSelf = editingUser !== null && session?.user?.id === String(editingUser.id);

  const openEditUser = (user: User) => {
    setEditingUser(user);
    setEditUserForm({
      email: user.email,
      username: user.username,
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
      is_active: user.is_active ? 'true' : 'false',
    });
    setEditUserError(null);
  };

  const closeEditUser = () => {
    setEditingUser(null);
    setEditUserError(null);
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = (session as any)?.accessToken;
    if (!token || !editingUser) return;
    setEditUserSaving(true);
    setEditUserError(null);

    try {
      const res = await sessionAwareFetch(`${API_URL}/api/v1/user/${editingUser.id}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: editUserForm.email,
          username: editUserForm.username,
          first_name: editUserForm.first_name,
          last_name: editUserForm.last_name,
          role: editUserForm.role,
          is_active: editUserForm.is_active === 'true',
        }),
      });

      if (res.ok) {
        const updated: User = await res.json();
        setUsers(prev => prev.map(u => u.id === updated.id ? updated : u));
        closeEditUser();
      } else {
        const err = await res.json();
        setEditUserError(typeof err.detail === 'string' ? err.detail : 'Error actualizando usuario');
      }
    } catch {
      setEditUserError('Error de conexión');
    } finally {
      setEditUserSaving(false);
    }
  };

  const handleDeleteUser = async (user: User) => {
    if (!confirm(`¿Seguro que deseas eliminar a ${user.first_name} ${user.last_name}? Esta acción no se puede deshacer.`)) return;
    const token = (session as any)?.accessToken;
    if (!token) return;
    setUserActionError(null);

    try {
      const res = await sessionAwareFetch(`${API_URL}/api/v1/user/${user.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (res.ok) {
        setUsers(prev => prev.filter(u => u.id !== user.id));
      } else {
        const err = await res.json().catch(() => ({}));
        setUserActionError(typeof err.detail === 'string' ? err.detail : 'Error eliminando usuario');
      }
    } catch {
      setUserActionError('Error de conexión');
    }
  };

  const roleColors: Record<string, string> = {
    'admin': 'bg-red-100 text-red-800',
    'manager': 'bg-blue-100 text-blue-800',
    'operator': 'bg-green-100 text-green-800',
  };

  const roleLabels: Record<string, string> = {
    'admin': 'ADMIN',
    'manager': 'MANAGER',
    'operator': 'OPERATIVO',
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
                {locationError && (
                  <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{locationError}</div>
                )}
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
                          <TableCell>
                            {editingLocation === location.id ? (
                              <Input value={editForm.name} onChange={(e) => setEditForm(p => ({...p, name: e.target.value}))} className="h-8" />
                            ) : (
                              <span className="font-medium">{location.name}</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {editingLocation === location.id ? (
                              <Input value={editForm.address} onChange={(e) => setEditForm(p => ({...p, address: e.target.value}))} className="h-8" placeholder="Dirección" />
                            ) : (
                              <span className="text-sm">{location.address || '-'}</span>
                            )}
                          </TableCell>
                          <TableCell className="text-sm">
                            {formatDate(location.created_at)}
                          </TableCell>
                          <TableCell>
                            {editingLocation === location.id ? (
                              <div className="flex space-x-2">
                                <Button size="sm" onClick={() => handleEditLocation(location.id)} disabled={editSaving || !editForm.name}>
                                  {editSaving ? 'Guardando...' : 'Guardar'}
                                </Button>
                                <Button variant="outline" size="sm" onClick={() => setEditingLocation(null)} disabled={editSaving}>
                                  Cancelar
                                </Button>
                              </div>
                            ) : (
                              <div className="flex space-x-2">
                                <Button variant="outline" size="sm" onClick={() => {
                                  setEditingLocation(location.id);
                                  setEditForm({ name: location.name, address: location.address || '' });
                                  setLocationError(null);
                                }}>
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
                            )}
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
          <div>
            {showNewUser && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>Nuevo Usuario</CardTitle>
                  <CardDescription>
                    {isAdmin
                      ? 'Crea un usuario con cualquier rol'
                      : 'Los managers solo pueden crear usuarios con rol Operativo'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleCreateUser} className="space-y-4">
                    {userError && (
                      <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{userError}</div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="user_first_name">Nombre *</Label>
                        <Input
                          id="user_first_name"
                          value={newUser.first_name}
                          onChange={(e) => setNewUser(prev => ({ ...prev, first_name: e.target.value }))}
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="user_last_name">Apellido *</Label>
                        <Input
                          id="user_last_name"
                          value={newUser.last_name}
                          onChange={(e) => setNewUser(prev => ({ ...prev, last_name: e.target.value }))}
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="user_email">Email *</Label>
                        <Input
                          id="user_email"
                          type="email"
                          value={newUser.email}
                          onChange={(e) => setNewUser(prev => ({ ...prev, email: e.target.value }))}
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="user_username">Usuario *</Label>
                        <Input
                          id="user_username"
                          value={newUser.username}
                          onChange={(e) => setNewUser(prev => ({ ...prev, username: e.target.value }))}
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="user_password">Contraseña *</Label>
                        <Input
                          id="user_password"
                          type="password"
                          minLength={8}
                          value={newUser.password}
                          onChange={(e) => setNewUser(prev => ({ ...prev, password: e.target.value }))}
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="user_role">Rol *</Label>
                        {isAdmin ? (
                          <Select
                            value={newUser.role}
                            onValueChange={(value) => setNewUser(prev => ({ ...prev, role: value }))}
                          >
                            <SelectTrigger id="user_role">
                              <SelectValue placeholder="Selecciona rol" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="admin">Administrador</SelectItem>
                              <SelectItem value="manager">Manager</SelectItem>
                              <SelectItem value="operator">Operativo</SelectItem>
                            </SelectContent>
                          </Select>
                        ) : (
                          <Input value="Operativo" disabled />
                        )}
                      </div>
                    </div>

                    <div className="flex justify-end space-x-2">
                      <Button type="button" variant="outline" onClick={() => { setShowNewUser(false); setUserError(null); }}>
                        Cancelar
                      </Button>
                      <Button type="submit" disabled={userSaving}>
                        {userSaving ? 'Creando...' : 'Crear Usuario'}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            )}

            <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Usuarios del Sistema</CardTitle>
                  <CardDescription>Lista de usuarios con acceso al sistema</CardDescription>
                </div>
                <Button onClick={() => setShowNewUser(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Nuevo Usuario
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {userActionError && (
                <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{userActionError}</div>
              )}
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
                      {isAdmin && <TableHead>Acciones</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => {
                      const isSelf = session?.user?.id === String(user.id);
                      return (
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
                          {isAdmin && (
                            <TableCell>
                              <div className="flex space-x-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  aria-label={`Editar ${user.first_name} ${user.last_name}`}
                                  onClick={() => openEditUser(user)}
                                >
                                  <Edit className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  aria-label={`Eliminar ${user.first_name} ${user.last_name}`}
                                  disabled={isSelf}
                                  title={isSelf ? 'No puedes eliminar tu propia cuenta' : undefined}
                                  onClick={() => handleDeleteUser(user)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          )}
                        </TableRow>
                      );
                    })}
                    {users.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={isAdmin ? 6 : 5} className="text-center text-sm text-gray-500">
                          No hay usuarios o no tienes permisos para verlos
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
      </main>

      {/* Editar Usuario */}
      <Dialog open={editingUser !== null} onOpenChange={(open) => { if (!open) closeEditUser(); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Usuario</DialogTitle>
            <DialogDescription>Actualiza los datos y el rol del usuario</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdateUser} className="space-y-4">
            {editUserError && (
              <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{editUserError}</div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="edit_user_first_name">Nombre *</Label>
                <Input
                  id="edit_user_first_name"
                  value={editUserForm.first_name}
                  onChange={(e) => setEditUserForm(prev => ({ ...prev, first_name: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="edit_user_last_name">Apellido *</Label>
                <Input
                  id="edit_user_last_name"
                  value={editUserForm.last_name}
                  onChange={(e) => setEditUserForm(prev => ({ ...prev, last_name: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="edit_user_email">Email *</Label>
                <Input
                  id="edit_user_email"
                  type="email"
                  value={editUserForm.email}
                  onChange={(e) => setEditUserForm(prev => ({ ...prev, email: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="edit_user_username">Usuario *</Label>
                <Input
                  id="edit_user_username"
                  value={editUserForm.username}
                  onChange={(e) => setEditUserForm(prev => ({ ...prev, username: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="edit_user_role">Rol *</Label>
                <Select
                  value={editUserForm.role}
                  onValueChange={(value) => setEditUserForm(prev => ({ ...prev, role: value }))}
                  disabled={isEditingSelf}
                >
                  <SelectTrigger id="edit_user_role">
                    <SelectValue placeholder="Selecciona rol" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Administrador</SelectItem>
                    <SelectItem value="manager">Manager</SelectItem>
                    <SelectItem value="operator">Operativo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="edit_user_status">Estado *</Label>
                <Select
                  value={editUserForm.is_active}
                  onValueChange={(value) => setEditUserForm(prev => ({ ...prev, is_active: value }))}
                  disabled={isEditingSelf}
                >
                  <SelectTrigger id="edit_user_status">
                    <SelectValue placeholder="Selecciona estado" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">Activo</SelectItem>
                    <SelectItem value="false">Inactivo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={closeEditUser} disabled={editUserSaving}>
                Cancelar
              </Button>
              <Button type="submit" disabled={editUserSaving}>
                {editUserSaving ? 'Guardando...' : 'Guardar Cambios'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
