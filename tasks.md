# EduTrack Backend — Task List

Production-grade code. Demo scope. No shortcuts.

Each task has a clear acceptance criterion ("Done when:"). Do not move to the next task until the current one passes. Tasks are ordered by dependency.

---

## Task 1: Project Scaffolding & Infrastructure

Set up the full project structure so the app runs and is ready for development.

**Deliverables:**
- Full folder structure per `prompt.md` (all `__init__.py` files, empty stubs)
- `requirements.txt`:
  ```
  fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic,
  pydantic[email], pydantic-settings, python-jose[cryptography],
  passlib[bcrypt], python-multipart, aiofiles
  ```
- `app/core/config.py` — Pydantic `BaseSettings` with fields:
  `DATABASE_URL, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES=30, REFRESH_TOKEN_EXPIRE_DAYS=7, UPLOAD_DIR, CORS_ORIGINS`
- `app/main.py` — FastAPI app with:
  - CORS middleware (origins from `config.CORS_ORIGINS`)
  - Global exception handler returning `{detail, code, statusCode}`
  - All routers registered under `/api`
  - `GET /api/health` → `{"status": "ok", "version": "1.0.0"}`
- `Dockerfile` — Python 3.11-slim, non-root user, production-ready
- `docker-compose.yml` — app + PostgreSQL (with healthcheck), named volumes
- `.env.example` — all required vars with safe defaults
- `app/core/exceptions.py` — `NotFoundError`, `ForbiddenError`, `ConflictError`, `ValidationError` exception classes

**Done when:** `docker compose up` starts, `GET /api/health` returns 200, CORS headers present on responses.

---

## Task 2: Database Setup & All Data Models

Configure SQLAlchemy async, Alembic, and implement every data model in one migration.

**Deliverables:**
- `app/core/database.py`:
  - Async engine configured from `config.DATABASE_URL`
  - `AsyncSessionLocal` session factory
  - `Base` declarative base
  - `get_db()` async generator dependency
- Alembic initialized with async template (`env.py` uses `run_async_migrations`)
- SQLAlchemy models for all 11 entities (see `prd.md` Section 3):
  - Use `Enum` types for status fields (not raw strings)
  - Use `JSON` column type for `categories` and `items` arrays
  - All relationships defined (with `lazy="selectin"` or explicit joins — no lazy loading surprises)
  - All models import from a central `app/models/__init__.py`
- Single Alembic migration generating all tables with correct FK constraints and indexes

**Done when:** `alembic upgrade head` runs without errors; all tables visible in PostgreSQL.

---

## Task 3: Pydantic Schemas

Create all request/response schemas with correct camelCase aliases.

**Deliverables:**
- One schema file per entity in `app/schemas/`
- `app/schemas/common.py` — shared types: `ErrorResponse`, `MessageResponse`, paginated list stub
- Every `Response` schema:
  - `model_config = ConfigDict(from_attributes=True, populate_by_name=True)`
  - All fields that differ from snake_case use `Field(alias="camelCaseName")`
  - Must match `mock.js` field names exactly
- Every entity has `Create`, `Update` (partial, all fields optional), and `Response` variants
- `hashed_password` never appears in any response schema
- Manual validation: instantiate each `Response` schema from a dict and confirm aliases serialize correctly

**Done when:** `python -c "from app.schemas import *"` imports without error; a test dict round-trips through each Response schema with correct camelCase output.

---

## Task 4: Authentication System

Full JWT auth with role-based access control.

**Deliverables:**
- `app/core/security.py`:
  - `hash_password(plain: str) -> str` (bcrypt)
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_access_token(data: dict) -> str` (30min expiry)
  - `create_refresh_token(data: dict) -> str` (7d expiry)
  - `decode_token(token: str) -> dict` (raises `401` on invalid/expired)
- `app/core/dependencies.py`:
  - `get_db` — yields `AsyncSession`
  - `get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User`
  - `require_role(*roles: str)` — returns a dependency that raises `403` if user role not in list
- `app/services/auth_service.py`:
  - `register(db, data: RegisterRequest) -> UserResponse` — creates User + role-specific profile row; raises `ConflictError` on duplicate email
  - `login(db, email, password) -> TokenResponse` — raises `401` on bad credentials or inactive user
  - `refresh(db, refresh_token) -> TokenResponse`
  - `get_profile(db, user: User) -> ProfileResponse` — returns user + role-specific data
- Endpoints in `app/api/auth.py`: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me`

**Done when:** full flow works: register as each role → login → get token → call a protected endpoint → get 403 with wrong role.

---

## Task 5: Blockchain Abstraction Layer & Mock Implementation

Implement the blockchain interface and mock before it's needed by other services.

**Deliverables:**
- `app/services/blockchain/base.py`:
  - `WalletResult` dataclass: `wallet_id: str, tx_hash: str`
  - `TxResult` dataclass: `tx_hash: str, object_id: str, status: str`
  - `BlockchainService` as a `Protocol` with all 5 method signatures (see `prd.md` Section 5.1)
