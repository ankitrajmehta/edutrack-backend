---
status: diagnosed
phase: 01-foundation
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 01-04-SUMMARY.md]
started: 2026-03-09T13:00:00Z
updated: 2026-03-09T13:30:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 6
name: User Registration
expected: |
  POST /api/v1/auth/register with valid email, password, full_name, and role (e.g., "ngo") returns 201 with a token response. The response uses camelCase keys (e.g., `accessToken`, not `access_token`).
awaiting: user response

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
result: issue
reported: "curl -s \"http://localhost:8000/api/v1/nonexistent\" returned {\"detail\":\"Not Found\"} — the custom exception handler format {detail, code, statusCode} is not being applied to 404s"
severity: major

### 5. Exception Handler Format
expected: Hitting a non-existent route (e.g., GET /api/v1/nonexistent) returns a JSON response with shape `{"detail": "...", "code": "...", "statusCode": 404}` — not FastAPI's default `{"detail": "Not Found"}`.
result: issue
reported: "POST /api/auth/register returned 500 — UndefinedTableError: relation \"users\" does not exist. Migrations have not been applied, so tables don't exist."
severity: blocker

### 6. User Registration
expected: POST /api/v1/auth/register with valid email, password, full_name, and role (e.g., "ngo") returns 201 with a token response. The response uses camelCase keys (e.g., `accessToken`, not `access_token`).
result: [pending]

### 7. User Login
expected: POST /api/v1/auth/login with the credentials from the previous test returns 200 with `accessToken` and `refreshToken`. Wrong password returns 401 with the standard error shape.
result: [pending]

### 8. Token Refresh
expected: POST /api/v1/auth/refresh with a valid refresh token returns a new `accessToken`. Using an invalid/expired token returns 401.
result: [pending]

### 9. Protected Route with RBAC
expected: GET /api/v1/auth/me with a valid Bearer token returns the user's profile (camelCase keys). Accessing it without a token returns 401. A token with an incorrect role on a role-restricted endpoint returns 403.
result: [pending]

### 10. Logout Invalidates Token
expected: POST /api/v1/auth/logout with a valid refresh token returns 200. Using that same refresh token in a subsequent /refresh call returns 401 (token is blacklisted/invalidated).
result: [pending]

### 11. Database Migration Runs
expected: After `docker compose up db -d`, running `alembic upgrade head` completes without errors. The database contains all expected tables (users, ngos, programs, students, donors, donations, invoices, schools, scholarship_applications, activity_logs, file_records).
result: [pending]

### 12. Blockchain Abstraction Wired
expected: The app boots with MockSuiService active (visible via logs or config). No route calls import mock_sui directly — the abstraction is used via dependency injection. This can be verified by checking that the app starts without errors related to blockchain imports.
result: [pending]

## Summary

total: 12
passed: 3
issues: 2
pending: 7
skipped: 0

## Gaps

- truth: "Non-existent routes return JSON with shape {detail, code, statusCode} using the custom exception handler"
  status: failed
  reason: "User reported: curl returned {\"detail\":\"Not Found\"} — FastAPI default 404, not custom format"
  severity: major
  test: 4
  root_cause: "register_exception_handlers() never registers a handler for starlette.exceptions.HTTPException. When FastAPI cannot match a route, Starlette raises HTTPException(404) internally — Starlette's ExceptionMiddleware intercepts it before the generic Exception handler fires, returning the bare {\"detail\": \"Not Found\"} shape."
  artifacts:
    - path: "app/core/exceptions.py"
      issue: "Missing @app.exception_handler(StarletteHTTPException) inside register_exception_handlers(). Only custom domain exceptions and RequestValidationError are registered."
  missing:
    - "Import starlette.exceptions.HTTPException as StarletteHTTPException in exceptions.py"
    - "Add handler for StarletteHTTPException inside register_exception_handlers() that maps status_code to code string and returns {detail, code, statusCode} shape"
  debug_session: ".planning/debug/exception-handler-404.md"

- truth: "POST /api/v1/auth/register hits the database successfully and returns 201 with token"
  status: failed
  reason: "User reported: 500 Internal Server Error — UndefinedTableError: relation \"users\" does not exist. Migrations not applied."
  severity: blocker
  test: 5
  root_cause: "alembic/versions/0001_initial_schema.py is a placeholder stub — its upgrade() function is literally just 'pass' with zero op.create_table() calls. Running 'alembic upgrade head' stamps the DB as migrated but creates no tables. app/main.py also has no startup hook so migrations were never triggered automatically."
  artifacts:
    - path: "alembic/versions/0001_initial_schema.py"
      issue: "upgrade() body is 'pass' — no DDL operations. File docstring acknowledges it was created without a live DB and needs regeneration."
    - path: "app/main.py"
      issue: "No startup lifecycle hook (lifespan/on_event) to run migrations before serving requests."
  missing:
    - "Replace placeholder migration with real DDL — either write op.create_table() calls for all 12 tables manually, or run 'alembic revision --autogenerate -m initial_schema' against a live empty DB"
    - "Run 'alembic upgrade head' after real migration exists"
    - "Add Docker entrypoint step (alembic upgrade head && uvicorn ...) or startup lifespan hook so migrations always apply on fresh start"
  debug_session: ".planning/debug/migrations-not-applied.md"
