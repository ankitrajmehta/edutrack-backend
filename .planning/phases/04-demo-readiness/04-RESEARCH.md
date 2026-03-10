# Phase 4: Demo Readiness - Research

**Researched:** 2026-03-11
**Domain:** FastAPI public endpoints, idempotent PostgreSQL seeding, Sui Move contract scaffolding, vanilla JS async frontend integration
**Confidence:** HIGH — all findings verified directly from codebase inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Frontend integration:** `src/data/mock.js` rewritten as async API client. All 15 pages continue importing from same path — exports become async fetch functions.
- **Demo mode:** No real login flow. Frontend auto-logs in at startup using hardcoded credentials per role. `api.js` calls `POST /api/auth/login` and caches the access token per role.
- **Role switching:** Navbar role switcher re-authenticates with new role's credentials. Per-role tokens cached in memory — switching back reuses cached token.
- **Render pattern:** Page render functions become `async` and `await` the api.js data fetching functions. Route handlers call `await renderPage()`.
- **Seed IDs:** Use exact string IDs from mock.js as PKs (e.g., `id = 'ngo-1'`, `id = 'stu-1'`). DB models use integer PKs — planner must resolve PK strategy. Seed sets IDs or maps to stable integer sequence.
- **Idempotency:** UPSERT strategy — `INSERT ... ON CONFLICT (id) DO UPDATE SET <all fields>`. Running twice overwrites with fresh mock.js values.
- **Seed hierarchy order:** Users → NGOs → Schools → Programs → Students → Donors → Donations → Invoices → Allocations → ActivityLog
- **Activity feed:** `GET /api/public/activity` returns full ActivityLog, `time` field is ISO 8601 timestamp (frontend computes relative string). No row limit.
- **Activity baseline:** 8 mock.js `recentActivity` entries seeded with computed timestamps (`NOW() - offset`).
- **Public endpoints:** All 4 require NO auth — no `Depends(get_current_user)`. Only `Depends(get_db)`.
- **Move contract:** `contracts/Move.toml` + `contracts/sources/scholarship.move`. Must pass `sui move build`. Module name `openScholar` or `open_scholar`. Narrative only — not called by backend.
- **Entrypoint:** Add `python scripts/seed.py` between `alembic upgrade head` and `uvicorn` in `entrypoint.sh`.
- **Frontend is vanilla JS SPA with Vite:** No bundler changes. Native ES modules, browser `fetch()`. No axios/libraries.
- **Demo credential format:** `admin@demo.openScholar.org / demo123` style — human-readable.
- **App name:** OpenScholar (NOT EduTrack). Move module name matches.

### Claude's Discretion
- Exact demo credential email format and passwords (consistent between seed and api.js)
- Loading state UI while async api.js fetches data (simple spinner or blank)
- Whether frontend token cache uses sessionStorage, localStorage, or in-memory JS variables
- `.env.example` exact contents (document whatever `config.py` reads)
- Admin user's linked profile (admin has no NGO/Donor/School/Student row)
- Move.toml package name and address (as long as it builds)

### Deferred Ideas (OUT OF SCOPE)
- Real Sui SDK integration (`pysui`) — v2
- Frontend login UI with real JWT auth flow — v2
- Activity feed pagination — v2
- Rate limiting, Nginx, encryption at rest — v2
- Automated test suite — v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-06 | Seed script (idempotent) populates DB with data matching mock.js exactly | PK strategy analysis, UPSERT pattern, hierarchy order documented |
| PUBL-01 | Unauthenticated user can view aggregate platform stats | `get_stats()` in admin_service.py is directly reusable; `AdminStatsResponse` schema matches mock.js `platformStats` |
| PUBL-02 | Unauthenticated user can view recent activity feed (type, text, time as relative string) | `ActivityLog` model confirmed; `timestamp` column is the field; ISO string returned, FE computes relative |
| PUBL-03 | Unauthenticated user can browse verified NGOs | `NGOResponse` schema exists; filter by `status='verified'`; drop internal fields |
| PUBL-04 | Unauthenticated user can browse active programs | `ProgramResponse` schema exists; filter by `status='active'` |
| BLKC-05 | Sui Move smart contract syntactically valid, deployable to testnet | Move.toml manifest structure, module syntax, minimal valid entry functions documented |
| ACTV-02 | Activity log entries expose `{type, color, text, time}` on public feed; `time` is relative string | `ActivityLog` has `type`, `color`, `text`, `timestamp` — response schema maps `timestamp` to `time` as ISO string |
| APIC-03 | Frontend works end-to-end against live API with no mock.js fallback | All 15 pages analyzed; import patterns documented; async migration strategy confirmed |
</phase_requirements>

---

## Summary

Phase 4 is an integration and glue phase — it wires together all the backend work from Phases 1–3 with the frontend and adds three new artifacts: the public API endpoints, the seed script, and the Move contract. Critically, this phase does NOT require any new business logic; it reuses existing service methods and models.

The most complex work is the **seed script**, which must navigate the mismatch between mock.js string IDs (`'ngo-1'`, `'stu-1'`) and the database's integer PKs. The models all use `Column(Integer, primary_key=True)`. The solution is to use PostgreSQL sequences: reset each table's sequence and INSERT with explicit integer IDs that correspond to the mock string suffixes (e.g., `ngo-1` → `id=1`, `stu-3` → `id=3`). The UPSERT strategy uses `ON CONFLICT (id) DO UPDATE` for idempotency.

