# Phase 1: Foundation - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

A running FastAPI + PostgreSQL application in Docker with working JWT authentication, RBAC skeleton, blockchain abstraction layer, and all 11 ORM models defined — the bedrock every other phase builds on.

**Delivers:**
- Project scaffolded per `prompt.md` directory structure (all `__init__.py` stubs, empty handlers, requirements.txt)
- Async SQLAlchemy engine + sessionmaker + Alembic async migrations (all tables in one migration)
- All 11 ORM models: User, NGO, Program, Student, Donor, Donation, Invoice, School, ScholarshipApplication, ActivityLog, FileRecord
- `app/core/config.py` (Pydantic BaseSettings), `app/core/exceptions.py` (typed errors + global handler)
- JWT auth endpoints: register, login, refresh, logout, me
- `require_role()` RBAC dependency (guard only — ownership scoping is Phase 2)
- `BlockchainService` Protocol + MockSuiBlockchain adapter injected via `Depends(get_blockchain)`
- Docker Compose (app + PostgreSQL) — `docker compose up` → `GET /healthz` 200

**Out of scope for this phase:**
- Any business entity endpoints (NGO CRUD, programs, students, etc.) — Phase 2
- Activity logging on actions — Phase 2 (writer must exist when services are built)
- File upload/download — Phase 2
- Invoice/donation/blockchain tx workflows — Phase 3
- Seed script, public endpoints, Move contract — Phase 4

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- Follow `prompt.md` directory structure exactly — no deviations
- All `app/api/*.py` files created as stubs (empty routers registered) so import tree is valid from day one
- `requirements.txt` pins: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic[email]`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`, `aiofiles`
- `bcrypt` pinned to `>=4.1.2,<5.0.0` — 4.1.0 yanked, ≥5.0.0 breaks passlib

### Database & Migrations
- Alembic initialized with `--template async` — mandatory (sync env.py + asyncpg deadlocks)
- `env.py` uses `run_async_migrations()` pattern
- `async_sessionmaker(expire_on_commit=False)` — prevents MissingGreenlet on post-commit attribute access
- All 11 tables in a single initial Alembic migration
- `Enum` types for all status fields (not raw strings) — e.g., `ngo_status`, `program_status`, `student_status`, `invoice_status`, `application_status`
- `JSON` column type for array fields: `Program.categories`, `Invoice.items`
- All relationships loaded eagerly — `lazy="selectin"` for one-to-many on models that need it; `lazy="joined"` for many-to-one; no default lazy loading
- Indexes on all FK columns and frequently-queried fields (e.g., `User.email`, `Student.scholarship_id`)

### Authentication
- JWT access token: 30-minute expiry, `sub` claim = `str(user.id)`
- JWT refresh token: 7-day expiry, stored in DB `RefreshToken` table with `used: bool` flag
- Refresh token invalidation: set `used=True` on use; reject any token where `used=True` (prevents race-condition reuse)
- Logout: `POST /api/auth/logout` sets `used=True` on the submitted refresh token
- Password hashing: `passlib[bcrypt]` with async wrapper (no sync `bcrypt.hashpw` calls in async context)
- `decode_token()` raises HTTP 401 on invalid/expired — never returns None silently
- JWT `sub` decoded back as `int(payload["sub"])` for DB lookup

### RBAC Guard Design
- `require_role(*roles: str)` returns a FastAPI dependency factory
- The dependency calls `get_current_user()` internally, then checks `user.role in roles`; raises HTTP 403 if not
- Returns the `User` object (not role-specific model) — ownership scoping (returning NGO, not User) is Phase 2 service-layer responsibility
- `get_current_user()` is a separate dependency used by `require_role` internally and exposed directly for endpoints that need "any authenticated user"
- Phase 1 only needs the guard to work correctly; the role-specific profile join (returning NGO vs Donor data) is implemented in `auth_service.get_profile()`

### Auth /me Profile Response
- `GET /api/auth/me` returns a merged flat object — user fields + role-specific profile fields combined
- Shape matches `mock.js` exactly: `{id, email, role, name, ...roleSpecificFields}` — no nested `{user, profile}` envelope
- `auth_service.get_profile()` fetches the role-specific model (NGO, Donor, School, Student) and merges into the response schema
- Admin has no separate profile model — `me` returns just User fields for admin role

### Error Handling
- Global exception handler in `app/main.py` catches all unhandled exceptions
- All errors return `{"detail": "...", "code": "ERROR_CODE", "statusCode": 4xx/5xx}` — no raw stack traces
- Custom exception classes: `NotFoundError(model, id)`, `ForbiddenError(message)`, `ConflictError(field, value)`, `ValidationError(message)`
- HTTP 422 (Pydantic validation errors) also converted to the standard error envelope

