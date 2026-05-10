'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DatePicker } from '@/components/ui/date-picker';
import { Badge } from '@/components/ui/badge';
import { Download, FileText, Package, Truck, DollarSign, Loader2 } from 'lucide-react';
import { useSession } from 'next-auth/react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type ReportTab = 'inventory' | 'transfers' | 'sales';

export default function ReportsPage() {
  const { data: session } = useSession();
  const [activeTab, setActiveTab] = useState<ReportTab>('inventory');
  const [dateFrom, setDateFrom] = useState<Date | undefined>(undefined);
  const [dateTo, setDateTo] = useState<Date | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const token = (session as any)?.accessToken;

  const downloadFile = async (url: string, filename: string) => {
    const res = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const fetchPreview = async (endpoint: string) => {
    const res = await fetch(`${API_URL}${endpoint}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
  };

  const handleGenerateReport = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const from = dateFrom?.toISOString().split('T')[0];
      const to = dateTo?.toISOString().split('T')[0];
      let url = '', filename = '';
      switch (activeTab) {
        case 'inventory':
          url = `${API_URL}/api/v1/reports/export/inventory`;
          filename = 'inventario.xlsx'; break;
        case 'transfers':
          url = `${API_URL}/api/v1/reports/export/transfers?date_from=${from}&date_to=${to}`;
          filename = `transferencias_${from}_${to}.xlsx`; break;
        case 'sales':
          url = `${API_URL}/api/v1/reports/export/sales?date_from=${from}&date_to=${to}`;
          filename = `ventas_${from}_${to}.xlsx`; break;
      }
      await downloadFile(url, filename);
    } catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  };

  const handlePreview = async () => {
    if (!token) return;
    setLoading(true); setError(null);
    try {
      const from = dateFrom?.toISOString().split('T')[0];
      const to = dateTo?.toISOString().split('T')[0];
      let endpoint = '';
      switch (activeTab) {
        case 'inventory': endpoint = '/api/v1/reports/inventory'; break;
        case 'transfers': endpoint = `/api/v1/reports/transfers?date_from=${from}&date_to=${to}&limit=20`; break;
        case 'sales': endpoint = `/api/v1/reports/sales?date_from=${from}&date_to=${to}`; break;
      }
      setPreviewData(await fetchPreview(endpoint));
    } catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  };

  const handleQuickReport = async (type: string) => {
    if (!token) return;
    setLoading(true); setError(null);
    try {
      const today = new Date().toISOString().split('T')[0];
      const firstOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0];
      switch (type) {
        case 'transfers':
          await downloadFile(`${API_URL}/api/v1/reports/export/transfers?date_from=${today}&date_to=${today}`, `transferencias_hoy_${today}.xlsx`); break;
        case 'inventory':
          await downloadFile(`${API_URL}/api/v1/reports/export/inventory`, `inventario_actual_${today}.xlsx`); break;
        case 'sales':
          await downloadFile(`${API_URL}/api/v1/reports/export/sales?date_from=${firstOfMonth}&date_to=${today}`, `ventas_mes_${today}.xlsx`); break;
      }
    } catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  };
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Reportes</h1>
          <p className="text-gray-600">Genera y descarga reportes de inventario, transferencias y ventas</p>
        </div>
      </div>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex gap-2 mb-6">
          {(['inventory', 'transfers', 'sales'] as const).map((key) => (
            <Button key={key} variant={activeTab === key ? 'default' : 'outline'} onClick={() => { setActiveTab(key); setPreviewData(null); setError(null); }}>
              {key === 'inventory' ? <Package className="mr-2 h-4 w-4" /> : key === 'transfers' ? <Truck className="mr-2 h-4 w-4" /> : <DollarSign className="mr-2 h-4 w-4" />}
              {key === 'inventory' ? 'Inventario' : key === 'transfers' ? 'Transferencias' : 'Ventas'}
            </Button>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <FileText className="mr-2 h-5 w-5" />
                {activeTab === 'inventory' ? 'Reporte de Inventario' : activeTab === 'transfers' ? 'Reporte de Transferencias' : 'Reporte de Ventas'}
              </CardTitle>
              <CardDescription>
                {activeTab === 'inventory' ? 'Descarga el estado actual del inventario.' : 'Selecciona el rango de fechas para exportar.'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {activeTab !== 'inventory' && (
                <div className="grid grid-cols-2 gap-4">
                  <div><Label>Fecha Desde</Label><DatePicker date={dateFrom} onDateChange={setDateFrom} placeholder="Fecha inicio" /></div>
                  <div><Label>Fecha Hasta</Label><DatePicker date={dateTo} onDateChange={setDateTo} placeholder="Fecha fin" /></div>
                </div>
              )}
              {error && (<div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">{error}</div>)}
              <div className="flex gap-2">
                <Button onClick={handlePreview} disabled={loading} variant="outline" className="flex-1">
                  {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Vista Previa
                </Button>
                <Button onClick={handleGenerateReport} disabled={loading} className="flex-1">
                  {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />} Descargar Excel
                </Button>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Vista Previa</CardTitle>
              <CardDescription>
                {previewData ? activeTab === 'inventory' ? `${previewData.total_units} unidades encontradas` : activeTab === 'transfers' ? `${previewData.total_transfers} transferencias encontradas` : `${previewData.total_sales} ventas encontradas` : 'Haz clic en "Vista Previa" para ver los datos.'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {previewData ? (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {activeTab === 'inventory' && previewData.units?.slice(0, 10).map((u: any) => (
                    <div key={u.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div><p className="font-medium text-sm">{u.brand} {u.model}</p><p className="text-xs text-gray-500">{u.engine_number || 'Sin motor'} | {u.color}</p></div>
                      <Badge variant="outline">{u.status}</Badge>
                    </div>
                  ))}
                  {activeTab === 'transfers' && previewData.transfers?.slice(0, 10).map((t: any) => (
                    <div key={t.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div><p className="font-medium text-sm">Transfer #{t.id}</p><p className="text-xs text-gray-500">Unit: {t.unit_id} | {t.status}</p></div>
                      <Badge variant="outline">{t.status}</Badge>
                    </div>
                  ))}
                  {activeTab === 'sales' && previewData.sales?.slice(0, 10).map((s: any) => (
                    <div key={s.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div><p className="font-medium text-sm">{s.brand} {s.model}</p><p className="text-xs text-gray-500">{s.engine_number || 'Sin motor'} | Vendido: {s.sold_date?.split('T')[0]}</p></div>
                      <Badge variant="outline">SOLD</Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400"><FileText className="mx-auto h-8 w-8 mb-2" /><p className="text-sm">Sin datos para mostrar</p></div>
              )}
            </CardContent>
          </Card>
        </div>
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Reportes Rápidos</CardTitle>
            <CardDescription>Descarga reportes predefinidos con un solo clic</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Button variant="outline" className="h-20 flex-col" onClick={() => handleQuickReport('transfers')} disabled={loading}>
                <Truck className="h-6 w-6 mb-2" /><span>Transferencias Hoy</span>
              </Button>
              <Button variant="outline" className="h-20 flex-col" onClick={() => handleQuickReport('inventory')} disabled={loading}>
                <Package className="h-6 w-6 mb-2" /><span>Inventario Actual</span>
              </Button>
              <Button variant="outline" className="h-20 flex-col" onClick={() => handleQuickReport('sales')} disabled={loading}>
                <DollarSign className="h-6 w-6 mb-2" /><span>Ventas del Mes</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
