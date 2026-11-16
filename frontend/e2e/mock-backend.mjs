/**
 * Mock backend for the e2e suite.
 *
 * Since the browser no longer talks to the API directly (every call goes
 * through the Next.js proxy), the API has to live somewhere for the tests to
 * have something to talk to. This server plays that role: it answers the
 * endpoints the specs use and it REQUIRES the `Authorization` header, so a
 * proxy that forgets to forward the credential fails the test loudly.
 *
 * It also records what it received, so a test can assert that the credential
 * arrived at the backend without the browser ever seeing it.
 */

import { createServer } from 'node:http';

const PORT = Number(process.env.PORT || 8017);

const units = [
  {
    id: 1,
    brand: 'Honda',
    model: 'PCX',
    engine_number: 'ENG001',
    chassis_number: 'CHS001',
    color: 'Rojo',
    status: 'AVAILABLE',
    current_location: { id: 1, name: 'Bodega Central' },
    current_location_id: 1,
    sold_date: null,
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 2,
    brand: 'Yamaha',
    model: 'NMAX',
    engine_number: 'ENG002',
    chassis_number: 'CHS002',
    color: 'Azul',
    status: 'SOLD',
    current_location: { id: 2, name: 'Sucursal Norte' },
    current_location_id: 2,
    sold_date: '2025-02-01T00:00:00Z',
    created_at: '2025-01-15T00:00:00Z',
  },
];

const locations = [
  { id: 1, name: 'Bodega Central', address: null, created_at: '2025-01-01T00:00:00Z' },
  { id: 2, name: 'Sucursal Norte', address: null, created_at: '2025-01-01T00:00:00Z' },
];

const users = [
  {
    id: 1,
    email: 'admin@thunderoll.com',
    username: 'admin',
    first_name: 'Admin',
    last_name: 'User',
    role: 'admin',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: null,
  },
];

const transfers = [
  {
    id: 1,
    unit_id: 1,
    dispatched_by_id: 1,
    dispatched_by_name: 'Admin User',
    received_by_id: null,
    origin_location_id: 1,
    destination_location_id: 2,
    status: 'IN_TRANSIT',
    dispatched_at: '2025-05-01T00:00:00Z',
    received_at: null,
  },
];

// The shape the API really returns (app/services/report.py): the counts are
// nested under "units"/"locations"/"transfers". An older flat shape
// (total_units, available_units, ...) used to be mocked here, and since the
// dashboard reads dashboardData.units.total, the page rendered zeros while
// the test still passed. Keep this in sync with the backend.
const dashboard = {
  units: { total: 42, available: 30, sold: 8, in_transit: 4 },
  locations: { total: 3 },
  transfers: { active: 2 },
  inventory_by_location: [{ location: 'Bodega Central', count: 25 }],
  inventory_by_brand: [{ brand: 'Honda', count: 25 }],
  sales_by_month: [{ month: '2025-05', count: 3 }],
  recent_transfers: [],
  recent_imports: [],
};

/** Everything the mock received, so a test can assert what the proxy sent. */
const received = [];

/**
 * The preview answers with problems when the uploaded file says so.
 *
 * It is decided by the name of the file and not by a global switch: the
 * tests run in parallel and a shared flag would make one test change what
 * another one sees.
 */
function wantsInvalidRows(filename) {
  return filename.toLowerCase().includes('invalid');
}

function json(res, status, body, headers = {}) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    ...headers,
  });
  res.end(payload);
}

function readBody(req) {
  return new Promise((resolve) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks)));
  });
}

/**
 * The name of the uploaded file, taken from the multipart body.
 *
 * The samples have Chinese characters in their names, and the browser sends
 * the name in UTF-8: the bytes are pulled out of the body as they are and
 * only those are decoded, so the binary content of the file does not matter.
 */
function uploadedFilename(body) {
  const marker = Buffer.from('filename="', 'latin1');
  const start = body.indexOf(marker);
  if (start === -1) return 'archivo';

  const from = start + marker.length;
  const end = body.indexOf(Buffer.from('"', 'latin1'), from);
  if (end === -1) return 'archivo';

  return body.subarray(from, end).toString('utf8');
}

function previewFor(filename) {
  const base = {
    filename,
    sheets: [
      {
        sheet: 'Hoja1',
        has_header: true,
        columns: ['Frame No.', 'Motor No.', 'Color', 'Model'],
        column_mapping: {
          'Frame No.': 'frame',
          'Motor No.': 'motor',
          Color: 'color',
          Model: 'model',
        },
        mapped_fields: {
          frame: 'Frame No.',
          motor: 'Motor No.',
          color: 'Color',
          model: 'Model',
        },
        rows: 2,
      },
    ],
    detected_fields: ['frame', 'motor', 'color', 'model'],
    preview_data: [
      {
        sheet: 'Hoja1',
        frame: 'LXYTCKPA9R0123456',
        motor: 'EM0987654321',
        color: 'rojo',
        model: 'X3',
      },
    ],
    invalid_rows: [],
    invalid_rows_count: 0,
    issues: [],
    validation: { is_valid: true, message: 'Archivo válido' },
  };

  if (!wantsInvalidRows(filename)) return base;

  return {
    ...base,
    invalid_rows: [{ sheet: 'Hoja1', row: 3, reasons: ['Falta chasis'], data: {} }],
    invalid_rows_count: 1,
    issues: [
      {
        level: 'warning',
        message: 'Algunas filas sin identificador',
        sheet: 'Hoja1',
      },
    ],
    validation: { is_valid: false, message: 'Hay filas con problemas' },
  };
}

