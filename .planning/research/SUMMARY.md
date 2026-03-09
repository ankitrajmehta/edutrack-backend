# Research Summary: EduTrack Backend

**Synthesized:** 2026-03-09
**Confidence:** HIGH across all four research areas (official docs, verified pip versions, PRD + mock.js analysis)

---

## Stack

**Core runtime:**
- Python **3.11** (avoid 3.13 — passlib/crypt deprecations)
- FastAPI `~0.115.14` + uvicorn `~0.41.0[standard]`
- PostgreSQL 16 (`postgres:16-alpine`)
- SQLAlchemy **`~2.0.48[asyncio]`** + asyncpg `~0.31.0` — connection string: `postgresql+asyncpg://`
- Alembic `~1.18.4` — init with `--template async` flag (non-negotiable)
- Pydantic `~2.12.5` + pydantic-settings `~2.13.1`

**Auth:**
- `python-jose[cryptography]~3.5.0` — always use `[cryptography]` extra, never default
- `passlib[bcrypt]~1.7.4` + `bcrypt>=4.1.2,<5.0.0` — pin range is critical (4.1.0 yanked, 5.0.0 breaks passlib)

**File handling:**
- `python-multipart~0.0.22` — required for any `UploadFile` endpoint (missing = silent 422)
- `aiofiles~25.1.0` — async file I/O; never use sync `open()` in async route

**Blockchain (v1):**
- No external SDK — mock uses `secrets.token_hex(32)` + `asyncio.sleep(0.1–0.4)`
- `pysui~0.96.0` deferred to v2 (one-file swap in `dependencies.py`)

**Critical version pairs to get right:**
| Pair | Status |
|------|--------|
| `passlib~1.7.4` + `bcrypt>=4.1.2,<5.0.0` | ✅ SAFE |
| `passlib` + `bcrypt==4.1.0` | ❌ YANKED |
| `passlib` + `bcrypt>=5.0.0` | ❌ BREAKS |
| `python-jose` without `[cryptography]` | ⚠️ CVE risk |
| `sqlalchemy` without `[asyncio]` | ⚠️ MissingGreenlet on ARM |
| Alembic with sync `env.py` + asyncpg | ❌ DEADLOCKS |
| Pydantic v2 with `class Config: orm_mode = True` | ❌ SILENTLY IGNORED |

---

## Table Stakes Features

**AUTH (all roles):**
- Register with role assignment, login → JWT (30min access / 7d refresh), token refresh, logout (DB-side refresh token invalidation), `GET /me` with role-specific profile, RBAC guards on every route

**ADMIN:**
- Platform stats dashboard (totalDonations, totalStudents, totalNGOs, totalPrograms, totalSchools, fundsAllocated, fundsUtilized)
- NGO list with status filter → verify / reject / blacklist / restore
- Student blacklist / restore
- Combined blacklist view

**NGO:**
- Dashboard (scoped stats), program CRUD, manual student registration (generates `EDU-YYYY-XXXXX` + blockchain wallet), application review (accept → auto-create student record, reject), invoice approval/rejection with blockchain settlement, fund allocation to student wallets

**DONOR:**
- Browse verified NGOs and active programs, make donation (3 targeting levels: NGO / program / student), donation history, fund flow detail view (tx_hash chain)

**SCHOOL:**
- Register as partner, submit invoice with supporting doc upload, view own invoices with status

**STUDENT:**
- Browse active programs, submit scholarship application, view own application statuses

**PUBLIC (no auth):**
- Aggregate platform stats, recent activity feed, verified NGOs list, active programs list

**Cross-cutting (must ship in v1):**
- File upload + download (NGO docs, invoice supporting docs)
- Activity log written atomically on every significant action
- Blockchain mock layer (port-and-adapter Protocol)
- Idempotent seed script matching `mock.js` exactly (same IDs, same shapes)
- camelCase API responses (Pydantic v2 Field aliases on every schema)
- Structured error format: `{detail, code, statusCode}` globally
- Docker + Docker Compose (app + PostgreSQL)

