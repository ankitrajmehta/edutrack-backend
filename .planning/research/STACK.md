# Stack Research: EduTrack Backend

**Project:** EduTrack — Blockchain-powered scholarship platform (Nepal / UNICEF Venture Fund demo)
**Researched:** 2026-03-09
**Python target:** 3.11+

---

## Recommended Stack (with versions)

### Core Runtime

| Library | Pin | Install as | Purpose | Confidence |
|---------|-----|-----------|---------|-----------|
| Python | 3.11.x | system / docker image | Language runtime; 3.11 chosen for speed + asyncio maturity | HIGH — project constraint |
| FastAPI | `~0.115.14` | `fastapi` | ASGI web framework; stable 0.115 series (latest non-breaking: 0.115.14). Do **not** jump to 0.116+ mid-project without reviewing changelog | HIGH — verified via pip index |
| uvicorn | `~0.41.0` | `uvicorn[standard]` | ASGI server; `[standard]` pulls `httptools` + `uvloop` for production performance | HIGH — verified via pip index |
| starlette | (FastAPI pins this) | transitive | Routing, middleware, background tasks; do not install separately | HIGH |

> **FastAPI version note:** The 0.115.x series (released throughout 2024-2025) is the stable production series. 0.116–0.135 exist but introduce incremental changes; pinning `~0.115` locks compatible minor updates while avoiding any breaking changes in newer feature releases. Revisit at v2.

### Database & ORM

| Library | Pin | Install as | Purpose | Confidence |
|---------|-----|-----------|---------|-----------|
| PostgreSQL | 16.x | Docker image `postgres:16-alpine` | Primary relational store | HIGH — standard |
| SQLAlchemy | `~2.0.48` | `sqlalchemy[asyncio]` | ORM + Core; **must use `[asyncio]` extra** to ensure `greenlet` is installed on all platforms (including Apple M1) | HIGH — verified via pip index + official docs |
| asyncpg | `~0.31.0` | `asyncpg` | Native async PostgreSQL driver for SQLAlchemy async engine; connection string prefix: `postgresql+asyncpg://` | HIGH — verified via pip index |
| alembic | `~1.18.4` | `alembic` | Database migrations; must use async template (see Key Notes below) | HIGH — verified via pip index |

> **SQLAlchemy 2.0 vs 2.1:** SQLAlchemy 2.0.48 is the current stable release (March 2, 2026). SQLAlchemy 2.1 is in beta at time of research — do NOT use 2.1.x for this project. Stick to `~2.0.48`.

### Authentication & Security

| Library | Pin | Install as | Purpose | Confidence |
|---------|-----|-----------|---------|-----------|
| python-jose | `~3.5.0` | `python-jose[cryptography]` | JWT encode/decode; **must use `[cryptography]` extra** — the default `python-rsa` backend is retired and has open CVEs. Latest release 3.5.0 (May 2025). Still has open issues (CVE-2024-33663 fixed in 3.4.0, CVE-2024-33664 fixed in 3.4.0). Use `[cryptography]` backend only, never default | HIGH — verified via GitHub commits + pip index |
| passlib | `~1.7.4` | `passlib[bcrypt]` | Password hashing context (CryptContext) for use with bcrypt. **Unmaintained since 2020** — last PyPI release 1.7.4. Works correctly when bcrypt is pinned to `<5.0` (see bcrypt note). For v2, replace with direct `bcrypt` calls | HIGH — verified via pip index |
| bcrypt | `>=4.1.2,<5.0` | `bcrypt` | bcrypt implementation; **pin below 5.0** — bcrypt 4.1.0 was yanked for incompatibility with passlib; 4.1.1 introduced a fix. bcrypt 5.0.0 (Sep 2025) adds 72-byte password length enforcement that breaks passlib's assumptions. Safe range: `>=4.1.2,<5.0.0` | HIGH — verified via PyPI release history |
| cryptography | `~46.0.0` | (transitive via python-jose) | Backend crypto for python-jose; pyca maintained, actively updated | HIGH — verified via pip index |

