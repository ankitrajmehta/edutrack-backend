---
phase: quick-1-fix-uat-gaps
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/api/ngo.py
  - app/services/ngo_service.py
  - app/services/auth_service.py
autonomous: true
requirements: []
gap_closure: true

must_haves:
  truths:
    - "NGO can delete their own programs (DELETE returns 204)"
    - "NGO cannot delete another NGO's program (returns 403)"
    - "POST /api/auth/register with role=student returns 400/422, not 500"
  artifacts:
    - path: "app/services/ngo_service.py"
      provides: "delete_program() service function"
      contains: "delete_program"
    - path: "app/api/ngo.py"
      provides: "DELETE /programs/{program_id} route"
      contains: "@router.delete"
    - path: "app/services/auth_service.py"
      provides: "_create_profile() without student branch"
  key_links:
    - from: "app/api/ngo.py"
      to: "app/services/ngo_service.py"
      via: "ngo_service.delete_program(db, program_id, ngo, current_user.id)"
    - from: "app/services/auth_service.py"
      to: "UserRole.student"
      via: "removed branch — no Student() instantiation on self-register"
---

<objective>
Fix three UAT gaps identified in phase 02-entity-management:
1. Add missing DELETE endpoint for NGO programs
2. Remove broken student self-registration path that causes HTTP 500
3. (Gap 3 — fileId integer vs UUID: accepted as-is, no change needed; functionally correct per UAT notes)

Purpose: Close UAT gaps so phase 02 is fully green before phase 03 (Fund Flow) begins.
Output: Two files modified — ngo.py + ngo_service.py for delete, auth_service.py for student 500 fix.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

<!-- Architecture constraints (from STATE.md Accumulated Context):
- All route handlers and service methods must be `async def`
- Service layer owns all db.commit() calls — no commits in route handlers
- activity_service.log() called BEFORE db.commit() — atomicity requirement
- Ownership check pattern: if record.ngo_id != ngo.id: raise ForbiddenError(...)
-->

<interfaces>
<!-- From app/services/ngo_service.py — existing ownership pattern to follow -->
```python
async def get_program(db: AsyncSession, program_id: int, ngo: NGO) -> ProgramResponse:
    result = await db.execute(select(Program).where(Program.id == program_id))
    program = result.scalar_one_or_none()
    if program is None:
        raise NotFoundError("Program", program_id)
    if program.ngo_id != ngo.id:
        raise ForbiddenError("You do not own this program")
    return ProgramResponse.model_validate(program)
```

<!-- From app/api/ngo.py — existing router pattern for program endpoints -->
```python
@router.put("/programs/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: int,
    data: ProgramUpdate,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("ngo")),
) -> ProgramResponse:
    return await ngo_service.update_program(db, program_id, data, ngo, current_user.id)
```

<!-- From app/services/auth_service.py — the broken student branch (lines 119-123) -->
```python
elif user.role == UserRole.student:
    from app.models.student import Student
    profile = Student(user_id=user.id, name=data.name, location=data.location)
    db.add(profile)
```
<!-- Student model has no user_id column — students are NGO-managed, not self-registered.
     This branch must be removed; student role self-registration should fail at validation. -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add DELETE /programs/{program_id} endpoint and service method</name>
  <files>app/services/ngo_service.py, app/api/ngo.py</files>
  <action>
    In `app/services/ngo_service.py`, add `delete_program()` after `update_program()`:

    ```python
    async def delete_program(
        db: AsyncSession, program_id: int, ngo: NGO, actor_id: int
    ) -> None:
        """Delete a program owned by the authenticated NGO."""
        result = await db.execute(select(Program).where(Program.id == program_id))
        program = result.scalar_one_or_none()
        if program is None:
            raise NotFoundError("Program", program_id)
        if program.ngo_id != ngo.id:
            raise ForbiddenError("You do not own this program")

        await activity_service.log(
            db,
            "program",
            f"Program '{program.name}' deleted by {ngo.name}",
            actor_id,
        )
        await db.delete(program)
        await db.commit()
    ```

    Note: `activity_service.log()` is called BEFORE `db.delete()/db.commit()` — atomicity requirement from STATE.md. NGO programs_count counter is NOT decremented here (programs_count tracks created programs, not active ones — consistent with create_program incrementing it but update_program not tracking status changes).

    In `app/api/ngo.py`, add the DELETE route after `update_program`:

    ```python
    @router.delete("/programs/{program_id}", status_code=204)
    async def delete_program(
        program_id: int,
        ngo: NGO = Depends(get_current_ngo),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(require_role("ngo")),
    ) -> None:
        await ngo_service.delete_program(db, program_id, ngo, current_user.id)
    ```

    Return type is `None` with status_code=204 — FastAPI sends empty body on 204.
  </action>
  <verify>
    <automated>
      # Start app (if not running) and test:
      curl -s -o /dev/null -w "%{http_code}" -X DELETE http://localhost:8000/api/ngo/programs/1 -H "Authorization: Bearer $NGO_TOKEN"
      # Expected: 204 for own program, 403 for another NGO's program, 404 for nonexistent
    </automated>
  </verify>
  <done>
    - `DELETE /api/ngo/programs/{id}` returns 204 when NGO deletes their own program
    - Returns 403 when NGO attempts to delete another NGO's program
    - Returns 404 when program doesn't exist
    - Activity log entry created on successful delete
  </done>