The **frontend migration** requires understanding that all 15 pages call synchronous functions from `mock.js` today. After rewriting `mock.js` as an async API client and making render functions `async`, the router in `main.js` must be updated to `await renderPage()`. The token cache in `api.js` persists per-role JWT tokens so role switching doesn't re-authenticate unnecessarily.

The **Move contract** is purely narrative — a syntactically valid but functionally placeholder Move module with the right struct and entry function names. The critical requirement is that `sui move build` succeeds, which requires a valid `Move.toml` with correct package name and dependencies.

**Primary recommendation:** Tackle in four sequential work areas: (1) public endpoints + activity feed schema, (2) seed script with PK strategy, (3) frontend mock.js rewrite + main.js async, (4) Move contract scaffolding.

---

## Standard Stack

### Core (already in project)
| Library/Tool | Version | Purpose | Notes |
|---------|---------|---------|--------------|
| SQLAlchemy (async) | 2.x | ORM + UPSERT queries | `insert().on_conflict_do_update()` via `postgresql` dialect |
| FastAPI | 0.110+ | Public router endpoints | `public.router` already registered in `main.py` |
| Pydantic v2 | 2.x | Response schemas | `BaseResponse` with `from_attributes=True` established |
| asyncpg | — | PostgreSQL async driver | Required for `AsyncSession` |
| passlib + bcrypt | — | Password hashing for seed users | bcrypt pinned `>=4.1.2,<5.0.0` |

### New for Phase 4
| Library/Tool | Version | Purpose | Notes |
|---------|---------|---------|-------------|
| Sui Move toolchain | latest | `sui move build` validation | Installed separately; not a Python dep |
| `sqlalchemy.dialects.postgresql` | built-in | `insert().on_conflict_do_update()` | PostgreSQL UPSERT |
| `asyncio` | stdlib | Run async seed script | `asyncio.run(main())` in seed script |

### Alternatives Considered
| Standard | Alternative | Why Standard Wins |
|------------|-----------|----------|
| PostgreSQL UPSERT via SQLAlchemy | Raw SQL `INSERT ... ON CONFLICT` | SQLAlchemy dialect approach keeps consistent patterns with existing code |
| ISO 8601 timestamp from API (FE computes relative) | Server-side `humanize` library | Keeps server stateless; FE computation avoids dependency on server clock drift |
| In-memory JS token cache | localStorage/sessionStorage | Simplest for demo; no persistence needed across page reloads |

---

## Architecture Patterns

### Recommended Project Structure for Phase 4
```
backend/
├── scripts/
│   ├── entrypoint.sh          # MODIFIED: add seed between migrate + uvicorn
│   └── seed.py                # NEW: idempotent seed script
├── app/
│   └── api/
│       └── public.py          # FILLED: 4 public endpoints
│   └── schemas/
│       └── public.py          # NEW: PublicStatsResponse, ActivityResponse, PublicNGOResponse, PublicProgramResponse
│   └── services/
│       └── public_service.py  # NEW: service functions for public endpoints
├── contracts/
│   ├── Move.toml              # NEW: package manifest
│   └── sources/
│       └── scholarship.move   # NEW: Move module
OpenScholar/src/
├── data/
│   └── mock.js                # REWRITTEN: async API client
├── main.js                    # MODIFIED: renderPage becomes async
└── (no other changes needed)
```

### Pattern 1: Public Endpoint (No Auth)
**What:** FastAPI endpoint with only `Depends(get_db)`, no `Depends(get_current_user)`
**When to use:** All 4 public endpoints (stats, activity, ngos, programs)

```python
# Source: established pattern from app/api/admin.py + app/core/database.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.public import PublicStatsResponse
from app.services import public_service

router = APIRouter()

@router.get("/stats", response_model=PublicStatsResponse)
async def get_public_stats(db: AsyncSession = Depends(get_db)):
    return await public_service.get_stats(db)
```

### Pattern 2: Reuse AdminStatsResponse for Public Stats
**What:** `get_stats()` from `admin_service.py` returns `AdminStatsResponse` which has exact mock.js shape
**When to use:** `GET /api/public/stats` — can call `admin_service.get_stats(db)` directly

```python
# Source: app/services/admin_service.py (lines 24-50)
# AdminStatsResponse already has: totalDonations, totalStudents, totalNGOs, 
# totalPrograms, totalSchools, fundsAllocated, fundsUtilized
# → directly reusable for public stats endpoint (same shape as mock.js platformStats)
from app.services.admin_service import get_stats as get_platform_stats
```

### Pattern 3: Activity Feed Response Schema
**What:** `ActivityLog` model has `type`, `color`, `text`, `timestamp` (DateTime) — response maps `timestamp` → `time` as ISO string
**When to use:** `GET /api/public/activity`

```python
# Source: app/models/activity_log.py (lines 25-37)
# ActivityLog fields: id, type, text, timestamp, actor_id, color
# NOTE: column is named 'timestamp', NOT 'created_at' (confirmed from model)

class ActivityResponse(BaseResponse):
    type: str
    color: Optional[str] = None
    text: str
    time: str  # ISO 8601 string from timestamp column, aliased

    @classmethod
    def from_log(cls, log: ActivityLog) -> "ActivityResponse":
        return cls(
            type=log.type.value if hasattr(log.type, 'value') else log.type,
            color=log.color or "gray",
            text=log.text,
            time=log.timestamp.isoformat() + "Z",
        )
```

### Pattern 4: PostgreSQL UPSERT (Idempotent Seed)
**What:** `INSERT ... ON CONFLICT (id) DO UPDATE SET field = EXCLUDED.field`
**When to use:** Every table in seed.py

