
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useAuth } from '@/lib/auth';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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

/**
 * Título del error según el status que devolvió el backend.
 *
 * El backend responde con errores tipados (400 tipo de archivo, 413 tamaño,
 * 422 contenido) y un mensaje que ya explica qué hacer. Aquí solo se
 * distingue el título para que el usuario sepa de un vistazo si el problema
 * es su archivo o el servidor.
 */
function getErrorTitle(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 413) return 'El archivo es demasiado grande';
    if (err.status === 400 || err.status === 422) return 'El archivo no es válido';
    if (err.status === 500) return 'Error interno del servidor';
  }
  return fallback;
}

export default function ImportsPage() {
  const { data: session } = useSession();
  const { viewImports } = useAuth();
  const router = useRouter();
  const token = (session as { accessToken?: string } | null)?.accessToken;

  useEffect(() => {
    if (session && !viewImports) {
      router.replace('/');
    }
  }, [session, viewImports, router]);

  const [file, setFile] = useState<File | null>(null);
  const [batchPeriod, setBatchPeriod] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorTitle, setErrorTitle] = useState('No se pudo procesar el archivo');
  const [overrides, setOverrides] = useState<Record<string, ColumnSelection>>({});
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [importErrors, setImportErrors] = useState<ImportError[] | null>(null);
  const [loadingErrors, setLoadingErrors] = useState(false);

  const resetResult = () => {
    setPreview(null);
    setError(null);
    setErrorTitle('No se pudo procesar el archivo');
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
      const title = getErrorTitle(err, 'No se pudo generar la vista previa');
      setError(message);
      setErrorTitle(title);
      setPreview(null);
      toast.error(title, { description: message });
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
          // Product type capture is disabled for now (not requested/used
          // downstream); the backend field and DB column stay in place in
          // case it's needed again.
          product_type: null,
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
      const title = getErrorTitle(err, 'No se pudo importar el archivo');
      setError(message);
      setErrorTitle(title);
      toast.error(title, { description: message });
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
    resetResult();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="mx-auto flex max-w-7xl items-start justify-between px-4 py-6 sm:px-6 lg:px-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Importar Inventario</h1>
            <p className="text-gray-600">
              Sube el archivo del proveedor para validarlo antes de importar
            </p>
          </div>
          <Link href="/imports/history">
            <Button variant="outline">Ver historial</Button>
          </Link>
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
                  <AlertTitle>{errorTitle}</AlertTitle>
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
                <li>Las columnas se detectan automáticamente (chasis, motor, color, modelo, marca).</li>
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