### Blockchain Abstraction
- `BlockchainService` Protocol in `app/services/blockchain/base.py` with methods:
  - `create_wallet(student_id: int) -> WalletResult`
  - `donate(donor_id, recipient_id, amount) -> TxResult`
  - `allocate_funds(ngo_id, student_id, amount) -> TxResult`
  - `settle_invoice(ngo_id, school_id, invoice_id, amount) -> TxResult`
  - `get_balance(wallet_address: str) -> Decimal`
- `MockSuiBlockchain` in `app/services/blockchain/mock_sui.py`:
  - `await asyncio.sleep(random.uniform(0.1, 0.4))` simulates network latency
  - `tx_hash = secrets.token_hex(32)` → 64-char hex string
  - `wallet_address = secrets.token_hex(16)` → 32-char mock wallet address
  - All methods log structured output via `logger.info()`
- Injected via `get_blockchain()` in `dependencies.py` — `MockSuiBlockchain` is the bound implementation; never imported directly in callers

### CORS & Middleware
- CORS: `allow_origins=["http://localhost:3000", "http://localhost:5173"]` — explicit, no wildcard (wildcard + credentials is browser-rejected)
- `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`

### Docker
- `Dockerfile`: Python 3.11-slim base, non-root user, production-ready (no dev deps in image)
- `docker-compose.yml`: app + PostgreSQL services, PostgreSQL healthcheck, named volumes for data persistence
- App container waits for PostgreSQL healthcheck to pass before starting

### Base Response Schema Pattern
- All response schemas inherit from a `BaseResponse` with `model_config = ConfigDict(from_attributes=True, populate_by_name=True)`
- This is the critical fix for silent ORM mode failure — explicitly required on every response schema
- All snake_case DB fields aliased to camelCase via `Field(alias="camelCaseName")`

### Claude's Discretion
- Exact Alembic migration file naming and structure
- Exact `logger` configuration (stdlib logging vs structlog — either works)
- Health endpoint response body shape (beyond `{"status": "ok", "version": "1.0.0"}`)
- RefreshToken model column names (as long as `used: bool` flag exists)
- Exact `token_hex` length for wallet address mock (just needs to look realistic)
- Whether to use `asyncio.gather` or sequential awaits in `get_profile()` for fetching role-specific data

</decisions>

<specifics>
## Specific Ideas

- `tasks.md` is the authoritative task order — implementation should follow Tasks 1 → 2 → 3 → 4 in sequence
- `prompt.md` defines the exact directory structure and coding standards — every file path and class name is specified there
- `prd.md` Section 3 defines all 11 data models with their exact fields — use as reference for ORM model columns
- `../edutrack/src/data/mock.js` is the contract for camelCase field names — researcher should verify exact field names before writing schemas (Phase 2 concern, but models should be named consistently)
- The grant demo is March 2026 (UNICEF Venture Fund, $100K equity-free) — production-grade standards required, not just "demo quality"
- Activity log writer (`activity_service.log()`) must exist as a stub in Phase 1 so Phase 2 services can call it — even if the writer is a no-op placeholder initially

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `contracts/` directory exists — Move contract goes in `contracts/sources/scholarship.move` (Phase 4 concern, directory already there)
- `uploads/` directory exists — file storage target already created
- `prd.md` — complete data model spec (Section 3); all field names defined
- `tasks.md` — ordered task breakdown with acceptance criteria; use as implementation checklist
- `prompt.md` — exact directory structure, coding standards, example patterns for routes/services/schemas

### Established Patterns
- **Route handler pattern:** `async def handler(data: Schema, user = Depends(require_role("ngo")), db = Depends(get_db), blockchain = Depends(get_blockchain)) -> ResponseSchema` — one service call, return result
- **Service pattern:** fetch → validate → mutate → commit → activity log → return Pydantic model (not dict)
- **Schema pattern:** `model_config = ConfigDict(from_attributes=True, populate_by_name=True)` on every response schema
- **Error pattern:** raise typed `NotFoundError` / `ForbiddenError` / `ConflictError` — global handler converts to `{detail, code, statusCode}`

### Integration Points
- `app/main.py` — all routers registered under `/api` prefix; global exception handler registered here
- `app/core/dependencies.py` — central DI hub; every Phase 2+ route handler imports from here
- `app/models/__init__.py` — all models imported here so Alembic autodiscovers them; Phase 2 models must be added to this file
- `alembic/env.py` — imports `Base` from `app/core/database.py` and `app.models` to discover all mapped classes

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. All Phase 1 requirements are clearly specified in existing docs.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-09*
