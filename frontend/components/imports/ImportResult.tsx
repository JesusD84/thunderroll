'use client';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import type { ImportError, UploadResult } from '@/lib/imports';

interface ImportResultProps {
  result: UploadResult;
  errors: ImportError[] | null;
  loadingErrors: boolean;
  onLoadErrors: () => void;
  onReset: () => void;
}

function Stat({ label, value, tone }: { label: string; value: number; tone: 'ok' | 'bad' | 'muted' }) {
  const color =
    tone === 'ok' ? 'text-green-600' : tone === 'bad' ? 'text-red-600' : 'text-gray-900';
  return (
    <div className="rounded-lg border bg-white p-4 text-center">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-sm text-gray-600">{label}</p>
    </div>
  );
}

export function ImportResult({
  result,
  errors,
  loadingErrors,
  onLoadErrors,
  onReset,
}: ImportResultProps) {
  const hasFailures = result.failed_imports > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center text-green-700">
          <CheckCircle2 className="mr-2 h-5 w-5" />
          Importación completada
        </CardTitle>
        <CardDescription>
          {result.message} (importación #{result.import_id})
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Stat label="Total de filas" value={result.total_records} tone="muted" />
          <Stat label="Importadas" value={result.successful_imports} tone="ok" />
          <Stat label="Con errores" value={result.failed_imports} tone={hasFailures ? 'bad' : 'muted'} />
        </div>

        {hasFailures && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="flex items-center text-sm text-gray-700">
                <AlertTriangle className="mr-2 h-4 w-4 text-red-600" />
                {result.failed_imports} fila(s) no se pudieron importar.
              </p>
              {errors === null && (
                <Button variant="outline" onClick={onLoadErrors} disabled={loadingErrors}>
                  {loadingErrors ? 'Cargando...' : 'Ver errores'}
                </Button>
              )}
            </div>

            {errors !== null && errors.length > 0 && (
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

            {errors !== null && errors.length === 0 && (
              <p className="text-sm text-gray-500">No hay detalles de errores disponibles.</p>
            )}
          </div>
        )}

        <div className="flex justify-end">
          <Button onClick={onReset}>Importar otro archivo</Button>
        </div>
      </CardContent>
    </Card>
  );
}
