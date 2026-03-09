# Pitfalls Research: EduTrack Backend

**Domain:** FastAPI + Async SQLAlchemy + Pydantic v2 + JWT RBAC + Blockchain Abstraction
**Researched:** 2026-03-09
**Overall Confidence:** HIGH (all pitfalls verified against official docs + known behavior)

---

## Critical Pitfalls (will break things)

These cause silent data corruption, deadlocked event loops, or production failures that are
painful to trace. Address in Phase 1 (foundation) or the damage compounds into every phase.

---

### 1. Async SQLAlchemy — Accessing Lazy-Loaded Relationships After Session Closes

**What goes wrong:**
After a service method calls `await db.commit()` and the request ends, accessing ORM
relationship attributes (e.g., `ngo.programs`) on a returned model raises
`MissingGreenlet` / `greenlet_spawn` errors or silently returns empty lists. This is the
#1 runtime error in async SQLAlchemy projects.

**Why it happens:**
`AsyncSession` exposes lazy-loading as a synchronous attribute access, but in an async
context there is no greenlet to bridge the sync/async boundary. SQLAlchemy 2.0 raises
`MissingGreenlet` when lazy loading is attempted outside of an async context.

**Consequences:**
- 500 errors on any endpoint that accesses relationship data after commit
- Silent empty lists when `selectinload` is omitted
- Impossible to reproduce in sync tests

**Warning signs:**
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
```
Or relationships returning `[]` when rows exist in DB.

**Prevention:**
```python
# WRONG — lazy load triggered outside session context
ngo = await db.get(NGO, ngo_id)
await db.commit()
return ngo.programs  # BOOM: session closed, lazy load fails

# RIGHT — use selectinload/joinedload BEFORE commit
from sqlalchemy.orm import selectinload
result = await db.execute(
    select(NGO).options(selectinload(NGO.programs)).where(NGO.id == ngo_id)
)
ngo = result.scalar_one_or_none()
```

**Also use `expire_on_commit=False` on the sessionmaker for post-commit access:**
```python
async_session = async_sessionmaker(engine, expire_on_commit=False)
```
Without this, all attributes on committed objects are expired immediately and will
trigger lazy loads on the next access.

**Phase to address:** Phase 1 — Set `expire_on_commit=False` in `database.py` before
writing any service. Define selectinload patterns in the first service written.

---

### 2. Sharing AsyncSession Across Concurrent Tasks (`asyncio.gather`)

**What goes wrong:**
Passing a single `AsyncSession` to multiple coroutines running concurrently via
`asyncio.gather()` causes undefined behavior — interleaved transactions, corrupted
results, or IntegrityError races.

**Why it happens:**
SQLAlchemy's `AsyncSession` is **not thread-safe and not concurrency-safe**. A single
session has one underlying connection and one transaction state. Concurrent coroutines
manipulating it simultaneously corrupt that state.

**Consequences:**
- Intermittent `InvalidRequestError: A transaction is already begun`
- Data silently written to wrong rows
- Race conditions in stat aggregation (e.g., `ngo.programs_count`)

**Warning signs:**
```
sqlalchemy.exc.InvalidRequestError: This session is provisioning a new connection;
concurrent operations are not permitted
```

**Prevention:**
```python
# WRONG — sharing one session across concurrent tasks
results = await asyncio.gather(
    service_a(db, ...),   # both share same AsyncSession
    service_b(db, ...),
)

# RIGHT — each concurrent task gets its own session
async with AsyncSession(engine) as session_a:
    async with AsyncSession(engine) as session_b:
        results = await asyncio.gather(
            service_a(session_a, ...),
            service_b(session_b, ...),
        )
```

**For EduTrack specifically:** The blockchain mock uses `asyncio.sleep()` to simulate
latency. Any service that calls blockchain AND writes to DB must sequence them, not
parallelize on the same session.

**Phase to address:** Phase 1 — Document the session-per-request pattern in `database.py`
as the single source of truth. Flag in code review checklist.

---

### 3. Blocking Sync Code in Async Route Handlers (Event Loop Starvation)

**What goes wrong:**
Calling any synchronous blocking function inside an `async def` handler starves the
event loop. All other concurrent requests freeze until the blocking call returns.

**Why it happens:**
FastAPI/Starlette runs on a single-threaded asyncio event loop. A sync call like
`time.sleep()`, `open()`, `bcrypt.hashpw()` (high work factor), or `requests.get()`
blocks the thread and suspends every other coroutine.

**Consequences:**
- API appears to hang under load
- Timeouts cascade — one slow call blocks all other requests
- Impossible to reproduce with single-user testing

**Warning signs:**
- `/health` endpoint becomes slow when other endpoints are called
- Uvicorn access log shows long gaps between request start and response

**Prevention:**
```python
# WRONG — sync bcrypt in async context
@router.post("/login")
async def login(data: LoginRequest):
    if bcrypt.checkpw(data.password, stored_hash):  # blocks event loop
        ...

