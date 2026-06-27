'use client';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import {
  CANONICAL_FIELDS,
  effectiveSelection,
  type CanonicalField,
  type ColumnSelection,
  type ImportPreviewResponse,
} from '@/lib/imports';

const FIELD_LABELS: Record<CanonicalField, string> = {
  frame: 'Chasis',
  motor: 'Motor',
  color: 'Color',
  model: 'Modelo',
};

const IGNORE = 'ignore';

interface PreviewResultProps {
  preview: ImportPreviewResponse;
  overrides?: Record<string, ColumnSelection>;
  onColumnChange?: (column: string, value: ColumnSelection) => void;
  onApplyMapping?: () => void;
  applying?: boolean;
}

export function PreviewResult({
  preview,
  overrides = {},
  onColumnChange,
  onApplyMapping,
  applying = false,
}: PreviewResultProps) {
  const {
    filename,
    sheets,
    detected_fields,
    preview_data,
    invalid_rows,
    invalid_rows_count,
    issues,
    validation,
  } = preview;

  const editable = Boolean(onColumnChange && onApplyMapping);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Vista previa de {filename}</h2>
        <p className="text-sm text-gray-600">
          {preview_data.length} filas en vista previa · {invalid_rows_count} con problemas ·{' '}
          {sheets.length} {sheets.length === 1 ? 'hoja' : 'hojas'}
        </p>
      </div>

      {/* Resultado de validación (informativo: no bloquea la importación) */}
      <Alert variant={validation.is_valid ? 'default' : 'destructive'}>
        {validation.is_valid ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : (
          <AlertTriangle className="h-4 w-4" />
        )}
        <AlertTitle>{validation.is_valid ? 'Archivo listo' : 'Revisa el archivo'}</AlertTitle>
        <AlertDescription>{validation.message}</AlertDescription>
      </Alert>

      {detected_fields.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-gray-600">Campos detectados:</span>
          {detected_fields.map((field) => (
            <Badge key={field} variant="secondary">
              {FIELD_LABELS[field]}
            </Badge>
          ))}
        </div>
      )}

      {/* Avisos del parser */}
      {issues.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center text-base">
              <Info className="mr-2 h-4 w-4" />
              Avisos ({issues.length})
            </CardTitle>
            <CardDescription>Mensajes del análisis del archivo</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {issues.map((issue, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <Badge variant={issue.level === 'error' ? 'destructive' : 'secondary'}>
                    {issue.level}
                  </Badge>
                  <span className="text-gray-700">
                    {issue.sheet ? `[${issue.sheet}] ` : ''}
                    {issue.message}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Columnas y mapeo propuesto por hoja */}
      {sheets.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Hojas detectadas</CardTitle>
            <CardDescription>
              {editable
                ? 'Ajusta el campo de cada columna y vuelve a previsualizar'
                : 'Columnas y mapeo propuesto para cada hoja'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue={sheets[0].sheet}>
              <TabsList className="flex-wrap">
                {sheets.map((sheet) => (
                  <TabsTrigger key={sheet.sheet} value={sheet.sheet}>
                    {sheet.sheet}
                  </TabsTrigger>
                ))}
              </TabsList>
              {sheets.map((sheet) => (
                <TabsContent key={sheet.sheet} value={sheet.sheet} className="space-y-3">
                  <p className="text-sm text-gray-600">
                    {sheet.rows} {sheet.rows === 1 ? 'fila' : 'filas'} ·{' '}
                    {sheet.has_header ? 'con encabezado' : 'sin encabezado'}
                  </p>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Columna</TableHead>
                        <TableHead>Campo</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sheet.columns.map((column) => {
                        const selection = effectiveSelection(preview, overrides, column);
                        return (
                          <TableRow key={column}>
                            <TableCell className="font-medium">{column}</TableCell>
                            <TableCell>
                              {editable ? (
                                <Select
                                  value={selection}
                                  onValueChange={(value) =>
                                    onColumnChange?.(column, value as ColumnSelection)
                                  }
                                  disabled={applying}
                                >
                                  <SelectTrigger
                                    aria-label={`Campo para ${column}`}
                                    className="w-44"
                                  >
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {CANONICAL_FIELDS.map((f) => (
                                      <SelectItem key={f} value={f}>
                                        {FIELD_LABELS[f]}
                                      </SelectItem>
                                    ))}
                                    <SelectItem value={IGNORE}>Sin mapear</SelectItem>
                                  </SelectContent>
                                </Select>
                              ) : selection === IGNORE ? (
                                <Badge variant="outline">Sin mapear</Badge>
                              ) : (
                                <Badge variant="default">{FIELD_LABELS[selection]}</Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TabsContent>
              ))}
            </Tabs>

            {editable && (
              <div className="mt-4 flex items-center justify-end">
                <Button onClick={onApplyMapping} disabled={applying}>
                  {applying ? 'Re-previsualizando...' : 'Re-previsualizar'}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Muestra de datos canónicos */}
      {preview_data.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Muestra de datos</CardTitle>
            <CardDescription>Primeras filas con identificador válido</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Hoja</TableHead>
                  <TableHead>Chasis</TableHead>
                  <TableHead>Motor</TableHead>
                  <TableHead>Color</TableHead>
                  <TableHead>Modelo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {preview_data.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell>{row.sheet}</TableCell>
                    <TableCell className="font-mono text-sm">{row.frame || '-'}</TableCell>
                    <TableCell className="font-mono text-sm">{row.motor || '-'}</TableCell>
                    <TableCell className="capitalize">{row.color || '-'}</TableCell>
                    <TableCell>{row.model || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Filas con problemas (no bloquean la importación) */}
      {invalid_rows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center text-base">
              <AlertTriangle className="mr-2 h-4 w-4" />
              Filas con problemas ({invalid_rows_count})
            </CardTitle>
            <CardDescription>
              Estas filas se omitirán al importar, pero no impiden importar el resto.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Hoja</TableHead>
                  <TableHead>Fila</TableHead>
                  <TableHead>Motivos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invalid_rows.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell>{row.sheet}</TableCell>
                    <TableCell>{row.row}</TableCell>
                    <TableCell>
                      <ul className="list-inside list-disc space-y-1">
                        {row.reasons.map((reason, i) => (
                          <li key={i} className="text-sm text-gray-700">
                            {reason}
                          </li>
                        ))}
                      </ul>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {invalid_rows_count > invalid_rows.length && (
              <p className="mt-3 text-sm text-gray-500">
                Mostrando {invalid_rows.length} de {invalid_rows_count} filas con problemas.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