> **bcrypt / passlib warning:** This combination is the single most common breaking point in FastAPI auth setups. `bcrypt==4.1.0` was **yanked** from PyPI because it broke passlib. `bcrypt==4.1.1` restored compatibility. `bcrypt>=5.0.0` breaks passlib again (password truncation behavior changed). The correct pin is `bcrypt>=4.1.2,<5.0.0`.

### Validation & Configuration

| Library | Pin | Install as | Purpose | Confidence |
|---------|-----|-----------|---------|-----------|
| pydantic | `~2.12.5` | `pydantic` | Request/response validation, schema definitions; v2 API is stable and mature | HIGH — verified via pip index |
| pydantic-settings | `~2.13.1` | `pydantic-settings` | `BaseSettings` for `.env` config loading — separated from pydantic core in v2 | HIGH — verified via pip index |

### File Handling

| Library | Pin | Install as | Purpose | Confidence |
|---------|-----|-----------|---------|-----------|
| python-multipart | `~0.0.22` | `python-multipart` | **Required for FastAPI file upload** — without this, `UploadFile` endpoints return 422 errors silently | HIGH — verified via pip index |
| aiofiles | `~25.1.0` | `aiofiles` | Async file I/O for writing/reading uploaded files without blocking the event loop | HIGH — verified via pip index |

### Infrastructure

| Library | Pin | Install as | Purpose | Confidence |
|---------|-----|-----------|---------|-----------|
| Docker | 25+ | system | Container runtime | HIGH — standard |
| Docker Compose | v2 (plugin) | system | Multi-container orchestration (app + postgres) | HIGH — standard |

---

## Blockchain Abstraction (v1 Mock / v2 Real)

| Library | Pin | Install as | Purpose | Confidence |
|---------|-----|-----------|---------|-----------|
| pysui | `~0.96.0` (deferred) | `pysui` | Python SDK for Sui blockchain; actively maintained (0.96.0 latest, frequent releases); **deferred to v2** — mock implementation ships in v1 | MEDIUM — verified via pip index; API stability requires review at v2 |

> **v1 approach:** Mock implementation uses `secrets.token_hex(32)` → 64-char hex tx hashes and `asyncio.sleep(0.1–0.4)` to simulate latency. Zero external dependencies for blockchain in v1. Real `pysui` integration is a single-file swap in `app/services/blockchain/sui.py`.

---

## Full requirements.txt (production)

```
# Core framework
fastapi~=0.115.14
uvicorn[standard]~=0.41.0

# Database
sqlalchemy[asyncio]~=2.0.48
asyncpg~=0.31.0
alembic~=1.18.4

# Auth & security
python-jose[cryptography]~=3.5.0
passlib[bcrypt]~=1.7.4
bcrypt>=4.1.2,<5.0.0

# Validation & config
pydantic~=2.12.5
pydantic-settings~=2.13.1

# File handling
python-multipart~=0.0.22
aiofiles~=25.1.0
```

---

## Key Library Notes

### FastAPI (0.115.x series)
- Route handlers must be `async def` throughout — sync handlers run in a threadpool, defeating the purpose of asyncpg
- `response_model_exclude_none=True` can be set globally in `FastAPI()` constructor; useful for nullable optional fields
- Background tasks (`BackgroundTasks`) are available for fire-and-forget ops (e.g. audit log writes) — but for this project, audit logging stays synchronous inside service transactions for consistency
- CORS middleware must be configured before any routes are added

