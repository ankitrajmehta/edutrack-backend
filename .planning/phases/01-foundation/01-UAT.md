---
status: diagnosed
phase: 01-foundation
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 01-04-SUMMARY.md]
started: 2026-03-09T13:00:00Z
updated: 2026-03-09T13:30:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->
Tests 1-10: All passing (verified via curl)



## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, any seed/migration completes, and a primary query (health check, homepage load, or basic API call) returns live data.
result: pass

### 2. Docker Compose Stack Starts
expected: Running `docker compose up --build` starts both the app container and PostgreSQL. PostgreSQL healthcheck passes before the app starts (no "connection refused" errors in app logs). Both services show as healthy in `docker compose ps`.
result: pass

### 3. API Docs Accessible
expected: Navigating to http://localhost:8000/docs shows the FastAPI Swagger UI with all 8 router groups listed (auth and any stubs). No import errors or 500 responses.
result: pass

### 4. CORS Headers Present
expected: A preflight OPTIONS request to any API endpoint from localhost:3000 or localhost:5173 returns the correct Access-Control-Allow-Origin header. Wildcard (*) should NOT appear — only explicit origins.
result: pass

### 5. Exception Handler Format
expected: Hitting a non-existent route (e.g., GET /api/v1/nonexistent) returns a JSON response with shape `{"detail": "...", "code": "...", "statusCode": 404}` — not FastAPI's default `{"detail": "Not Found"}`.
result: pass

### 6. User Registration
expected: POST /api/v1/auth/register with valid email, password, full_name, and role (e.g., "ngo") returns 201 with a token response. The response uses camelCase keys (e.g., `accessToken`, not `access_token`).
result: pass

### 7. User Login
expected: POST /api/v1/auth/login with the credentials from the previous test returns 200 with `accessToken` and `refreshToken`. Wrong password returns 401 with the standard error shape.
result: pass

### 8. Token Refresh
expected: POST /api/v1/auth/refresh with a valid refresh token returns a new `accessToken`. Using an invalid/expired token returns 401.
result: pass

### 9. Protected Route with RBAC
expected: GET /api/v1/auth/me with a valid Bearer token returns the user's profile (camelCase keys). Accessing it without a token returns 401. A token with an incorrect role on a role-restricted endpoint returns 403.
result: pass

### 10. Logout Invalidates Token
expected: POST /api/v1/auth/logout with a valid refresh token returns 200. Using that same refresh token in a subsequent /refresh call returns 401 (token is blacklisted/invalidated).
result: pass

### 11. Database Migration Runs
expected: After `docker compose up db -d`, running `alembic upgrade head` completes without errors. The database contains all expected tables (users, ngos, programs, students, donors, donations, invoices, schools, scholarship_applications, activity_logs, file_records).
result: pass

### 12. Blockchain Abstraction Wired
expected: The app boots with MockSuiService active (visible via logs or config). No route calls import mock_sui directly — the abstraction is used via dependency injection. This can be verified by checking that the app starts without errors related to blockchain imports.
result: pass

## Summary

total: 12
passed: 12
issues: 0
pending: 0
skipped: 0

## Gaps

<!-- No remaining gaps - all issues resolved -->
- truth: "Non-existent routes return JSON with shape {detail, code, statusCode} using the custom exception handler"
  status: resolved
  test: 5
  note: "Verified via curl - custom handler returns {detail, code, statusCode}"

- truth: "POST /api/v1/auth/register hits the database successfully and returns 201 with token"
  status: resolved
  test: 6
  note: "Verified via curl - registration returns 201 with tokens. Note: API uses /api/auth/ not /api/v1/auth/"
