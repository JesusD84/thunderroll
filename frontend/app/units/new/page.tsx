
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Save } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useSession } from 'next-auth/react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Location {
  id: number;
  name: string;
}

export default function NewUnitPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [locations, setLocations] = useState<Location[]>([]);
  const [formData, setFormData] = useState({
    brand: '',
    model: '',
    color: '',
    engine_number: '',
    chassis_number: '',
    current_location_id: '',
    notes: ''
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLocations = async () => {
      const token = (session as any)?.accessToken;
      if (!token) return;
      try {
        const res = await fetch(`${API_URL}/api/v1/locations/`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (res.ok) setLocations(await res.json());
      } catch (err) {
        console.error('Error fetching locations:', err);
      }
    };
    fetchLocations();
  }, [session]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const token = (session as any)?.accessToken;
    if (!token) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/units/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          engine_number: formData.engine_number || null,
          chassis_number: formData.chassis_number || null,
          model: formData.model,
          brand: formData.brand,
          color: formData.color,
          current_location_id: formData.current_location_id ? parseInt(formData.current_location_id) : null,
          notes: formData.notes || null,
        }),
      });

      if (res.ok) {
        router.push('/units');
      } else {
        const err = await res.json();
        setError(err.detail || 'Error creando unidad');
      }
    } catch (err) {
      console.error('Error creando unidad:', err);
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center">
            <Link href="/units">
              <Button variant="ghost" size="sm" className="mr-4">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Agregar Nueva Unidad</h1>
              <p className="text-gray-600">Registra manualmente una nueva unidad en el inventario</p>
            </div>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
        <Card>
          <CardHeader>
            <CardTitle>Información de la Unidad</CardTitle>
            <CardDescription>
              Completa la información disponible. Los campos # Motor y # Chasis se pueden agregar después en el taller.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Información Básica */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="brand">Marca</Label>
                  <Input
                    id="brand"
                    value={formData.brand}
                    onChange={(e) => handleInputChange('brand', e.target.value)}
                    placeholder="ej. Honda, Yamaha"
                  />
                </div>
                
                <div>
                  <Label htmlFor="model">Modelo</Label>
                  <Input
                    id="model"
                    value={formData.model}
                    onChange={(e) => handleInputChange('model', e.target.value)}
                    placeholder="ej. PCX, NMAX"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="color">Color *</Label>
                <Select value={formData.color} onValueChange={(value) => handleInputChange('color', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona el color" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ROJO">Rojo</SelectItem>
                    <SelectItem value="NEGRO">Negro</SelectItem>
                    <SelectItem value="VERDE">Verde</SelectItem>
                    <SelectItem value="ROSA">Rosa</SelectItem>
                    <SelectItem value="GRIS">Gris</SelectItem>
                    <SelectItem value="AZUL">Azul</SelectItem>
                    <SelectItem value="BLANCO">Blanco</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Números de Identificación */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="engine_number">Número de Motor</Label>
                  <Input
                    id="engine_number"
                    value={formData.engine_number}
                    onChange={(e) => handleInputChange('engine_number', e.target.value)}
                    placeholder="Opcional - se puede agregar en el taller"
                  />
                </div>
                
                <div>
                  <Label htmlFor="chassis_number">Número de Chasis</Label>
                  <Input
                    id="chassis_number"
                    value={formData.chassis_number}
                    onChange={(e) => handleInputChange('chassis_number', e.target.value)}
                    placeholder="Opcional - se puede agregar en el taller"
                  />
                </div>
              </div>

              {/* Ubicación */}
              <div>
                <Label>Ubicación Inicial</Label>
                <Select value={formData.current_location_id} onValueChange={(value) => handleInputChange('current_location_id', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona ubicación" />
                  </SelectTrigger>
                  <SelectContent>
                    {locations.map((loc) => (
                      <SelectItem key={loc.id} value={String(loc.id)}>{loc.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="notes">Notas</Label>
                <Input
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => handleInputChange('notes', e.target.value)}
                  placeholder="Observaciones adicionales"
                />
              </div>

              {error && (
                <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
              )}

              {/* Botones */}
              <div className="flex justify-end space-x-4">
                <Link href="/units">
                  <Button variant="outline" disabled={loading}>
                    Cancelar
                  </Button>
                </Link>
                <Button type="submit" disabled={loading || !formData.model || !formData.brand || !formData.color || !formData.current_location_id}>
                  {loading ? (
                    <>Guardando...</>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Guardar Unidad
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
