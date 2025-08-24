
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DatePicker } from '@/components/ui/date-picker';
import { Download, FileText, Calendar } from 'lucide-react';

export default function ReportsPage() {
  const [dateFrom, setDateFrom] = useState<Date | undefined>(undefined);
  const [dateTo, setDateTo] = useState<Date | undefined>(undefined);
  const [format, setFormat] = useState('xlsx');
  const [reportType, setReportType] = useState('movements');
  const [loading, setLoading] = useState(false);

  const handleGenerateReport = async () => {
    if (!dateFrom || !dateTo) {
      alert('Por favor selecciona ambas fechas');
      return;
    }

    setLoading(true);
    
    try {
      // Simular generación de reporte
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Aquí iría la llamada al API del backend
      console.log('Generando reporte:', {
        type: reportType,
        from: dateFrom,
        to: dateTo,
        format
      });
      
      // Simular descarga
      alert(`Reporte ${format.toUpperCase()} generado exitosamente`);
    } catch (error) {
      console.error('Error generando reporte:', error);
      alert('Error generando reporte');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickReport = async (type: string) => {
    setLoading(true);
    
    try {
      // Simular generación de reporte rápido
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      let reportData = '';
      switch (type) {
        case 'movements':
          reportData = 'movimientos_hoy.xlsx';
          break;
        case 'inventory':
          reportData = 'inventario_actual.xlsx';
          break;
        case 'sales':
          reportData = 'ventas_del_mes.xlsx';
          break;
      }
      
      console.log(`Generando reporte rápido: ${reportData}`);
      alert(`Reporte ${reportData} generado exitosamente`);
    } catch (error) {
      console.error('Error generando reporte rápido:', error);
      alert('Error generando reporte rápido');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Reportes</h1>
          <p className="text-gray-600">Genera reportes de movimientos y auditoría</p>
        </div>
      </div>

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Formulario de Reporte */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <FileText className="mr-2 h-5 w-5" />
                Generar Reporte
              </CardTitle>
              <CardDescription>
                Selecciona el rango de fechas y el formato para exportar
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <Label>Tipo de Reporte</Label>
                <Select value={reportType} onValueChange={setReportType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="movements">Movimientos de Inventario</SelectItem>
                    <SelectItem value="sales">Ventas</SelectItem>
                    <SelectItem value="inventory">Estado de Inventario</SelectItem>
                    <SelectItem value="audit">Auditoría Completa</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Fecha Desde *</Label>
                  <DatePicker
                    date={dateFrom}
                    onDateChange={setDateFrom}
                    placeholder="Fecha inicio"
                  />
                </div>
                
                <div>
                  <Label>Fecha Hasta *</Label>
                  <DatePicker
                    date={dateTo}
                    onDateChange={setDateTo}
                    placeholder="Fecha fin"
                  />
                </div>
              </div>

              <div>
                <Label>Formato de Exportación</Label>
                <Select value={format} onValueChange={setFormat}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="xlsx">Excel (.xlsx)</SelectItem>
                    <SelectItem value="csv">CSV (.csv)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button 
                onClick={handleGenerateReport}
                disabled={!dateFrom || !dateTo || loading}
                className="w-full"
              >
                {loading ? (
                  'Generando Reporte...'
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    Generar y Descargar
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Información de Columnas */}
          <Card>
            <CardHeader>
              <CardTitle>Columnas del Reporte</CardTitle>
              <CardDescription>Información incluida en el reporte de movimientos</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="text-sm">
                  <strong>Timestamp:</strong> Fecha y hora del evento
                </div>
                <div className="text-sm">
                  <strong>Unit ID:</strong> Identificador único de la unidad
                </div>
                <div className="text-sm">
                  <strong>Event Type:</strong> Tipo de evento (CREATED, TRANSFER, SALE, etc.)
                </div>
                <div className="text-sm">
                  <strong>From → To:</strong> Ubicación origen y destino
                </div>
                <div className="text-sm">
                  <strong>Usuario:</strong> Usuario que realizó la acción
                </div>
                <div className="text-sm">
                  <strong>Lote:</strong> Código del lote de envío
                </div>
                <div className="text-sm">
                  <strong>Sucursal:</strong> Sucursal involucrada (si aplica)
                </div>
                <div className="text-sm">
                  <strong>Notas:</strong> Observaciones adicionales
                </div>
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium text-blue-900 mb-2">Zona Horaria</h4>
                <p className="text-sm text-blue-700">
                  Todas las fechas se exportan en zona horaria de México (GMT-6)
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Reportes Rápidos */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Reportes Rápidos</CardTitle>
            <CardDescription>Reportes predefinidos para acceso rápido</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Button 
                variant="outline" 
                className="h-20 flex-col"
                onClick={() => handleQuickReport('movements')}
                disabled={loading}
              >
                <Calendar className="h-6 w-6 mb-2" />
                <span>Movimientos Hoy</span>
              </Button>
              
              <Button 
                variant="outline" 
                className="h-20 flex-col"
                onClick={() => handleQuickReport('inventory')}
                disabled={loading}
              >
                <FileText className="h-6 w-6 mb-2" />
                <span>Inventario Actual</span>
              </Button>
              
              <Button 
                variant="outline" 
                className="h-20 flex-col"
                onClick={() => handleQuickReport('sales')}
                disabled={loading}
              >
                <Download className="h-6 w-6 mb-2" />
                <span>Ventas del Mes</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
