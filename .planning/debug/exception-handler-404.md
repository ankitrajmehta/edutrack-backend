---
status: diagnosed
trigger: "Non-existent routes return FastAPI default 404 {detail: Not Found} instead of custom {detail, code, statusCode} shape"
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
---

## Current Focus

hypothesis: The exception handler registers custom app-exception types and `RequestValidationError` but never registers a handler for `StarletteHTTPException` (or integer 404). FastAPI raises `StarletteHTTPException` internally for unmatched routes — this bypasses all registered handlers and falls through to Starlette's built-in default, which returns `{"detail": "Not Found"}`.
test: Read `app/core/exceptions.py` and verify which exception types are registered.
expecting: No `@app.exception_handler(StarletteHTTPException)` or `@app.exception_handler(404)` present.
next_action: ROOT CAUSE CONFIRMED — no fix applied (diagnose-only mode).

## Symptoms

expected: GET /api/v1/nonexistent returns {"detail": "Not Found", "code": "NOT_FOUND", "statusCode": 404}
actual: GET /api/v1/nonexistent returns {"detail": "Not Found"} (FastAPI/Starlette default shape)
errors: None (HTTP 404 status is correct, JSON body shape is wrong)
reproduction: curl -s "http://localhost:8000/api/v1/nonexistent"
started: Discovered during UAT Phase 01-foundation Test 4

## Eliminated

- hypothesis: The exception handler module is not being imported or called
  evidence: app/main.py line 6 imports `register_exception_handlers` and line 31 calls it before router registration. Module is definitely loaded.
  timestamp: 2026-03-09T00:00:00Z

- hypothesis: The generic `Exception` handler catches the 404 and should format it
  evidence: StarletteHTTPException is NOT a subclass of Python's base `Exception` in the way FastAPI resolves handler priority — Starlette intercepts HTTP exceptions before they reach the ASGI exception middleware that calls user-registered Exception handlers. The generic handler only fires for unhandled Python exceptions, not Starlette HTTP exceptions.
  timestamp: 2026-03-09T00:00:00Z

## Evidence

- timestamp: 2026-03-09T00:00:00Z
  checked: app/core/exceptions.py — registered exception handler types
  found: |
    Handlers registered (lines 50–130):
      - NotFoundError (custom app exception)
      - ForbiddenError (custom app exception)
      - ConflictError (custom app exception)
      - UnauthorizedError (custom app exception)
      - AppValidationError (custom app exception)
      - RequestValidationError (fastapi.exceptions — Pydantic validation)
      - Exception (generic Python base exception)
    
    MISSING:
      - starlette.exceptions.HTTPException  ← NOT registered
      - fastapi.exceptions.HTTPException    ← NOT registered
      - Integer status code 404             ← NOT registered
  implication: When FastAPI cannot match a route, it raises `starlette.exceptions.HTTPException(status_code=404)`. No handler is registered for this type, so Starlette's built-in handler runs and returns the default `{"detail": "Not Found"}` body.

- timestamp: 2026-03-09T00:00:00Z
  checked: app/main.py — handler registration order and router prefixes
  found: |
    - register_exception_handlers(app) called at line 31 (before routers)
    - All routers use prefix "/api/<group>" (no /api/v1/ prefix at all — separate but unrelated issue)
    - No additional exception handler registration anywhere in main.py
  implication: Registration order is fine. The gap is purely the missing HTTPException handler.

- timestamp: 2026-03-09T00:00:00Z
  checked: FastAPI/Starlette exception handling architecture
  found: |
    FastAPI inherits from Starlette. When a route is not found, Starlette's router raises
    `starlette.exceptions.HTTPException(status_code=404, detail="Not Found")`.
    FastAPI's `HTTPException` is a subclass of Starlette's `HTTPException`, so registering
    a handler for either catches both.
    
    The generic `@app.exception_handler(Exception)` does NOT catch HTTPException because
    Starlette's ExceptionMiddleware handles HTTPException before Python's normal exception
    propagation reaches the generic handler.
  implication: The only way to intercept Starlette's 404 is to register a handler explicitly for `StarletteHTTPException` or `HTTPException` or the integer `404`.

## Resolution

root_cause: |
  `register_exception_handlers()` in app/core/exceptions.py registers handlers for custom
  application exception classes and RequestValidationError, but does NOT register any handler
  for `starlette.exceptions.HTTPException` (or `fastapi.exceptions.HTTPException`, or the
  integer status code 404).

  When FastAPI cannot match an incoming request to any route, Starlette internally raises
  `starlette.exceptions.HTTPException(status_code=404, detail="Not Found")`. Because no
  user-registered handler exists for this exception type, Starlette's own built-in handler
  fires and returns the default `{"detail": "Not Found"}` JSON body — completely bypassing
  the custom error format.

  The generic `@app.exception_handler(Exception)` does NOT cover this case because
  Starlette's ExceptionMiddleware intercepts HTTPException before normal Python exception
  propagation, so the generic handler never sees it.

fix: NOT APPLIED (diagnose-only mode)
verification: NOT APPLIED
files_changed: []

suggested_fix_direction: |
  In app/core/exceptions.py, add a handler inside `register_exception_handlers()`:

    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "code": _status_to_code(exc.status_code),  # e.g. "NOT_FOUND", "METHOD_NOT_ALLOWED"
                "statusCode": exc.status_code,
            },
        )

  This single handler catches ALL Starlette/FastAPI HTTP exceptions (404, 405, 403, etc.)
  and formats them with the custom shape. The existing custom app-exception handlers
  (NotFoundError, ForbiddenError, etc.) remain unchanged and take priority for
  domain-raised errors.
