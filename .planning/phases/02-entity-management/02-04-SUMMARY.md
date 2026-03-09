---
phase: 02-entity-management
plan: 04
subsystem: api
tags: [fastapi, sqlalchemy, rbac, donor, school, student, application]

# Dependency graph
requires:
  - phase: 02-entity-management
    provides: activity_service, submitted_by_user_id migration (Plan 01)
  - phase: 01-foundation
    provides: require_role RBAC guard, models, schemas, dependencies
provides:
  - donor_service: browse_ngos, browse_programs, browse_students (read-only filtered)
  - school_service: register (idempotent), get_profile
  - student_service: browse_programs, submit_application, list_own_applications
  - 8 role-scoped API endpoints across donor/school/student modules
affects: [03-fund-flow, ngo_service, activity logging phase]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Role-scoped service modules: one service file per stakeholder role"
    - "Router prefix-free pattern: main.py supplies /api/{role} prefix, routers have no prefix"
    - "submitted_by_user_id ownership anchor: auth user.id → application filter (no Student ORM row needed)"
    - "Idempotent school register: SELECT existing row, no INSERT"

key-files:
  created:
    - app/services/donor_service.py
    - app/services/school_service.py
    - app/services/student_service.py
    - app/api/donor.py
    - app/api/school.py
    - app/api/student.py
  modified: []

key-decisions:
  - "Router prefix pattern: empty prefix in router, main.py supplies /api/{role} prefix — consistent with existing ngo.py pattern"
  - "student_service uses submitted_by_user_id=current_user.id as sole ownership anchor — Student ORM row not required for application ownership"
  - "school_service.register() is idempotent: SELECT only, no INSERT — School row was created at auth/register time"
  - "ConflictError raised when student applies to non-active program — fail fast with 409 before DB write"

patterns-established:
  - "Role service modules: donor_service/school_service/student_service follow same async pattern as activity_service"
  - "Ownership filtering via submitted_by_user_id: WHERE submitted_by_user_id == current_user.id"
  - "Status-filtered browse: verified/active enum checks in WHERE clause"

requirements-completed: [DONOR-01, DONOR-02, DONOR-03, SCHL-01, SCHL-02, STUD-01, STUD-02, STUD-03, RBAC-03, RBAC-04, RBAC-05]

# Metrics
duration: 3min
completed: 2026-03-09
---

# Phase 2 Plan 4: Donor, School, Student Services and Route Handlers Summary

**3 role-scoped service modules + 8 RBAC-gated endpoints: donor browse (verified/active only), school idempotent profile retrieval, student application submission with submitted_by_user_id ownership scoping**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-09T16:38:07Z
- **Completed:** 2026-03-09T16:40:50Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- `donor_service.py`: 3 read-only browse functions filtering by verified NGOs, active programs, and active students
- `school_service.py`: idempotent register (SELECT existing row from auth/register) and get_profile — no INSERT
- `student_service.py`: browse active programs, submit applications with `submitted_by_user_id=current_user.id` ownership anchor, list own applications filtered by `submitted_by_user_id == current_user.id`
- 8 route handlers across donor.py, school.py, student.py — all gated by `require_role()` with correct roles
- camelCase responses via Pydantic `model_validate()` + schema aliases (matches mock.js contract)
- Non-authorized roles receive HTTP 403 via existing `require_role()` infrastructure

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement donor_service.py and school_service.py** - `f26de91` (feat)
2. **Task 2: Implement student_service.py with submitted_by_user_id ownership scoping** - `6947e8c` (feat)
3. **Task 3: Implement donor.py, school.py, student.py route handlers** - `2b9620e` (feat)

## Files Created/Modified

- `app/services/donor_service.py` — browse_ngos (NGOStatus.verified), browse_programs (ProgramStatus.active), browse_students (StudentStatus.active)
- `app/services/school_service.py` — register (idempotent SELECT by user_id), get_profile (same)
- `app/services/student_service.py` — browse_programs, submit_application (submitted_by_user_id set), list_own_applications (submitted_by_user_id filter)
- `app/api/donor.py` — 3 GET endpoints, require_role("donor")
- `app/api/school.py` — POST /register (201), GET /profile, require_role("school")
- `app/api/student.py` — GET /programs, POST /apply (201), GET /applications, require_role("student")

## Decisions Made

- **Router prefix pattern:** Plan code showed `prefix="/donor"` in routers, but `main.py` already provides `/api/donor` prefix. Following the `ngo.py` stub pattern: empty prefix in router, `main.py` supplies full prefix. Avoids doubled path segments like `/api/donor/donor/browse/ngos`.
- **submitted_by_user_id as sole ownership anchor:** Student auth users do NOT have a `Student` ORM row until enrolled. Applications are anchored to the submitting auth user.id — no ORM join required for ownership filtering.
- **Idempotent register:** The `School` row is created at auth/register time. `school_service.register()` only SELECTs — calling it multiple times is safe (idempotent, no duplicate creation).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Router prefix adjusted to match main.py registration pattern**
- **Found during:** Task 3 (route handler implementation)
- **Issue:** Plan code specified `prefix="/donor"` (and `/schools`, `/student`) inside each router. But `main.py` already registers them at `prefix="/api/donor"`, `prefix="/api/schools"`, `prefix="/api/student"`. Using the plan's prefix would result in doubled paths like `/api/donor/donor/browse/ngos`.
- **Fix:** Used `router = APIRouter()` with no prefix — consistent with the existing `ngo.py` stub pattern and the `main.py` registration
- **Files modified:** app/api/donor.py, app/api/school.py, app/api/student.py
- **Verification:** Route counts verified (3+2+3=8), full verification script passed
- **Committed in:** `2b9620e` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — prefix conflict)
**Impact on plan:** Fix was required for correct routing. All endpoints now resolve to the paths specified in the plan's `must_haves.truths` (e.g., `/api/donor/browse/ngos`). No scope creep.

## Issues Encountered

None — all tasks completed cleanly. LSP errors visible in editor were pre-existing issues in `auth_service.py` (unrelated to this plan).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 10 requirements for Plan 04 fulfilled (DONOR-01–03, SCHL-01–02, STUD-01–03, RBAC-03–05)
- Phase 2 Entity Management now has all stakeholder surfaces implemented
- Ready for remaining Phase 2 plans (02-02, 02-03 NGO service; then fund flow phase)

---
*Phase: 02-entity-management*
*Completed: 2026-03-09*