```python
# Source: SQLAlchemy PostgreSQL dialect docs
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(NGO).values(
    id=1,
    name="Bright Future Foundation",
    ...
).on_conflict_do_update(
    index_elements=["id"],
    set_=dict(
        name="Bright Future Foundation",
        ...
    )
)
await db.execute(stmt)
```

### Pattern 5: PK Strategy for String-ID Mock Data
**What:** Mock uses string IDs (`'ngo-1'`), DB uses integer PKs. Map suffix to integer: `ngo-1 → 1`, `ngo-5 → 5`.
**When to use:** All seed tables. Reset sequences after explicit inserts.

```python
# Mock ID → Integer ID mapping (deterministic, not coincidental)
# ngo-{N} → N  (ngo-1 → 1, ngo-2 → 2, ..., ngo-5 → 5)
# prog-{N} → N  (prog-1 → 1, ..., prog-5 → 5)
# stu-{N} → N   (stu-1 → 1, ..., stu-5 → 5)
# donor-{N} → N (donor-1 → 1, ..., donor-5 → 5)
# school-{N} → N (school-1 → 1, ..., school-4 → 4)
# don-{N} → N  (don-1 → 1, ..., don-7 → 7)
# inv-{N} → N  (inv-1 → 1, ..., inv-4 → 4)
# Users: admin=1, ngo-user=2, school-user=3, donor-user=4, student-user=5

# After seeding, reset the sequence so new records don't conflict:
await db.execute(text("SELECT setval('ngos_id_seq', (SELECT MAX(id) FROM ngos))"))
```

### Pattern 6: Seed Script Structure (Async)
**What:** Standalone async script using `asyncio.run()` with the project's `AsyncSessionLocal`
**When to use:** `scripts/seed.py`

```python
# Source: app/core/database.py pattern + standard asyncio
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password  # for hashing demo passwords

async def main():
    async with AsyncSessionLocal() as db:
        await seed_users(db)
        await seed_ngos(db)
        await seed_schools(db)
        await seed_programs(db)
        await seed_students(db)
        await seed_donors(db)
        await seed_donations(db)
        await seed_invoices(db)
        await seed_allocations(db)
        await seed_activity_log(db)
        await db.commit()
        print("Seed complete.")

if __name__ == "__main__":
    asyncio.run(main())
```

### Pattern 7: Frontend Async Migration
**What:** mock.js exports become async functions; pages `await` them; main.js router uses `async` handlers
**When to use:** All 15 page files in OpenScholar

```javascript
// BEFORE (sync mock.js):
export const ngos = [{ id: 'ngo-1', ... }];

// AFTER (async api client mock.js):
import { api } from './api.js';  // api.js handles token management

export async function getNGOs() {
    return await api.get('/api/public/ngos');
}

// BEFORE (sync page render):
import { ngos } from '../data/mock.js';
export function renderDonorBrowse() {
    const verifiedNgos = ngos.filter(n => n.status === 'verified');
    return `...`;
}

// AFTER (async page render):
import { getNGOs, getPrograms, getStudents } from '../data/mock.js';
export async function renderDonorBrowse() {
    const ngos = await getNGOs();
    const verifiedNgos = ngos.filter(n => n.status === 'verified');
    return `...`;
}
```

### Pattern 8: api.js Token Management
**What:** Central API client with per-role token cache; auto-login on first request
**When to use:** `src/data/api.js` (new file alongside rewritten mock.js)

```javascript
// Source: CONTEXT.md decisions + browser fetch() pattern
const DEMO_CREDENTIALS = {
    admin:   { email: 'admin@demo.openscholar.org',   password: 'demo123' },
    ngo:     { email: 'ngo@demo.openscholar.org',     password: 'demo123' },
    donor:   { email: 'donor@demo.openscholar.org',   password: 'demo123' },
    school:  { email: 'school@demo.openscholar.org',  password: 'demo123' },
    student: { email: 'student@demo.openscholar.org', password: 'demo123' },
};

const API_BASE = 'http://localhost:8000';
const tokenCache = {};  // in-memory: { role: 'jwt-token' }
let currentRole = 'public';

async function getToken(role) {
    if (!DEMO_CREDENTIALS[role]) return null;
    if (tokenCache[role]) return tokenCache[role];
    const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(DEMO_CREDENTIALS[role]),
    });
    const data = await res.json();
    tokenCache[role] = data.accessToken;  // camelCase from backend
    return tokenCache[role];
}

export const api = {
    setRole(role) { currentRole = role; },
    async get(path, role = currentRole) {
        const token = await getToken(role);
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await fetch(`${API_BASE}${path}`, { headers });
        return res.json();
    },
    async post(path, body, role = currentRole) {
        const token = await getToken(role);
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers.Authorization = `Bearer ${token}`;
        const res = await fetch(`${API_BASE}${path}`, {
            method: 'POST', headers, body: JSON.stringify(body)
        });
        return res.json();
    },
};
```

### Pattern 9: main.js Async Router
**What:** Route handlers must `await renderPage()` since render functions are now async
**When to use:** `OpenScholar/src/main.js`

```javascript
// BEFORE:
function renderPage(route) {
    let pageContent = '';
    switch (route) {
        case '/donor/browse':
            pageContent = renderDonorBrowse();  // sync
            break;
    }
    app.innerHTML = `... ${pageContent} ...`;
}

// AFTER:
async function renderPage(route) {
    app.innerHTML = `<div class="loading-state">Loading...</div>`;  // optional
    let pageContent = '';
    switch (route) {
        case '/donor/browse':
            pageContent = await renderDonorBrowse();  // async
            break;
    }
    app.innerHTML = `... ${pageContent} ...`;
}

// Router callback must also be async:
allRoutes.forEach(route => {
    registerRoute(route, async () => await renderPage(route));
});
```

