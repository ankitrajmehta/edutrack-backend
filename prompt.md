# EduTrack Backend — Agent Instructions

## Project Context

You are building the backend for **EduTrack**, a transparent scholarship delivery platform. The frontend exists at `../edutrack/` and uses mock data. Your job: build the Python/FastAPI backend that serves real data to this frontend.

This is v1 of a production-grade application. It is scoped as a grant demo, but every line of code should be written as if it will be maintained and extended. No shortcuts in architecture, error handling, type safety, or code structure.

## Non-Negotiable Rules

1. **Never modify `../edutrack/`** — the frontend is read-only.
2. **All API responses must use camelCase** matching `../edutrack/src/data/mock.js`. Read that file before implementing any endpoint.
3. **Work inside `../backend/`** only.
4. **Check `tasks.md`** for the task list. Complete tasks in order.
5. **Every task has a "Done when:" acceptance criterion.** Do not mark a task complete until it passes.
6. **No silent failures.** Every exception must be caught, logged, and returned as structured JSON.

## Tech Stack

- Python 3.11+, FastAPI (async)
- PostgreSQL via SQLAlchemy async (asyncpg driver)
- Alembic for migrations (async template)
- JWT auth: python-jose[cryptography] + passlib[bcrypt]
- Pydantic v2 for all schemas
- Local disk file storage (S3-compatible interface)
- Docker Compose (app + PostgreSQL)

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, CORS middleware, router registration
│   ├── api/                       # Route handlers — thin, no business logic
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── ngo.py
│   │   ├── donor.py
│   │   ├── school.py
│   │   ├── student.py
│   │   ├── public.py
│   │   └── files.py
│   ├── models/                    # SQLAlchemy ORM models (snake_case columns)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── ngo.py
│   │   ├── program.py
│   │   ├── student.py
│   │   ├── donor.py
│   │   ├── donation.py
│   │   ├── invoice.py
│   │   ├── school.py
│   │   ├── application.py
│   │   ├── activity_log.py
│   │   └── file_record.py
│   ├── schemas/                   # Pydantic v2 schemas (camelCase aliases)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── ngo.py
│   │   ├── program.py
│   │   ├── student.py
│   │   ├── donor.py
│   │   ├── donation.py
│   │   ├── invoice.py
│   │   ├── school.py
│   │   ├── application.py
│   │   └── common.py              # Shared types (ErrorResponse, etc.)
│   ├── services/                  # All business logic lives here
│   │   ├── auth_service.py
│   │   ├── admin_service.py
│   │   ├── ngo_service.py
│   │   ├── donor_service.py
│   │   ├── school_service.py
│   │   ├── student_service.py
│   │   ├── activity_service.py
│   │   ├── file_service.py
│   │   └── blockchain/
│   │       ├── base.py            # BlockchainService Protocol (interface)
│   │       └── mock_sui.py        # Mock implementation (swap for real SDK)
│   └── core/
│       ├── config.py              # Pydantic BaseSettings from .env
│       ├── database.py            # Async engine, session factory, Base
│       ├── security.py            # JWT create/verify, bcrypt helpers
│       ├── dependencies.py        # get_current_user, require_role, get_db, get_blockchain
│       └── exceptions.py          # Custom exception classes + global handler
├── contracts/
│   └── sources/scholarship.move   # Complete Move contract (deployable to testnet)
├── alembic/
│   ├── env.py                     # Async-configured
│   └── versions/
├── scripts/
│   ├── seed.py                    # Idempotent DB seed matching mock.js exactly
│   └── start.sh                   # Run migrations + seed + start uvicorn
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

## Coding Standards

