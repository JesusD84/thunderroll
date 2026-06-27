'use client';

import { useCallback, useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import { Repeat, Plus, Pencil, Trash2 } from 'lucide-react';
import {
  listModelEquivalences,
  listUnmappedModels,
  createModelEquivalence,
  updateModelEquivalence,
  deleteModelEquivalence,
  type ModelEquivalence,
} from '@/lib/imports';
import { ApiError } from '@/lib/api';

interface DialogState {
  open: boolean;
  mode: 'create' | 'edit';
  id: number | null;
  manufacturer_model: string;
  internal_model: string;
  notes: string;
}

const EMPTY_DIALOG: DialogState = {
  open: false,
  mode: 'create',
  id: null,
  manufacturer_model: '',
  internal_model: '',
  notes: '',
};

export default function ModelEquivalencesPage() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const role = ((session?.user as { role?: string } | undefined)?.role ?? '').toLowerCase();
  const isAdmin = role === 'admin';
  const canManage = isAdmin || role === 'manager';

  const [equivalences, setEquivalences] = useState<ModelEquivalence[] | null>(null);
  const [unmapped, setUnmapped] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const [dialog, setDialog] = useState<DialogState>(EMPTY_DIALOG);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [eqs, unm] = await Promise.all([
        listModelEquivalences(token),
        listUnmappedModels(token),
      ]);
      setEquivalences(eqs);
      setUnmapped(unm);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'No se pudieron cargar las equivalencias.';
      setError(message);
      setEquivalences([]);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = (manufacturerModel = '') => {
    setFormError(null);
    setDialog({ ...EMPTY_DIALOG, open: true, mode: 'create', manufacturer_model: manufacturerModel });
  };

  const openEdit = (record: ModelEquivalence) => {
    setFormError(null);
    setDialog({
      open: true,
      mode: 'edit',
      id: record.id,
      manufacturer_model: record.manufacturer_model,
      internal_model: record.internal_model,
      notes: record.notes ?? '',
    });
  };

  const closeDialog = () => setDialog((d) => ({ ...d, open: false }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const manufacturer = dialog.manufacturer_model.trim();
    const internal = dialog.internal_model.trim();
    if (!manufacturer || !internal) {
      setFormError('El modelo del fabricante y el modelo interno son obligatorios.');
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const payload = {
        manufacturer_model: manufacturer,
        internal_model: internal,
        notes: dialog.notes.trim() || null,
      };
      if (dialog.mode === 'create') {
        await createModelEquivalence(payload, token);
        toast.success('Equivalencia creada');
      } else if (dialog.id != null) {
        await updateModelEquivalence(dialog.id, payload, token);
        toast.success('Equivalencia actualizada');
      }
      closeDialog();
      await load();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'No se pudo guardar la equivalencia.';
      setFormError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await deleteModelEquivalence(id, token);
      toast.success('Equivalencia eliminada');
      await load();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'No se pudo eliminar la equivalencia.';
      toast.error('Error al eliminar', { description: message });
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="mx-auto flex max-w-7xl items-start justify-between px-4 py-6 sm:px-6 lg:px-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Equivalencias de modelos</h1>
            <p className="text-gray-600">
              Traduce los modelos del fabricante a los modelos internos
            </p>
          </div>
          {canManage && (
            <Button onClick={() => openCreate()}>
              <Plus className="mr-2 h-4 w-4" />
              Nueva equivalencia
            </Button>
          )}
        </div>
      </div>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {error && <ErrorState message={error} onRetry={load} />}

        {unmapped.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Modelos sin equivalencia ({unmapped.length})</CardTitle>
              <CardDescription>
                Modelos presentes en el inventario que aún no tienen equivalencia
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {unmapped.map((model) => (
                  <div
                    key={model}
                    className="flex items-center gap-2 rounded-md border bg-white px-3 py-1.5"
                  >
                    <span className="text-sm font-medium">{model}</span>
                    {canManage && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-2"
                        aria-label={`Crear equivalencia para ${model}`}
                        onClick={() => openCreate(model)}
                      >
                        <Plus className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Equivalencias</CardTitle>
            <CardDescription>Modelo del fabricante → modelo interno</CardDescription>
          </CardHeader>
          <CardContent>
            {equivalences === null ? (
              <LoadingState rows={3} label="Cargando equivalencias..." />
            ) : equivalences.length === 0 ? (
              <EmptyState
                icon={Repeat}
                title="No hay equivalencias todavía."
                action={
                  canManage ? (
                    <Button variant="link" onClick={() => openCreate()}>
                      Crear la primera
                    </Button>
                  ) : undefined
                }
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Modelo del fabricante</TableHead>
                    <TableHead>Modelo interno</TableHead>
                    <TableHead>Notas</TableHead>
                    {canManage && <TableHead className="text-right">Acciones</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {equivalences.map((record) => (
                    <TableRow key={record.id}>
                      <TableCell className="font-medium">{record.manufacturer_model}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{record.internal_model}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">{record.notes || '-'}</TableCell>
                      {canManage && (
                        <TableCell>
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              aria-label={`Editar ${record.manufacturer_model}`}
                              onClick={() => openEdit(record)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            {isAdmin && (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    aria-label={`Eliminar ${record.manufacturer_model}`}
                                    disabled={deletingId === record.id}
                                  >
                                    <Trash2 className="h-4 w-4 text-red-600" />
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Eliminar equivalencia</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Se eliminará la equivalencia &quot;{record.manufacturer_model}&quot; →
                                      &quot;{record.internal_model}&quot;. Esta acción no se puede deshacer.
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
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>

      <Dialog open={dialog.open} onOpenChange={(open) => (open ? null : closeDialog())}>
        <DialogContent>
          <form onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>
                {dialog.mode === 'create' ? 'Nueva equivalencia' : 'Editar equivalencia'}
              </DialogTitle>
              <DialogDescription>
                Asocia un modelo del fabricante con el modelo interno del cliente.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="manufacturer_model">Modelo del fabricante</Label>
                <Input
                  id="manufacturer_model"
                  value={dialog.manufacturer_model}
                  onChange={(e) =>
                    setDialog((d) => ({ ...d, manufacturer_model: e.target.value }))
                  }
                  placeholder="Ej. X3"
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="internal_model">Modelo interno</Label>
                <Input
                  id="internal_model"
                  value={dialog.internal_model}
                  onChange={(e) => setDialog((d) => ({ ...d, internal_model: e.target.value }))}
                  placeholder="Ej. Thunder X3"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Notas (opcional)</Label>
                <Input
                  id="notes"
                  value={dialog.notes}
                  onChange={(e) => setDialog((d) => ({ ...d, notes: e.target.value }))}
                />
              </div>

              {formError && <ErrorState message={formError} />}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={closeDialog}>
                Cancelar
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? 'Guardando...' : 'Guardar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