### Pattern 10: Move Contract Minimal Valid Syntax
**What:** Sui Move module with structs and entry functions that build cleanly
**When to use:** `contracts/sources/scholarship.move`

```move
// Source: Sui Move documentation — minimal valid module structure
module openScholar::scholarship {
    use sui::object::{Self, UID};
    use sui::tx_context::TxContext;

    struct Scholarship has key, store {
        id: UID,
        student_id: vector<u8>,
        amount: u64,
        ngo_id: vector<u8>,
    }

    struct StudentWallet has key, store {
        id: UID,
        owner: address,
        balance: u64,
    }

    public entry fun create_student_wallet(ctx: &mut TxContext) {
        abort 0  // placeholder — production would create and transfer wallet
    }

    public entry fun donate(amount: u64, ctx: &mut TxContext) {
        abort 0  // placeholder — production would call coin::transfer
    }

    public entry fun allocate_funds(amount: u64, ctx: &mut TxContext) {
        abort 0  // placeholder
    }

    public entry fun settle_invoice(invoice_id: vector<u8>, ctx: &mut TxContext) {
        abort 0  // placeholder
    }
}
```

```toml
# contracts/Move.toml
[package]
name = "OpenScholar"
version = "0.0.1"
edition = "2024.beta"

[dependencies]
Sui = { git = "https://github.com/MystenLabs/sui.git", subdir = "crates/sui-framework/packages/sui-framework", rev = "framework/mainnet" }

[addresses]
openScholar = "0x0"
```

### Anti-Patterns to Avoid
- **Committing in seed per-row:** Call `await db.commit()` ONCE at the end of the entire seed, not after each table. Wrap in a transaction.
- **`db.add()` for UPSERT:** `db.add()` uses INSERT which fails on conflict. Must use `pg_insert(...).on_conflict_do_update()`.
- **Async render functions called synchronously:** `renderPage(route)` returning a Promise without `await` causes the route handler to set `innerHTML` before the Promise resolves — always `await`.
- **`time` field pre-formatted on backend:** The CONTEXT.md decision is clear: return ISO timestamp, FE computes "2 hours ago". Do not install or import `humanize` or `arrow` on the backend.
- **ActivityLog `created_at` vs `timestamp`:** The model uses `timestamp` (column name), not `created_at`. This is a naming inconsistency — reference `log.timestamp` not `log.created_at` in the service.
- **Sharing AsyncSession across awaits without care:** The seed script must use a single session for all operations (single transaction). Do not create separate sessions per table.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Relative time formatting | Server-side "2 hours ago" string builder | Return ISO timestamp; let frontend compute | Decision locked in CONTEXT.md; server-side adds statefulness |
| Password hashing for seed users | Manual bcrypt calls | `app.core.security.hash_password()` or existing auth service pattern | Already exists; consistent hashing |
| JWT creation for test tokens | Manual PyJWT encode in seed | Real credentials seeded; frontend calls `POST /api/auth/login` | Frontend auto-logs in; seed only needs user rows |
| Relative time on frontend | Custom JS date formatter | Simple JS arithmetic: `const diff = Date.now() - new Date(isoStr)` | 10 lines of JS, no library needed |
| Move contract coin logic | Real Sui transfer functions | `abort 0` placeholders | Narrative only; complexity not needed for demo |
| Custom UPSERT SQL | Raw `cursor.execute()` | SQLAlchemy `insert().on_conflict_do_update()` | Type-safe; consistent with codebase patterns |

---

## Common Pitfalls

### Pitfall 1: ActivityLog `timestamp` vs `created_at`
**What goes wrong:** Accessing `log.created_at` raises `AttributeError` — the column is named `timestamp`.
**Why it happens:** Most SQLAlchemy models use `created_at` by convention; this model uses `timestamp`.
**How to avoid:** In `public_service.py`, reference `log.timestamp.isoformat()`.
**Warning signs:** `AttributeError: 'ActivityLog' object has no attribute 'created_at'`

### Pitfall 2: Integer PK vs String Mock ID Mismatch
**What goes wrong:** Frontend pages hardcode `ngos.find(n => n.id === 'ngo-1')` but API returns `{"id": 1}`. After mock.js rewrite, the comparison `n.id === 'ngo-1'` never matches.
**Why it happens:** Mock.js used string IDs; DB models use integer PKs. The mock.js rewrite must NOT expect the API to return string IDs.
**How to avoid:** After rewriting mock.js, page files that do `ngos.find(n => n.id === 'ngo-1')` must be updated to use integer: `ngos.find(n => n.id === 1)`. ALL pages that use hardcoded mock IDs for filtering must be updated too. The NGO dashboard (`ngo/dashboard.js`) filters by `ngo.id === 'ngo-1'` — this breaks post-rewrite.
**Warning signs:** Empty page content, no NGOs/programs visible in role-specific views.

### Pitfall 3: Public Page Imports Destroyed by Async Migration
**What goes wrong:** Pages import `{ ngos, programs }` as named exports from mock.js (arrays). After rewrite, these become async functions. Destructuring arrays breaks silently.
**Why it happens:** The import syntax `import { ngos } from '../data/mock.js'` stays the same, but `ngos` is now a function, not an array. Code like `ngos.filter(...)` throws `TypeError: ngos.filter is not a function`.
**How to avoid:** Change all page files to call `const ngos = await getNGOs()` inside the async render function. Export names change from data constants to function names: `ngos` → `getNGOs`, `programs` → `getPrograms`, etc.
**Warning signs:** `TypeError: X.filter is not a function` in browser console.

