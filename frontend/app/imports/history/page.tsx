'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
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
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { ArrowLeft, AlertTriangle, Trash2 } from 'lucide-react';
import { listImports, deleteImport, type ImportRecord } from '@/lib/imports';
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

export default function ImportsHistoryPage() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const role = ((session?.user as { role?: string } | undefined)?.role ?? '').toLowerCase();
  const isAdmin = role === 'admin';

  const [imports, setImports] = useState<ImportRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listImports(token);
      setImports(data);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'No se pudo cargar el historial de importaciones.';
      setError(message);
      setImports([]);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await deleteImport(id, token);
      setImports((prev) => (prev ? prev.filter((i) => i.id !== id) : prev));
      toast.success('Importación eliminada');
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'No se pudo eliminar la importación.';
      toast.error('Error al eliminar', { description: message });
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Link
            href="/imports"
            className="mb-2 inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Volver a importar
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Historial de importaciones</h1>
          <p className="text-gray-600">Revisa las importaciones realizadas y sus resultados</p>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Card>
          <CardHeader>
            <CardTitle>Importaciones</CardTitle>
            <CardDescription>Las más recientes primero</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {imports === null ? (
              <div className="space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : imports.length === 0 ? (
              <div className="py-12 text-center text-gray-500">
                <p>No hay importaciones todavía.</p>
                <Link href="/imports" className="mt-2 inline-block text-blue-600 hover:underline">
                  Importar un archivo
                </Link>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Archivo</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Importadas</TableHead>
                    <TableHead className="text-right">Con errores</TableHead>
                    <TableHead>Lote</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {imports.map((record) => {
                    const status = STATUS[record.status] ?? {
                      label: record.status,
                      className: 'bg-gray-100 text-gray-800',
                    };
                    return (
                      <TableRow key={record.id}>
                        <TableCell className="font-medium">{record.original_filename}</TableCell>
                        <TableCell>
                          <Badge className={status.className}>{status.label}</Badge>
                        </TableCell>
                        <TableCell className="text-sm">{formatDate(record.import_date)}</TableCell>
                        <TableCell className="text-right">{record.total_records}</TableCell>
                        <TableCell className="text-right text-green-700">
                          {record.successful_imports}
                        </TableCell>
                        <TableCell className="text-right text-red-700">
                          {record.failed_imports}
                        </TableCell>
                        <TableCell className="text-sm">{record.batch_period || '-'}</TableCell>
                        <TableCell>
                          <div className="flex items-center justify-end gap-2">
                            <Link href={`/imports/${record.id}`}>
                              <Button variant="outline" size="sm">
                                Detalle
                              </Button>
                            </Link>
                            {isAdmin && (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    aria-label={`Eliminar importación ${record.original_filename}`}
                                    disabled={deletingId === record.id}
                                  >
                                    <Trash2 className="h-4 w-4 text-red-600" />
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Eliminar importación</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Se eliminará el registro de &quot;{record.original_filename}&quot; y
                                      sus errores asociados. Esta acción no se puede deshacer.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancelar</AlertDialogCancel>
                                    <AlertDialogAction onClick={() => handleDelete(record.id)}>
                                      Eliminar
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
