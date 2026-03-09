# Architecture Research: EduTrack Backend

**Domain:** Multi-role scholarship platform REST API with blockchain abstraction
**Researched:** 2026-03-09
**Confidence:** HIGH — based on official FastAPI docs, SQLAlchemy 2.0 asyncio docs, and project-specific PRD/prompt analysis

---

## Component Map

### Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│  External Consumers                                         │
│  ┌──────────────────┐     ┌──────────────────────────────┐  │
│  │  EduTrack FE     │     │  Public / Unauthenticated    │  │
│  │  (read-only)     │     │  Clients                     │  │
│  └────────┬─────────┘     └──────────────┬───────────────┘  │
└───────────┼──────────────────────────────┼───────────────────┘
            │  HTTP (camelCase JSON)        │
┌───────────▼──────────────────────────────▼───────────────────┐
│  API Layer  (app/api/)                                       │
│  ┌────────┐ ┌───────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │auth.py │ │admin  │ │ngo.py  │ │donor │ │school│ │public│ │
│  │        │ │.py    │ │        │ │.py   │ │.py   │ │.py   │ │
│  └────────┘ └───────┘ └────────┘ └──────┘ └──────┘ └──────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  student.py    files.py                                  │ │
│  └──────────────────────────────────────────────────────────┘ │
│  Rule: handlers call ONE service method, return its result   │
└───────────────────────────┬──────────────────────────────────┘
                            │  typed function calls
┌───────────────────────────▼──────────────────────────────────┐
│  Core (app/core/)                                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ dependencies.py                                         │ │
│  │   get_db() → AsyncSession (yield pattern)               │ │
│  │   get_current_user() → User (JWT decode + DB lookup)    │ │
│  │   require_role(role) → User (guard, raises 403)         │ │
│  │   get_blockchain() → BlockchainService (Protocol)       │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌──────────┐ ┌────────────┐ ┌─────────────┐ ┌────────────┐  │
│  │config.py │ │database.py │ │security.py  │ │exceptions  │  │
│  │(Settings)│ │(engine,    │ │(JWT create/ │ │.py (typed  │  │
│  │          │ │sessionmaker│ │verify,      │ │errors +    │  │
│  │          │ │Base)       │ │bcrypt)      │ │handler)    │  │
│  └──────────┘ └────────────┘ └─────────────┘ └────────────┘  │
└───────────────────────────┬──────────────────────────────────┘
                            │  injected via Depends()
┌───────────────────────────▼──────────────────────────────────┐
│  Service Layer  (app/services/)                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│  │ auth_service │ │ admin_service│ │ ngo_service          │  │
│  └──────────────┘ └──────────────┘ └──────────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│  │donor_service │ │school_service│ │ student_service      │  │
│  └──────────────┘ └──────────────┘ └──────────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐                           │
│  │activity_svc  │ │ file_service │                           │
│  └──────────────┘ └──────────────┘                           │
│                                                              │
│  Services own: DB writes, stat updates, activity logs,       │
│  blockchain calls. Services are independently testable.      │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  blockchain/  (port-and-adapter)                        │ │
│  │  ┌───────────────────┐  ┌──────────────────────────┐   │ │
│  │  │ base.py           │  │ mock_sui.py              │   │ │
│  │  │ BlockchainService │  │ MockSuiBlockchain        │   │ │
│  │  │ Protocol          │  │ (swap ↔ SuiBlockchain)   │   │ │
│  │  └───────────────────┘  └──────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────┬───────────────────────────────┬───────────────────┘
           │ await db.*()                  │ await blockchain.*()