function filterUnits(url) {
  const search = url.searchParams.get('search')?.toLowerCase();
  const status = url.searchParams.get('status');
  const locationId = url.searchParams.get('location_id');
  const skip = Number(url.searchParams.get('skip') || 0);
  const limit = Number(url.searchParams.get('limit') || 20);

  const filtered = units.filter((unit) => {
    const matchesSearch =
      !search ||
      unit.engine_number?.toLowerCase().includes(search) ||
      unit.chassis_number?.toLowerCase().includes(search) ||
      unit.brand.toLowerCase().includes(search) ||
      unit.model.toLowerCase().includes(search);
    const matchesStatus = !status || unit.status === status;
    const matchesLocation = !locationId || String(unit.current_location_id) === locationId;
    return matchesSearch && matchesStatus && matchesLocation;
  });

  return filtered.slice(skip, skip + limit);
}

/**
 * The collection routes of the backend have a trailing slash. FastAPI
 * answers a path that misses it with a redirect (`/api/v1/units` ->
 * `/api/v1/units/`), and the proxy follows that redirect on the server.
 */
const COLLECTION_ROUTES = new Set([
  '/api/v1/units/',
  '/api/v1/locations/',
  '/api/v1/transfers/',
  '/api/v1/user/',
]);

const server = createServer(async (req, res) => {
  const url = new URL(req.url || '/', `http://localhost:${PORT}`);
  const path = url.pathname;

  // Control endpoints for the tests: they are not part of the API.
  if (path === '/health') return json(res, 200, { status: 'ok' });
  if (path === '/__mock/requests') return json(res, 200, received);

  received.push({
    method: req.method,
    path,
    // The whole point of the proxy: the credential must arrive here, and it
    // must never be readable by the browser.
    hasAuthorization: Boolean(req.headers.authorization),
    authorizationScheme: (req.headers.authorization || '').split(' ')[0] || null,
  });

  // The API only answers a request that carries the credential.
  if (!req.headers.authorization) {
    return json(res, 401, { detail: 'Could not validate credentials' });
  }

  // FastAPI redirects a collection path that misses its trailing slash.
  if (!path.endsWith('/') && COLLECTION_ROUTES.has(`${path}/`)) {
    res.writeHead(307, { Location: `${path}/${url.search}` });
    return res.end();
  }

  if (path === '/api/v1/reports/dashboard') return json(res, 200, dashboard);
  if (path === '/api/v1/locations/') return json(res, 200, locations);
  if (path === '/api/v1/user/') return json(res, 200, users);
  if (path === '/api/v1/user/me') {
    // The role travels in the token the proxy forwarded, so the mock answers
    // with the role of the session that is calling.
    const token = (req.headers.authorization || '').split(' ')[1] || '';
    const role = token.endsWith('-operator')
      ? 'operator'
      : token.endsWith('-manager')
        ? 'manager'
        : 'admin';
    return json(res, 200, { ...users[0], role });
  }
  if (path === '/api/v1/transfers/') return json(res, 200, transfers);
  if (path === '/api/v1/units/') {
    const filtered = filterUnits(url);
    return json(res, 200, filtered, { 'X-Total-Count': String(filtered.length) });
  }
  if (path.startsWith('/api/v1/units/')) {
    const id = Number(path.split('/')[4]);
    const unit = units.find((u) => u.id === id);
    if (!unit) return json(res, 404, { detail: 'Unit not found' });
    return json(res, 200, unit);
  }
  if (path === '/api/v1/imports/preview') {
    const body = await readBody(req);
    return json(res, 200, previewFor(uploadedFilename(body)));
  }
  if (path === '/api/v1/imports/upload') {
    await readBody(req);
    return json(res, 200, {
      import_id: 7,
      message: 'Importación realizada',
      total_records: 2,
      successful_imports: 2,
      failed_imports: 0,
    });
  }
  if (/^\/api\/v1\/imports\/\d+\/errors$/.test(path)) return json(res, 200, []);
  if (/^\/api\/v1\/imports\/\d+$/.test(path)) {
    return json(res, 200, {
      id: 7,
      filename: 'uploads/mock.xlsx',
      original_filename: 'mock.xlsx',
      user_id: 1,
      status: 'completed',
      total_records: 2,
      successful_imports: 2,
      failed_imports: 0,
      batch_period: null,
      product_type: null,
      notes: null,
      import_date: '2025-05-01T00:00:00Z',
      completed_at: '2025-05-01T00:00:05Z',
    });
  }

  return json(res, 404, { detail: 'Not Found' });
});

server.listen(PORT, () => {
  console.log(`Mock backend listening on http://localhost:${PORT}`);
});
