---
phase: 03-fund-flow
plan: 03
subsystem: api
tags: [invoice, allocation, blockchain, ngo, endpoint, service]

# Dependency graph
requires:
  - phase: 03-fund-flow
    provides: Allocation model from 03-01
provides:
  - Five NGO invoice and allocation endpoints
  - Ownership-scoped queries via ngo_id
  - Blockchain-integrated transaction flow (settle_invoice, allocate_funds)
affects: [03-fund-flow-wave2-plans]

# Tech tracking
tech-stack:
  added: []
  patterns: [async service functions, blockchain injection via Depends, atomic transaction flow]

key-files:
  created: []
  modified:
    - app/services/ngo_service.py
    - app/api/ngo.py

key-decisions:
  - "blockchain.settle_invoice() called BEFORE invoice status mutation and db.commit()"
  - "blockchain.allocate_funds() called BEFORE Allocation insert and db.commit()"
  - "ForbiddenError raised if invoice.ngo_id != ngo.id (ownership check)"
  - "AppValidationError raised if invoice.status != pending"

patterns-established:
  - "Invoice approval workflow: blockchain tx first, then status mutation, then commit"
  - "Allocation workflow: blockchain tx, update student wallet/program allocated, then commit"

requirements-completed: [NGO-08, NGO-09, NGO-10, NGO-11]

# Metrics
duration: <1min
completed: 2026-03-10T00:15:00Z
---

# Phase 3 Plan 3: NGO Invoice & Allocation Endpoints Summary

**Five NGO invoice and allocation endpoints with blockchain transaction support**

## Performance

- **Duration:** <1 min
- **Started:** 2026-03-10T00:14:00Z
- **Completed:** 2026-03-10T00:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- list_invoices (NGO-08) - returns NGO's invoices scoped by ngo_id
- approve_invoice (NGO-09) - blockchain.settle_invoice() before commit, logs activity atomically
- reject_invoice (NGO-09) - no blockchain call, status → rejected
- create_allocation (NGO-10) - blockchain.allocate_funds() before commit, updates student wallet
- list_allocations (NGO-11) - returns NGO's allocations scoped by ngo_id

## Task Commits

Each task was committed atomically:

1. **Task 1: NGO service — invoice + allocation methods** - `7336f12` (feat)
2. **Task 2: NGO router — invoice + allocation endpoints** - `7336f12` (feat, same commit)

## Files Created/Modified
- `app/services/ngo_service.py` - Added five service functions
- `app/api/ngo.py` - Added five endpoints

## Decisions Made
- blockchain.settle_invoice() called BEFORE invoice status mutation and db.commit()
- blockchain.allocate_funds() called BEFORE Allocation insert and db.commit()
- ForbiddenError raised if invoice.ngo_id != ngo.id (ownership check)
- AppValidationError raised if invoice.status != pending

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- NGO invoice and allocation endpoints complete (NGO-08, NGO-09, NGO-10, NGO-11)
- Ready for remaining Phase 3 plans

---
*Phase: 03-fund-flow*
*Completed: 2026-03-10*