### Pitfall 4: `renderPage` Route Handlers Not Awaited
**What goes wrong:** `app.innerHTML` is set before async render completes — blank or loading spinner never replaced with content.
**Why it happens:** `routes[hash]()` in `router.js` calls the route handler synchronously. If the handler is `async function renderPage()`, the Promise is created but not awaited.
**How to avoid:** Route registration must use async callbacks: `registerRoute(route, async () => { await renderPage(route); })`. The `handleRoute()` function in `router.js` must also `await` the handler.
**Warning signs:** Loading spinner never disappears; page flashes blank briefly.

### Pitfall 5: Seed Sequence Not Reset After Explicit ID Inserts
**What goes wrong:** After seeding with explicit IDs (1–5 for NGOs), the first new NGO created through the API gets `id=1` (sequence reset to 1, conflicts with seed).
**Why it happens:** PostgreSQL sequences are not automatically advanced when INSERT specifies explicit IDs.
**How to avoid:** After each table's UPSERT, execute `SELECT setval('{table}_id_seq', (SELECT MAX(id) FROM {table}))`.
**Warning signs:** UniqueViolation errors on first API-created record after seed.

### Pitfall 6: Activity Seed Timestamps Drift
**What goes wrong:** Seeded activity entries show "X days ago" instead of "2 hours ago" because timestamps were baked in as fixed values.
**Why it happens:** If seed uses `datetime(2026, 3, 11, 8, 0, 0)` as a hardcoded timestamp, by next day it reads "1 day ago".
**How to avoid:** Compute timestamps relative to `datetime.utcnow()` at seed runtime: `datetime.utcnow() - timedelta(hours=2)` for the "2 hours ago" entry.
**Warning signs:** Activity feed shows "N days ago" immediately after deployment.

### Pitfall 7: CORS Not Configured for Frontend Origin
**What goes wrong:** Browser rejects API calls with CORS error — especially if frontend runs on `localhost:5173` (Vite dev server).
**Why it happens:** `CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]` is in `config.py` with correct values — but if `.env` overrides it with a different value, CORS fails.
**How to avoid:** Ensure `.env` doesn't override CORS_ORIGINS, or explicitly includes both origins. The OpenScholar frontend runs on `localhost:5173` (confirmed in `vite.config.js`).
**Warning signs:** Browser console: `Access to fetch at 'http://localhost:8000/...' from origin 'http://localhost:5173' has been blocked by CORS policy`.

### Pitfall 8: Move.toml Framework Version Mismatch
**What goes wrong:** `sui move build` fails with `error[E0002]: unresolved module 'sui::object'` or dependency fetch error.
**Why it happens:** The Sui framework Git rev in `Move.toml` must match a valid tag or branch.
**How to avoid:** Use `framework/mainnet` rev (stable). If Sui CLI version doesn't match mainnet, use `framework/testnet`. The `abort 0` placeholder functions avoid needing actual Sui coin/transfer types.
**Warning signs:** `error: failed to resolve dependencies` during `sui move build`.

### Pitfall 9: admin_service.get_stats() Returns AdminStatsResponse (Schema with aliases)
**What goes wrong:** Public stats endpoint returns `AdminStatsResponse` which serializes with camelCase aliases — but if the endpoint uses `response_model=AdminStatsResponse` and FastAPI serializes correctly, this works fine. Problem only if developer creates a separate dict.
**Why it happens:** Misunderstanding that `AdminStatsResponse` can be returned directly.
**How to avoid:** Return the `AdminStatsResponse` instance directly from `admin_service.get_stats(db)` — aliases fire during FastAPI serialization.

---

## Code Examples

Verified patterns from direct codebase inspection:

### Public Endpoint Pattern (confirmed from admin.py + public.py stub)
```python
# app/api/public.py — fill in the stub
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.admin import AdminStatsResponse
from app.schemas.public import ActivityResponse, PublicNGOResponse, PublicProgramResponse
from app.services import admin_service, public_service

router = APIRouter()

@router.get("/stats", response_model=AdminStatsResponse)
async def public_stats(db: AsyncSession = Depends(get_db)):
    return await admin_service.get_stats(db)

@router.get("/activity", response_model=List[ActivityResponse])
async def public_activity(db: AsyncSession = Depends(get_db)):
    return await public_service.get_activity(db)

@router.get("/ngos", response_model=List[PublicNGOResponse])
async def public_ngos(db: AsyncSession = Depends(get_db)):
    return await public_service.get_public_ngos(db)

@router.get("/programs", response_model=List[PublicProgramResponse])
async def public_programs(db: AsyncSession = Depends(get_db)):
    return await public_service.get_public_programs(db)
```

### ActivityLog Query (note: `timestamp` not `created_at`)
```python
# app/services/public_service.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity_log import ActivityLog

async def get_activity(db: AsyncSession) -> list:
    result = await db.execute(
        select(ActivityLog).order_by(ActivityLog.timestamp.desc())
    )
    logs = result.scalars().all()
    return [
        {
            "type": log.type.value if hasattr(log.type, 'value') else log.type,
            "color": log.color or "gray",
            "text": log.text,
            "time": log.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        for log in logs
    ]
```