</task>

<task type="auto">
  <name>Task 2: Remove broken student self-registration branch from auth_service</name>
  <files>app/services/auth_service.py</files>
  <action>
    In `app/services/auth_service.py`, remove the `elif user.role == UserRole.student:` branch from `_create_profile()` (lines 119-123).

    The student branch tries to instantiate `Student(user_id=user.id, ...)` but `Student` model has no `user_id` column — students are created by NGOs via `ngo_service._create_student()`, not via self-registration.

    After removing the branch, the `_create_profile()` function for `student` role will fall through to the final `# admin: no separate profile row` comment (no profile created). However, the `register()` function in `auth_service.py` currently allows any role string via `UserRole(data.role)`. To make `role=student` return a proper 400 instead of silently succeeding with no profile:

    Add a guard at the top of `_create_profile()` before the role checks:

    ```python
    async def _create_profile(db: AsyncSession, user: User, data: RegisterRequest) -> None:
        """Create the role-specific profile row for a new user."""
        # Students are NGO-managed — no self-registration path
        if user.role == UserRole.student:
            from app.core.exceptions import ConflictError
            raise ConflictError("role", "students cannot self-register; contact an NGO")
    ```

    Then the rest of the if/elif chain for ngo/donor/school/admin remains unchanged.

    This converts the HTTP 500 (SQLAlchemy column error) into a proper HTTP 409 ConflictError (which maps to 409 via the existing exception handler). A 409 clearly communicates "this operation is not allowed" without exposing internals.

    If `ConflictError` semantics feel wrong, check `app/core/exceptions.py` for a `BadRequestError` or similar — if one exists, prefer it for a 400. Use whichever maps to 4xx in the existing exception handler. Do NOT create new exception classes.
  </action>
  <verify>
    <automated>
      curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/auth/register \
        -H "Content-Type: application/json" \
        -d '{"email":"student@test.com","password":"pass123","role":"student","name":"Test Student"}'
      # Expected: 4xx response (400, 409, or 422), NOT 500
    </automated>
  </verify>
  <done>
    - `POST /api/auth/register` with `role=student` returns 4xx (not 500)
    - Response includes a human-readable error message
    - No SQLAlchemy traceback or internal error exposed
    - Other roles (ngo, donor, school, admin) still register correctly (no regression)
  </done>
</task>

</tasks>

<verification>
After both tasks complete:
1. `DELETE /api/ngo/programs/{id}` — 204 own, 403 cross-NGO, 404 missing
2. `POST /api/auth/register` with `role=student` — returns 4xx, not 500
3. All existing UAT tests still pass (no regressions):
   - NGO program CRUD (POST/GET/PUT) still works
   - Auth register for ngo/donor/school still works
4. Docker rebuild not required (code changes only, no migration needed)
</verification>

<success_criteria>
- Gap 1 closed: DELETE endpoint exists and enforces ownership
- Gap 2 closed: Student self-register returns 4xx instead of 500
- Gap 3 accepted: fileId as integer is functionally correct; no change needed
- Zero regressions in existing passing tests
</success_criteria>

<output>
After completion, create `.planning/quick/1-fix-uat-gaps-from-phase-02-entity-manage/1-SUMMARY.md`
</output>
