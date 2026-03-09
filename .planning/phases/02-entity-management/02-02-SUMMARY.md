---
phase: 02-entity-management
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, admin, rbac]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "Base ORM model, AsyncSession, require_role dependency, exception handlers"
  - phase: 02-entity-management
    plan: 01
    provides: "activity_service.log() callable, ActivityLog model with color column"
provides:
  - "AdminStatsResponse schema with totalDonations, totalStudents, totalNGOs, totalPrograms, totalSchools, fundsAllocated, fundsUtilized (camelCase aliases)"
  - "BlacklistResponse schema with ngos and students lists"
  - "5 admin service functions: get_stats, list_ngos, update_ngo_status, get_blacklist, update_student_status"
  - "9 admin API endpoints all gated by require_role('admin')"
  - "NGO verification workflow (pending → verified/rejected → blacklisted → restored)"
affects:
  - 02-entity-management (plans 03-05 may reference admin service patterns)
  - 03-fund-flow
  - 04-demo-readiness

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Thin route handlers: exactly one admin_service call per handler, no business logic in routes"
    - "Service layer owns all db.commit() calls — no commits in route handlers"
    - "activity_service.log() called BEFORE db.commit() for atomic transaction logging"
    - "action_map dict pattern in update_ngo_status for clean status→enum mapping"

key-files:
  created:
    - app/schemas/admin.py
  modified:
    - app/services/admin_service.py
    - app/api/admin.py

key-decisions:
  - "total_ngos field alias is 'totalNGOs' (capital NGOs) — exact match to mock.js platformStats.totalNGOs"
  - "list_ngos() returns empty list on invalid status string — graceful degradation, no 422 error"
  - "action_map dict in update_ngo_status maps action name to (NGOStatus, log_type, log_text) tuple — clean, extensible pattern"
  - "restore action maps to NGOStatus.pending not NGOStatus.verified — NGO re-enters review queue"

patterns-established:
  - "Admin route pattern: require_role('admin') dependency on every endpoint, no exceptions"
  - "Status mutation pattern: fetch → validate → mutate → log → commit → return validated model"

requirements-completed:
  - ADMN-01
  - ADMN-02
  - ADMN-03
  - ADMN-04
  - ADMN-05
  - RBAC-02

# Metrics
duration: 2min
completed: 2026-03-09
---

# Phase 2 Plan 02: Admin Service and Route Handlers Summary

**9 admin API endpoints with NGO verification workflow, blacklist management, and dashboard stats — all gated by require_role('admin') with atomic activity logging**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-09T16:37:50Z
- **Completed:** 2026-03-09T16:39:58Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `AdminStatsResponse` schema with exact camelCase aliases matching mock.js (`totalNGOs` not `totalNgos`)
- Implemented 5 admin service functions with proper atomicity (activity_service.log() before db.commit())
- Registered 9 admin API endpoints: GET /dashboard, GET /ngos, PATCH /ngos/{id}/{verify|reject|blacklist|restore}, GET /blacklist, PATCH /students/{id}/{blacklist|restore}
- All endpoints gated by `require_role("admin")` — non-admin receives HTTP 403

## Task Commits

Each task was committed atomically:

1. **Task 1: Create AdminStatsResponse and BlacklistResponse schemas** - `aacc543` (feat)
2. **Task 2: Implement admin_service.py with 5 service functions** - `8c1d9b5` (feat)
3. **Task 3: Implement admin.py route handlers (9 endpoints)** - `8e9549d` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `app/schemas/admin.py` — AdminStatsResponse and BlacklistResponse Pydantic schemas with camelCase aliases
- `app/services/admin_service.py` — 5 async service functions (get_stats, list_ngos, update_ngo_status, get_blacklist, update_student_status)
- `app/api/admin.py` — 9 admin route handlers all protected by require_role("admin")

## AdminStatsResponse Field Names (FE Contract)

```python
AdminStatsResponse.model_dump(by_alias=True) keys:
  - "totalDonations"   # SUM(Donation.amount)
  - "totalStudents"    # COUNT(Student.id)
  - "totalNGOs"        # COUNT(NGO.id)  ← capital NGOs, matches mock.js exactly
  - "totalPrograms"    # COUNT(Program.id)
  - "totalSchools"     # COUNT(School.id)
  - "fundsAllocated"   # SUM(NGO.total_funded)
  - "fundsUtilized"    # SUM(Student.total_received)
```

## Decisions Made

- **`totalNGOs` alias** (not `totalNgos`): Exact match to `platformStats.totalNGOs` in mock.js — camelCase with NGO as acronym
- **Graceful degradation on invalid status**: `list_ngos()` returns `[]` on invalid status string instead of raising HTTP 422 — cleaner API behavior
- **restore → pending** (not → verified): NGO re-enters the review queue after restoration, consistent with the business requirement that blacklisted NGOs need re-verification
- **action_map dict pattern**: Maps action name string to `(NGOStatus, log_type, log_text)` tuple in `update_ngo_status` — clean, extensible, easy to add new transitions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Admin endpoints fully implemented and ready for integration testing
- Plans 02-03 through 02-05 (NGO, Student, Donor services) can follow the same thin-route + service-layer pattern established here
- `activity_service.log()` pattern confirmed working in update_ngo_status and update_student_status

## Self-Check: PASSED

All created files found on disk:
- `app/schemas/admin.py` ✓
- `app/services/admin_service.py` ✓
- `app/api/admin.py` ✓

All 3 task commits verified in git log:
- `aacc543` feat(02-02): create AdminStatsResponse and BlacklistResponse schemas ✓
- `8c1d9b5` feat(02-02): implement admin_service.py with 5 service functions ✓
- `8e9549d` feat(02-02): implement admin.py route handlers (9 endpoints) ✓

---
*Phase: 02-entity-management*
*Completed: 2026-03-09*