# RIGHT — use run_in_executor for CPU-bound blocking calls
import asyncio
loop = asyncio.get_event_loop()
verified = await loop.run_in_executor(None, bcrypt.checkpw, password, hash)

# BETTER for passlib — use passlib's CryptContext which handles this
# python-jose JWT verification is fast enough (not a problem)
# asyncpg is fully async (not a problem)
# File I/O: use aiofiles or run_in_executor
```

**For EduTrack specifically:** `passlib[bcrypt]` with high work factors (default=12) is
CPU-bound. Wrap it in `run_in_executor` or use `asyncio.to_thread()` (Python 3.9+):
```python
import asyncio
hashed = await asyncio.to_thread(pwd_context.hash, password)
verified = await asyncio.to_thread(pwd_context.verify, password, stored_hash)
```

**Phase to address:** Phase 1 (auth service) — The very first service that does password
hashing. Get this right once, copy the pattern everywhere.

---

### 4. Pydantic v2 `model_validate` vs `from_orm` — ORM Mode Requires `from_attributes=True`

**What goes wrong:**
Calling `SomeSchema.model_validate(orm_object)` silently fails or raises
`ValidationError` because `from_attributes` is not set to `True` in the model config.
In v1, this was `orm_mode = True` in the inner `Config` class — that syntax is now
**silently ignored** in v2, meaning old-pattern schemas validate nothing and return
empty/default models.

**Why it happens:**
Pydantic v2 removed the inner `Config` class pattern. The v1 syntax `class Config: orm_mode = True`
is accepted but `orm_mode` is a deprecated key — v2 renamed it to `from_attributes`.
Worse: if you accidentally keep `class Config: orm_mode = True`, Pydantic v2 **does not
raise an error**; it simply ignores it.

**Consequences:**
- All ORM→schema conversions silently return models with all-None or default fields
- API responses return empty objects instead of 500 errors
- Extremely hard to debug because no exception is raised

**Warning signs:**
```python
# All response fields are None or default values
# No ValidationError raised
response = ProgramResponse.model_validate(program_orm_object)
print(response.name)  # None  <-- silent failure
```

**Prevention (mandatory pattern for ALL schemas):**
```python
# CORRECT v2 pattern — use ConfigDict, not inner Config class
from pydantic import BaseModel, ConfigDict, Field

class ProgramResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,    # required for ORM objects
        populate_by_name=True,   # required when using aliases
    )
    id: int
    ngo_id: int = Field(alias="ngoId")
    name: str
    total_budget: float = Field(alias="totalBudget")
```

**Phase to address:** Phase 1 — Define a `BaseSchema` with `from_attributes=True` that
all response schemas inherit. This prevents the mistake on every individual schema.

---

### 5. camelCase Alias Inconsistency — Response vs Serialization

**What goes wrong:**
Defining `Field(alias="camelCase")` makes the alias work for **input parsing** but NOT
for **output serialization** unless `model_dump(by_alias=True)` is called. FastAPI's
`response_model` serialization uses `by_alias=True` by default ONLY when the router is
configured correctly. Missing this means snake_case fields leak into API responses,
breaking the FE contract.

**The two sub-traps:**

**Sub-trap A: `populate_by_name` not set**
```python
# If populate_by_name=False (default), you can ONLY set fields via alias
# This breaks: ProgramResponse(ngo_id=1)  -- uses snake_case
# You must use: ProgramResponse(ngoId=1)  -- uses alias
# Services building responses programmatically fail silently
```

**Sub-trap B: Response not serialized by alias**
```python
# FastAPI DOES serialize by alias by default for response_model
# BUT if you return a dict instead of the Pydantic model, by_alias is NOT applied
# WRONG:
return {"ngo_id": 1, "name": "foo"}  # returns snake_case

