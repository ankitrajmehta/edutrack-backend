# Phase 4: Demo Readiness - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

The full OpenScholar frontend runs against the live backend API with zero mock.js fallbacks, the database seeds from an idempotent script matching mock.js exactly, and a syntactically valid Sui Move smart contract is present for the grant demo narrative.

**Delivers:**
- `scripts/seed.py` — idempotent UPSERT seed with full data hierarchy matching mock.js (users, NGOs, programs, students, donors, donations, invoices, schools, allocations, activity log baseline)
- `app/api/public.py` — 4 public endpoints: `/api/public/stats`, `/api/public/activity`, `/api/public/ngos`, `/api/public/programs` (no auth required)
- ACTV-02: activity feed returns `{type, color, text, time}` with ISO timestamp for relative time computation
- Frontend: `src/data/mock.js` rewritten as async API client with auto-login per role
- Frontend: all 15 pages updated to use async API client instead of synchronous mock.js imports
- `contracts/Move.toml` + `contracts/sources/scholarship.move` — buildable with `sui move build`, narrative-only
- `entrypoint.sh` updated to run seed after migrations
- `.env.example` documents all environment variables

**Out of scope for this phase:**
- Real Sui SDK calls — mock stays; contract is narrative only
- Automated tests
- Pagination / filtering
- Rate limiting, Nginx, encryption at rest
- Any new backend business logic (all endpoints from Phases 1–3 must already exist)

</domain>

<decisions>
## Implementation Decisions

### Frontend Integration Strategy
- **Approach:** `src/data/mock.js` is rewritten as an async API client. All 15 pages that currently `import { x } from '../data/mock.js'` continue to use the same import path — but the exports become async functions that fetch from the backend.
- **Demo mode:** No real login flow. The frontend auto-logs in at startup using hardcoded credentials per role (email/password stored in api.js config constants). `api.js` calls `POST /api/auth/login` with the demo credentials and caches the access token per role.
- **Role switching:** The navbar role switcher triggers a re-authentication with the new role's demo credentials. Per-role tokens are cached in memory — switching back to a previous role reuses the cached token without re-logging in.
- **Render pattern:** Page render functions become `async` and `await` the api.js data fetching functions. Route handlers call `await renderPage()`.
- **Loading states:** Claude's discretion — show a simple loading state while fetching.
- **Demo credentials per role:** Seeded in the database — one user per role (admin, ngo, donor, school, student) with known email/password combinations. Example: `admin@demo.openScholar.org / demo123`. These credentials are hardcoded in `api.js`.

### Seed Script
- **IDs:** Use the exact string IDs from mock.js as primary keys (e.g., `id = 'ngo-1'`, `id = 'stu-1'`) — the DB models must support string PKs or the IDs map to a stable integer sequence. If models use integer PKs, the seed sets IDs using `INSERT ... ON CONFLICT ... DO UPDATE SET id = EXCLUDED.id` or sequences are reset to allow hardcoded IDs. The planner must resolve the exact PK type strategy.
- **Idempotency:** UPSERT strategy — `INSERT ... ON CONFLICT (id) DO UPDATE SET <all fields>`. Running seed twice overwrites with fresh mock.js values; no duplicate rows.
- **Hierarchy order (insert sequence):**
  1. Users (one per role: admin, ngo-owner for ngo-1, donor-1, school-1, student-1)
  2. NGOs (ngo-1 through ngo-5) linked to ngo-owner user
  3. Schools (school-1 through school-4)
  4. Programs (prog-1 through prog-5) linked to NGOs
  5. Students (stu-1 through stu-5) linked to programs and NGOs
  6. Donors (donor-1 through donor-5) linked to donor users
  7. Donations (don-1 through don-7) with mock tx hashes
  8. Invoices (inv-1 through inv-4) with items JSON and mock tx hashes for approved ones
  9. Allocations (matching mock fund allocation data) with mock tx hashes
  10. ActivityLog baseline (8 entries from mock.js `recentActivity` with computed timestamps)