### Seed Script UPSERT for Users
```python
# scripts/seed.py — users table (must come first for FK relationships)
from passlib.context import CryptContext
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_PASSWORD_HASH = pwd_context.hash("demo123")

SEED_USERS = [
    {"id": 1, "email": "admin@demo.openscholar.org", "hashed_password": DEMO_PASSWORD_HASH, "role": UserRole.admin, "is_active": True},
    {"id": 2, "email": "ngo@demo.openscholar.org",   "hashed_password": DEMO_PASSWORD_HASH, "role": UserRole.ngo, "is_active": True},
    {"id": 3, "email": "school@demo.openscholar.org","hashed_password": DEMO_PASSWORD_HASH, "role": UserRole.school, "is_active": True},
    {"id": 4, "email": "donor@demo.openscholar.org", "hashed_password": DEMO_PASSWORD_HASH, "role": UserRole.donor, "is_active": True},
    {"id": 5, "email": "student@demo.openscholar.org","hashed_password": DEMO_PASSWORD_HASH, "role": UserRole.student, "is_active": True},
]

async def seed_users(db):
    for user in SEED_USERS:
        stmt = pg_insert(User).values(**user).on_conflict_do_update(
            index_elements=["id"],
            set_={k: v for k, v in user.items() if k != "id"}
        )
        await db.execute(stmt)
    await db.execute(text("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))"))
```

### Seed Activity Log with Relative Timestamps
```python
# scripts/seed.py — activity_log entries with computed timestamps
from datetime import datetime, timedelta
from app.models.activity_log import ActivityLog, ActivityType

async def seed_activity_log(db):
    now = datetime.utcnow()
    entries = [
        # "2 hours ago" → now - 2h
        {"type": ActivityType.donation, "color": "green",
         "text": "Sarah Mitchell donated $2,500 to Mountain Girls Scholarship",
         "timestamp": now - timedelta(hours=2), "actor_id": None},
        # "5 hours ago"
        {"type": ActivityType.invoice, "color": "amber",
         "text": "Shree Janapriya School submitted invoice for winter uniforms ($4,200)",
         "timestamp": now - timedelta(hours=5), "actor_id": None},
        # "1 day ago"
        {"type": ActivityType.verify, "color": "blue",
         "text": "Children First Nepal's registration is pending verification",
         "timestamp": now - timedelta(days=1), "actor_id": None},
        # "1 day ago" (second entry)
        {"type": ActivityType.allocation, "color": "green",
         "text": "Bright Future Foundation allocated $3,500 to Aarati Tamang",
         "timestamp": now - timedelta(days=1, hours=1), "actor_id": None},
        # "2 days ago"
        {"type": ActivityType.invoice, "color": "green",
         "text": "Tuition invoice from Annapurna Secondary School approved",
         "timestamp": now - timedelta(days=2), "actor_id": None},
        # "3 days ago"
        {"type": ActivityType.program, "color": "blue",
         "text": "Teacher Training Initiative program launched by Nepal Education Alliance",
         "timestamp": now - timedelta(days=3), "actor_id": None},
        # "3 days ago" (second)
        {"type": ActivityType.donation, "color": "green",
         "text": "James Chen donated $8,000 to Teacher Training Initiative",
         "timestamp": now - timedelta(days=3, hours=2), "actor_id": None},
        # "5 days ago"
        {"type": ActivityType.blacklist, "color": "red",
         "text": "Learn & Grow Trust's application was rejected due to incomplete documents",
         "timestamp": now - timedelta(days=5), "actor_id": None},
    ]
    # ActivityLog has no unique constraint on content, so check existence first
    # or use TRUNCATE + INSERT for activity log (it's baseline data)
    for entry in entries:
        db.add(ActivityLog(**entry))
```