# RIGHT:
return ProgramResponse.model_validate(program)  # FastAPI serializes with by_alias=True
# OR let FastAPI do it by returning the ORM object and declaring response_model
```

**Prevention:**
```python
# Base schema pattern for ALL response schemas
class BaseResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,   # allow BOTH snake_case and camelCase in code
    )
```
And in services: always return the Pydantic response object, never a raw dict.

**Phase to address:** Phase 1 — Define `BaseResponse` in `schemas/common.py`. Phase 2
onwards — verify each endpoint's JSON output against mock.js field names before marking
complete.

---

### 6. Alembic Async Migration — `env.py` Not Configured for asyncpg

**What goes wrong:**
Running `alembic upgrade head` with an async engine URL (`postgresql+asyncpg://...`)
crashes with `ModuleNotFoundError` or hangs indefinitely because Alembic's default
`env.py` runs synchronously and asyncpg is async-only.

**Why it happens:**
Alembic needs a special async `env.py` configuration that wraps the migration execution
in an `asyncio.run()` call and uses `run_sync()` to execute the actual migration
operations within the async connection.

**Consequences:**
- Migrations never run; database stays at initial state
- `start.sh` silently fails before uvicorn starts
- Hours lost debugging "table not found" errors

**Warning signs:**
```
asyncpg.exceptions._base.InterfaceError: cannot perform operation:
connection is closed
```
Or: `alembic upgrade head` hangs with no output.

**Prevention — the correct async env.py pattern:**
```python
# alembic/env.py — async-configured
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# ... (config setup)

def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
    )

    async def run_async_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    asyncio.run(run_async_migrations())

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

**Phase to address:** Phase 1 — Get migrations working in the very first commit. Run
`alembic upgrade head` as part of Docker startup; broken migrations = broken demo.

---

### 7. JWT `python-jose` — `sub` Claim as String, Not Integer

**What goes wrong:**
`python-jose` decodes JWT payloads with JSON rules: the `sub` field is always a string
in JWT spec. If you encode `{"sub": user.id}` where `user.id` is an `int`, decoding
returns `{"sub": "42"}` (a string). Comparing this to a database integer ID with `==`
silently returns `False` for type mismatch in some ORM queries.

**Why it happens:**
JWT `sub` claim is defined as a string by RFC 7519. `python-jose` respects this. If
you store `user.id` directly as an int, round-trip through JWT changes its type.

**Consequences:**
- All `get_current_user` lookups silently fail (user not found)
- Returns 401 on every authenticated request after the first
- Extremely confusing: token decodes successfully but user is "not found"

**Warning signs:**
```python
payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
user_id = payload.get("sub")  # returns "42" (string), not 42 (int)
user = await db.get(User, user_id)  # passes string to integer PK → None
```

**Prevention:**
```python
# ALWAYS convert sub to int when reading from JWT
user_id = int(payload.get("sub"))  # explicit cast

# And always encode as string for maximum compatibility
token_data = {"sub": str(user.id), "role": user.role}
```

**Phase to address:** Phase 1 (auth service) — The `get_current_user` dependency is used
by every authenticated endpoint. Fix this once at the source.

---

### 8. CORS — `allow_credentials=True` with `allow_origins=["*"]` Silently Fails

**What goes wrong:**
Setting both `allow_credentials=True` AND `allow_origins=["*"]` causes the browser to
**reject** the response. The browser's CORS policy forbids wildcard origins with
credentials. FastAPI/Starlette does not raise an error — it simply sends headers that
browsers refuse.

**Why it happens:**
CORS spec (MDN, W3C) explicitly prohibits `Access-Control-Allow-Origin: *` when
`Access-Control-Allow-Credentials: true` is set. The browser enforces this.

**Consequences:**
- All API calls from the frontend return "CORS error" in browser console
- Server logs show 200 OK — you see success on the backend but failure in the browser
- Extremely confusing to debug because the server is technically responding

**Warning signs:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/...' from origin
'http://localhost:3000' has been blocked by CORS policy: The value of the
'Access-Control-Allow-Origin' header in the response must not be the wildcard
'*' when the request's credentials mode is 'include'.
```

