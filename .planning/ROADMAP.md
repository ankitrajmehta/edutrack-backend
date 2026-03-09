# Roadmap: EduTrack Backend

**Created:** 2026-03-09
**Phases:** 4
**Requirements:** 63 v1 requirements, 0 unmapped

---

## Phase Overview

| # | Phase | Goal | Requirements | Plans |
|---|-------|------|--------------|-------|
| 1 | Foundation | Working authenticated API skeleton in Docker | INFRA-01–05, AUTH-01–06, RBAC-01, BLKC-01–04 | 4 plans |
| 2 | Entity Management | All stakeholder entities fully CRUD-able with scoped access | RBAC-02–05, ADMN-01–05, NGO-01–07, DONOR-01–03, SCHL-01–02, STUD-01–03, ACTV-01, FILE-01–03, APIC-01–02 | TBD |
| 3 | Fund Flow | Every money movement triggers a blockchain tx with a recorded hash | NGO-08–11, DONOR-04–06, SCHL-03–04 | TBD |
| 4 | Demo Readiness | Frontend runs against live API with no mock data, Move contract deployable | INFRA-06, PUBL-01–04, BLKC-05, ACTV-02, APIC-03 | TBD |

---

## Phase Details

### Phase 1: Foundation

**Goal:** A running FastAPI + PostgreSQL application in Docker with working JWT authentication, RBAC skeleton, blockchain abstraction layer, and all ORM models — the bedrock every other phase builds on.

**Depends on:** None

**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, RBAC-01, BLKC-01, BLKC-02, BLKC-03, BLKC-04

**Plans:** 4 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffolding, Docker Compose, config, exceptions, all stub routers
- [ ] 01-02-PLAN.md — Async DB setup, all 12 ORM models, Alembic async migrations
- [ ] 01-03-PLAN.md — BlockchainService Protocol, MockSuiService, get_blockchain() DI
- [ ] 01-04-PLAN.md — Pydantic schemas (camelCase), JWT security, auth service, auth endpoints, RBAC guard

### Success Criteria
1. `docker compose up` starts the application and PostgreSQL with no manual intervention; `GET /healthz` returns HTTP 200.
2. `POST /api/auth/register` creates a user and `POST /api/auth/login` returns a valid JWT access token (30 min) and refresh token (7 days).
3. `GET /api/auth/me` returns the authenticated user's role-specific profile; calling it with an expired token returns HTTP 401; calling a role-protected endpoint with the wrong role returns HTTP 403.
4. Any unhandled exception returns `{"detail": "...", "code": "...", "statusCode": ...}` — no raw stack traces leak to the client.
5. `BlockchainService` Protocol is importable, the mock implementation returns a 64-char hex string tx hash within 0.4 seconds, and the mock is injected via `Depends(get_blockchain)` (no direct import in callers).

### Scope Notes
- Alembic **must** be initialized with `--template async`. Sync `env.py` + asyncpg deadlocks at migration time.
- `async_sessionmaker(expire_on_commit=False)` is mandatory — post-commit attribute access causes `MissingGreenlet`.
- All Pydantic response schemas must inherit from a `BaseResponse` with `model_config = ConfigDict(from_attributes=True, populate_by_name=True)` — solves the silent ORM mode failure pitfall.
- JWT `sub` claim must be encoded/decoded as `str(user.id)` / `int(payload["sub"])`.
- CORS must use explicit origins `["http://localhost:3000", "http://localhost:5173"]` — wildcard + credentials is browser-rejected.
- Refresh tokens stored in DB with `used: bool` flag to prevent race-condition reuse.
- `bcrypt` pinned to `>=4.1.2,<5.0.0` — 4.1.0 is yanked, ≥5.0.0 breaks passlib.

---

### Phase 2: Entity Management

**Goal:** Every stakeholder (Admin, NGO, Donor, School, Student) can manage their entities through scoped, role-enforced CRUD endpoints, with activity logging and file storage operational — all responses in camelCase matching mock.js.

**Depends on:** Phase 1

**Requirements:** RBAC-02, RBAC-03, RBAC-04, RBAC-05, ADMN-01, ADMN-02, ADMN-03, ADMN-04, ADMN-05, NGO-01, NGO-02, NGO-03, NGO-04, NGO-05, NGO-06, NGO-07, DONOR-01, DONOR-02, DONOR-03, SCHL-01, SCHL-02, STUD-01, STUD-02, STUD-03, ACTV-01, FILE-01, FILE-02, FILE-03, APIC-01, APIC-02