### Entrypoint.sh Updated
```sh
#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Seeding database..."
python scripts/seed.py

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend: Relative Time Computation (JS, no library)
```javascript
// src/data/mock.js helper — computes "2 hours ago" from ISO string
function relativeTime(isoString) {
    const diff = Date.now() - new Date(isoString).getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0)    return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0)   return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return 'just now';
}
```

---

## Critical Data Mapping: Mock.js → DB Models

This is the core reference the planner needs for the seed script tasks.

### Mock.js ID → Integer PK Mapping (LOCKED)
| Mock ID | Integer PK | Table | Notes |
|---------|------------|-------|-------|
| `ngo-1` | 1 | ngos | Bright Future Foundation, user_id=2 |
| `ngo-2` | 2 | ngos | EduHope International |
| `ngo-3` | 3 | ngos | Children First Nepal (pending) |
| `ngo-4` | 4 | ngos | Nepal Education Alliance |
| `ngo-5` | 5 | ngos | Learn & Grow Trust (rejected) |
| `prog-1` | 1 | programs | Girls Education Program 2026, ngo_id=1 |
| `prog-2` | 2 | programs | STEM Scholarship 2025, ngo_id=1, status=completed |
| `prog-3` | 3 | programs | Mountain Girls Scholarship, ngo_id=2 |
| `prog-4` | 4 | programs | Eastern Nepal Literacy Drive, ngo_id=4 |
| `prog-5` | 5 | programs | Teacher Training Initiative, ngo_id=4 |
| `stu-1` | 1 | students | Aarati Tamang, ngo_id=1, program_id=1 |
| `stu-2` | 2 | students | Binod Shrestha, ngo_id=1, program_id=1 |
| `stu-3` | 3 | students | Chandra Maya Gurung, ngo_id=2, program_id=3 |
| `stu-4` | 4 | students | Deepa Rai, ngo_id=4, program_id=4 |
| `stu-5` | 5 | students | Ekta Sharma, ngo_id=1, program_id=1, status=graduated |
| `donor-1` | 1 | donors | Sarah Mitchell, user_id=4 |
| `donor-2` | 2 | donors | James Chen |
| `donor-3` | 3 | donors | Priya Patel |
| `donor-4` | 4 | donors | Nordic Aid Foundation |
| `donor-5` | 5 | donors | Global Ed Trust |
| `school-1` | 1 | schools | Shree Janapriya Secondary, user_id=3 |
| `school-2` | 2 | schools | Annapurna Secondary |
| `school-3` | 3 | schools | Koshi Valley School |
| `school-4` | 4 | schools | Himalayan Model School |
| `don-1` | 1 | donations | donor_id=1, ngo_id=1, program_id=1, amount=5000 |
| `don-2` | 2 | donations | donor_id=2, ngo_id=2, program_id=3, amount=10000 |
| `don-3` | 3 | donations | donor_id=3, ngo_id=1, program_id=NULL, type=general |
| `don-4` | 4 | donations | donor_id=4, ngo_id=4, program_id=4, amount=25000 |
| `don-5` | 5 | donations | donor_id=5, ngo_id=1, program_id=1, amount=50000 |
| `don-6` | 6 | donations | donor_id=1, ngo_id=2, program_id=3, student_id=3, type=student |
| `don-7` | 7 | donations | donor_id=2, ngo_id=4, program_id=5, amount=8000 |
| `inv-1` | 1 | invoices | school_id=1, ngo_id=1, prog_id=1, status=approved, tx_hash needed |
| `inv-2` | 2 | invoices | school_id=1, ngo_id=1, prog_id=1, status=pending |
| `inv-3` | 3 | invoices | school_id=2, ngo_id=2, prog_id=3, status=approved, tx_hash needed |
| `inv-4` | 4 | invoices | school_id=3, ngo_id=4, prog_id=4, status=pending |

### Frontend Pages Using Mock.js Imports (All 15)
| Page File | Mock Imports | API Endpoints Needed | Role |
|-----------|-------------|---------------------|------|
| `public-dashboard.js` | `platformStats, recentActivity, ngos, programs` | `/api/public/stats`, `/api/public/activity`, `/api/public/ngos` | public |
| `admin/dashboard.js` | `ngos, students, platformStats` | `/api/admin/dashboard`, `/api/admin/ngos` | admin |
| `admin/verify-ngos.js` | `ngos` | `/api/admin/ngos` | admin |
| `admin/blacklist.js` | `ngos, students` | `/api/admin/blacklist` | admin |
| `donor/browse.js` | `ngos, programs, students` | `/api/public/ngos`, `/api/public/programs`, (students endpoint) | donor |
| `donor/donate.js` | `ngos, programs, students` | same as browse | donor |
| `donor/track.js` | `donations, ngos, programs, students` | `/api/donor/donations` | donor |
| `ngo/dashboard.js` | `programs, students, invoices, donations, ngos` | `/api/ngo/dashboard`, `/api/ngo/programs`, etc. | ngo |
| `ngo/programs.js` | `programs, ngos` | `/api/ngo/programs` | ngo |
| `ngo/students.js` | `students, programs, ngos` | `/api/ngo/students` | ngo |
| `ngo/invoices.js` | `invoices, programs, ngos` | `/api/ngo/invoices` | ngo |
| `ngo/fund-allocation.js` | `programs, students` | `/api/ngo/programs`, `/api/ngo/students`, `/api/ngo/allocations` | ngo |
| `student/apply.js` | `programs, ngos` | `/api/public/programs` (or student endpoint) | student |
| `school/register.js` | none (no mock imports) | — | school |
| `school/invoices.js` | `invoices, programs, ngos` | `/api/school/invoices` | school |

**Note:** `school/register.js` has NO mock.js imports — it's a static form. No changes needed.

### Pages Hardcoding String IDs (Must Update)
These pages filter by hardcoded string IDs — must be updated to integer equivalents after mock.js rewrite:
- `ngo/dashboard.js` line 9: `ngos.find(n => n.id === 'ngo-1')` → `n.id === 1`
- `ngo/dashboard.js` line 10–13: `programs.filter(p => p.ngoId === 'ngo-1')` etc.
- `ngo/students.js` line 9: `students.filter(s => s.ngoId === 'ngo-1')`
- `ngo/fund-allocation.js` lines 9–10: same pattern
- `donor/track.js` line 9: `donations.filter(d => d.donorId === 'donor-1')`
- `school/invoices.js` line 9: `invoices.filter(i => i.schoolId === 'school-1')`

**These can be resolved by**: having the API client return role-appropriate data filtered server-side (e.g., `/api/ngo/programs` already returns only the authenticated NGO's programs), so the frontend doesn't need to filter by hardcoded ID at all.

### Environment Variables (for .env.example)
From `app/core/config.py` (lines 7–12):
```
DATABASE_URL=postgresql+asyncpg://edutrack:edutrack@localhost:5432/edutrack
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
UPLOAD_DIR=./uploads
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `db.execute(text("INSERT ... ON CONFLICT"))` | `sqlalchemy.dialects.postgresql.insert().on_conflict_do_update()` | Type-safe, no raw SQL strings |
| Synchronous seed scripts | `asyncio.run(async_seed_main())` | Required by asyncpg; sync connections won't work with async engine |
| Mock.js as static data | Mock.js as async API client | Zero frontend code changes except render functions become async |
| Move contract with real logic | Placeholder `abort 0` | Demo-safe; no testnet deployment needed |

---

## Open Questions

