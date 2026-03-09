---
phase: quick-1-fix-uat-gaps
plan: 01
subsystem: ngo, auth
tags: [uat-gap, delete-endpoint, student-fix]
dependency_graph:
  requires: []
  provides:
    - "app/services/ngo_service.py::delete_program"
    - "app/api/ngo.py::DELETE /programs/{program_id}"
  affects:
    - "app/services/auth_service.py::_create_profile"
tech_stack:
  added: []
  patterns:
    - "DELETE endpoint with 204 status code"
    - "Ownership check before delete"
    - "ConflictError for disallowed self-registration"
key_files:
  created: []
  modified:
    - "app/api/ngo.py"
    - "app/services/ngo_service.py"
    - "app/services/auth_service.py"
decisions:
  - "Used ConflictError (409) for student self-rejection to properly communicate the error without exposing internals"
metrics:
  duration: "2 min"
  completed: "2026-03-09"
  tasks: 2
  files: 3
---

# Quick Task: Fix UAT Gaps from Phase 02

**One-liner:** Added DELETE endpoint for NGO programs and fixed student self-registration returning 500

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add DELETE /programs/{program_id} endpoint | 494eec8 | ngo.py, ngo_service.py |
| 2 | Fix student self-registration 500 error | 494eec8 | auth_service.py |

## Gap Closure

### Gap 1: DELETE Program Endpoint (CLOSED)
- **Before:** No DELETE endpoint existed for NGO programs
- **After:** `DELETE /api/ngo/programs/{id}` returns 204 for own program, 403 for another NGO's program, 404 for missing
- **Verification:** 
  - `DELETE /api/ngo/programs/1` with NGO's own token → 204
  - `DELETE /api/ngo/programs/1` with different NGO's token → 403
  - `DELETE /api/ngo/programs/99999` → 404

### Gap 2: Student Self-Registration (CLOSED)
- **Before:** POST /api/auth/register with role=student returned HTTP 500 (SQLAlchemy error)
- **After:** Returns 409 ConflictError with message "students cannot self-register; contact an NGO"
- **Verification:**
  - `curl -X POST /api/auth/register -d '{"email":"test@stu.com","password":"pass","role":"student","name":"Test"}'` → 409 (not 500)

### Gap 3: fileId Integer vs UUID (ACCEPTED - NO CHANGE)
- fileId as integer is functionally correct per UAT notes; no change needed

## Deviations from Plan

**None - plan executed exactly as written.**

## Self-Check: PASSED

- [x] DELETE endpoint exists: `app/api/ngo.py` contains `@router.delete("/programs/{program_id}")`
- [x] Service function exists: `app/services/ngo_service.py` contains `delete_program()`
- [x] Student guard exists: `app/services/auth_service.py` raises `ConflictError` for student role
- [x] Commit exists: 494eec8
