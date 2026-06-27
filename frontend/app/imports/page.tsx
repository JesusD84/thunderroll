
'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Upload, AlertTriangle, Info } from 'lucide-react';
import { PreviewResult } from '@/components/imports/PreviewResult';
import { ImportResult } from '@/components/imports/ImportResult';
import {
  previewImport,
  uploadImport,
  getImportErrors,
  buildColumnMapping,
  type ColumnMapping,
  type ColumnSelection,
  type ImportError,
  type ImportPreviewResponse,
  type UploadResult,
} from '@/lib/imports';
import { ApiError } from '@/lib/api';

const PRODUCT_TYPES = [
  { value: 'triciclo', label: 'Triciclo' },
  { value: 'bicicleta_electrica', label: 'Bicicleta eléctrica' },
  { value: 'scooter', label: 'Scooter / Moto eléctrica' },
];

const NONE = 'none';

export default function ImportsPage() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;

  const [file, setFile] = useState<File | null>(null);
  const [batchPeriod, setBatchPeriod] = useState('');
  const [productType, setProductType] = useState<string>(NONE);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [overrides, setOverrides] = useState<Record<string, ColumnSelection>>({});
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [importErrors, setImportErrors] = useState<ImportError[] | null>(null);
  const [loadingErrors, setLoadingErrors] = useState(false);

  const resetResult = () => {
    setPreview(null);
    setError(null);
    setOverrides({});
    setResult(null);
    setImportErrors(null);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null);
    resetResult();
  };

  const runPreview = async (mapping: ColumnMapping | null) => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const result = await previewImport(file, mapping, token);
      setPreview(result);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'No se pudo procesar el archivo. Inténtalo de nuevo.';
      setError(message);
      setPreview(null);
      toast.error('Error al generar la vista previa', { description: message });
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = () => runPreview(null);

  const handleColumnChange = (column: string, value: ColumnSelection) => {
    setOverrides((prev) => ({ ...prev, [column]: value }));
  };

  const handleApplyMapping = () => {
    if (!preview) return;
    runPreview(buildColumnMapping(preview, overrides));
  };

  const handleImport = async () => {
    if (!file || !preview) return;

    setUploading(true);
    setError(null);

    try {
      const res = await uploadImport(
        file,
        {
          batch_period: batchPeriod.trim() || null,
          product_type: productType === NONE ? null : productType,
          columnMapping: buildColumnMapping(preview, overrides),
        },
        token,
      );
      setResult(res);
      setImportErrors(null);
      toast.success('Importación completada', { description: res.message });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'No se pudo importar el archivo. Inténtalo de nuevo.';
      setError(message);
      toast.error('Error al importar', { description: message });
    } finally {
      setUploading(false);
    }
  };

  const handleLoadErrors = async () => {
    if (!result) return;

    setLoadingErrors(true);
    try {
      const errors = await getImportErrors(result.import_id, token);
      setImportErrors(errors);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'No se pudieron cargar los errores.';
      toast.error('Error al cargar los errores', { description: message });
      setImportErrors([]);
    } finally {
      setLoadingErrors(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setBatchPeriod('');
    setProductType(NONE);
    resetResult();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Importar Inventario</h1>
          <p className="text-gray-600">
            Sube el archivo del proveedor para validarlo antes de importar
          </p>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Formulario de subida */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Upload className="mr-2 h-5 w-5" />
                Subir archivo
              </CardTitle>
              <CardDescription>
                Acepta Excel (.xlsx, .xls) y CSV. Los datos del lote son opcionales.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="batch_period">Periodo de lote</Label>
                <Input
                  id="batch_period"
                  value={batchPeriod}
                  onChange={(e) => setBatchPeriod(e.target.value)}
                  placeholder="ej. 2026-ABRIL"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="product_type">Tipo de producto</Label>
                <Select value={productType} onValueChange={setProductType}>
                  <SelectTrigger id="product_type">
                    <SelectValue placeholder="Sin especificar" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>Sin especificar</SelectItem>
                    {PRODUCT_TYPES.map((pt) => (
                      <SelectItem key={pt.value} value={pt.value}>
                        {pt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="file">Archivo</Label>
                <Input
                  id="file"
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileSelect}
                />
                {file && (
                  <p className="text-sm text-gray-600">
                    Archivo seleccionado: {file.name}
                  </p>
                )}
              </div>

              <div className="flex space-x-2">
                <Button
                  onClick={handlePreview}
                  disabled={!file || loading}
                  className="flex-1"
                >
                  {loading ? 'Procesando...' : 'Vista previa'}
                </Button>

                {(file || preview || error) && (
                  <Button onClick={handleReset} variant="outline" disabled={loading}>
                    Limpiar
                  </Button>
                )}
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>No se pudo procesar el archivo</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Cómo funciona */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Info className="mr-2 h-5 w-5" />
                Cómo funciona
              </CardTitle>
              <CardDescription>El archivo se valida sin guardar nada</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm text-gray-600 space-y-2 list-disc list-inside">
                <li>Acepta varias hojas y encabezados en español, inglés o chino.</li>
                <li>Las columnas se detectan automáticamente (chasis, motor, color, modelo).</li>
                <li>Podrás revisar y ajustar el mapeo antes de importar.</li>
                <li>Los números de chasis y motor se conservan tal cual, sin recortes.</li>
                <li>La vista previa es informativa: las filas con problemas se muestran, pero no bloquean.</li>
              </ul>
            </CardContent>
          </Card>
        </div>

        {/* Pantalla de resultado tras importar */}
        {result && (
          <section className="mt-8">
            <ImportResult
              result={result}
              errors={importErrors}
              loadingErrors={loadingErrors}
              onLoadErrors={handleLoadErrors}
              onReset={handleReset}
            />
          </section>
        )}

        {/* Vista previa detallada del archivo con mapeo asistido */}
        {preview && !result && (
          <section className="mt-8 space-y-6">
            <PreviewResult
              preview={preview}
              overrides={overrides}
              onColumnChange={handleColumnChange}
              onApplyMapping={handleApplyMapping}
              applying={loading}
            />
            <div className="flex justify-end">
              <Button onClick={handleImport} disabled={uploading || loading} size="lg">
                {uploading ? 'Importando...' : 'Importar al inventario'}
              </Button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
