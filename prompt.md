# EduTrack Backend — Agent Instructions

## Project Context

You are building the backend for **EduTrack**, a transparent scholarship delivery platform. The frontend already exists at `../edutrack/` and uses mock data. Your job is to build the Python/FastAPI backend that serves real data to this frontend.

## Critical Rules

1. **NEVER modify any file inside `../edutrack/`** — the frontend is read-only.
2. **All API response shapes must match `../edutrack/src/data/mock.js`** — use camelCase keys in JSON responses. Study this file before implementing any endpoint.
3. **Work inside `../backend/`** — this is your workspace.
4. **One task per iteration** — read PRD.md for the task spec, check progress.txt for what's done, complete exactly one task, then stop.
5. **Always verify** — each task has a "Verify" line. Run the verification before marking complete.

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI (async)
- **Database:** PostgreSQL (via SQLAlchemy async + asyncpg)
- **Migrations:** Alembic (async template)
- **Auth:** JWT (python-jose + passlib/bcrypt)
- **Blockchain:** Sui Move contracts + Python Sui SDK
- **Files:** Local disk storage (S3-compatible adapter for prod)
- **Containerization:** Docker + Docker Compose

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry
│   ├── api/                  # Route handlers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── ngo.py
│   │   ├── donor.py
│   │   ├── school.py
│   │   ├── student.py
│   │   └── public.py
│   ├── models/               # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── *.py
│   ├── schemas/              # Pydantic schemas
│   │   ├── __init__.py
│   │   └── *.py
│   ├── services/             # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── file_service.py
│   │   ├── activity_service.py
│   │   └── sui_service.py
│   └── core/                 # Config, DB, deps
│       ├── __init__.py
│       ├── config.py
│       ├── database.py
│       ├── security.py
│       └── dependencies.py
├── contracts/                # Sui Move contracts
│   └── sources/
│       └── scholarship.move
├── alembic/                  # DB migrations
├── scripts/
│   ├── seed.py
│   └── start.sh
├── tests/
├── docs/
│   ├── PRD.md
│   ├── prompt.md
│   └── progress.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## Coding Conventions

- Use `async def` for all route handlers and DB operations
- Type hints on all function signatures
- Docstrings on all public functions
- Use FastAPI dependency injection for auth, DB sessions
- SQLAlchemy models use snake_case; Pydantic response schemas alias to camelCase
- Keep route handlers thin — business logic goes in `services/`
- Log errors, never silently swallow exceptions

## FE Data Contract Reference

Before implementing any endpoint, read `../edutrack/src/data/mock.js` to see the exact shape the FE expects. Key points:
- NGO fields: `id, name, location, status, description, taxDoc, regDoc, avatar, color, totalFunded, studentsHelped, programsCount, registeredDate, programs[]`
- Program fields: `id, ngoId, name, description, status, categories[], totalBudget, allocated, studentsEnrolled, startDate, endDate`
- Student fields: `id, name, age, school, grade, guardian, programId, ngoId, scholarshipId, walletBalance, totalReceived, status, location`
- Donation fields: `id, donorId, ngoId, programId, amount, date, type, studentId?`
- Invoice fields: `id, schoolId, schoolName, ngoId, programId, amount, category, status, items[{desc, amount}], date, approvedDate`
- School fields: `id, name, location, status, studentsInPrograms, totalInvoiced`
- Platform stats: `totalDonations, totalStudents, totalNGOs, totalPrograms, totalSchools, fundsAllocated, fundsUtilized`
- Activity feed: `{type, color, text, time}` — time is relative ("2 hours ago")