**Prevention:**
```python
# WRONG
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # INCOMPATIBLE with wildcard origin
)

# CORRECT — explicit origins when credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Vite dev server (EduTrack FE)
        "http://localhost:5173",   # Vite alternate port
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Phase to address:** Phase 1 (`main.py`) — Set this correctly from day one. The
EduTrack frontend runs on a different port; CORS will be triggered immediately.

---

## Common Mistakes (will slow things down)

These don't crash on day one but create painful debugging sessions or rework later.

---

### 9. Missing `await db.refresh(obj)` After `db.commit()`

**What goes wrong:**
After `await db.commit()`, SQLAlchemy expires all attributes on committed objects (by
default). Accessing any attribute — including auto-generated fields like `id`,
`created_at`, DB-level defaults — raises `MissingGreenlet` or returns stale data.

**Prevention:**
```python
db.add(program)
await db.commit()
await db.refresh(program)  # required: re-loads from DB after commit
return ProgramResponse.model_validate(program)
```
Or use `expire_on_commit=False` (set globally) and avoid the need for refresh.
Both approaches are valid; pick one and be consistent.

**Phase:** Phase 2+ — Every service that creates or updates records.

---

### 10. Pydantic v2 `Optional[str]` is Now Required (Breaking Behavior Change)

**What goes wrong:**
In Pydantic v1, `Optional[str]` meant "not required, defaults to None". In Pydantic v2,
`Optional[str]` means "required, but can be None". This causes 422 Unprocessable Entity
errors on previously-valid requests.

**v1 vs v2 behavior:**
```python
# v1: optional, defaults to None
class Schema(BaseModel):
    message: Optional[str]  # not required, None by default

# v2: REQUIRED, but accepts None
class Schema(BaseModel):
    message: Optional[str]  # REQUIRED field! Must pass explicitly

# v2 correct pattern for "not required, can be None":
class Schema(BaseModel):
    message: Optional[str] = None  # explicit default needed
```

**For EduTrack:** Donation `message`, Invoice `approved_date`, and Student `wallet_balance`
zero-value default — all nullable fields must have `= None` or `= 0` explicitly.

**Phase:** Phase 1 — Establish the pattern in the first schema file.

---

### 11. Pydantic v2 Validator Syntax — `@validator` is Deprecated

**What goes wrong:**
Using `@validator` from Pydantic v1 still works in v2 but emits deprecation warnings
and has subtle behavioral differences. Custom validators using the old signature
`(cls, v, values, field)` will fail with `TypeError` in strict mode.

**Prevention:**
```python
# WRONG (v1 pattern)
from pydantic import validator

class Schema(BaseModel):
    @validator("amount")
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("amount must be positive")
        return v

# CORRECT (v2 pattern)
from pydantic import field_validator

class Schema(BaseModel):
    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v
```

**Phase:** Phase 1 — Use v2 validators from the first schema.

---

### 12. `model_dump()` Does Not Serialize by Alias by Default

**What goes wrong:**
Calling `schema.model_dump()` in a service (e.g., to pass to another function or
log) returns snake_case keys, not camelCase. This is correct Python-internal behavior,
but developers mistake it for the "API response" and compare it to mock.js field names.

**Prevention:**
```python
# For internal use (Python code): model_dump() is fine — snake_case
data = schema.model_dump()  # {"ngo_id": 1, "total_budget": 100}

# For API response: FastAPI handles by_alias=True automatically when you
# return the Pydantic model and declare response_model on the decorator
# You never need to call model_dump(by_alias=True) in route handlers

# The one case you DO need it:
# When manually building JSON for tests or logging
data = schema.model_dump(by_alias=True)  # {"ngoId": 1, "totalBudget": 100}
```

**Phase:** Phase 2 — Verify during first endpoint implementation.

---

### 13. Alembic Autogenerate Missing Non-SQLAlchemy Schema Changes

**What goes wrong:**
`alembic revision --autogenerate` only detects changes to SQLAlchemy model metadata.
It does NOT detect: custom PostgreSQL types, check constraints defined outside the ORM,
index changes on JSON fields, or manual DB changes. Running autogenerate produces an
empty migration while the DB is actually out of sync.

**Prevention:**
- Always review generated migration files before applying
- Never trust autogenerate as the sole source of truth for schema state
- For EduTrack's JSON columns (`categories`, `items`): these are stored as JSONB in
  PostgreSQL; autogenerate detects them but won't generate GIN indexes automatically

**Phase:** Phase 1 — Add a note to migration workflow.

---

### 14. FastAPI Response Model — Including Fields Not in `response_model` Leaks Data

**What goes wrong:**
If a service accidentally returns an ORM object that has more fields than the declared
`response_model`, FastAPI will filter to only response_model fields. BUT if no
`response_model` is declared, all ORM fields are serialized — including `hashed_password`.

**Prevention:**
```python
# ALWAYS declare response_model on every endpoint
@router.get("/me", response_model=UserResponse)  # filters to declared fields only
async def get_me(...):
    ...

