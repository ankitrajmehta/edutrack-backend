---
phase: 03-fund-flow
plan: 01
subsystem: database
tags: [allocation, orm, migration, schema, pydantic]

# Dependency graph
requires:
  - phase: 02-entity-management
    provides: NGO, Program, Student models with relationships
provides:
  - Allocation ORM model for fund allocation tracking
  - AllocationCreate/AllocationResponse Pydantic schemas
  - DonationDetailResponse with fund-flow chain fields
  - Alembic migration 0003 creating allocations table
affects: [03-fund-flow-wave2-plans]

# Tech tracking
tech-stack:
  added: []
  patterns: [SQLAlchemy ORM model, Pydantic schema inheritance, Alembic raw SQL migration]

key-files:
  created:
    - app/models/allocation.py
    - app/schemas/allocation.py
    - alembic/versions/0003_phase3_allocations.py
  modified:
    - app/models/__init__.py
    - app/schemas/donation.py

key-decisions:
  - "Used raw op.execute() SQL in migration to match existing 0002 pattern"
  - "Created FundFlowAllocation/FundFlowInvoice as separate classes for reusability"
  - "DonationDetailResponse extends DonationResponse to inherit all base fields"

patterns-established:
  - "Allocation schema with student_id OR program_id (mutually exclusive allocation target)"
  - "DonationDetailResponse for complete fund-flow chain serialization"

requirements-completed: [NGO-10, NGO-11]

# Metrics
duration: <1min
completed: 2026-03-09
---

# Phase 3 Plan 1: Allocation Foundation Summary

**Allocation ORM model with Pydantic schemas and Alembic migration for fund-flow chain**

## Performance

- **Duration:** <1 min
- **Started:** 2026-03-09T18:15:23Z
- **Completed:** 2026-03-09T18:15:23Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Allocation ORM model with ngo_id, student_id, program_id, amount, date, tx_hash columns
- AllocationCreate and AllocationResponse Pydantic schemas with camelCase aliases
- FundFlowAllocation and FundFlowInvoice summary schemas for embedded use
- DonationDetailResponse extending DonationResponse with allocations and invoices lists
- Alembic migration 0003 with CREATE TABLE IF NOT EXISTS, chained from 0002

## Task Commits

Each task was committed atomically:

1. **Task 1: Allocation ORM model + migration 0003** - `68dcaf8` (feat)
2. **Task 2: Allocation schemas + DonationDetailResponse** - `6917fce` (feat)

## Files Created/Modified
- `app/models/allocation.py` - Allocation ORM model with relationships
- `app/models/__init__.py` - Added Allocation import and export
- `app/schemas/allocation.py` - AllocationCreate and AllocationResponse schemas
- `app/schemas/donation.py` - Added FundFlowAllocation, FundFlowInvoice, DonationDetailResponse
- `alembic/versions/0003_phase3_allocations.py` - Migration creating allocations table

## Decisions Made
- Used raw `op.execute()` SQL in migration to match existing 0002 pattern
- Created FundFlowAllocation/FundFlowInvoice as separate classes for reusability
- DonationDetailResponse extends DonationResponse to inherit all base fields

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Allocation model and schemas ready for Wave 2 plans (02, 03, 04)
- Migration can be applied with `alembic upgrade head`

---
*Phase: 03-fund-flow*
*Completed: 2026-03-09*
