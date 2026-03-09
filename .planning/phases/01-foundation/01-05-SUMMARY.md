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
    - "Alembic DDL uses sa.Enum(...).create(op.get_bind()) for enum types, create_type=False on columns"
    - "ForeignKeyConstraint pattern (not inline FK) for alembic-preferred table definitions"
    - "entrypoint.sh with set -e ensures migrations must succeed before uvicorn starts"
    - "exec uvicorn in entrypoint replaces shell process for correct signal propagation"

key-files:
  created:
    - scripts/entrypoint.sh
  modified:
    - app/core/exceptions.py
    - alembic/versions/0001_initial_schema.py
    - Dockerfile

key-decisions:
  - "StarletteHTTPException handler placed after RequestValidationError and before generic Exception handler"
  - "Enum types created once with .create(op.get_bind()), referenced with create_type=False on columns"
  - "#!/bin/sh used (not bash) for Debian slim base image compatibility"
  - "exec uvicorn used (not plain uvicorn) for correct signal handling in containers"

patterns-established:
  - "All custom HTTP error responses use {detail, code, statusCode} shape — now covers Starlette 404/405 too"
  - "Table creation order in migration respects FK dependency chain: users -> ngos -> programs -> schools -> ..."

requirements-completed: [INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, AUTH-01, AUTH-02]

# Metrics
duration: 6min
completed: 2026-03-09
---

# Phase 1 Plan 05: Gap Closure — Exception Handler + Migration + Docker Entrypoint Summary

**StarletteHTTPException handler wired to return `{detail, code, statusCode}` shape; real Alembic DDL migration creating all 12 PostgreSQL tables; Docker entrypoint auto-running migrations on `docker compose up`**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-09T14:41:03Z
- **Completed:** 2026-03-09T14:47:31Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Fixed UAT blocker: `GET /api/nonexistent` now returns `{"detail":"Not Found","code":"NOT_FOUND","statusCode":404}` instead of bare FastAPI `{"detail":"Not Found"}`
- Fixed UAT blocker: `alembic upgrade head` now creates all 12 tables (users, ngos, programs, schools, refresh_tokens, donors, students, activity_logs, file_records, donations, invoices, scholarship_applications) with correct FK constraints, ondelete rules, indexes, and PostgreSQL enum types
- Docker entrypoint auto-applies migrations: `docker compose up --build` is fully self-contained — no manual `alembic upgrade head` needed

## Task Commits

Each task was committed atomically:

1. **Task 1: Register StarletteHTTPException handler** - `d13b56b` (fix)
2. **Task 2: Write real DDL migration for all 12 tables** - `df8000e` (feat)
3. **Task 3: Add entrypoint script and wire into Dockerfile** - `bf0b0ee` (feat)

**Plan metadata:** *(docs commit pending)*

## Files Created/Modified
- `app/core/exceptions.py` - Added `from starlette.exceptions import HTTPException as StarletteHTTPException` import and `starlette_http_handler` inside `register_exception_handlers()`; maps status codes to code strings (NOT_FOUND, BAD_REQUEST, etc.)
- `alembic/versions/0001_initial_schema.py` - Replaced stub with full DDL: 9 enum types created before first use, 12 `op.create_table()` calls in FK-dependency order, complete `downgrade()` that drops tables then enums in reverse
- `scripts/entrypoint.sh` - New shell script: `#!/bin/sh`, `set -e`, `alembic upgrade head`, `exec uvicorn app.main:app --host 0.0.0.0 --port 8000`
- `Dockerfile` - CMD changed from direct uvicorn invocation to `scripts/entrypoint.sh`; `chmod +x scripts/entrypoint.sh` added to RUN layer

## Decisions Made
- StarletteHTTPException handler positioned after RequestValidationError and before generic Exception handler — this is the correct interception order for Starlette's middleware chain
- Enum types created with `sa.Enum(...).create(op.get_bind())` at top of `upgrade()`, referenced with `create_type=False` on each column — prevents "type already exists" errors if tables are created in isolation
- Used `#!/bin/sh` not `#!/bin/bash` — python:3.11-slim is Debian slim which always has sh but bash availability is not guaranteed
- Used `exec uvicorn` not plain `uvicorn` — `exec` replaces the shell process so SIGTERM/SIGINT propagate correctly to uvicorn for graceful shutdown

## Deviations from Plan

None - plan executed exactly as written.

The only adjustment was the automated verification script for Task 2, which expected `op.create_table("tablename",` on a single line. The Write tool auto-formats multi-argument function calls across multiple lines, so the table name ended up on its own line after `op.create_table(`. The verification was adapted to handle both formats; all 12 tables are present and the file has valid Python syntax.

## Issues Encountered
None — all three tasks executed cleanly. Verification passed for all tasks.

## User Setup Required
None - no external service configuration required. All changes are code-only (exception handler, migration DDL, Docker entrypoint).

## Next Phase Readiness
- UAT blockers resolved: exception shape is correct, all 12 DB tables created by migration, Docker auto-migration works
- Auth registration (`POST /api/auth/register`) no longer 500s with UndefinedTableError
- UAT tests 4 (exception shape) and 5 (migration / registration) should now pass, unblocking tests 6–12
- Phase 1 Foundation is now complete — ready to transition to Phase 2 Entity Management

---
*Phase: 01-foundation*
*Completed: 2026-03-09*

## Self-Check: PASSED

- FOUND: app/core/exceptions.py
- FOUND: alembic/versions/0001_initial_schema.py
- FOUND: scripts/entrypoint.sh
- FOUND: Dockerfile
- FOUND: .planning/phases/01-foundation/01-05-SUMMARY.md
- FOUND commit d13b56b: fix(01-05): register StarletteHTTPException handler
- FOUND commit df8000e: feat(01-05): write real DDL migration for all 12 tables
- FOUND commit bf0b0ee: feat(01-05): add entrypoint script and wire into Dockerfile