- `app/services/blockchain/mock_sui.py` — `MockSuiService(BlockchainService)`:
  - Each method `await asyncio.sleep(uniform(0.1, 0.4))` then returns realistic data
  - `tx_hash = secrets.token_hex(32)` (64-char hex, Sui-style)
  - `object_id = "0x" + secrets.token_hex(16)`
  - Structured log on every call: `logger.info("[BLOCKCHAIN] %s | txHash: %s", method_name, tx_hash)`
  - `get_balance` returns a deterministic float based on wallet_id hash (consistent across calls)
- `app/core/dependencies.py` — `get_blockchain() -> BlockchainService` (returns `MockSuiService()`)
- `contracts/sources/scholarship.move` — complete, syntactically valid Move module with:
  - `ScholarshipWallet` struct, `ProgramEscrow` struct
  - All 5 functions implemented with Move syntax
  - Events emitted on every fund movement
  - Full docblock comments on each function

**Done when:** `python -c "import asyncio; from app.services.blockchain.mock_sui import MockSuiService; asyncio.run(MockSuiService().donate('1','program','2',100))"` prints a log line and returns a TxResult with a 64-char tx_hash; `sui move build` succeeds in `contracts/`.

---

## Task 6: File Upload Service

Production-ready file handling with a storage-agnostic interface.

**Deliverables:**
- `app/services/file_service.py`:
  - `upload_file(db, file: UploadFile, uploader_id: int) -> FileRecord` — saves to `config.UPLOAD_DIR/{uuid}/{original_name}`, creates `FileRecord` in DB
  - `get_file(db, file_id: int) -> tuple[Path, str]` — returns path + mime_type; raises `NotFoundError` if not found
- `app/api/files.py`:
  - `POST /api/files/upload` — requires auth (any role); returns `FileResponse` with `{id, url, filename, mimeType, sizeBytes}`
  - `GET /api/files/{id}` — streams file via `FileResponse`; requires auth
- `UPLOAD_DIR` created on startup if it doesn't exist
- Files stored outside the app container volume (mapped in docker-compose)

**Done when:** upload a PDF via `/api/files/upload`, receive an ID, retrieve it via `/api/files/{id}`, file content is identical.

---

## Task 7: Activity Logging Service

Centralized service used by all other services. Implement before the role APIs.

**Deliverables:**
- `app/services/activity_service.py`:
  - `log(db: AsyncSession, type: ActivityType, text: str, actor_id: int) -> ActivityLog`
  - `get_feed(db, limit: int = 20) -> list[ActivityFeedItem]`
  - `ActivityFeedItem` — `{type, color, text, time}` where `time` is relative ("2 hours ago", "1 day ago", "just now")
  - Color map: `{"donation": "blue", "invoice": "green", "verify": "purple", "allocation": "yellow", "program": "indigo", "blacklist": "red"}`
  - Relative time computed at read time (not stored)
- Used by all services that perform significant actions

**Done when:** calling `log()` creates an `ActivityLog` row; calling `get_feed()` returns correctly formatted entries with relative timestamps.

---

## Task 8: Admin APIs

System admin dashboard and NGO/student management.

**Deliverables:**
- `app/services/admin_service.py` with functions for each operation
- All endpoints require `require_role("admin")`
- `GET /api/admin/dashboard` — returns aggregated stats:
  - NGO counts by status, total schools, students, programs
  - `totalDonations` (sum of all donation amounts), `fundsAllocated` (sum of allocations), `fundsUtilized` (sum of approved invoices)
  - Response shape matches `platformStats` from `mock.js`
- `GET /api/admin/ngos?status=` — list with optional status filter; response matches `ngos[]` shape
- `PATCH /api/admin/ngos/{id}/verify|reject|blacklist|restore` — updates status; logs to ActivityLog; raises `404` if not found, `409` if transition is invalid (e.g., restoring a non-blacklisted NGO)
- `PATCH /api/admin/students/{id}/blacklist|restore` — same pattern
- `GET /api/admin/blacklist` — combined list `{ngos: [], students: []}` filtered to blacklisted status

**Done when:** admin can verify an NGO, blacklist a student, and view the combined blacklist; all actions appear in the activity log.

---

## Task 9: NGO APIs

Full NGO workflow — programs, students, applications, invoices, allocations.

**Deliverables:**
- All endpoints require `require_role("ngo")`; NGO can only access their own data (raise `403` on cross-NGO access attempts)
- `app/services/ngo_service.py` with functions for each operation
- **Dashboard**: `GET /api/ngo/dashboard` — NGO-scoped stats (own programs, students, pending invoices, funds allocated)
- **Programs**: Full CRUD — `POST/GET /api/ngo/programs`, `GET/PUT /api/ngo/programs/{id}`
  - On create: set `status=active`, `allocated=0`, `students_enrolled=0`; increment `ngo.programs_count`; log activity
