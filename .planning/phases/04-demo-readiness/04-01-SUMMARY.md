---
phase: 04-demo-readiness
plan: "01"
subsystem: api
tags: [public-api, seed-script, pydantic, fastapi]

# Dependency graph
requires:
  - phase: 03-fund-flow
    provides: All entity models (User, NGO, Program, Student, Donor, School, Donation, Invoice, Allocation, ActivityLog) with full CRUD services
provides:
  - 4 public endpoints: /api/public/stats, /api/public/activity, /api/public/ngos, /api/public/programs
  - Idempotent seed script populating all mock.js data
  - Entrypoint configured to run seed between migrate and uvicorn
affects: [03-fund-flow, frontend-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Public endpoints with no auth dependencies (Depends(get_db) only)
    - Idempotent seed with PostgreSQL upsert (pg_insert + on_conflict_do_update)
    - Sequence reset after explicit ID inserts to avoid conflicts with API-created records

key-files:
  created:
    - app/schemas/public.py
    - app/services/public_service.py
    - scripts/seed.py
  modified:
    - app/api/public.py (filled with 4 endpoint handlers)
    - scripts/entrypoint.sh (added seed between migrate and uvicorn)

key-decisions:
  - "Reuse AdminStatsResponse for /stats endpoint - matches mock.js platformStats shape exactly"
  - "Use ActivityLog.timestamp (not created_at) for activity feed ordering"
  - "Compute activity timestamps relative to datetime.utcnow() at seed runtime"

patterns-established:
  - "Public API pattern: router with no auth dependencies, only Depends(get_db)"
  - "Idempotent seed: upsert + sequence reset pattern"

requirements-completed: [PUBL-01, PUBL-02, PUBL-03, PUBL-04, ACTV-02, INFRA-06]

# Metrics
duration: 8min
completed: 2026-03-11
---

# Phase 4 Plan 1: Demo Readiness Public APIs Summary

**4 public API endpoints returning mock.js data shapes, plus idempotent seed script that populates all demo records with correct IDs**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-11T00:00:00Z (approximate)
- **Completed:** 2026-03-11T00:08:00Z (approximate)
- **Tasks:** 3
- **Files modified:** 5 (2 created, 2 modified)

## Accomplishments
- Created public schemas (ActivityResponse, PublicNGOResponse, PublicProgramResponse) with camelCase aliases matching mock.js field names
- Implemented 4 public endpoints: /stats (reuses AdminStatsResponse), /activity (timestamp DESC), /ngos (verified only), /programs (active only)
- Built idempotent seed script with 10 seed functions covering all entities
- All seeded IDs match mock.js suffixes (ngo-1→1, prog-3→3, stu-2→2, donor-1→1, school-2→2, don-5→5, inv-1→1)
- Updated entrypoint.sh to run seed between Alembic migrate and uvicorn

## Task Commits

Each task was committed atomically:

1. **Task 1: Public schemas + public service** - `4d039a0` (feat)
2. **Task 2: Fill public.py router (4 endpoints)** - `8be2bb7` (feat)
3. **Task 3: Idempotent seed script + entrypoint update** - `9588731` (feat)

**Plan metadata:** (to be committed after SUMMARY.md)

## Files Created/Modified

- `app/schemas/public.py` - Pydantic schemas for public API responses
- `app/services/public_service.py` - Service functions: get_activity, get_public_ngos, get_public_programs
- `app/api/public.py` - 4 public endpoint handlers (/stats, /activity, /ngos, /programs)
- `scripts/seed.py` - Idempotent seed script with 10 seed functions
- `scripts/entrypoint.sh` - Updated to run seed between migrate and uvicorn

## Decisions Made

- Reused AdminStatsResponse for /stats endpoint (already matches mock.js platformStats shape)
- Used ActivityLog.timestamp column (not created_at) for activity feed ordering
- Computed activity timestamps relative to datetime.utcnow() at seed runtime to ensure "time" field is correct on first run
- Used pg_insert().on_conflict_do_update() pattern for all seed functions (idempotent)

## Deviations from Plan

None - plan executed exactly as written.

All model fields confirmed:
- NGO: id, user_id, name, location, status (NGOStatus enum), description, avatar, color, total_funded, students_helped, programs_count, registered_date
- Program: id, ngo_id, name, description, status (ProgramStatus enum), categories, total_budget, allocated, students_enrolled, start_date, end_date
- Student: id, name, age, school, grade, guardian, location, ngo_id, program_id, scholarship_id, wallet_address, wallet_balance, total_received, status (StudentStatus enum)
- ActivityLog: id, type (ActivityType enum), color, text, timestamp, actor_id

## Issues Encountered

None

## User Setup Required

None - no external service configuration required. The seed script populates all data needed for demo.

## Next Phase Readiness

- Public API endpoints are ready for frontend integration (Plan 03)
- Seed script is ready to populate database on first deploy
- All mock.js data shapes are available via public endpoints
- Ready for frontend to fetch: platform stats, activity feed, verified NGOs, active programs

---
*Phase: 04-demo-readiness*
*Completed: 2026-03-11*
