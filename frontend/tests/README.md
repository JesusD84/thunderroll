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
│   └── ui-components-2.test.tsx  # Input, Label, Select, Calendar, DatePicker, Popover (12 tests)
├── e2e/                    # End-to-end tests (Playwright)
│   └── smoke.spec.ts       # E2E smoke test
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
| 1 | UI Components | 30-40 |
| 2 | Navigation & Auth | 15-20 |
| 3 | Dashboard | 10-12 |
| 4 | Units | 18-22 |
| 5 | Transfers | 10-12 |
| 6 | Imports | 8-10 |
| 7 | Reports | 8-10 |
| 8 | Settings | 10-12 |
| 9 | E2E (Playwright) | 12-15 |
| 10 | Use Cases (Smoke) | 32 |