### Success Criteria
1. Admin can verify an NGO (`PATCH /api/admin/ngos/{id}/status`), which changes its status and writes an `ActivityLog` entry in the same database transaction.
2. NGO can create a program, register a student (generating an `EDU-YYYY-XXXXX` scholarship ID + mock blockchain wallet address), list their students, and review scholarship applications — all scoped to their own records only; cross-NGO access returns HTTP 403.
3. School can register as a partner and view their own profile; Student can browse active programs and submit a scholarship application; Donor can browse verified NGOs and active programs.
4. `POST /api/files/upload` accepts a multipart file and returns `{fileId, url}`; `GET /api/files/{id}` returns the file — all using async I/O (`aiofiles`) with no blocking `open()` calls.
5. Every API response uses camelCase field names exactly matching `mock.js` (e.g., `scholarshipId`, `walletAddress`, `createdAt`) — no snake_case leaks to the frontend.

### Scope Notes
- Invoice submission (SCHL-03–04) and invoice approval (NGO-08–09) are **not** in this phase — they involve blockchain tx and belong in Phase 3.
- NGO-07 (accept application → auto-create student) is in this phase; the blockchain `create_wallet()` call for the auto-created student is via the mock injected from Phase 1.
- `activity_service.log()` must be called **before** `await db.commit()` in every service method — atomicity is non-negotiable.
- Services must return Pydantic model instances, never raw dicts — dict bypass breaks camelCase alias serialization.
- `selectinload()` for one-to-many relationships, `joinedload()` for many-to-one — never default lazy loading.

---

### Phase 3: Fund Flow

**Goal:** Every money movement — donations, fund allocations to student wallets, and invoice settlements — triggers a blockchain transaction, records a tx hash, and is reflected in donor fund-flow detail views.

**Depends on:** Phase 2

**Requirements:** NGO-08, NGO-09, NGO-10, NGO-11, DONOR-04, DONOR-05, DONOR-06, SCHL-03, SCHL-04

### Success Criteria
1. Donor makes a donation to an NGO, program, or named student (`POST /api/donor/donations`) — the response includes a `txHash` (64-char hex), and the donation is queryable in the donor's history.
2. NGO allocates funds to a student or program (`POST /api/ngo/allocations`) — the student's `walletBalance` is updated, a `txHash` is recorded, and the allocation appears in NGO's allocation history.
3. School submits an invoice (`POST /api/school/invoices`) and NGO approves it (`PATCH /api/ngo/invoices/{id}/approve`) — the invoice status transitions to `approved`, a `txHash` is set, and an `ActivityLog` entry is written atomically.
4. `GET /api/donor/donations/{id}` returns the complete fund-flow chain: donation → allocation(s) → invoice settlement, each with its `txHash`.

### Scope Notes
- All blockchain calls go through `Depends(get_blockchain)` — no direct mock imports in service layer.
- Each of the three blockchain operations (`donate`, `allocate_funds`, `settle_invoice`) must call `activity_service.log()` before commit so fund movements appear on the activity feed atomically.
- This phase contains the highest density of concurrent async code: validate session-per-request pattern carefully — never share an `AsyncSession` across concurrent tasks.
- `Invoice.tx_hash` and `Invoice.approved_date` are `Optional[str] = None` (explicit default) per Pydantic v2 behavior.

---

### Phase 4: Demo Readiness

**Goal:** The full EduTrack frontend runs against the live API with zero mock.js fallbacks, the database seeds from an idempotent script matching mock.js exactly, and a syntactically valid Move smart contract is present for the grant demo narrative.

**Depends on:** Phase 3

**Requirements:** INFRA-06, PUBL-01, PUBL-02, PUBL-03, PUBL-04, BLKC-05, ACTV-02, APIC-03

### Success Criteria
1. `docker compose up` followed by `scripts/start.sh` (runs Alembic migrations + seed + uvicorn) starts the full stack; the seed script is idempotent — running it twice produces no duplicates and no errors.
2. The seeded database contains the exact records from `mock.js` (same IDs, same field values, same relationships) — the frontend's hardcoded IDs in routes resolve to real API data.
3. Public endpoints (`GET /api/public/stats`, `/api/public/activity`, `/api/public/ngos`, `/api/public/programs`) return correct data with no authentication header required.
4. The activity feed endpoint returns entries with `{type, color, text, time}` where `time` is a human-readable relative string (e.g., "2 hours ago").
5. `contracts/sources/scholarship.move` is syntactically valid Move — `sui move build` succeeds without errors.

### Scope Notes
- Seed script must use `ON CONFLICT DO NOTHING` (or equivalent upsert) — idempotency is mandatory.
- `.env.example` must document every environment variable the application reads from `config.py`.
- Relative time formatting for activity feed (`"2 hours ago"`) computed server-side — no client-side libraries needed.
- The Move contract is for demo narrative only — it does not need to be called by the Python backend in v1.
- `APIC-03` is the integration checkpoint: the frontend should work end-to-end without any changes to `../edutrack/`.

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/4 | In Progress | 2026-03-09 |
| 2. Entity Management | 0/? | Not Started | — |
| 3. Fund Flow | 0/? | Not Started | — |
| 4. Demo Readiness | 0/? | Not Started | — |

---
*Roadmap created: 2026-03-09*