- **Students**: `POST/GET /api/ngo/students`, `GET /api/ngo/students/{id}`
  - On register: auto-generate `scholarship_id = f"EDU-{year}-{seq:05d}"` (atomic sequence per NGO-year); call `blockchain.create_wallet()`; store `wallet_id` and `tx_hash`; increment `program.students_enrolled` and `ngo.students_helped`
- **Applications**: `GET /api/ngo/applications`, `PATCH /{id}/accept|reject`
  - On accept: run the full student registration logic (same as `POST /api/ngo/students`) using application data; update application status
  - On reject: update status, optional reason stored; log activity
- **Invoices**: `GET /api/ngo/invoices`, `PATCH /{id}/approve|reject`
  - On approve: set `approved_date=now`; call `blockchain.settle_invoice()`; store `tx_hash` on invoice; update `school.total_invoiced`; log activity
- **Allocations**: `POST /api/ngo/allocations`, `GET /api/ngo/allocations`
  - On create: call `blockchain.allocate_funds()`; update `student.wallet_balance`, `student.total_received`, `program.allocated`; store `tx_hash`; log activity

**Done when:** NGO registers a student (gets scholarship ID + blockchain wallet reference), allocates funds (student wallet balance updates, tx_hash present), approves an invoice (tx_hash present, school total_invoiced updated).

---

## Task 10: Donor, School & Student APIs

**Donor:**
- `GET /api/donor/browse/ngos|programs|students` — verified/active entities; no auth required on browse (check `prd.md`)
- `POST /api/donor/donate` — body: `{ngoId, programId?, studentId?, amount, type, name, email, message?}`
  - Creates `Donor` record if email not seen before; updates `total_donated` + `donations_count` on existing
  - Calls `blockchain.donate()`; stores `tx_hash`; updates `ngo.total_funded`; logs activity
- `GET /api/donor/donations` and `GET /api/donor/donations/{id}` — own history with program/NGO names; response matches `donations[]` shape

**School** (requires `require_role("school")`):
- `POST /api/schools/register` — creates School linked to User; status defaults to `pending`
- `GET /api/schools/profile` — own profile matching `schools[]` shape
- `POST /api/schools/invoices` — body: `{ngoId, programId, category, items[{desc, amount}]}`; `amount` auto-summed from items; status defaults to `pending`
- `GET /api/schools/invoices` — own invoices with status

**Student** (requires `require_role("student")`):
- `GET /api/student/programs` — active programs with `spotsRemaining` computed field
- `POST /api/student/apply` — creates `ScholarshipApplication`; status `pending`; logs activity
- `GET /api/student/applications` — own applications with status

**Done when:** donor makes a donation with a tx_hash in response; school submits invoice with line items; student applies and sees `pending` status.

---

## Task 11: Public APIs

Unauthenticated transparency dashboard.

**Deliverables:**
- No auth required on any of these endpoints
- `GET /api/public/stats` — aggregate counts matching `platformStats` from `mock.js`
- `GET /api/public/activity` — last 20 activity log entries via `activity_service.get_feed()`; response: `[{type, color, text, time}]`
- `GET /api/public/ngos` — verified NGOs with public-safe fields (no tax_doc paths, no internal IDs)
- `GET /api/public/programs` — active programs with public-safe fields

**Done when:** all 4 endpoints return correct shapes with no auth token; activity feed shows relative times.

---

## Task 12: Seed Script, Move Contract & README

**Seed Script (`scripts/seed.py`):**
- Idempotent (checks for existing data before inserting; safe to re-run)
- Inserts exactly: 5 NGOs, 5 programs, 5 students, 5 donors, 7 donations, 4 invoices, 4 schools, 8 activity log entries
- All IDs, field values, and relationships must match `mock.js` exactly
- Creates one admin user: `admin@edutrack.org` / `admin123` (configurable via env)
- Creates one user account per NGO/school/donor/student for demo login
- Runs migrations before seeding (`alembic upgrade head` inside script)

**Move Contract (`contracts/sources/scholarship.move`):**
- Syntactically valid Move module (`sui move build` passes)
- `ScholarshipWallet` and `ProgramEscrow` structs fully defined
- All 5 functions implemented: `create_wallet`, `donate`, `allocate_funds`, `settle_invoice`, `get_balance`
- Events emitted on every state change
- Full NatSpec-style doc comments on each function explaining on-chain semantics

**README (`README.md`):**
- Prerequisites (Docker, Python 3.11, Sui CLI optional)
- Quick start: `docker compose up` → `python scripts/seed.py` → frontend connects
- Environment variable reference
- How to swap mock blockchain for real Sui SDK (one-paragraph guide)
- API docs: link to `/docs` (FastAPI auto-generated Swagger)

**Done when:** `python scripts/seed.py` runs cleanly; `GET /api/public/stats` returns values matching seeded data; `sui move build` passes in `contracts/`; README is accurate.