- **Timing:** Seed runs in `entrypoint.sh` after `alembic upgrade head` and before `uvicorn` starts. Command: `python scripts/seed.py`.
- **Blockchain tx hashes:** Approved invoices and donations use 64-char hex mock tx hashes (same format as MockSuiBlockchain generates — `secrets.token_hex(32)` for realistic appearance).

### Activity Feed (ACTV-02)
- **Endpoint:** `GET /api/public/activity` — no auth required
- **Data source:** Real `ActivityLog` rows from DB, ordered by `created_at DESC`, **no row limit** (return all)
- **Response shape per entry:** `{type, color, text, time}` where `time` is an ISO 8601 timestamp string (e.g., `"2026-03-11T10:00:00Z"`) — the frontend computes the relative string ("2 hours ago") from the ISO timestamp
- **Baseline entries:** The 8 mock.js `recentActivity` entries are seeded as ActivityLog rows. Their `created_at` timestamps are computed from the mock.js `time` text: `"2 hours ago"` → `NOW() - 2h`, `"1 day ago"` → `NOW() - 1d`, etc., relative to when the seed runs. This makes the frontend display "2 hours ago" correctly on first run.
- **New entries:** Any real actions taken during the demo (NGO verification, donations, etc.) create new ActivityLog rows that appear above the seeded baseline entries when ordered by `created_at DESC`.

### Public Endpoints (PUBL-01 through PUBL-04)
- **All 4 endpoints require no authentication** — no `Depends(get_current_user)` or `require_role()`
- **`GET /api/public/stats`** — returns `platformStats` shape matching mock.js: `{totalDonations, totalStudents, totalNGOs, totalPrograms, totalSchools, fundsAllocated, fundsUtilized}` — computed from live DB aggregates (COUNT/SUM queries)
- **`GET /api/public/activity`** — returns full ActivityLog list as described above
- **`GET /api/public/ngos`** — returns only verified NGOs (status='verified'), public fields only (no internal admin fields)
- **`GET /api/public/programs`** — returns only active programs (status='active'), public fields only

### Move Smart Contract (BLKC-05)
- **Purpose:** Narrative-only for UNICEF grant demo — not called by the Python backend
- **File layout:** `contracts/Move.toml` (package manifest) + `contracts/sources/scholarship.move` (contract source). Must pass `sui move build` without errors.
- **Contract content:** A `openScholar` module (note: name matches the new app name) with domain-aligned structs and entry functions that mirror the Python blockchain interface:
  - Structs: `Scholarship`, `StudentWallet`, `FundAllocation`, `Invoice`
  - Entry functions: `create_student_wallet`, `donate`, `allocate_funds`, `settle_invoice`
  - No real Sui coin/transfer logic required — can use placeholder implementations (e.g., `abort 0`)
  - Comments explain what each function would do in production