### SQLAlchemy 2.0 async
- **Critical:** Install as `sqlalchemy[asyncio]`, not just `sqlalchemy`. The asyncio extension requires `greenlet` which is only auto-installed by the extra
- `create_async_engine("postgresql+asyncpg://...")` — note the `+asyncpg` dialect specifier
- Use `async_sessionmaker` (not the older `sessionmaker`) for session factories
- `AsyncSession.execute()` returns `CursorResult`; for ORM results use `session.scalars()` or `session.execute(select(Model))`
- `selectinload()` / `lazy="selectin"` required for relationship loading in async context — **do not use `lazy="dynamic"` or default lazy loading**, as it triggers implicit I/O which raises `MissingGreenlet` in async context
- `db.refresh(obj)` is `async` — await it after commit
- JSON columns: use `sqlalchemy.types.JSON` for `categories`, `items` fields in Program and Invoice models

### Pydantic v2 (critical changes from v1)
- `orm_mode = True` → **replaced by** `model_config = ConfigDict(from_attributes=True)`
- `class Config: orm_mode = True` pattern is **gone** — will silently not work or warn
- `populate_by_name=True` **must be set** in ConfigDict when using `Field(alias="camelCase")` — without it, you cannot access the field by its Python name (only by alias), which breaks `model_validate` calls
- Full ConfigDict for response schemas: `ConfigDict(from_attributes=True, populate_by_name=True)`
- `schema.dict()` → **replaced by** `schema.model_dump()`
- `schema.from_orm(obj)` → **replaced by** `schema.model_validate(obj)`
- `@validator` → **replaced by** `@field_validator` with different signature
- `model_dump(by_alias=True)` required when serializing to send camelCase JSON responses — set `response_model` on routes and FastAPI handles this automatically via `model_config`

### Alembic async setup
- Initialize with `alembic init --template async alembic` — this creates an async-compatible `env.py`
- Do **not** use the default (sync) template — it will deadlock with asyncpg
- `env.py` must import and use `run_async_migrations()` pattern with `asyncio.run()`
- `alembic revision --autogenerate` works with async setup; run from an async context or via the sync wrapper in env.py
- Connection string in `alembic.ini` must also use `postgresql+asyncpg://`

### python-jose[cryptography] (3.5.0)
- Always import as `from jose import jwt, JWTError`
- Use `algorithm="HS256"` for symmetric HMAC signing (suitable for v1 — single service, shared secret)
- `[cryptography]` extra replaces the deprecated `python-rsa` backend; never use `python-jose` without this extra
- Latest release 3.5.0 (May 28, 2025); CVE-2024-33663 and CVE-2024-33664 were fixed in 3.4.0 — use ≥3.4.0
- Open issues remain (algorithm confusion, ECDSA key handling) — mitigated by using HS256 with a strong secret key for v1

### passlib[bcrypt]
- `CryptContext(schemes=["bcrypt"], deprecated="auto")` is the standard pattern
- Unmaintained (last release 1.7.4, 2020) but functional with pinned bcrypt
- bcrypt 5.0.0 breaks passlib because passlib does not enforce the 72-byte password limit and the behavior change in bcrypt 5.0 raises `ValueError` — pin `bcrypt<5.0.0`
- bcrypt 4.1.0 was **yanked** from PyPI for breaking passlib's internal `__about__` detection — do not pin to 4.1.0 specifically

### python-multipart (file upload)
- FastAPI depends on this for any endpoint using `UploadFile` or `Form()` parameters
- Missing this package produces a confusing 422 validation error with no clear message
- 0.0.22 is the latest stable release; actively maintained

### aiofiles (async file I/O)
- Use `async with aiofiles.open(path, "wb") as f: await f.write(content)` for saving uploads
- Never use synchronous `open()` inside an async route or service — blocks the event loop
- 25.1.0 is the latest stable release (2025 release cadence)

### pydantic-settings
- `BaseSettings` was extracted to this separate package in Pydantic v2
- Import: `from pydantic_settings import BaseSettings`
- Loads `.env` files automatically when `model_config = SettingsConfigDict(env_file=".env")`
- `env_file_encoding="utf-8"` recommended

---

## What NOT to Use