# UserResponse MUST NOT include hashed_password field
class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    # hashed_password intentionally omitted
```

**Phase:** Phase 1 (auth endpoints) — Any endpoint returning User data.

---

### 15. Token Refresh Race Condition — Dual Refresh Token Storage

**What goes wrong:**
If two browser tabs simultaneously detect an expired access token and both call
`/api/auth/refresh`, the first refresh invalidates the stored refresh token. The second
call then fails with 401, logging the user out even though they're active.

**Prevention for EduTrack v1 (demo scope):**
Store refresh tokens in the DB with a `used` flag. On first use, mark as used and
issue a new one. Reject any reuse of a used token. This prevents the race condition
without requiring Redis.

```python
# RefreshToken model
class RefreshToken(Base):
    token: str (unique, indexed)
    user_id: FK
    expires_at: datetime
    used: bool = False
    created_at: datetime
```

**Phase:** Phase 1 (auth service) — Design this correctly upfront. Retrofitting token
invalidation into an existing auth system requires a migration and code changes.

---

### 16. `python-jose` vs `PyJWT` — API Surface Incompatibility

**What goes wrong:**
The project spec uses `python-jose[cryptography]`. If a developer accidentally reads
FastAPI's current official docs (which now recommend `PyJWT`), they'll use a different
API. `python-jose` and `PyJWT` have different import paths and slightly different
exception classes.

**python-jose API (what EduTrack uses):**
```python
from jose import jwt, JWTError
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
# Raises: jose.JWTError (not jwt.exceptions.InvalidTokenError)
```

**Prevention:**
- Use `from jose import jwt, JWTError` consistently
- Exception handler must catch `jose.JWTError`, not `jwt.exceptions.InvalidTokenError`
- Add a comment in `security.py` noting the library choice

**Phase:** Phase 1 — Set the import pattern correctly in `security.py`.

---

### 17. Activity Log — Writing Inside Closed Session

**What goes wrong:**
`activity_service.log()` is called after `await db.commit()` in some patterns. If the
session is closed or the transaction has ended, the log write fails silently or raises
`InvalidRequestError`.

**Prevention:**
```python
# WRONG — log after commit (session may be expired/closed)
await db.commit()
await activity_service.log(db, "program", "...", ngo.user_id)  # fails

# RIGHT — log before commit (all in same transaction)
db.add(program)
await activity_service.log(db, "program", "...", ngo.user_id)
await db.commit()  # commits both program + activity log atomically
```

**For EduTrack:** Activity logs are a core feature. They must be atomic with the
operation they describe. If the program creation fails, the activity log should also
roll back.

**Phase:** Phase 2 (first service with activity logging, e.g., ngo_service).

---

## Pydantic v2 Specific

A targeted reference for v1→v2 patterns relevant to EduTrack schemas.

---

### The `orm_mode` → `from_attributes` Rename

| v1 | v2 |
|----|----|
| `class Config: orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| `class Config: allow_population_by_field_name = True` | `model_config = ConfigDict(populate_by_name=True)` |
| `Schema.from_orm(obj)` | `Schema.model_validate(obj)` |
| `Schema.parse_obj(dict)` | `Schema.model_validate(dict)` |
| `schema.dict()` | `schema.model_dump()` |
| `schema.json()` | `schema.model_dump_json()` |
| `Schema.__fields__` | `Schema.model_fields` |
| `@validator("field")` | `@field_validator("field")` with `@classmethod` |
| `@root_validator` | `@model_validator(mode="before"/"after")` |

### camelCase alias_generator vs Per-Field Alias

