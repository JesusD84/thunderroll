import { http, HttpResponse } from 'msw';

const API = 'http://localhost:8000';

export const handlers = [
  http.post(`${API}/api/v1/auth/login`, () => HttpResponse.json({ access_token: 'mock-jwt' })),
  http.get(`${API}/api/v1/user/me`, () => HttpResponse.json({ id: 1, email: 'admin@t.com', first_name: 'Admin', last_name: 'User', role: 'admin' })),
  http.get(`${API}/api/v1/reports/dashboard`, () => HttpResponse.json({ total_units: 42, available_units: 30, sold_units: 8, in_transit_units: 4, inventory_by_location: [], sales_by_month: [], recent_transfers: [], recent_imports: [] })),
  http.get(`${API}/api/v1/units/`, () => HttpResponse.json([{ id: 1, brand: 'Honda', model: 'PCX', engine_number: 'ENG001', chassis_number: 'CHS001', color: 'Rojo', status: 'AVAILABLE', location_name: 'Bodega Central' }, { id: 2, brand: 'Yamaha', model: 'NMAX', engine_number: 'ENG002', chassis_number: 'CHS002', color: 'Azul', status: 'SOLD', location_name: 'Sucursal Norte' }])),
  http.post(`${API}/api/v1/units/`, () => HttpResponse.json({ id: 3, brand: 'New', model: 'M', engine_number: 'ENG003', status: 'AVAILABLE' }, { status: 201 })),
  http.get(`${API}/api/v1/units/:id`, ({ params }) => HttpResponse.json({ id: Number(params.id), brand: 'Honda', model: 'PCX', engine_number: 'ENG001', chassis_number: 'CHS001', color: 'Rojo', status: 'AVAILABLE', location_name: 'Bodega Central' })),
  http.get(`${API}/api/v1/locations/`, () => HttpResponse.json([{ id: 1, name: 'Bodega Central' }, { id: 2, name: 'Sucursal Norte' }])),
  http.post(`${API}/api/v1/locations/`, () => HttpResponse.json({ id: 3, name: 'New Loc' }, { status: 201 })),
  http.delete(`${API}/api/v1/locations/:id`, () => HttpResponse.json({ ok: true })),
  http.get(`${API}/api/v1/transfers/`, () => HttpResponse.json([{ id: 1, unit_id: 1, from_location_id: 1, to_location_id: 2, status: 'IN_TRANSIT', created_at: '2025-05-20T00:00:00Z' }])),
  http.post(`${API}/api/v1/transfers/`, () => HttpResponse.json({ id: 2, unit_id: 1, status: 'IN_TRANSIT' }, { status: 201 })),
  http.get(`${API}/api/v1/user/`, () => HttpResponse.json([{ id: 1, email: 'a@t.com', first_name: 'A', last_name: 'U', role: 'admin', is_active: true }])),
];