### Route Handlers
```python
@router.post("/programs", response_model=ProgramResponse, status_code=201)
async def create_program(
    data: ProgramCreate,
    current_ngo: NGO = Depends(require_role("ngo")),
    db: AsyncSession = Depends(get_db),
    blockchain: BlockchainService = Depends(get_blockchain),
) -> ProgramResponse:
    """Create a new scholarship program for this NGO."""
    return await ngo_service.create_program(db, blockchain, current_ngo.id, data)
```
- `async def` always
- Full type hints on all parameters and return types
- Docstring on every public function
- Handler calls exactly one service method and returns its result
- No DB queries, no business logic, no `if/else` in handlers

### Services
```python
async def create_program(
    db: AsyncSession,
    blockchain: BlockchainService,
    ngo_id: int,
    data: ProgramCreate,
) -> ProgramResponse:
    """Create a scholarship program. Raises NotFoundError if NGO not found."""
    ngo = await db.get(NGO, ngo_id)
    if ngo is None:
        raise NotFoundError("NGO", ngo_id)
    program = Program(ngo_id=ngo_id, **data.model_dump())
    db.add(program)
    ngo.programs_count += 1
    await db.commit()
    await db.refresh(program)
    await activity_service.log(db, "program", f"New program '{program.name}' created", ngo.user_id)
    return ProgramResponse.model_validate(program)
```
- All DB operations inside services
- All stat updates (e.g., `ngo.programs_count`) inside the same transaction
- All ActivityLog writes inside service methods
- Raise typed exceptions; never return error dicts

### Schemas
```python
class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    ngo_id: int = Field(alias="ngoId")
    name: str
    total_budget: float = Field(alias="totalBudget")
    students_enrolled: int = Field(alias="studentsEnrolled")
    # ... all fields with camelCase aliases
```
- Every response schema has `from_attributes=True` (ORM mode)
- All fields that differ from snake_case get an explicit `Field(alias="camelCase")`
- Separate `Create`, `Update`, `Response` schemas per entity
- Never expose `hashed_password` in any schema

### Error Handling
```python
# app/core/exceptions.py
class NotFoundError(HTTPException):
    def __init__(self, resource: str, id: Any):
        super().__init__(status_code=404, detail=f"{resource} {id} not found")

class ForbiddenError(HTTPException):
    def __init__(self, reason: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=reason)
```
- Global exception handler in `main.py` catches all unhandled exceptions
- Logs the full traceback before returning 500
- All 4xx errors have a consistent `{detail, code, statusCode}` shape

### Blockchain Service
```python
# All callers use the Protocol — never import mock_sui directly
blockchain: BlockchainService = Depends(get_blockchain)
result = await blockchain.donate(donor_id, "program", program_id, amount)
tx_hash = result.tx_hash  # store this in DB
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)

# In services:
logger.info("Allocating %.2f to student %s", amount, student_id)
logger.error("Blockchain call failed: %s", exc, exc_info=True)
```
- Use module-level loggers (`__name__`)
- Log before raising exceptions
- Log all blockchain calls (mock logs these by default)

## FE Data Contract

Before implementing any endpoint, read `../edutrack/src/data/mock.js` for exact field names.

Key shapes:
- **NGO**: `id, name, location, status, description, taxDoc, regDoc, avatar, color, totalFunded, studentsHelped, programsCount, registeredDate, programs[]`
- **Program**: `id, ngoId, name, description, status, categories[], totalBudget, allocated, studentsEnrolled, startDate, endDate`
- **Student**: `id, name, age, school, grade, guardian, programId, ngoId, scholarshipId, walletBalance, totalReceived, status, location`
- **Donation**: `id, donorId, ngoId, programId, amount, date, type, studentId?, message?, txHash`
- **Invoice**: `id, schoolId, schoolName, ngoId, programId, amount, category, status, items[{desc, amount}], date, approvedDate, supportingDoc`
- **School**: `id, name, location, status, studentsInPrograms, totalInvoiced`
- **Platform stats**: `totalDonations, totalStudents, totalNGOs, totalPrograms, totalSchools, fundsAllocated, fundsUtilized`
- **Activity feed entry**: `{type, color, text, time}` — `time` is a relative string ("2 hours ago")
