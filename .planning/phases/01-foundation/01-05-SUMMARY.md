---
phase: 01-foundation
plan: 05
subsystem: infra
tags: [fastapi, starlette, alembic, postgresql, docker, exceptions, migrations]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: FastAPI app, exception handlers, ORM models, Alembic configuration

provides:
  - StarletteHTTPException handler returning {detail, code, statusCode} shape for all HTTP errors
  - Real Alembic DDL migration creating all 12 tables with correct FK dependencies and enum types
  - scripts/entrypoint.sh that auto-runs migrations before uvicorn starts in Docker
  - Self-contained docker compose up workflow (no manual alembic upgrade head needed)

affects: [all phases - DB tables must exist before any service can run]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "StarletteHTTPException handler registered after RequestValidationError to intercept bare 404/405/etc"
    - "Alembic async migration: sa.Enum().create() fires before_create twice via SQLAlchemy event system — use op.execute() with DO $$ BEGIN...EXCEPTION WHEN duplicate_object THEN NULL; END $$ instead"
    - "asyncpg does not support multiple statements in one op.execute() — each CREATE TABLE/INDEX must be its own call"
    - "CREATE TABLE IF NOT EXISTS and DO blocks make the migration idempotent against partial runs"
    - "Dockerfile CMD must use [\"/bin/sh\", \"/app/scripts/entrypoint.sh\"] (absolute path, explicit shell) — exec-form with relative path silently falls back to uvicorn without running migrations"
    - "entrypoint.sh with set -e ensures migrations must succeed before uvicorn starts"
    - "exec uvicorn in entrypoint replaces shell process for correct signal propagation"
    - "TIMESTAMP WITHOUT TIME ZONE columns require naive datetimes — use datetime.now(timezone.utc).replace(tzinfo=None) before storing"

key-files:
  created:
    - scripts/entrypoint.sh
  modified:
    - app/core/exceptions.py
    - alembic/versions/0001_initial_schema.py
    - Dockerfile

key-decisions:
  - "StarletteHTTPException handler placed after RequestValidationError and before generic Exception handler"
  - "Switched migration enum creation from sa.Enum().create(op.get_bind()) to op.execute() with PostgreSQL DO blocks — SQLAlchemy's before_create event fires a second CREATE TYPE even when create_type=False is set on columns, causing DuplicateObjectError through the asyncpg adapter"
  - "Rewrote all op.create_table() calls as op.execute(CREATE TABLE IF NOT EXISTS ...) raw SQL — avoids the SQLAlchemy type event system entirely and makes migration idempotent"
  - "Dockerfile CMD changed from [\"scripts/entrypoint.sh\"] to [\"/bin/sh\", \"/app/scripts/entrypoint.sh\"] — the exec-form with relative path was silently not running the script; entrypoint logs (Running Alembic migrations...) were absent"
  - "#!/bin/sh used (not bash) for Debian slim base image compatibility"
  - "exec uvicorn used (not plain uvicorn) for correct signal handling in containers"
  - "datetime.now(timezone.utc).replace(tzinfo=None) used when storing expires_at — TIMESTAMP WITHOUT TIME ZONE columns reject timezone-aware datetimes through asyncpg"

patterns-established:
  - "All custom HTTP error responses use {detail, code, statusCode} shape — now covers Starlette 404/405 too"
  - "Table creation order in migration respects FK dependency chain: users -> ngos -> programs -> schools -> ..."
  - "Alembic async migrations: always use op.execute() with raw SQL, never sa.Enum().create() or op.create_table() with typed enum columns — the asyncpg adapter breaks SQLAlchemy's checkfirst mechanism"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, AUTH-01, AUTH-02]

# Metrics
duration: 6min
completed: 2026-03-09
---

# Phase 1 Plan 05: Gap Closure — Exception Handler + Migration + Docker Entrypoint Summary

**StarletteHTTPException handler wired to return `{detail, code, statusCode}` shape; real Alembic DDL migration creating all 12 PostgreSQL tables via raw SQL `op.execute()`; Docker entrypoint auto-running migrations on `docker compose up`; timezone-naive datetimes stored in refresh_tokens.**

## Performance

- **Duration:** ~40 min (including debugging)
- **Started:** 2026-03-09T14:41:03Z
- **Completed:** 2026-03-09T15:58:00Z
- **Tasks:** 3 + post-debug fixes
- **Files modified:** 5

## Accomplishments
- Fixed UAT blocker: `GET /api/nonexistent` now returns `{"detail":"Not Found","code":"NOT_FOUND","statusCode":404}` instead of bare FastAPI `{"detail":"Not Found"}`
- Fixed UAT blocker: `alembic upgrade head` now creates all 12 tables (users, ngos, programs, schools, refresh_tokens, donors, students, activity_logs, file_records, donations, invoices, scholarship_applications) with correct FK constraints, ondelete rules, indexes, and PostgreSQL enum types
- Docker entrypoint auto-applies migrations: `docker compose up --build` is fully self-contained — no manual `alembic upgrade head` needed
- `POST /api/auth/register` returns tokens successfully — confirmed working end-to-end

## Task Commits

Each task was committed atomically:

1. **Task 1: Register StarletteHTTPException handler** - `d13b56b` (fix)
2. **Task 2: Write real DDL migration for all 12 tables** - `df8000e` (feat) + subsequent rework
3. **Task 3: Add entrypoint script and wire into Dockerfile** - `bf0b0ee` (feat) + subsequent CMD fix

**Plan metadata:** `2398a61` (docs)