---

## Differentiators

These are the UNICEF demo story — what makes this different from Submittable/Blackbaud:

1. **Blockchain tx hash on every money movement** — Donation, allocation, invoice settlement each write a verifiable tx hash. In v1 it's a realistic mock; in v2 it's real Sui ledger entries.
2. **End-to-end fund flow tracing** — Donor can see: donation → student → invoice → settlement tx hash. Radical transparency vs. "you donated $X to NGO Y."
3. **Per-student scholarship wallet** — Each student has a wallet address + balance. Funds flow NGO → student wallet → drawn down by school invoices. Student is an economic principal, not a passive record.
4. **Auto-generated scholarship ID (`EDU-YYYY-XXXXX`)** — Human-readable, portable beneficiary credential.
5. **Public activity feed** — Open ledger readable without auth or blockchain expertise. Earns public trust.
6. **Granular donation targeting** — NGO / program / named student. Enables "sponsor a child" model.
7. **NGO lifecycle governance** — Pending → Verified → Blacklisted → Restored. Admin as gatekeeper. No verified = no programs = no funds.

---

## Architecture Highlights

**Layer structure (strict):**
```
HTTP → API routes (app/api/*.py)
          ↓ one service call per handler
       Service layer (app/services/*.py)
          ↓ DB + blockchain calls
       Data layer (app/models/*.py → asyncpg → PostgreSQL)
       Blockchain port (app/services/blockchain/base.py Protocol)
          ↓ implemented by
       Mock adapter (mock_sui.py) ↔ future SuiBlockchainService (one-line swap)
```

**Key patterns (non-negotiable):**
- **Async everywhere:** All route handlers and service methods are `async def`. Blocking in async = event loop starvation.
- **`Depends(get_db)` session per request:** One `AsyncSession` per request, yielded via generator with rollback-on-exception. Never share across concurrent tasks.
- **`async_sessionmaker(expire_on_commit=False)`:** Without this, post-commit attribute access triggers lazy loads → MissingGreenlet errors.
- **`selectinload()` for one-to-many, `joinedload()` for many-to-one:** Never use default lazy loading in async context.
- **Service layer owns all commits:** Handlers call one service method and return its result. No `db.commit()` in route handlers.
- **Activity log before commit:** `activity_service.log()` called before `await db.commit()` so the log and the triggering event are atomically consistent.
- **Port-and-adapter blockchain:** `BlockchainService` Protocol defined in `base.py`. `get_blockchain()` dependency returns `MockSuiBlockchain()`. Swap to real SDK = change one line in `dependencies.py`.
- **Pydantic v2 schemas with camelCase aliases:** `ConfigDict(from_attributes=True, populate_by_name=True)` on every response schema. `Field(alias="camelCase")` per field. Never return raw dicts from services.
- **RBAC via dependency chain:** `require_role("ngo")` → `get_current_user()` → `get_db()`. Services additionally scope by owner ID (role check alone is insufficient).

**Recommended build order (dependency-driven):**
1. `config.py` → `database.py` → models → Alembic migration
2. `security.py` + `dependencies.py` → `auth_service.py` → auth routes → `main.py`
3. All schemas → `activity_service` + `file_service` → remaining services
4. API routes in dependency order: `public` → `admin` → `ngo` → `donor` → `school` → `student` → `files`
5. `scripts/seed.py` + Dockerfile + docker-compose.yml + `start.sh`

---

## Top Pitfalls to Avoid

**CRITICAL (Phase 1 — fix before writing any service):**

1. **Alembic sync env.py + asyncpg = deadlock.** Always init with `alembic init --template async`. The async `env.py` wraps migrations in `asyncio.run(run_async_migrations())`.

2. **MissingGreenlet from lazy-loaded relationships.** Set `expire_on_commit=False` on `async_sessionmaker`. Use `selectinload()`/`joinedload()` explicitly in every query that accesses relationships. Never access relationship attributes after session close.