### Claude's Discretion
- Exact demo credential email format and passwords (as long as they're in the seed and hardcoded in api.js consistently)
- Loading state UI while async api.js fetches data (simple spinner or blank is fine)
- Whether the frontend token cache uses sessionStorage, localStorage, or in-memory JS variables
- `.env.example` exact contents (document whatever `config.py` reads)
- Admin user's linked profile (admin has no NGO/Donor/School/Student row — `GET /api/auth/me` returns just User fields)
- Move.toml package name and address (as long as it builds)

</decisions>

<specifics>
## Specific Ideas

- **App name is OpenScholar** (not EduTrack — the frontend already uses this name). The Move module should be named `openScholar` or `open_scholar` to match. Seed script comments should reference OpenScholar.
- **Frontend is a vanilla JS SPA** (no bundler, no npm, no build step) — api.js changes must use native ES modules and browser `fetch()`. No axios, no libraries.
- **Demo credential format:** Something like `admin@demo.openScholar.org` / `demo123` — human-readable for the grant demo presentation.
- **The grant demo is March 2026 (UNICEF Venture Fund, $100K equity-free)** — the demo walkthrough order matters: public dashboard → admin → NGO → donor → student → school. The seed data should paint a coherent story across roles.
- **Seed data coherence:** stu-1 (Aarati Tamang) is in prog-1 (ngo-1's program), has received allocations, and school-1 submitted invoices for that program. The story should be visible end-to-end in the NGO dashboard and donor fund-flow view.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/api/public.py`: Empty router stub — Phase 4 fills in all 4 public endpoints here
- `app/services/activity_service.py`: `log()` function already implemented (Phase 2) — public feed reads from the same ActivityLog table
- `app/services/admin_service.py`: Has `get_platform_stats()` already (Phase 2) — reuse for public stats endpoint
- `scripts/entrypoint.sh`: Already runs `alembic upgrade head` then `uvicorn` — add `python scripts/seed.py` between them
- `contracts/sources/`: Directory exists — add `contracts/Move.toml` and `contracts/sources/scholarship.move`
- `uploads/`: Already exists for file storage

### Established Patterns
- **Public endpoint pattern:** No `Depends(get_current_user)` — just `Depends(get_db)` for DB access; call service layer function; return Pydantic model
- **Response schema pattern:** All schemas inherit `BaseResponse` (`from_attributes=True`, `populate_by_name=True`); all keys camelCase matching mock.js exactly
- **Service pattern:** async function, receives `db: AsyncSession`, returns Pydantic model instance (never raw dict)
- **camelCase aliases:** All snake_case DB fields aliased — `total_donations` → `totalDonations`, etc.
- **Frontend pattern:** Vanilla JS ES modules, hash-based routing, render functions return HTML strings, `app.innerHTML` is set by router

### Integration Points
- `app/main.py`: `public.router` already registered under `/api` prefix (from Phase 1 stub) — Phase 4 just populates it
- `src/data/mock.js` (OpenScholar frontend): Rewrite this file — it's the integration seam. All 15 page files import from it. Exports must remain named the same (`ngos`, `programs`, `students`, `platformStats`, `recentActivity`, etc.) but become async fetch functions.
- `src/main.js`: Route handlers currently call synchronous render functions — update to `await renderPage()` pattern
- `app/models/activity_log.py`: Has `type`, `color`, `text`, `created_at` fields — `time` field in the API response is computed from `created_at` (ISO string, not pre-formatted)

### Frontend Mock.js Data Shapes (exact keys for API contract)
From mock.js — these camelCase keys must match API responses:
- NGO: `{id, name, location, status, description, taxDoc, regDoc, avatar, color, totalFunded, studentsHelped, programsCount, registeredDate, programs}`
- Program: `{id, ngoId, name, description, status, categories, totalBudget, allocated, studentsEnrolled, startDate, endDate}`
- Student: `{id, name, age, school, grade, guardian, programId, ngoId, scholarshipId, walletBalance, totalReceived, status, location}`
- Donor: `{id, name, totalDonated, donations}`
- Donation: `{id, donorId, ngoId, programId, amount, date, type, studentId?}`
- Invoice: `{id, schoolId, schoolName, ngoId, programId, amount, category, status, items, date, approvedDate}`
- School: `{id, name, location, status, studentsInPrograms, totalInvoiced}`
- Activity: `{type, color, text, time}` — `time` is ISO timestamp in API (frontend computes relative string)
- PlatformStats: `{totalDonations, totalStudents, totalNGOs, totalPrograms, totalSchools, fundsAllocated, fundsUtilized}`

</code_context>

<deferred>
## Deferred Ideas

- Real Sui SDK integration (`pysui`) — v2, BLKC-V2-01
- Frontend login UI with real JWT auth flow — v2 (current demo mode uses hardcoded credentials)
- Activity feed pagination — v2 (currently returns all entries)
- Rate limiting, Nginx, encryption at rest — production hardening, v2
- Automated test suite — v2, TEST-V2-01

</deferred>

---

*Phase: 04-demo-readiness*
*Context gathered: 2026-03-11*