| Library | Why Not | Use Instead |
|---------|---------|-------------|
| `databases` (encode/databases) | Older async DB abstraction; superseded by SQLAlchemy 2.0 async | `sqlalchemy[asyncio]` + `asyncpg` |
| `tortoise-orm` | Different ORM paradigm; not compatible with Alembic migration workflow | SQLAlchemy 2.0 async |
| `psycopg3` (asyncio mode) | Valid alternative driver but asyncpg has better performance and wider FastAPI community adoption | `asyncpg` (stick to project constraint) |
| `PyJWT` | Simpler JWT library but does not support JWK/JWKS or RSA; project specifies `python-jose` | `python-jose[cryptography]` |
| `argon2-cffi` | Better password hashing than bcrypt — but `passlib` is already the project constraint. Evaluate for v2 | `passlib[bcrypt]` with pinned bcrypt |
| `bcrypt==4.1.0` | **Yanked from PyPI** — breaks passlib's version detection | `bcrypt>=4.1.2,<5.0.0` |
| `bcrypt>=5.0.0` | Password >72 bytes now raises `ValueError`; passlib passes full password to bcrypt without truncating | `bcrypt>=4.1.2,<5.0.0` |
| `sqlalchemy` (without `[asyncio]`) | Silently missing `greenlet` on non-x86 platforms (Apple M1, ARM) causes `MissingGreenlet` errors | `sqlalchemy[asyncio]` |
| `orm_mode = True` in Pydantic Config | Pydantic v1 syntax — silently ignored in v2 | `ConfigDict(from_attributes=True)` |
| Sync `open()` in async code | Blocks event loop, defeating asyncio performance | `aiofiles` |
| `lazy="dynamic"` on SQLAlchemy relationships | Triggers implicit sync I/O in async context → `MissingGreenlet` exception | `lazy="selectin"` or `selectinload()` |
| `pysui` in v1 | Adds Rust-based dependency complexity; blockchain is mocked in v1 | `secrets.token_hex(32)` in mock implementation |
| SQLAlchemy 2.1.x (beta) | Beta status; may introduce breaking changes before stable release | `~2.0.48` |
| FastAPI `>=0.116` | Stable but untested with this exact stack combo; pin to known-good 0.115 series | `~0.115.14` |

---

## Compatibility Matrix

### Critical Version Pairs

| Combination | Status | Notes |
|------------|--------|-------|
| `passlib~1.7.4` + `bcrypt>=4.1.2,<5.0.0` | ✅ SAFE | bcrypt 4.1.1 restored passlib compatibility; 4.1.2+ is clean |
| `passlib~1.7.4` + `bcrypt==4.1.0` | ❌ YANKED | Do not use; 4.1.0 was yanked from PyPI |
| `passlib~1.7.4` + `bcrypt>=5.0.0` | ❌ BREAKS | ValueError on passwords >72 bytes; passlib does not truncate |
| `python-jose~3.5.0` + `cryptography~46.0.0` | ✅ SAFE | python-jose 3.5.0 uses cryptography ≥3.4; 46.x is current |
| `python-jose~3.5.0` (no `[cryptography]` extra) | ⚠️ RISKY | Falls back to `python-rsa` backend which is retired + has CVEs |
| `sqlalchemy~2.0.48` + `asyncpg~0.31.0` | ✅ SAFE | Tested combination; asyncpg 0.31 supports PG 12-17 |
| `sqlalchemy~2.0.48` (no `[asyncio]` extra) | ⚠️ RISKY | `greenlet` not guaranteed on ARM/M1; `MissingGreenlet` at runtime |
| `pydantic~2.12.5` + `fastapi~0.115.14` | ✅ SAFE | FastAPI 0.115 targets Pydantic v2; fully compatible |
| `pydantic~1.x` + `fastapi~0.115.14` | ❌ BREAKS | FastAPI 0.115 requires Pydantic v2; v1 shim is not supported |
| `alembic~1.18.4` + `sqlalchemy~2.0.48` | ✅ SAFE | Alembic 1.18 targets SQLAlchemy 2.0 |
| Alembic sync template + asyncpg | ❌ BREAKS | Sync env.py calls sync methods on async engine → deadlock |
| `ConfigDict(from_attributes=True)` + Pydantic v2 | ✅ REQUIRED | ORM mode in Pydantic v2 |
| `class Config: orm_mode = True` + Pydantic v2 | ❌ SILENT FAIL | v1 syntax; ignored or deprecated warning in v2 |