3. **Pydantic v2 silent ORM mode failure.** `class Config: orm_mode = True` is silently ignored. Every response schema needs `model_config = ConfigDict(from_attributes=True, populate_by_name=True)`. Easiest fix: define a `BaseResponse` that all schemas inherit.

4. **JWT `sub` claim type mismatch.** `python-jose` decodes `sub` as a string even if you encode an int. Always: `user_id = int(payload.get("sub"))`. Always encode as: `{"sub": str(user.id)}`.

5. **CORS wildcard + credentials = browser rejection.** `allow_origins=["*"]` is incompatible with `allow_credentials=True`. Use explicit origins: `["http://localhost:3000", "http://localhost:5173"]`.

6. **bcrypt pin.** `bcrypt==4.1.0` is yanked. `bcrypt>=5.0.0` breaks passlib (>72-byte password ValueError). Safe range: `>=4.1.2,<5.0.0`.

**HIGH (Phase 2 — service layer):**

7. **Activity log after commit = phantom logs or silent failure.** Always call `activity_service.log(db, ...)` before `await db.commit()`. Both the operation and the log entry commit atomically or roll back together.

8. **Shared AsyncSession across concurrent tasks.** Never pass one `AsyncSession` to `asyncio.gather()` concurrently. Each concurrent task needs its own session.

9. **Blocking sync code in async handlers.** bcrypt hashing is CPU-bound. Wrap it: `await asyncio.to_thread(pwd_context.hash, password)`. Use `aiofiles` for file I/O — never `open()` in async route.

**MEDIUM (Phase 3+):**

10. **`Optional[str]` behavior change in Pydantic v2.** `Optional[str]` is now *required but nullable*. For optional fields with None default: `Optional[str] = None` (explicit default required). Applies to: `Donation.message`, `Invoice.tx_hash`, `Invoice.approved_date`.

11. **Refresh token race condition.** Two tabs refreshing simultaneously = second call fails = user logged out. Store refresh tokens in DB with `used: bool` flag. Mark used on first use, reject reuse.

12. **camelCase alias only works for serialization when returning Pydantic model, not dict.** Services must return Pydantic model instances. Returning a raw dict bypasses alias serialization → snake_case leaks to FE.

---

## Roadmap Implications

**Phase sequencing is strictly dependency-driven. No skipping levels.**

### Phase 1 — Foundation (CRITICAL PATH)
**Deliver:** Working DB + auth + Docker skeleton