## Files Created/Modified
- `app/core/exceptions.py` — Added `from starlette.exceptions import HTTPException as StarletteHTTPException` import and `starlette_http_handler` inside `register_exception_handlers()`; maps status codes to code strings (NOT_FOUND, BAD_REQUEST, etc.)
- `alembic/versions/0001_initial_schema.py` — Rewrote from `op.create_table()` + `sa.Enum().create()` to pure `op.execute()` with raw SQL (`CREATE TYPE ... IF NOT EXISTS` via DO blocks, `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) — required because SQLAlchemy's `before_create` event fires a duplicate `CREATE TYPE` through asyncpg even when `create_type=False` is set
- `scripts/entrypoint.sh` — New shell script: `#!/bin/sh`, `set -e`, `alembic upgrade head`, `exec uvicorn app.main:app --host 0.0.0.0 --port 8000`
- `Dockerfile` — CMD fixed from `["scripts/entrypoint.sh"]` to `["/bin/sh", "/app/scripts/entrypoint.sh"]`; relative-path exec-form was silently skipping migrations; also added `chmod +x scripts/entrypoint.sh` to RUN layer
- `app/services/auth_service.py` — All three `expires_at` assignments changed to `datetime.now(timezone.utc).replace(tzinfo=None)` — asyncpg rejects timezone-aware datetimes into `TIMESTAMP WITHOUT TIME ZONE` columns

## Decisions Made
- StarletteHTTPException handler positioned after RequestValidationError and before generic Exception handler — correct interception order for Starlette's middleware chain
- Switched from `sa.Enum().create(op.get_bind(), checkfirst=True)` to `op.execute("DO $$ BEGIN CREATE TYPE ... EXCEPTION WHEN duplicate_object THEN NULL; END $$")` — the SQLAlchemy `checkfirst` mechanism doesn't work through the asyncpg greenlet bridge; the before_create event fires anyway
- Each `op.execute()` call contains exactly one statement — asyncpg raises `cannot insert multiple commands into a prepared statement` for multi-statement strings
- All `op.create_table()` calls replaced with `op.execute("CREATE TABLE IF NOT EXISTS ...")` — avoids the SQLAlchemy type event system entirely; inline `sa.Enum` columns trigger type creation regardless of `create_type=False`
- Dockerfile CMD uses absolute path + explicit `/bin/sh` — exec-form Docker CMD with a relative script path doesn't resolve correctly from WORKDIR in all environments
- `datetime.now(timezone.utc).replace(tzinfo=None)` for DB storage — column is `TIMESTAMP WITHOUT TIME ZONE`; Python's asyncpg adapter raises `DataError: invalid input for query argument` when given aware datetimes

## Deviations from Plan

The migration implementation required significant rework beyond the original plan:

1. **`sa.Enum().create()` approach failed** — SQLAlchemy's event system fires a second `CREATE TYPE` via `before_create` on `op.create_table()` calls, even with `create_type=False` on columns, because the asyncpg bridge bypasses the `checkfirst` check. Switched to raw SQL DO blocks.
2. **Multi-statement `op.execute()` failed** — asyncpg requires each statement in its own call. Rewrote to individual `op.execute()` per statement (9 enums + 12 tables + ~15 indexes = ~36 separate calls).
3. **Dockerfile CMD didn't invoke entrypoint** — `["scripts/entrypoint.sh"]` with a relative path silently fell through to... nothing (container exited). Fixed to `["/bin/sh", "/app/scripts/entrypoint.sh"]`.
4. **Timezone mismatch in auth_service** — after migrations ran, register returned 500 due to `can't subtract offset-naive and offset-aware datetimes` in asyncpg. Fixed in auth_service.py.

## Issues Encountered

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `DuplicateObjectError: type "userrole" already exists` | `sa.Enum.create()` + `before_create` event both fire CREATE TYPE | Raw SQL DO blocks with EXCEPTION WHEN duplicate_object |
| `cannot insert multiple commands into a prepared statement` | asyncpg prepared statement limit | One statement per `op.execute()` call |
| Entrypoint script not running (no migration logs) | Dockerfile CMD `["scripts/entrypoint.sh"]` relative path in exec-form | `["/bin/sh", "/app/scripts/entrypoint.sh"]` absolute path |
| `DataError: can't subtract offset-naive and offset-aware datetimes` | `datetime.now(timezone.utc)` stored into `TIMESTAMP WITHOUT TIME ZONE` column | `.replace(tzinfo=None)` before storing |

## User Setup Required
None — `docker compose up --build` is fully self-contained after these fixes.

## Next Phase Readiness
- UAT blockers resolved: exception shape correct, all 12 DB tables created by migration, Docker auto-migration works, registration endpoint returns tokens
- `POST /api/auth/register` confirmed working end-to-end
- Phase 1 Foundation is complete — ready to transition to Phase 2 Entity Management

---
*Phase: 01-foundation*
*Completed: 2026-03-09*

## Self-Check: PASSED

- FOUND: app/core/exceptions.py
- FOUND: alembic/versions/0001_initial_schema.py (rewritten as raw SQL op.execute())
- FOUND: scripts/entrypoint.sh
- FOUND: Dockerfile (CMD fixed to absolute path + explicit /bin/sh)
- FOUND: app/services/auth_service.py (timezone-naive expires_at fix)
- FOUND: .planning/phases/01-foundation/01-05-SUMMARY.md
- FOUND commit d13b56b: fix(01-05): register StarletteHTTPException handler
- FOUND commit df8000e: feat(01-05): write real DDL migration for all 12 tables
- FOUND commit bf0b0ee: feat(01-05): add entrypoint script and wire into Dockerfile
- VERIFIED: docker compose up --build runs migrations then starts uvicorn
- VERIFIED: POST /api/auth/register returns 200 with accessToken + refreshToken