### Python Version Compatibility

| Library | Python 3.11 | Python 3.12 | Python 3.13 | Notes |
|---------|------------|------------|------------|-------|
| FastAPI 0.115.x | ✅ | ✅ | ✅ | |
| SQLAlchemy 2.0.48 | ✅ | ✅ | ✅ | |
| asyncpg 0.31.0 | ✅ | ✅ | ✅ | |
| pydantic 2.12.x | ✅ | ✅ | ✅ | |
| python-jose 3.5.0 | ✅ | ✅ | ✅ | |
| passlib 1.7.4 | ✅ | ✅ | ⚠️ | Python 3.13 deprecated some `crypt` stdlib internals; test carefully |
| bcrypt 4.1.2-4.3.0 | ✅ | ✅ | ✅ | |
| aiofiles 25.1.0 | ✅ | ✅ | ✅ | |

> **Recommendation:** Use Python 3.11 for maximum library compatibility and asyncio stability. 3.12 is safe. Avoid 3.13 due to passlib/crypt deprecations until passlib gets a new maintainer or is replaced.

---

## Alembic Async Init Commands

```bash
# Initialize with async template (one-time setup)
alembic init --template async alembic

# Generate initial migration from models
alembic revision --autogenerate -m "initial_schema"

# Apply migrations
alembic upgrade head
```

The `--template async` flag generates an `env.py` with `run_async_migrations()` that works with asyncpg. Without this flag, the sync template will error at runtime when it tries to call sync methods on an async engine.

---

## Sources

| Claim | Source | Confidence |
|-------|--------|-----------|
| FastAPI latest = 0.135.1, stable series = 0.115.x | `pip index versions fastapi` (verified 2026-03-09) | HIGH |
| SQLAlchemy latest = 2.0.48 (March 2, 2026) | `pip index versions sqlalchemy` + docs.sqlalchemy.org | HIGH |
| SQLAlchemy `[asyncio]` extra required for greenlet | https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html | HIGH |
| asyncpg 0.31.0 latest | `pip index versions asyncpg` | HIGH |
| Alembic 1.18.4 latest | `pip index versions alembic` | HIGH |
| python-jose 3.5.0 latest, CVEs fixed in 3.4.0 | `pip index versions` + github.com/mpdavis/python-jose/commits | HIGH |
| python-jose `[cryptography]` required for secure backend | GitHub issues: python-rsa backend is retired | HIGH |
| passlib 1.7.4 latest (unmaintained since 2020) | `pip index versions passlib` | HIGH |
| bcrypt 4.1.0 yanked; 5.0.0 breaks passlib | https://pypi.org/project/bcrypt/#history (release notes) | HIGH |
| bcrypt 5.0.0 raises ValueError on >72 byte passwords | PyPI project description changelog | HIGH |
| Pydantic 2.12.5 latest | `pip index versions pydantic` | HIGH |
| pydantic-settings 2.13.1 latest | `pip index versions pydantic-settings` | HIGH |
| python-multipart 0.0.22 latest | `pip index versions python-multipart` | HIGH |
| aiofiles 25.1.0 latest | `pip index versions aiofiles` | HIGH |
| pysui 0.96.0 latest, actively maintained | `pip index versions pysui` | HIGH |
| Pydantic v2: `from_attributes=True` replaces `orm_mode` | Official Pydantic v2 migration docs | HIGH |
| Pydantic v2: `populate_by_name=True` needed for alias + field access | Official Pydantic v2 docs | HIGH |