┌──────────▼────────────┐    ┌─────────────▼──────────────────┐
│  Data Layer           │    │  External Adapter Layer        │
│  (app/models/)        │    │                                │
│  ┌──────────────────┐ │    │  Mock: asyncio.sleep(0.1-0.4)  │
│  │ user, ngo,       │ │    │        secrets.token_hex(32)   │
│  │ program, student,│ │    │        → 64-char tx hash       │
│  │ donor, donation, │ │    │                                │
│  │ invoice, school, │ │    │  Real (future):                │
│  │ application,     │ │    │  pysui → Sui testnet/mainnet   │
│  │ activity_log,    │ │    │  (one-file swap in deps.py)    │
│  │ file_record      │ │    │                                │
│  └──────────────────┘ │    └────────────────────────────────┘
│                       │
│  PostgreSQL            │
│  (asyncpg driver)      │
│  Alembic migrations    │
└───────────────────────┘
```

### Component Responsibility Table

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `app/main.py` | FastAPI app init, CORS, router inclusion, lifespan, global exception handler | All routers |
| `app/api/*.py` | Route handlers — parse request, call one service, return schema | Service layer via direct call |
| `app/core/config.py` | Pydantic BaseSettings; loads `.env`; single source of truth for all config | All modules that need config |
| `app/core/database.py` | `AsyncEngine`, `async_sessionmaker`, `Base` declarative base | Services (via DI), Alembic |
| `app/core/security.py` | JWT create/verify (python-jose), bcrypt hash/verify (passlib) | `auth_service`, `dependencies.py` |
| `app/core/dependencies.py` | `get_db`, `get_current_user`, `require_role`, `get_blockchain` — all DI factories | Every route handler |
| `app/core/exceptions.py` | `NotFoundError`, `ForbiddenError`, `ConflictError`, global handler | Services (raise), `main.py` (register) |
| `app/models/*.py` | SQLAlchemy ORM models, snake_case columns, FK relationships | Services (read/write), Alembic |
| `app/schemas/*.py` | Pydantic v2 models with camelCase aliases, `from_attributes=True` | Route handlers (validate in/out) |
| `app/services/*.py` | All business logic: DB writes, stat updates, activity logs, blockchain calls | DB (AsyncSession), blockchain port |
| `app/services/blockchain/base.py` | `BlockchainService` Protocol — the port definition | Services (call), `dependencies.py` (bind) |
| `app/services/blockchain/mock_sui.py` | Mock adapter — realistic tx hashes, simulated latency | Only called via Protocol |
| `app/services/activity_service.py` | Write `ActivityLog` rows on every significant action | Called from every other service |
| `app/services/file_service.py` | Save/retrieve files with local disk + S3-compatible interface | Called from upload/download handlers |
| `alembic/` | Schema migrations; async-configured `env.py` | `database.py` (engine import) |
| `scripts/seed.py` | Idempotent seed matching `mock.js` exactly | DB (direct AsyncSession) |
| `contracts/sources/scholarship.move` | Sui Move smart contract — syntactically valid, deployable | Independent (not called by Python) |

---

## Data Flow

### Standard Authenticated Request (e.g., NGO creates a program)

```
HTTP POST /api/ngo/programs
Authorization: Bearer <access_token>
Body: { "name": "...", "totalBudget": 50000, ... }

  │
  ▼
[FastAPI router: app/api/ngo.py]
  │  1. Deserialize body via ProgramCreate schema (camelCase → snake_case)
  │  2. FastAPI resolves Depends():
  │     a. get_db()         → opens AsyncSession, yields it
  │     b. require_role("ngo") → get_current_user() → JWT decode
  │                             → db.get(User, user_id)
  │                             → verify role == "ngo"
  │                             → returns NGO object
  │     c. get_blockchain() → returns MockSuiBlockchain instance
  │  3. Handler calls:
  │     return await ngo_service.create_program(db, blockchain, ngo.id, data)
  │
  ▼
[Service: app/services/ngo_service.py]
  │  1. await db.get(NGO, ngo_id)           # fetch NGO
  │  2. Validate business rules             # e.g., NGO is verified
  │  3. program = Program(**data.model_dump())
  │  4. db.add(program)
  │  5. ngo.programs_count += 1            # stat update in same transaction
  │  6. await db.commit()
  │  7. await db.refresh(program)
  │  8. await activity_service.log(db, "program", "...", ngo.user_id)
  │  9. return ProgramResponse.model_validate(program)  # ORM → camelCase
  │
  ▼
[Async DB (asyncpg → PostgreSQL)]
  │  All awaitable: db.get(), db.execute(), db.commit(), db.refresh()
  │  Single session per request (no cross-request state)
  │
  ▼
[FastAPI serializes ProgramResponse → camelCase JSON]
  │  response_model=ProgramResponse triggers model_validate
  │  populate_by_name=True allows both snake and alias field access
  │
  ▼
HTTP 201 { "id": 1, "ngoId": 3, "name": "...", "totalBudget": 50000, ... }
```

### Blockchain-Triggering Request (e.g., NGO approves invoice)

```
HTTP PATCH /api/ngo/invoices/{id}/approve

  ▼
[Handler: ngo.py] calls ngo_service.approve_invoice(db, blockchain, invoice_id)

  ▼
[Service: ngo_service.py]
  │  1. Fetch invoice, verify status == "pending"
  │  2. await blockchain.settle_invoice(ngo_id, school_id, invoice_id, amount)
  │     │
  │     ▼
  │  [Port: BlockchainService Protocol]
  │     │
  │     ▼
  │  [Adapter: MockSuiBlockchain.settle_invoice()]
  │     │  await asyncio.sleep(0.1–0.4)    # simulates network
  │     │  tx_hash = secrets.token_hex(32) # 64-char hex
  │     │  logger.info("settle_invoice: %s", tx_hash)
  │     │  return TxResult(tx_hash=tx_hash, success=True)
  │     │
  │  3. invoice.tx_hash = result.tx_hash   # write blockchain ref to DB
  │  4. invoice.status = "approved"
  │  5. invoice.approved_date = datetime.utcnow()
  │  6. await db.commit()
  │  7. await activity_service.log(db, "invoice", "Invoice approved", ...)
  │  8. return InvoiceResponse.model_validate(invoice)
```

### JWT Authentication Flow

```
POST /api/auth/login { email, password }

  ▼
[auth_service.login()]
  │  1. SELECT user WHERE email = ?           (async DB query)
  │  2. passlib.verify(password, user.hashed_password)
  │  3. create_access_token({"sub": user.id}) → 30min JWT
  │  4. create_refresh_token({"sub": user.id}) → 7d JWT
  │  5. return { accessToken, refreshToken, user }

Subsequent requests:
  Authorization: Bearer <access_token>
  │
  ▼
[get_current_user() dependency in dependencies.py]
  │  1. python-jose: jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
  │  2. Extract user_id from payload["sub"]
  │  3. await db.get(User, user_id)
  │  4. if not user.is_active → raise 401
  │  5. return user

[require_role("ngo") dependency]
  │  1. current_user = await get_current_user(token, db)
  │  2. if current_user.role != "ngo" → raise ForbiddenError (403)
  │  3. Fetch role-specific profile (NGO, Donor, etc.)
  │  4. return profile object (typed)
```

### Async Session Lifecycle (per-request)

```
Request arrives
  │
  ▼
FastAPI resolves Depends(get_db)
  │
  ▼
get_db() generator:
  async with async_sessionmaker() as session:
      yield session          ← injected into handler + services
  # session.close() called automatically in finally block
  # happens AFTER response is sent (scope="request" default)

Key invariants:
  - ONE session per request (no sharing across concurrent requests)
  - All DB calls within that session are awaitable (no sync blocking)
  - commit() inside service methods (not in handlers)
  - rollback() on exception (SQLAlchemy default on session close without commit)
```

---

## Recommended Build Order

Build order follows strict dependency resolution — lower layers must exist before higher layers can use them.

### Phase 1: Infrastructure Foundation
**Must be built first. Everything else depends on this.**

```
1. app/core/config.py          ← Pydantic BaseSettings; needed by database.py
2. app/core/database.py        ← AsyncEngine, sessionmaker, Base; needed by models
3. app/core/exceptions.py      ← Custom exception classes; needed by services
4. app/core/security.py        ← JWT + bcrypt helpers; needed by auth_service
5. app/models/__init__.py      ← Import all models; needed by Alembic
6. app/models/user.py          ← User model; FK target for most others
7. app/models/ngo.py           ← NGO model; FK target for program, student, etc.
8. app/models/[rest].py        ← All remaining models (order: program→student→donor
                                  →donation→school→invoice→application→activity_log
                                  →file_record)
9. alembic/env.py              ← Async-configured; import all models; generate migration
10. alembic/versions/001_*.py  ← First migration; run to verify DB schema
```

### Phase 2: Core DI and Auth
**Security and session injection — all routes depend on this.**

```
11. app/core/dependencies.py   ← get_db, get_current_user, require_role, get_blockchain
12. app/schemas/auth.py        ← LoginRequest, TokenResponse, UserResponse
13. app/schemas/common.py      ← ErrorResponse, shared types
14. app/services/blockchain/base.py     ← BlockchainService Protocol
15. app/services/blockchain/mock_sui.py ← Mock adapter (WalletResult, TxResult)
16. app/services/auth_service.py        ← register, login, refresh, logout, me
17. app/api/auth.py                     ← Auth routes wired to auth_service
18. app/main.py                         ← App init, CORS, include auth router, global handler
```
> **Checkpoint:** `POST /api/auth/login` returns JWT. `GET /api/auth/me` returns user.

### Phase 3: Schemas and Remaining Services
**Build schemas before services; services before routes.**

```
19. app/schemas/[all remaining].py  ← ngo, program, student, donor, donation,
                                       invoice, school, application
    Order within: Create → Update → Response variants
    Key: every Response schema has from_attributes=True + camelCase Field aliases

20. app/services/activity_service.py  ← log() helper; called by every other service
21. app/services/file_service.py      ← save/retrieve with S3-compatible interface

22. app/services/admin_service.py     ← verify/reject/blacklist NGOs, students, stats
23. app/services/ngo_service.py       ← programs, students, applications, invoices,
                                          allocations (calls blockchain)
24. app/services/donor_service.py     ← browse, donate (calls blockchain)
25. app/services/school_service.py    ← register, invoices
26. app/services/student_service.py   ← browse programs, apply
```

### Phase 4: API Routes
**One router per role. Build in dependency order.**

```
27. app/api/public.py    ← No auth; stats, activity feed, public NGOs/programs
28. app/api/admin.py     ← require_role("admin"); NGO mgmt, blacklist, dashboard
29. app/api/ngo.py       ← require_role("ngo"); programs, students, invoices, alloc
30. app/api/donor.py     ← require_role("donor"); browse, donate, history
31. app/api/school.py    ← require_role("school"); register, invoices
32. app/api/student.py   ← require_role("student"); browse, apply, status
33. app/api/files.py     ← Authenticated; upload/download file records
34. app/main.py update   ← Include all routers with /api prefix
```
> **Checkpoint:** All ~40 endpoints return correct camelCase shapes matching mock.js.

### Phase 5: Operational Tooling
**After API is functional.**

```
35. scripts/seed.py          ← Idempotent seed; identical to mock.js data + same IDs
36. Dockerfile               ← Python 3.11-slim, copy app, pip install, expose 8000
37. docker-compose.yml       ← app service + postgres service; shared network
38. scripts/start.sh         ← alembic upgrade head && python scripts/seed.py && uvicorn
39. .env.example             ← All required vars documented
40. contracts/scholarship.move ← Move contract (independent of Python build)
```

### Dependency Graph (Critical Path)

```
config.py
  └→ database.py
       └→ models/
            └→ alembic migration
            └→ schemas/
                 └→ services/
                      └→ api/
                           └→ main.py (complete)

security.py ──→ auth_service ──→ api/auth.py
                                        │
dependencies.py ←──────────────────────┘
  (uses security.py + database.py)
  └→ all route handlers

blockchain/base.py + mock_sui.py ──→ dependencies.py (get_blockchain)
                                      └→ ngo_service, donor_service

activity_service ──→ all other services (imported, not injected via DI)
```

---

## Key Patterns

### 1. Async Session via `Depends(get_db)`

**The canonical pattern for FastAPI + SQLAlchemy async (HIGH confidence — official docs):**

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# app/core/dependencies.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # close() called automatically by async context manager
```

**Critical async rules:**
- `expire_on_commit=False` — prevents SQLAlchemy from expiring attributes after commit, which would trigger implicit lazy-loads (forbidden in async context)
- Every attribute access on an ORM object after `commit()` must be prefetched with `await db.refresh(obj)` or loaded via `selectinload()` in the original query
- `lazy="raise"` on relationships during development catches implicit I/O early
- Never use `db.execute()` in a `sync def` — causes event loop deadlock

```python
# In services: correct async query pattern
result = await db.execute(
    select(NGO)
    .where(NGO.status == "verified")
    .options(selectinload(NGO.programs))  # explicit eager load
)
ngos = result.scalars().all()
```

### 2. Port-and-Adapter Blockchain Abstraction

**The port-and-adapter (hexagonal architecture) pattern applied to blockchain:**

```
"Port" = the interface callers depend on
"Adapter" = the implementation that satisfies the port

Port:    app/services/blockchain/base.py  (BlockchainService Protocol)
Adapter: app/services/blockchain/mock_sui.py  (MockSuiBlockchain)
Future:  app/services/blockchain/sui.py   (SuiBlockchainService)

Binding: app/core/dependencies.py
         def get_blockchain() -> BlockchainService:
             return MockSuiBlockchain()
         # Swap: return SuiBlockchainService(settings.SUI_RPC_URL)
```

```python
# app/services/blockchain/base.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class TxResult:
    tx_hash: str
    success: bool

@dataclass
class WalletResult:
    wallet_address: str
    tx_hash: str

class BlockchainService(Protocol):
    async def create_wallet(self, student_id: str) -> WalletResult: ...
    async def donate(self, donor_id: str, target_type: str, target_id: str, amount: float) -> TxResult: ...
    async def allocate_funds(self, ngo_id: str, program_id: str, student_id: str, amount: float) -> TxResult: ...
    async def settle_invoice(self, ngo_id: str, school_id: str, invoice_id: str, amount: float) -> TxResult: ...
    async def get_balance(self, wallet_id: str) -> float: ...
```

**Why Protocol (not ABC):** Python `typing.Protocol` enables structural subtyping — the mock and real implementation don't inherit from the same class; they just satisfy the same interface. This makes testing easier (any object with the right `async def` methods works).

**Swap procedure (one-line change):**
```python
# dependencies.py — current
def get_blockchain() -> BlockchainService:
    return MockSuiBlockchain()

# dependencies.py — production swap
def get_blockchain() -> BlockchainService:
    return SuiBlockchainService(rpc_url=settings.SUI_RPC_URL, wallet_key=settings.SUI_WALLET_KEY)
```
Zero other changes. All callers continue calling `blockchain.donate(...)` unchanged.

### 3. RBAC via Dependency Injection

**Two-level dependency chain: token decode → role check:**

```python
# app/core/dependencies.py

# Level 1: decode JWT, return any authenticated user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: int = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive or not found")
    return user

# Level 2: enforce role, return role-specific profile
def require_role(role: str):
    async def _require(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:  # returns User or role-specific model
        if current_user.role != role:
            raise ForbiddenError(f"Requires role: {role}")
        return current_user
    return _require

# Usage in route handler (note: db injected separately for service use)
@router.post("/programs", response_model=ProgramResponse, status_code=201)
async def create_program(
    data: ProgramCreate,
    current_ngo: User = Depends(require_role("ngo")),
    db: AsyncSession = Depends(get_db),
    blockchain: BlockchainService = Depends(get_blockchain),
) -> ProgramResponse:
    return await ngo_service.create_program(db, blockchain, current_ngo.id, data)
```

**RBAC enforcement points:**
- `require_role("admin")` → admin router
- `require_role("ngo")` → ngo router
- `require_role("donor")` → donor router
- `require_role("school")` → school router
- `require_role("student")` → student router
- `get_current_user()` only (no role check) → `GET /api/auth/me`, `POST /api/files/upload`
- No auth dependency → public router

**Resource scoping:** Services additionally scope by owner ID. Example: `ngo_service.list_students()` filters `WHERE student.ngo_id = current_ngo.ngo_profile.id` — role check alone is insufficient for multi-tenant data isolation.

### 4. Pydantic v2 camelCase Alias Pattern

**The FE contract enforcement mechanism:**

```python
# app/schemas/ngo.py
from pydantic import BaseModel, ConfigDict, Field

class NGOResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    name: str
    location: str
    status: str
    description: str | None = None
    tax_doc: str | None = Field(default=None, alias="taxDoc")
    reg_doc: str | None = Field(default=None, alias="regDoc")
    avatar: str | None = None
    color: str | None = None
    total_funded: float = Field(alias="totalFunded")
    students_helped: int = Field(alias="studentsHelped")
    programs_count: int = Field(alias="programsCount")
    registered_date: datetime = Field(alias="registeredDate")
```

**Serialization configuration in main.py:**
```python
app = FastAPI()
# Ensure aliases are used in all responses:
# Either set response_model_by_alias=True globally or use model_config
```

**Note:** `populate_by_name=True` allows internal code to use snake_case names while external responses use camelCase aliases. Both `ngo.total_funded` and `ngo.totalFunded` are valid in Python code; only camelCase goes to the wire.

### 5. Global Error Handler

**Consistent `{detail, code, statusCode}` for all errors:**

```python
# app/core/exceptions.py
class AppError(HTTPException):
    def __init__(self, status_code: int, detail: str, code: str):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code

class NotFoundError(AppError):
    def __init__(self, resource: str, id: Any):
        super().__init__(404, f"{resource} with id {id} not found", "NOT_FOUND")

class ForbiddenError(AppError):
    def __init__(self, reason: str = "Insufficient permissions"):
        super().__init__(403, reason, "FORBIDDEN")

class ConflictError(AppError):
    def __init__(self, detail: str):
        super().__init__(409, detail, "CONFLICT")

# app/main.py
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code, "statusCode": exc.status_code}
    )

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR", "statusCode": 500}
    )
```

### 6. Service-Scoped Activity Logging

**Activity log written inside service methods (not handlers), using the same open session:**

```python
# app/services/activity_service.py
async def log(
    db: AsyncSession,
    event_type: str,  # "donation" | "invoice" | "verify" | "allocation" | ...
    text: str,
    actor_id: int,
) -> None:
    entry = ActivityLog(type=event_type, text=text, actor_id=actor_id)
    db.add(entry)
    # No commit here — caller commits atomically with main operation
    # If the service method rolls back, the log entry rolls back too

# Usage pattern in any service:
await activity_service.log(db, "program", f"Program '{program.name}' created by NGO {ngo.name}", ngo.user_id)
await db.commit()  # commits both the program AND the activity log atomically
```

**Why same transaction:** Ensures activity log and the triggering event are atomically consistent. If a donation is rolled back, no phantom activity log entry appears.

---

## Integration Points

### Frontend Contract (`../edutrack/src/data/mock.js`)

**Non-negotiable interface:** Every API response key must match mock.js camelCase field names exactly.

| Source of Truth | Format | Enforcement |
|----------------|--------|-------------|
| `mock.js` field names | camelCase | Pydantic `Field(alias="camelCase")` |
| DB column names | snake_case | SQLAlchemy model columns |
| Python internal | snake_case | Internal service / model code |

**Translation happens exclusively in Pydantic schema serialization.** No manual key mapping in handlers or services.

**Verification approach:** Run `scripts/seed.py` → hit each endpoint → diff response keys against mock.js shapes. Should be byte-compatible.

### File Storage (S3-Compatible Interface)

```python
# app/services/file_service.py
class FileStorageService:
    """Local disk implementation with S3-compatible interface.
    
    Production swap: replace _save/_retrieve with boto3/aiobotocore calls.
    Method signatures unchanged.
    """
    async def save(self, file: UploadFile, uploaded_by: int, db: AsyncSession) -> FileRecord: ...
    async def get_url(self, file_id: int, db: AsyncSession) -> str: ...
    async def get_stream(self, file_id: int, db: AsyncSession) -> AsyncGenerator[bytes, None]: ...
```

**Upload flow:** `POST /api/files/upload` → `file_service.save()` → write bytes to `./uploads/{uuid}.{ext}` → insert `FileRecord` → return `{id, url}`. The `url` is used as a reference in invoices (`supporting_doc`) and NGO docs (`tax_doc`, `reg_doc`).

### Blockchain Mock (Current) ↔ Real Sui SDK (Future)

| Aspect | Mock (`mock_sui.py`) | Real (`sui.py`, future) |
|--------|---------------------|------------------------|
| Wallet creation | `secrets.token_hex(32)` as address | Sui `keytool generate` wrapper |
| Tx hash | `secrets.token_hex(32)` (64-char hex) | Real Sui tx digest |
| Latency | `asyncio.sleep(0.1–0.4)` | Real network RTT |
| State | In-memory / DB only | Sui ledger + DB |
| Activation | Default in `get_blockchain()` | Change 1 line in `dependencies.py` |

**Realistic mock design:** The mock MUST persist results to DB identically to what the real implementation will do. `tx_hash` fields in `Donation`, `Invoice`, `Student` are populated by mock — removing the mock doesn't change the DB schema or any service logic.

### Docker Compose Integration

```yaml
# docker-compose.yml (structure)
services:
  app:
    build: .
    depends_on: [db]
    environment: [from .env]
    command: ["./scripts/start.sh"]   # migrate → seed → uvicorn
    ports: ["8000:8000"]
  db:
    image: postgres:15
    volumes: [pgdata:/var/lib/postgresql/data]
    environment: [POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]
```

**Startup sequence in `start.sh`:**
1. `alembic upgrade head` — apply all migrations (idempotent)
2. `python scripts/seed.py` — seed data if not already present (idempotent via `ON CONFLICT DO NOTHING`)
3. `uvicorn app.main:app --host 0.0.0.0 --port 8000`

---

## Async Patterns: Critical Rules

These are the most common failure modes in FastAPI + SQLAlchemy async projects:

| Situation | Wrong | Right |
|-----------|-------|-------|
| Accessing relationship after commit | `program.ngo.name` (lazy load → MissingGreenlet error) | `selectinload(Program.ngo)` in query, or `await db.refresh(program, ['ngo'])` |
| Forgetting expire_on_commit | Default `True` → attributes expire → implicit I/O on access | `async_sessionmaker(..., expire_on_commit=False)` |
| Sync function calling async DB | `def get_stats(): db.execute(...)` → deadlock | Always `async def` for any function touching DB |
| Session shared across requests | Module-level `session = AsyncSession(engine)` → race conditions | `Depends(get_db)` gives each request its own session |
| Commit in handler | `await db.commit()` in `api/ngo.py` | All commits inside service methods |
| Blockchain in handler | `result = await blockchain.donate(...)` in `api/donor.py` | Blockchain calls inside `donor_service.py` only |

---

## Sources

- **FastAPI official docs — Dependencies with yield:** https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/ (HIGH confidence)
- **FastAPI official docs — Bigger Applications:** https://fastapi.tiangolo.com/tutorial/bigger-applications/ (HIGH confidence)
- **SQLAlchemy 2.0 asyncio docs:** https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html (HIGH confidence, version 2.0.48, released 2026-03-02)
- **PRD (`prd.md`):** Architecture principles, blockchain interface, FE contract (project source)
- **Coding standards (`prompt.md`):** Route handler pattern, service pattern, schema pattern (project source)
- **PROJECT.md:** Tech stack constraints, out-of-scope decisions (project source)
