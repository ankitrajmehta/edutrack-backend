---
status: testing
phase: 02-entity-management
source: 02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md, 02-04-SUMMARY.md, 02-05-SUMMARY.md
started: 2026-03-09T17:00:00Z
updated: 2026-03-09T17:00:00Z
---

## Current Test

number: 1
name: Cold Start Smoke Test
expected: |
  Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, any seed/migration completes, and a primary query (health check, homepage load, or basic API call) returns live data.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, any seed/migration completes, and a primary query (health check, homepage load, or basic API call) returns live data.
result: [pending]

### 2. Alembic Migration 0002 Applies Clean
expected: Running `alembic upgrade head` (or starting fresh) applies migration 0002 without error. The database gains three new columns: `color` on activity_logs, `rejection_reason` and `submitted_by_user_id` on scholarship_applications.
result: [pending]

### 3. Activity Logging Records with Color
expected: When any admin/NGO action triggers activity logging (e.g., verifying an NGO, rejecting an application), the resulting activity_log row has a non-null `color` field matching the action type (blue for verify/program, red for blacklist, purple for allocation, green for donation, amber for invoice). Unknown types get "gray".
result: [pending]

### 4. Admin Dashboard Stats
expected: Authenticated admin calls `GET /api/admin/dashboard`. Response returns JSON with keys: `totalDonations`, `totalStudents`, `totalNGOs`, `totalPrograms`, `totalSchools`, `fundsAllocated`, `fundsUtilized` (exact camelCase). Non-admin user gets HTTP 403.
result: [pending]

### 5. Admin NGO Verification Workflow
expected: Admin can verify, reject, blacklist, and restore NGOs via `PATCH /api/admin/ngos/{id}/{action}`. Verify sets status to verified; reject sets to rejected; blacklist sets to blacklisted; restore sets status back to pending (re-enters review queue). Non-admin gets 403.
result: [pending]

### 6. Admin Blacklist View
expected: `GET /api/admin/blacklist` returns a response with `ngos` and `students` lists containing blacklisted entries. Non-admin gets 403.
result: [pending]

### 7. Admin Student Blacklist/Restore
expected: Admin can blacklist or restore a student via `PATCH /api/admin/students/{id}/{blacklist|restore}`. Status changes accordingly. Activity log is created. Non-admin gets 403.
result: [pending]

### 8. NGO Dashboard Stats
expected: Authenticated NGO user calls `GET /api/ngo/dashboard` (or equivalent NGO stats endpoint). Response includes `programsCount`, `studentsHelped`, `fundsAllocated` fields. Non-NGO user gets 403.
result: [pending]

### 9. NGO Program CRUD
expected: NGO can create a program (POST), list their programs (GET), update a program (PATCH/PUT), and delete a program (DELETE). Attempting to modify another NGO's program returns 403.
result: [pending]

### 10. NGO Student Registration with Blockchain Wallet
expected: NGO registers a student directly (POST /api/ngo/students). A Student record is created, a blockchain wallet is created for the student, and an activity log entry is recorded. The student gets a scholarship ID in `EDU-YYYY-XXXXX` format.
result: [pending]

### 11. NGO Application Accept (Creates Student)
expected: NGO accepts a pending scholarship application (PATCH /api/ngo/applications/{id}/accept). A Student record is created via the same `_create_student()` path (blockchain wallet + activity log). The application status updates to accepted.
result: [pending]

### 12. NGO Application Reject
expected: NGO rejects a pending application (PATCH /api/ngo/applications/{id}/reject) with a rejection reason in the body. Application status updates to rejected and `rejection_reason` column is saved.
result: [pending]

### 13. NGO Lists Only Pending Applications
expected: `GET /api/ngo/applications` returns only applications with status=pending. Accepted or rejected applications are not included in this list.
result: [pending]

### 14. Donor Browse (Verified/Active Filter)
expected: Donor (authenticated) calls `GET /api/donor/browse/ngos` — sees only verified NGOs. `GET /api/donor/browse/programs` — sees only active programs. `GET /api/donor/browse/students` — sees only active students. Non-donor gets 403.
result: [pending]

### 15. School Idempotent Profile Registration
expected: School user calls `POST /api/schools/register` (or equivalent). Response returns the school profile. Calling it again returns the same profile without creating a duplicate row. Non-school user gets 403.
result: [pending]

### 16. Student Browse Programs and Apply
expected: Student (authenticated) can browse active programs via `GET /api/student/programs`. Student submits an application via `POST /api/student/apply` with a program_id. Application is created with `submitted_by_user_id` set to the student's user ID. Applying to an inactive program returns 409 Conflict.
result: [pending]

### 17. Student Lists Own Applications Only
expected: `GET /api/student/applications` returns only applications where `submitted_by_user_id` matches the authenticated student's user ID. A different student's applications are not visible.
result: [pending]

### 18. File Upload
expected: Authenticated user uploads a file via `POST /api/files/upload` (multipart form). Response returns `{"fileId": "...", "url": "..."}`. File is saved to `uploads/{role}/{uuid}.ext` on disk.
result: [pending]

### 19. File Download
expected: Authenticated user downloads a file via `GET /api/files/{id}`. Server streams the file back. Using an invalid/nonexistent ID returns 404.
result: [pending]

### 20. RBAC Enforcement Across All Roles
expected: Each role-restricted endpoint returns HTTP 403 when accessed with the wrong role. For example: a student calling an admin endpoint gets 403, a donor calling an NGO endpoint gets 403, an unauthenticated request gets 401.
result: [pending]

## Summary

total: 20
passed: 0
issues: 0
pending: 20
skipped: 0

## Gaps

[none yet]
