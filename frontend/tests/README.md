# Frontend Tests

## Stack

| Capa | Tecnología |
|---|---|
| Test runner | Vitest |
| Component testing | React Testing Library |
| API mocking | MSW (Mock Service Worker) |
| E2E | Playwright |
| Assertions | Vitest + @testing-library/jest-dom |

## Test structure

```
frontend/
├── tests/                  # Unit + Integration tests (Vitest + RTL)
│   ├── setup.ts            # Test setup (jest-dom matchers)
│   ├── smoke.test.tsx       # Infra smoke test
│   ├── ui-components-1.test.tsx  # Badge, Button, Card, Alert, Table (18 tests)
│   ├── ui-components-2.test.tsx  # Input, Label, Select, Calendar, DatePicker, Popover (12 tests)
│   ├── navigation.test.tsx  # Navigation component (7 tests)
│   ├── login.test.tsx       # Login page (6 tests)
│   ├── session-provider.test.tsx  # SessionProvider (1 test)
│   ├── dashboard.test.tsx    # Dashboard page (10 tests)
│   ├── units.test.tsx        # Units list + create form (23 tests)
│   ├── transfers.test.tsx    # Transfers list + create (16 tests)
│   ├── imports.test.tsx      # Imports page (11 tests)
│   ├── reports.test.tsx      # Reports page (15 tests)
│   ├── settings.test.tsx     # Settings page (13 tests)
│   ├── use-cases.test.tsx    # Smoke/acceptance tests (17 tests)
│   └── mocks/               # MSW handlers + server
│       ├── handlers.ts
│       └── server.ts
├── e2e/                    # End-to-end tests (Playwright)
│   ├── auth.spec.ts        # Auth flows + navigation (10 tests)
│   └── responsive.spec.ts  # Responsive design (1 test)
├── vitest.config.ts        # Vitest configuration
├── playwright.config.ts    # Playwright configuration
└── TEST_PLAN.md            # Full test plan (10 phases)
```

## Running tests

```bash
# Unit + Integration tests
npm test

# Watch mode
npm run test:watch

# E2E tests
npm run test:e2e

# E2E with UI
npm run test:e2e:ui
```

## Test plan

See [TEST_PLAN.md](../TEST_PLAN.md) for the full 10-phase strategy (157-191 tests estimated).

| Phase | Scope | Tests |
|---|---|---|
| 0 | Infra | ✅ Done |
| 1 | UI Components | ✅ Done (30) |
| 2 | Navigation & Auth | ✅ Done (14) |
| 3 | Dashboard | ✅ Done (10) |
| 4 | Units | ✅ Done (23) |
| 5 | Transfers | ✅ Done (16) |
| 6 | Imports | ✅ Done (11) |
| 7 | Reports | ✅ Done (15) |
| 8 | Settings | ✅ Done (13) |
| 9 | E2E (Playwright) | ✅ Done (11) |
| 10 | Use Cases (Smoke) | ✅ Done (17) |
| **Total** | | **150** |