1. **Donor profile for mock donors 2–5**
   - What we know: Only `donor-1` (Sarah Mitchell) is linked to `user_id=4`. The seed creates 1 donor user.
   - What's unclear: Do donors 2–5 need corresponding user rows? The `donors` table has `user_id` as FK.
   - Recommendation: Create users for all 5 donors. Donors 2–5 get emails like `donor2@demo.openscholar.org` with same `demo123` password. Or: seed donors 2–5 with `user_id` pointing to a shared donor user (donor user = donor-1, others are data-only with `user_id=4` if nullable — but `user_id` is NOT NULL and UNIQUE). **Best approach:** create 5 separate user rows for donors 1–5, only `donor@demo.openscholar.org` is the "demo" login. The other 4 are background data rows.

2. **School mock data: schools 2, 3, 4 need user rows?**
   - What we know: `schools.user_id` is NOT NULL and UNIQUE. Only `school-1` corresponds to the demo school user.
   - What's unclear: Schools 2, 3, 4 need their own user rows to satisfy the FK + UNIQUE constraint.
   - Recommendation: Create throwaway user rows for schools 2–4 with emails `school2@demo.openscholar.org`, etc. Only `school@demo.openscholar.org` is the demo credential.

3. **ActivityLog idempotency for seed**
   - What we know: `activity_logs` has no unique constraint on content — UPSERT by `id` is the only way to be idempotent.
   - What's unclear: Should we assign explicit IDs to the 8 baseline entries?
   - Recommendation: Yes — assign `id=1` through `id=8` to baseline entries, use `pg_insert().on_conflict_do_update()` same as other tables.

4. **PublicNGOResponse vs NGOResponse for `/api/public/ngos`**
   - What we know: CONTEXT.md says "public fields only (no internal admin fields)".
   - What's unclear: Whether `programs` relationship list is included. Mock.js NGO has `programs: ['prog-1', 'prog-2']`.
   - Recommendation: Exclude `programs` list from public response (it's a list of IDs in mock, not needed for donor browse view). `PublicNGOResponse` = subset of `NGOResponse` without `tax_doc`, `reg_doc`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None detected (v2 requirement) |
| Config file | None |
| Quick run command | Manual browser verification |
| Full suite command | N/A |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-06 | Seed runs twice without error | manual-only | Run `python scripts/seed.py` twice, check no duplicates | ❌ Wave 0 |
| PUBL-01 | `GET /api/public/stats` returns stats | smoke | `curl http://localhost:8000/api/public/stats` | N/A |
| PUBL-02 | `GET /api/public/activity` returns ISO times | smoke | `curl http://localhost:8000/api/public/activity` | N/A |
| PUBL-03 | `GET /api/public/ngos` returns only verified | smoke | `curl http://localhost:8000/api/public/ngos` | N/A |
| PUBL-04 | `GET /api/public/programs` returns only active | smoke | `curl http://localhost:8000/api/public/programs` | N/A |
| BLKC-05 | `sui move build` succeeds | manual | `sui move build` in contracts/ dir | ❌ Wave 0 |
| ACTV-02 | Activity entries have correct shape | smoke | curl + inspect JSON | N/A |
| APIC-03 | Frontend loads all 15 pages without errors | manual | Open browser, navigate all routes | N/A |

### Sampling Rate
- **Per task commit:** Manual curl checks for the specific endpoint added
- **Per wave merge:** Full browser walkthrough: all 15 routes, all roles
- **Phase gate:** `docker compose up`, full demo walkthrough before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `scripts/seed.py` — does not exist yet (main deliverable)
- [ ] `contracts/Move.toml` — does not exist yet
- [ ] `contracts/sources/scholarship.move` — does not exist yet
- [ ] `app/schemas/public.py` — does not exist yet
- [ ] `app/services/public_service.py` — does not exist yet
- [ ] `OpenScholar/src/data/api.js` — does not exist yet
- [ ] `.env.example` — does not exist yet

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `app/models/activity_log.py` (timestamp column name confirmed)
- Direct codebase inspection — `app/models/ngo.py`, `user.py`, `student.py`, `program.py`, `donation.py`, `invoice.py`, `allocation.py`, `donor.py`, `school.py` (all integer PKs confirmed)
- Direct codebase inspection — `app/services/admin_service.py` (get_stats() reusable, AdminStatsResponse shape)
- Direct codebase inspection — `app/api/public.py` (empty stub confirmed)
- Direct codebase inspection — `app/main.py` (public router registered at `/api/public`)
- Direct codebase inspection — `app/core/config.py` (all env vars inventoried)
- Direct codebase inspection — `OpenScholar/src/data/mock.js` (all IDs and data shapes)
- Direct codebase inspection — `OpenScholar/src/main.js` (all 15 routes, sync render pattern)
- Direct codebase inspection — `OpenScholar/src/pages/*` (all mock.js imports inventoried per page)
- Direct codebase inspection — `scripts/entrypoint.sh` (current migration-only content)
- Direct codebase inspection — `.planning/phases/04-demo-readiness/04-CONTEXT.md` (locked decisions)

### Secondary (MEDIUM confidence)
- SQLAlchemy PostgreSQL dialect UPSERT pattern: `insert().on_conflict_do_update()` — standard established pattern
- Sui Move minimal module syntax — `abort 0` placeholder pattern for narrative-only contracts

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified from codebase
- Architecture: HIGH — based on established patterns in existing code
- Pitfalls: HIGH — identified from direct code inspection (especially ActivityLog.timestamp naming, integer PK mismatch, hardcoded string IDs in page files)
- Seed data: HIGH — mock.js fully read, all IDs and relationships documented

**Research date:** 2026-03-11
**Valid until:** Phase 4 implementation (data is project-specific, not time-sensitive)
