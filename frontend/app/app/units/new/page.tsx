
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Save } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function NewUnitPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    brand: '',
    model: '',
    color: '',
    engine_number: '',
    chassis_number: '',
    supplier_invoice: '',
    shipment_batch: '',
    notes: ''
  });

  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Aquí iría la llamada al API del backend
      console.log('Creando unidad:', formData);
      
      // Simular delay de API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Redirigir a la lista de unidades
      router.push('/units');
    } catch (error) {
      console.error('Error creando unidad:', error);
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
                    <SelectItem value="red">Rojo</SelectItem>
                    <SelectItem value="black">Negro</SelectItem>
                    <SelectItem value="green">Verde</SelectItem>
                    <SelectItem value="pink">Rosa</SelectItem>
                    <SelectItem value="grey">Gris</SelectItem>
                    <SelectItem value="blue">Azul</SelectItem>
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

              {/* Información de Lote */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="supplier_invoice">Factura Proveedor</Label>
                  <Input
                    id="supplier_invoice"
                    value={formData.supplier_invoice}
                    onChange={(e) => handleInputChange('supplier_invoice', e.target.value)}
                    placeholder="Número de factura"
                  />
                </div>
                
                <div>
                  <Label htmlFor="shipment_batch">Lote de Envío</Label>
                  <Input
                    id="shipment_batch"
                    value={formData.shipment_batch}
                    onChange={(e) => handleInputChange('shipment_batch', e.target.value)}
                    placeholder="Código del lote"
                  />
                </div>
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

              {/* Botones */}
              <div className="flex justify-end space-x-4">
                <Link href="/units">
                  <Button variant="outline" disabled={loading}>
                    Cancelar
                  </Button>
                </Link>
                <Button type="submit" disabled={loading || !formData.color}>
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
