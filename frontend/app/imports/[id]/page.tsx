'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ErrorState, LoadingState } from '@/components/ui/states';
import { ArrowLeft } from 'lucide-react';
import {
  getImport,
  getImportErrors,
  type ImportError,
  type ImportRecord,
} from '@/lib/imports';
import { ApiError } from '@/lib/api';

const STATUS: Record<string, { label: string; className: string }> = {
  completed: { label: 'Completado', className: 'bg-green-100 text-green-800' },
  processing: { label: 'Procesando', className: 'bg-yellow-100 text-yellow-800' },
  failed: { label: 'Fallido', className: 'bg-red-100 text-red-800' },
};

function formatDate(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('es-MX');
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm text-gray-500">{label}</dt>
      <dd className="text-sm font-medium text-gray-900">{value}</dd>
    </div>
  );
}

export default function ImportDetailPage() {
  const params = useParams();
  const id = Number(params?.id);
  const { data: session } = useSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;

  const [record, setRecord] = useState<ImportRecord | null>(null);
  const [errors, setErrors] = useState<ImportError[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!Number.isFinite(id)) {
      setError('Identificador de importación inválido.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [detail, detailErrors] = await Promise.all([
        getImport(id, token),
        getImportErrors(id, token),
      ]);
      setRecord(detail);
      setErrors(detailErrors);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'No se pudo cargar la importación.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [id, token]);

  useEffect(() => {
    load();
  }, [load]);

  const status = record
    ? STATUS[record.status] ?? { label: record.status, className: 'bg-gray-100 text-gray-800' }
    : null;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Link
            href="/imports/history"
            className="mb-2 inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Volver al historial
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">
            {record ? record.original_filename : 'Detalle de importación'}
          </h1>
        </div>
      </div>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {error && <ErrorState message={error} onRetry={load} />}

        {loading ? (
          <LoadingState rows={2} className="[&>*]:h-40" label="Cargando importación..." />
        ) : record ? (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-3">
                  Resumen
                  {status && <Badge className={status.className}>{status.label}</Badge>}
                </CardTitle>
                <CardDescription>Importación #{record.id}</CardDescription>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                  <Detail label="Total de filas" value={record.total_records} />
                  <Detail
                    label="Importadas"
                    value={<span className="text-green-700">{record.successful_imports}</span>}
                  />
                  <Detail
                    label="Con errores"
                    value={<span className="text-red-700">{record.failed_imports}</span>}
                  />
                  <Detail label="Periodo de lote" value={record.batch_period || '-'} />
                  <Detail label="Tipo de producto" value={record.product_type || '-'} />
                  <Detail label="Fecha" value={formatDate(record.import_date)} />
                  <Detail label="Completada" value={formatDate(record.completed_at)} />
                </dl>
                {record.notes && (
                  <p className="mt-4 text-sm text-gray-600">
                    <span className="font-medium">Notas:</span> {record.notes}
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Errores ({errors.length})</CardTitle>
                <CardDescription>Filas que no se pudieron importar</CardDescription>
              </CardHeader>
              <CardContent>
                {errors.length === 0 ? (
                  <p className="text-sm text-gray-500">Sin errores registrados.</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Fila</TableHead>
                        <TableHead>Error</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {errors.map((err) => (
                        <TableRow key={err.id}>
                          <TableCell>{err.row_number}</TableCell>
                          <TableCell className="text-sm text-gray-700">{err.error_message}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </>
        ) : null}
      </main>
    </div>
  );
}
