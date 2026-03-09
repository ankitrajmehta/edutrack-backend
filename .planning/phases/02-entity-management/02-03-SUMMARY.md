---
phase: 02-entity-management
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, blockchain, ngo, programs, students, applications]

# Dependency graph
requires:
  - phase: 02-entity-management plan 01
    provides: Phase 2 DB migration (rejection_reason column, ApplicationStatus enum), ActivityLog model, activity_service
  - phase: 01-foundation
    provides: get_db, require_role, get_blockchain, BlockchainService protocol, NotFoundError, ForbiddenError, ConflictError

provides:
  - NGOStatsResponse and ApplicationRejectRequest schemas in app/schemas/ngo.py
  - ngo_service.py with _create_student() helper and 11 async service functions
  - app/api/ngo.py with 11 route handlers all protected by get_current_ngo dependency

affects:
  - 03-fund-flow (register_student path used for scholarship allocation)
  - 04-demo-readiness (NGO dashboard stats endpoint)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_create_student() shared helper pattern: direct registration and accept-application share same creation path"
    - "Blockchain atomicity: db.flush() → create_wallet() → activity_service.log() → db.commit()"
    - "get_current_ngo local dependency: resolves NGO profile from authenticated user, raises 404 if missing"
    - "NGO ownership enforcement: program.ngo_id != ngo.id raises ForbiddenError"
    - "db.refresh(ngo) after _create_student() commit to avoid stale counter state"

key-files:
  created: []
  modified:
    - app/schemas/ngo.py
    - app/services/ngo_service.py
    - app/api/ngo.py

key-decisions:
  - "_create_student() is module-private helper shared by register_student and accept_application — single canonical student creation path"
  - "get_current_ngo defined locally in ngo.py (not dependencies.py) — it's NGO-domain-specific"
  - "db.refresh(ngo) called after _create_student() commit to refresh stale ORM state before updating counters"
  - "Scholarship ID format: EDU-YYYY-XXXXX with 10-retry collision avoidance"
  - "list_applications returns only pending status — NGO workflow expectation"

patterns-established:
  - "flush-wallet-log-commit: canonical blockchain atomicity pattern for student creation"
  - "Ownership check: load record, check .ngo_id != ngo.id, raise ForbiddenError"
  - "Local dependency for entity-scoped auth: get_current_ngo pattern reusable for other entities"

requirements-completed:
  - NGO-01
  - NGO-02
  - NGO-03
  - NGO-04
  - NGO-05
  - NGO-06
  - NGO-07
  - RBAC-02

# Metrics
duration: 2min
completed: 2026-03-09
---

# Phase 2 Plan 03: NGO Service and API Summary

**NGO service with _create_student() shared helper, blockchain wallet atomicity (flush→wallet→log→commit), and 11 FastAPI route handlers scoped to authenticated NGO via get_current_ngo dependency**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-09T16:37:54Z
- **Completed:** 2026-03-09T16:40:22Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- NGOStatsResponse schema with camelCase aliases (programsCount, studentsHelped, fundsAllocated)
- ngo_service.py: _create_student() shared helper enforcing blockchain atomicity — used by both register_student and accept_application
- 11 NGO endpoints all protected by get_current_ngo dependency (NGO ownership enforced throughout)
- Scholarship ID generation: EDU-YYYY-XXXXX with retry-on-collision (max 10 attempts)
- Cross-NGO access denied via ForbiddenError (HTTP 403) on all program/student/application operations

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NGOStatsResponse and ApplicationRejectRequest schemas** - `42f41ff` (feat)
2. **Task 2: Implement ngo_service.py with _create_student() helper** - `02f1731` (feat)
3. **Task 3: Implement ngo.py route handlers with get_current_ngo** - `debedb6` (feat)

## Files Created/Modified
- `app/schemas/ngo.py` - Added NGOStatsResponse (dashboard stats) and ApplicationRejectRequest (reject endpoint body)
- `app/services/ngo_service.py` - Full implementation: _create_student() helper + 11 public service functions
- `app/api/ngo.py` - 11 route handlers with get_current_ngo local dependency

## Decisions Made
- **_create_student() is the canonical student creation path**: both direct registration (POST /ngo/students) and application acceptance (PATCH /ngo/applications/{id}/accept) use the same helper — no duplication, no drift
- **get_current_ngo defined locally in ngo.py**: NGO profile resolution is domain-specific to the NGO API; not appropriate for the global dependencies.py
- **db.refresh(ngo) after _create_student() commit**: _create_student() internally commits, which expires SQLAlchemy's in-memory ORM state — refresh is mandatory before updating ngo.students_helped counter
- **list_applications returns only pending**: NGO acceptance workflow expectation — accepted/rejected applications are historical and surfaced elsewhere

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- NGO service complete: dashboard, program CRUD, student registration, application accept/reject
- _create_student() signature documented: `(db, ngo, name, age, school, grade, guardian, location, program_id, blockchain, actor_id) -> Student`
- Phase 3 Fund Flow can directly call ngo_service functions or use the blockchain abstraction pattern
- Remaining Phase 2 plans: donor, school, and student management services

---
*Phase: 02-entity-management*
*Completed: 2026-03-09*

## Self-Check: PASSED

- FOUND: app/schemas/ngo.py
- FOUND: app/services/ngo_service.py
- FOUND: app/api/ngo.py
- FOUND: .planning/phases/02-entity-management/02-03-SUMMARY.md
- Commits verified: 42f41ff, 02f1731, debedb6 — all present in git log
- Final verification command: `python -c "from app.api.ngo import router; assert len(router.routes) == 11"` — PASSED
