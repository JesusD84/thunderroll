
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Upload, Download, Check, AlertTriangle, FileSpreadsheet } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface ImportPreview {
  brand?: string;
  model?: string;
  color: string;
  engine_number?: string;
  chassis_number?: string;
  row_number: number;
  errors?: string[];
}

export default function ImportsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<ImportPreview[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [isDryRun, setIsDryRun] = useState(true);
  const [importData, setImportData] = useState({
    shipment_batch: '',
    supplier_invoice: ''
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreview([]);
      setErrors([]);
    }
  };

  const handleDownloadTemplate = () => {
    // Crear un CSV template simple
    const csvContent = `brand,model,color,engine_number,chassis_number
Honda,PCX,red,20250823001001,HXYXYZ202501001
Yamaha,NMAX,black,20250823001002,HXYXYZ202501002
Honda,Beat,blue,20250823001003,HXYXYZ202501003`;
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'plantilla_inventario.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const handlePreview = async () => {
    if (!file) return;

    setUploading(true);
    
    try {
      // Simular procesamiento de Excel
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const samplePreview: ImportPreview[] = [
        {
          brand: 'Honda',
          model: 'PCX',
          color: 'red',
          engine_number: '20250823035825',
          chassis_number: 'HXY202507501',
          row_number: 2
        },
        {
          brand: 'Yamaha',
          model: 'NMAX',
          color: 'black',
          engine_number: '20250823035826',
          chassis_number: 'HXY202507502',
          row_number: 3
        },
        {
          color: 'green',
          chassis_number: 'HXY202507503',
          row_number: 4,
          errors: ['Número de motor faltante']
        }
      ];

      setPreview(samplePreview);
      setErrors(['Fila 4: Número de motor faltante']);
    } catch (error) {
      setErrors(['Error procesando el archivo Excel']);
    } finally {
      setUploading(false);
    }
  };

  const handleImport = async () => {
    if (!file || preview.length === 0) return;

    setUploading(true);
    
    try {
      // Simular importación real
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Aquí iría la llamada al API del backend
      console.log('Importando:', { file, importData, isDryRun: false });
      
      alert('Importación completada exitosamente');
      
      // Limpiar formulario
      setFile(null);
      setPreview([]);
      setErrors([]);
      setImportData({ shipment_batch: '', supplier_invoice: '' });
    } catch (error) {
      setErrors(['Error durante la importación']);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Importar Inventario</h1>
          <p className="text-gray-600">Importa unidades desde archivos Excel del proveedor</p>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Formulario de Importación */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Upload className="mr-2 h-5 w-5" />
                Subir Archivo Excel
              </CardTitle>
              <CardDescription>
                Selecciona el archivo Excel del proveedor y completa la información del lote
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="shipment_batch">Código de Lote *</Label>
                <Input
                  id="shipment_batch"
                  value={importData.shipment_batch}
                  onChange={(e) => setImportData(prev => ({ ...prev, shipment_batch: e.target.value }))}
                  placeholder="ej. BATCH_202508_001"
                />
              </div>

              <div>
                <Label htmlFor="supplier_invoice">Factura Proveedor *</Label>
                <Input
                  id="supplier_invoice"
                  value={importData.supplier_invoice}
                  onChange={(e) => setImportData(prev => ({ ...prev, supplier_invoice: e.target.value }))}
                  placeholder="ej. INV-2025-001"
                />
              </div>

              <div>
                <Label htmlFor="file">Archivo Excel</Label>
                <Input
                  id="file"
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileSelect}
                />
                {file && (
                  <div className="text-sm text-gray-600 mt-1">
                    Archivo seleccionado: {file.name}
                  </div>
                )}
              </div>

              <div className="flex space-x-2">
                <Button 
                  onClick={handlePreview}
                  disabled={!file || !importData.shipment_batch || !importData.supplier_invoice || uploading}
                  variant="outline"
                  className="flex-1"
                >
                  {uploading ? 'Procesando...' : 'Vista Previa'}
                </Button>
                
                {preview.length > 0 && (
                  <Button 
                    onClick={handleImport}
                    disabled={uploading || errors.length > 0}
                    className="flex-1"
                  >
                    <FileSpreadsheet className="mr-2 h-4 w-4" />
                    Importar ({preview.length} unidades)
                  </Button>
                )}
              </div>

              {errors.length > 0 && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    <div>Errores encontrados:</div>
                    <ul className="list-disc list-inside mt-1">
                      {errors.map((error, index) => (
                        <li key={index} className="text-sm">{error}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Instrucciones */}
          <Card>
            <CardHeader>
              <CardTitle>Instrucciones</CardTitle>
              <CardDescription>Formato esperado del archivo Excel</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-900">Columnas Requeridas</h4>
                  <ul className="text-sm text-gray-600 mt-2 space-y-1">
                    <li>• <strong>chassis_number</strong>: Número de chasis (requerido)</li>
                    <li>• <strong>engine_number</strong>: Número de motor (requerido)</li>
                    <li>• <strong>color</strong>: Color de la unidad (requerido)</li>
                    <li>• <strong>brand</strong>: Marca (opcional)</li>
                    <li>• <strong>model</strong>: Modelo (opcional)</li>
                  </ul>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900">Formato de Datos</h4>
                  <ul className="text-sm text-gray-600 mt-2 space-y-1">
                    <li>• Números de chasis: HXY + YYYYMM + secuencial</li>
                    <li>• Números de motor: 14 dígitos</li>
                    <li>• Colores: red, black, green, pink, grey, blue</li>
                  </ul>
                </div>

                <div>
                  <Button variant="outline" size="sm" onClick={handleDownloadTemplate}>
                    <Download className="mr-2 h-4 w-4" />
                    Descargar Plantilla
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Vista Previa */}
        {preview.length > 0 && (
          <Card className="mt-8">
            <CardHeader>
              <CardTitle>Vista Previa de Importación</CardTitle>
              <CardDescription>
                Revisa los datos antes de importar. Se detectaron {preview.length} unidades.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fila</TableHead>
                    <TableHead>Marca/Modelo</TableHead>
                    <TableHead>Color</TableHead>
                    <TableHead># Motor</TableHead>
                    <TableHead># Chasis</TableHead>
                    <TableHead>Estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell>{item.row_number}</TableCell>
                      <TableCell>
                        {item.brand && item.model ? `${item.brand} ${item.model}` : 'No especificado'}
                      </TableCell>
                      <TableCell className="capitalize">{item.color}</TableCell>
                      <TableCell className="font-mono text-sm">{item.engine_number || '-'}</TableCell>
                      <TableCell className="font-mono text-sm">{item.chassis_number || '-'}</TableCell>
                      <TableCell>
                        {item.errors && item.errors.length > 0 ? (
                          <Badge variant="destructive">
                            <AlertTriangle className="mr-1 h-3 w-3" />
                            Error
                          </Badge>
                        ) : (
                          <Badge variant="default">
                            <Check className="mr-1 h-3 w-3" />
                            OK
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