**Option A: Per-field alias (EduTrack's approach per prompt.md)**
```python
class NGOResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int
    total_funded: float = Field(alias="totalFunded")
    programs_count: int = Field(alias="programsCount")
```
Pros: Explicit control, easy to see exact alias. Required when FE field names don't
follow a consistent camelCase pattern (e.g., `taxDoc`, `regDoc`).

**Option B: alias_generator (alternative)**
```python
from pydantic.alias_generators import to_camel

class BaseResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )
```
Pros: Less boilerplate. Cons: Any deviation from camelCase convention requires
`alias_priority=2` on the field to override the generator.

**Recommendation for EduTrack:** Use per-field aliases as specified in `prompt.md`.
The FE mock.js fields include cases like `taxDoc`, `regDoc`, `scholarshipId` which
auto-generators handle, but explicit is safer given the strict FE contract requirement.

### `Optional[str]` Required Behavior Change

```python
# v2 REQUIRED nullable (migration gotcha from v1):
message: Optional[str]       # REQUIRED — must pass None explicitly

# v2 NOT required, nullable:
message: Optional[str] = None  # not required, defaults to None

# EduTrack fields that need explicit defaults:
# Donation.message → Optional[str] = None
# Invoice.approved_date → Optional[datetime] = None
# Invoice.tx_hash → Optional[str] = None
# Student.wallet_balance → float = 0.0
```

### `model_dump(by_alias=True)` for Serialization

FastAPI's `response_model` machinery calls `model_dump(by_alias=True)` internally.
This means:
- Returning a Pydantic model from a route handler → camelCase in response ✓
- Returning a dict → NOT automatically aliased → snake_case leaks into response ✗
- Returning an ORM object directly → NOT serialized by alias ✗

Always return Pydantic model instances from service methods.

---

## Async SQLAlchemy Specific

Deep dive on session lifecycle, lazy loading, and common async patterns.

---

### Session Lifecycle — The FastAPI `Depends` Pattern

The `get_db` dependency must use `async with` and `yield` to guarantee cleanup:

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,     # detect dropped connections
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,  # critical: prevents lazy-load on post-commit access
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()    # commit at end of successful request
        except Exception:
            await session.rollback()  # rollback on any exception
            raise
        finally:
            await session.close()
```

**Note:** The `try/except/finally` pattern ensures that exceptions cause a rollback and
the session is always closed, preventing connection pool exhaustion.

### Querying Patterns — `select()` vs `db.get()`

```python
# db.get() — simple PK lookup, uses identity map cache
user = await db.get(User, user_id)

# select() — for filtering, joining, eagerly loading relationships
result = await db.execute(
    select(NGO)
    .where(NGO.status == "verified")
    .options(selectinload(NGO.programs))
    .order_by(NGO.created_at.desc())
)
ngos = result.scalars().all()

# IMPORTANT: result.scalars() vs result.scalar_one() vs result.scalar_one_or_none()
# scalars().all()        → list, empty list if no rows
# scalar_one()           → raises NoResultFound if 0 rows, MultipleResultsFound if >1
# scalar_one_or_none()   → returns None if 0 rows, raises if >1
```

### Relationship Loading Strategies

For EduTrack's data shapes:

```python
# NGO with programs — use selectinload (separate query, efficient for 1-to-many)
result = await db.execute(
    select(NGO).options(selectinload(NGO.programs)).where(NGO.id == ngo_id)
)

# Student with ngo + program info — use joinedload (JOIN, efficient for many-to-one)
result = await db.execute(
    select(Student)
    .options(
        joinedload(Student.ngo),
        joinedload(Student.program),
    )
    .where(Student.id == student_id)
)
```

**Rule of thumb:**
- `selectinload` → use for one-to-many (one NGO has many programs)
- `joinedload` → use for many-to-one (many students belong to one NGO)

### The `MissingGreenlet` Error — Root Cause Tree

```
MissingGreenlet raised when:
├── Accessing lazy-loaded relationship OUTSIDE async context
│   └── Fix: Use selectinload/joinedload in the query
├── Accessing any attribute after session.close()
│   └── Fix: expire_on_commit=False + refresh if needed
├── Using a sync SQLAlchemy event handler in async context
│   └── Fix: Use asyncio-compatible event listener
└── Running ORM operations in sync code called from async code
    └── Fix: Use run_sync() for such cases
```

### Bulk Operations Pitfall

Avoid N+1 queries in loops:

```python
# WRONG — N+1 queries (one per student in a loop)
for student in students:
    student.wallet_balance += amount
    await db.commit()  # commits after each student!

# RIGHT — bulk update in a single query
await db.execute(
    update(Student)
    .where(Student.program_id == program_id)
    .values(wallet_balance=Student.wallet_balance + amount)
)
await db.commit()
```

For EduTrack's fund allocation flow, this is critical: allocating to multiple students
must be a single transaction, not N commits.

---

## Phase Mapping

Which pitfall to address in which build phase to prevent compounding damage.

| Phase | Topic | Pitfall to Address | Mitigation |
|-------|-------|-------------------|------------|
| **Phase 1: Foundation** | `database.py` setup | Session lifecycle, `expire_on_commit=False`, `get_db` pattern (#1, #2, #9) | Use the `async_sessionmaker` with `expire_on_commit=False` from day one |
| **Phase 1: Foundation** | `schemas/common.py` | `from_attributes=True`, `populate_by_name=True` on BaseResponse (#4, #5) | Define `BaseResponse` that all schemas inherit |
| **Phase 1: Foundation** | `main.py` CORS | `allow_credentials=True` + explicit origins, not wildcard (#8) | Hardcode dev origins in `.env.example` |
| **Phase 1: Foundation** | `alembic/env.py` | Async migration configuration (#6) | Use async `env.py` template from SQLAlchemy docs |
| **Phase 1: Auth Service** | `security.py` + `auth_service.py` | JWT `sub` as string (#7), `python-jose` API (#16), bcrypt blocking (#3) | Cast `sub` to `int`, wrap bcrypt in `asyncio.to_thread` |
| **Phase 1: Auth Service** | Refresh token storage | Race condition, token invalidation (#15) | Add `RefreshToken` model with `used` flag |
| **Phase 2: NGO Service** | First service with relations | Lazy loading (#1), selectinload patterns | Query reviews before merge |
| **Phase 2: NGO Service** | Activity logging | Atomic log writes (#17) | Always log before commit |
| **Phase 2+: All Services** | Session sharing | Concurrent session access (#2) | Code review checklist item |
| **Phase 2+: All Services** | Post-commit refresh | Missing `refresh()` (#9) | Pair with `expire_on_commit=False` decision |
| **Phase 3+: All Schemas** | Pydantic v2 validators | `@validator` deprecated (#11), `Optional[str]` (#10) | Use `@field_validator` from first schema |
| **Phase 4: Blockchain** | Mock service | Mock uses `asyncio.sleep` — ensure it doesn't share session (#2) | Blockchain call → commit → activity log, in that order |
| **Phase 5: Seed Script** | `scripts/seed.py` | Idempotent seed must use `merge()` or check-before-insert, not bare `add()` | Use `db.merge()` or `INSERT ... ON CONFLICT DO NOTHING` |

### High-Risk Phases

| Phase | Risk Level | Reason |
|-------|-----------|--------|
| Phase 1 (Foundation) | CRITICAL | All subsequent phases inherit whatever patterns are set here |
| Phase 2 (NGO/Program services) | HIGH | First complex service with relationships; lazy-load traps common |
| Phase 3 (Auth + RBAC) | HIGH | JWT type bugs surface as silent auth failures |
| Phase 4 (Blockchain + Donations) | MEDIUM | Async mock + session sharing if not careful |
| Phase 5 (Seed + Docker) | LOW | Well-understood patterns; idempotency is the only concern |

---

## Sources

| Source | Confidence | Used For |
|--------|-----------|----------|
| [SQLAlchemy 2.0 Asyncio Docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) | HIGH | Session lifecycle, MissingGreenlet, selectinload patterns |
| [Pydantic v2 Migration Guide](https://docs.pydantic.dev/latest/migration/) | HIGH | orm_mode → from_attributes, Optional behavior, validator deprecation |
| [Pydantic v2 Alias Docs](https://docs.pydantic.dev/latest/concepts/alias/) | HIGH | alias, populate_by_name, serialization_alias behavior |
| [FastAPI CORS Docs](https://fastapi.tiangolo.com/tutorial/cors/) | HIGH | allow_credentials + wildcard incompatibility |
| [FastAPI JWT Tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) | HIGH | JWT patterns, sub claim, python-jose usage |
| [Alembic Cookbook — Asyncio](https://alembic.sqlalchemy.org/en/latest/cookbook.html) | HIGH | Async env.py configuration |
| RFC 7519 (JWT spec) | HIGH | sub claim must be a string |
| [MDN CORS docs](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) | HIGH | Credentials + wildcard browser rejection |
| EduTrack project files (PROJECT.md, prd.md, prompt.md) | N/A | Project-specific context |