- `config.py` → `database.py` (with `expire_on_commit=False`) → all models → Alembic async migration
- `security.py` (JWT + bcrypt with `asyncio.to_thread`) → `exceptions.py` → `dependencies.py`
- `BaseResponse` schema in `schemas/common.py` (all pitfalls #3, #4 addressed here)
- `auth_service.py` with refresh token DB model + `used` flag
- `main.py` with CORS explicit origins (not wildcard)
- Auth routes: register, login, refresh, logout, `GET /me`
- Docker Compose (app + PostgreSQL), `start.sh` (migrate → seed → uvicorn)

**Checkpoint:** `POST /auth/login` returns JWT. `GET /auth/me` returns role-specific user. Docker `docker-compose up` starts clean.

**Pitfalls to address here:** #1, #2, #3, #4, #5, #6, #9, #11 — get these right once, they propagate everywhere.

---

### Phase 2 — Blockchain Abstraction + Core Entity Services
**Deliver:** NGO/Admin/School/Student entity management fully functional

- `BlockchainService` Protocol (`base.py`) + `MockSuiBlockchain` (`mock_sui.py`)
- `activity_service.py` (used by every service from here on)
- `file_service.py` (S3-compatible local disk interface)
- `admin_service.py` — verify/reject/blacklist/restore NGOs + students, platform stats
- `ngo_service.py` — program CRUD, manual student registration (calls `blockchain.create_wallet()`), application review
- `school_service.py` — partner registration, invoice submission
- `student_service.py` — browse programs, apply for scholarship
- All corresponding API routers (`admin.py`, `ngo.py`, `school.py`, `student.py`)

**Checkpoint:** NGO can be verified by admin. NGO can create a program. Student can apply. School can submit invoice.

**Pitfalls to address here:** #7 (activity log before commit), #8 (session sharing), `selectinload` patterns in every service.

---

### Phase 3 — Fund Flow (Donations + Allocations + Invoice Settlement)
**Deliver:** Complete money movement with blockchain tx hashes

- `donor_service.py` — donate with 3 targeting levels (calls `blockchain.donate()`), donation history, fund flow detail view
- NGO fund allocation (calls `blockchain.allocate_funds()`) — updates student wallet balance
- NGO invoice approval (calls `blockchain.settle_invoice()`) — sets `Invoice.tx_hash`
- All fund-flow activity log entries
- `donor.py` router

**Checkpoint:** Donor makes donation → tx_hash recorded. NGO allocates → student wallet balance updated + tx_hash. NGO approves invoice → `Invoice.status='approved'` + tx_hash. Activity feed shows all events.

**Risk:** This phase touches the most concurrent async code (blockchain mock + DB writes). Validate session-per-request pattern carefully.

---

### Phase 4 — Public Endpoints + Seed Script
**Deliver:** Demo-ready: FE can run against real API with no mock data

- `public.py` router — aggregate stats, activity feed, public NGO/program lists (no auth)
- `scripts/seed.py` — idempotent, matches `mock.js` exactly (same IDs, same relationships, `ON CONFLICT DO NOTHING`)
- `.env.example` with all required vars documented
- `contracts/scholarship.move` — syntactically valid Move contract (independent of Python)

**Checkpoint:** `docker-compose up` → `scripts/start.sh` runs migrations + seed → FE connects to `http://localhost:8000` with zero changes → all mock.js data shapes validated against live API responses.

---

### Anti-features (explicitly out of scope for all phases):
- Real pysui SDK calls (mock is a one-file swap — don't touch until v2)
- Celery/Redis task queue (service layer is already async-ready)
- Automated test suite (architecture supports it — next milestone)
- Pagination (add `?page=&limit=` after demo)
- Email notifications, rate limiting, encryption at rest

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack versions | HIGH | All verified via `pip index versions` on 2026-03-09 |
| Features | HIGH | PRD + mock.js + user stories are the source of truth; FE contract is exact |
| Architecture patterns | HIGH | Official FastAPI + SQLAlchemy 2.0 asyncio docs; no speculation |
| Pitfalls | HIGH | All verified against official docs or known CVE/changelog history |
| Blockchain mock design | HIGH | Interface fully specified; mock has no external dependencies |
| Phase sequencing | HIGH | Derived from strict dependency graph in FEATURES.md Level 0–10 |

**Gaps:** None blocking. Two areas to watch:
- `passlib` is unmaintained (last release 2020). Works correctly with pinned bcrypt for v1. Plan to replace with direct `bcrypt` calls in v2.
- `python-jose` has open issues (algorithm confusion attacks). Mitigated by using HS256 with a strong secret key. Evaluate migration to `PyJWT` at v2.

---

## Sources (aggregated)

- **PRD (`prd.md`):** Endpoint list, data models, role definitions — HIGH confidence
- **mock.js (`../edutrack/src/data/mock.js`):** Canonical camelCase field names — HIGH confidence (FE contract)
- **prompt.md + PROJECT.md:** Architecture constraints, coding standards — project source
- **SQLAlchemy 2.0 asyncio docs:** Session lifecycle, MissingGreenlet, selectinload — HIGH
- **Pydantic v2 migration guide + alias docs:** orm_mode rename, Optional behavior, validator deprecation — HIGH
- **FastAPI official docs:** CORS, JWT tutorial, dependencies-with-yield — HIGH
- **Alembic cookbook (asyncio):** Async env.py configuration — HIGH
- **PyPI release history:** All version pins and compatibility notes verified 2026-03-09 — HIGH
- **RFC 7519:** JWT `sub` claim must be string — HIGH
