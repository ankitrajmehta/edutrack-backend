#!/usr/bin/env python3
"""
OpenScholar Demo Seed Script
Idempotent — safe to run multiple times.

Populates the database with all mock.js data for the demo.
"""

import asyncio
import secrets
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from passlib.context import CryptContext

from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.ngo import NGO, NGOStatus
from app.models.program import Program, ProgramStatus
from app.models.student import Student, StudentStatus
from app.models.donor import Donor
from app.models.school import School, SchoolStatus
from app.models.donation import Donation, DonationType
from app.models.invoice import Invoice, InvoiceStatus
from app.models.allocation import Allocation
from app.models.activity_log import ActivityLog, ActivityType

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEMO_HASH = pwd_context.hash("demo123")


async def upsert(db, model, data: dict):
    """Upsert a single record using PostgreSQL upsert."""
    stmt = (
        pg_insert(model)
        .values(**data)
        .on_conflict_do_update(
            index_elements=["id"], set_={k: v for k, v in data.items() if k != "id"}
        )
    )
    await db.execute(stmt)


async def reset_seq(db, table_name: str):
    """Reset PostgreSQL sequence to max id + 1 for explicit id inserts."""
    await db.execute(
        text(
            f"SELECT setval('{table_name}_id_seq', (SELECT MAX(id) FROM {table_name}))"
        )
    )


async def seed_users(db):
    """Seed 12 users with demo credentials."""
    users_data = [
        {
            "id": 1,
            "email": "admin@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.admin,
        },
        {
            "id": 2,
            "email": "ngo@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.ngo,
        },
        {
            "id": 3,
            "email": "school@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.school,
        },
        {
            "id": 4,
            "email": "donor@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.donor,
        },
        {
            "id": 5,
            "email": "student@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.student,
        },
        {
            "id": 6,
            "email": "donor2@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.donor,
        },
        {
            "id": 7,
            "email": "donor3@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.donor,
        },
        {
            "id": 8,
            "email": "donor4@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.donor,
        },
        {
            "id": 9,
            "email": "donor5@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.donor,
        },
        {
            "id": 10,
            "email": "school2@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.school,
        },
        {
            "id": 11,
            "email": "school3@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.school,
        },
        {
            "id": 12,
            "email": "school4@demo.openscholar.org",
            "hashed_password": DEMO_HASH,
            "role": UserRole.school,
        },
    ]
    for user_data in users_data:
        await upsert(db, User, user_data)
    await reset_seq(db, "users")


async def seed_ngos(db):
    """Seed 5 NGOs."""
    ngos_data = [
        {
            "id": 1,
            "user_id": 2,
            "name": "Bright Future Foundation",
            "location": "Kathmandu Nepal",
            "status": NGOStatus.verified,
            "description": "Empowering children through education",
            "avatar": "BF",
            "color": "#10b981",
            "total_funded": 245000.0,
            "students_helped": 342,
            "programs_count": 5,
            "registered_date": datetime(2024, 6, 15),
        },
        {
            "id": 2,
            "user_id": 2,
            "name": "EduHope International",
            "location": "Pokhara Nepal",
            "status": NGOStatus.verified,
            "description": "Bringing quality education to rural areas",
            "avatar": "EH",
            "color": "#3b82f6",
            "total_funded": 189000.0,
            "students_helped": 218,
            "programs_count": 3,
            "registered_date": datetime(2024, 8, 20),
        },
        {
            "id": 3,
            "user_id": 2,
            "name": "Children First Nepal",
            "location": "Lalitpur Nepal",
            "status": NGOStatus.pending,
            "description": "Child-centered development programs",
            "avatar": "CF",
            "color": "#f59e0b",
            "total_funded": 0.0,
            "students_helped": 0,
            "programs_count": 0,
            "registered_date": datetime(2025, 2, 10),
        },
        {
            "id": 4,
            "user_id": 2,
            "name": "Nepal Education Alliance",
            "location": "Biratnagar Nepal",
            "status": NGOStatus.verified,
            "description": "Alliance for educational excellence",
            "avatar": "NE",
            "color": "#a855f7",
            "total_funded": 156000.0,
            "students_helped": 195,
            "programs_count": 4,
            "registered_date": datetime(2024, 4, 1),
        },
        {
            "id": 5,
            "user_id": 2,
            "name": "Learn & Grow Trust",
            "location": "Chitwan Nepal",
            "status": NGOStatus.rejected,
            "description": "Learning and growth for all",
            "avatar": "LG",
            "color": "#ef4444",
            "total_funded": 0.0,
            "students_helped": 0,
            "programs_count": 0,
            "registered_date": datetime(2025, 1, 15),
        },
    ]
    for ngo_data in ngos_data:
        await upsert(db, NGO, ngo_data)
    await reset_seq(db, "ngos")


async def seed_schools(db):
    """Seed 4 schools."""
    schools_data = [
        {
            "id": 1,
            "user_id": 3,
            "name": "Shree Janapriya Secondary",
            "location": "Kathmandu",
            "status": SchoolStatus.verified,
            "students_in_programs": 12,
            "total_invoiced": 18500.0,
        },
        {
            "id": 2,
            "user_id": 10,
            "name": "Annapurna Secondary",
            "location": "Pokhara",
            "status": SchoolStatus.verified,
            "students_in_programs": 8,
            "total_invoiced": 12000.0,
        },
        {
            "id": 3,
            "user_id": 11,
            "name": "Koshi Valley School",
            "location": "Biratnagar",
            "status": SchoolStatus.verified,
            "students_in_programs": 6,
            "total_invoiced": 8500.0,
        },
        {
            "id": 4,
            "user_id": 12,
            "name": "Himalayan Model School",
            "location": "Dharan",
            "status": SchoolStatus.verified,
            "students_in_programs": 4,
            "total_invoiced": 5000.0,
        },
    ]
    for school_data in schools_data:
        await upsert(db, School, school_data)
    await reset_seq(db, "schools")


async def seed_programs(db):
    """Seed 5 programs."""
    programs_data = [
        {
            "id": 1,
            "ngo_id": 1,
            "name": "Girls Education Program 2026",
            "description": "Empowering girls through education",
            "status": ProgramStatus.active,
            "categories": ["education", "girls"],
            "total_budget": 150000.0,
            "allocated": 85000.0,
            "students_enrolled": 45,
            "start_date": datetime(2026, 1, 1),
            "end_date": datetime(2026, 12, 31),
        },
        {
            "id": 2,
            "ngo_id": 1,
            "name": "STEM Scholarship 2025",
            "description": "Science and technology scholarships",
            "status": ProgramStatus.completed,
            "categories": ["education", "stem"],
            "total_budget": 80000.0,
            "allocated": 80000.0,
            "students_enrolled": 30,
            "start_date": datetime(2025, 1, 1),
            "end_date": datetime(2025, 12, 31),
        },
        {
            "id": 3,
            "ngo_id": 2,
            "name": "Mountain Girls Scholarship",
            "description": "Scholarships for girls in mountain regions",
            "status": ProgramStatus.active,
            "categories": ["scholarship", "girls"],
            "total_budget": 120000.0,
            "allocated": 65000.0,
            "students_enrolled": 38,
            "start_date": datetime(2025, 6, 1),
            "end_date": datetime(2026, 5, 31),
        },
        {
            "id": 4,
            "ngo_id": 4,
            "name": "Eastern Nepal Literacy Drive",
            "description": "Improving literacy in eastern Nepal",
            "status": ProgramStatus.active,
            "categories": ["literacy"],
            "total_budget": 90000.0,
            "allocated": 45000.0,
            "students_enrolled": 60,
            "start_date": datetime(2025, 9, 1),
            "end_date": datetime(2026, 8, 31),
        },
        {
            "id": 5,
            "ngo_id": 4,
            "name": "Teacher Training Initiative",
            "description": "Training teachers for better education",
            "status": ProgramStatus.active,
            "categories": ["training", "teachers"],
            "total_budget": 75000.0,
            "allocated": 30000.0,
            "students_enrolled": 25,
            "start_date": datetime(2025, 11, 1),
            "end_date": datetime(2026, 10, 31),
        },
    ]
    for program_data in programs_data:
        await upsert(db, Program, program_data)
    await reset_seq(db, "programs")


async def seed_students(db):
    """Seed 5 students."""
    wallet_address_base = "0x" + "a" * 40
    students_data = [
        {
            "id": 1,
            "name": "Aarati Tamang",
            "age": 16,
            "school": "Shree Janapriya Secondary",
            "grade": "10",
            "guardian": "Ram Tamang",
            "location": "Kathmandu",
            "ngo_id": 1,
            "program_id": 1,
            "scholarship_id": "EDU-2026-00001",
            "wallet_address": wallet_address_base,
            "wallet_balance": 3500.0,
            "total_received": 3500.0,
            "status": StudentStatus.active,
        },
        {
            "id": 2,
            "name": "Binod Shrestha",
            "age": 17,
            "school": "Annapurna Secondary",
            "grade": "11",
            "guardian": "Sita Shrestha",
            "location": "Pokhara",
            "ngo_id": 1,
            "program_id": 1,
            "scholarship_id": "EDU-2026-00002",
            "wallet_address": "0x" + "b" * 40,
            "wallet_balance": 2800.0,
            "total_received": 2800.0,
            "status": StudentStatus.active,
        },
        {
            "id": 3,
            "name": "Chandra Maya Gurung",
            "age": 15,
            "school": "Koshi Valley School",
            "grade": "9",
            "guardian": "Dil Bahadur Gurung",
            "location": "Biratnagar",
            "ngo_id": 2,
            "program_id": 3,
            "scholarship_id": "EDU-2025-00001",
            "wallet_address": "0x" + "c" * 40,
            "wallet_balance": 5200.0,
            "total_received": 5200.0,
            "status": StudentStatus.active,
        },
        {
            "id": 4,
            "name": "Deepa Rai",
            "age": 14,
            "school": "Himalayan Model School",
            "grade": "8",
            "guardian": "Mina Rai",
            "location": "Dharan",
            "ngo_id": 4,
            "program_id": 4,
            "scholarship_id": "EDU-2025-00002",
            "wallet_address": "0x" + "d" * 40,
            "wallet_balance": 1800.0,
            "total_received": 1800.0,
            "status": StudentStatus.active,
        },
        {
            "id": 5,
            "name": "Ekta Sharma",
            "age": 18,
            "school": "Shree Janapriya Secondary",
            "grade": "12",
            "guardian": "Raj Sharma",
            "location": "Kathmandu",
            "ngo_id": 1,
            "program_id": 1,
            "scholarship_id": "EDU-2024-00001",
            "wallet_address": "0x" + "e" * 40,
            "wallet_balance": 0.0,
            "total_received": 4200.0,
            "status": StudentStatus.graduated,
        },
    ]
    for student_data in students_data:
        await upsert(db, Student, student_data)
    await reset_seq(db, "students")


async def seed_donors(db):
    """Seed 5 donors."""
    donors_data = [
        {
            "id": 1,
            "user_id": 4,
            "name": "Sarah Mitchell",
            "email": "sarah@example.com",
            "total_donated": 7500.0,
        },
        {
            "id": 2,
            "user_id": 6,
            "name": "James Chen",
            "email": "james@example.com",
            "total_donated": 18000.0,
        },
        {
            "id": 3,
            "user_id": 7,
            "name": "Priya Patel",
            "email": "priya@example.com",
            "total_donated": 3500.0,
        },
        {
            "id": 4,
            "user_id": 8,
            "name": "Nordic Aid Foundation",
            "email": "nordic@example.com",
            "total_donated": 25000.0,
        },
        {
            "id": 5,
            "user_id": 9,
            "name": "Global Ed Trust",
            "email": "global@example.com",
            "total_donated": 50000.0,
        },
    ]
    for donor_data in donors_data:
        await upsert(db, Donor, donor_data)
    await reset_seq(db, "donors")


async def seed_donations(db):
    """Seed 7 donations."""
    now = datetime.utcnow()
    donations_data = [
        {
            "id": 1,
            "donor_id": 1,
            "ngo_id": 1,
            "program_id": 1,
            "student_id": None,
            "amount": 5000.0,
            "type": DonationType.program,
            "date": datetime(2026, 1, 15),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 2,
            "donor_id": 2,
            "ngo_id": 2,
            "program_id": 3,
            "student_id": None,
            "amount": 10000.0,
            "type": DonationType.program,
            "date": datetime(2026, 1, 20),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 3,
            "donor_id": 3,
            "ngo_id": 1,
            "program_id": None,
            "student_id": None,
            "amount": 3500.0,
            "type": DonationType.general,
            "date": datetime(2026, 2, 1),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 4,
            "donor_id": 4,
            "ngo_id": 4,
            "program_id": 4,
            "student_id": None,
            "amount": 25000.0,
            "type": DonationType.program,
            "date": datetime(2026, 2, 10),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 5,
            "donor_id": 5,
            "ngo_id": 1,
            "program_id": 1,
            "student_id": None,
            "amount": 50000.0,
            "type": DonationType.program,
            "date": datetime(2026, 2, 15),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 6,
            "donor_id": 1,
            "ngo_id": 2,
            "program_id": 3,
            "student_id": 3,
            "amount": 2500.0,
            "type": DonationType.student,
            "date": datetime(2026, 2, 20),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 7,
            "donor_id": 2,
            "ngo_id": 4,
            "program_id": 5,
            "student_id": None,
            "amount": 8000.0,
            "type": DonationType.program,
            "date": datetime(2026, 3, 1),
            "tx_hash": secrets.token_hex(32),
        },
    ]
    for donation_data in donations_data:
        await upsert(db, Donation, donation_data)
    await reset_seq(db, "donations")


async def seed_invoices(db):
    """Seed 4 invoices."""
    invoices_data = [
        {
            "id": 1,
            "school_id": 1,
            "ngo_id": 1,
            "program_id": 1,
            "school_name": "Shree Janapriya Secondary",
            "amount": 4200.0,
            "category": "Tuition",
            "status": InvoiceStatus.approved,
            "items": [{"description": "Tuition fees Q1", "amount": 4200}],
            "date": datetime(2026, 1, 20),
            "approved_date": datetime(2026, 1, 25),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 2,
            "school_id": 1,
            "ngo_id": 1,
            "program_id": 1,
            "school_name": "Shree Janapriya Secondary",
            "amount": 1800.0,
            "category": "Supplies",
            "status": InvoiceStatus.pending,
            "items": [{"description": "School supplies", "amount": 1800}],
            "date": datetime(2026, 2, 10),
            "approved_date": None,
            "tx_hash": None,
        },
        {
            "id": 3,
            "school_id": 2,
            "ngo_id": 2,
            "program_id": 3,
            "school_name": "Annapurna Secondary",
            "amount": 3600.0,
            "category": "Tuition",
            "status": InvoiceStatus.approved,
            "items": [{"description": "Tuition fees semester 1", "amount": 3600}],
            "date": datetime(2026, 1, 15),
            "approved_date": datetime(2026, 1, 22),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 4,
            "school_id": 3,
            "ngo_id": 4,
            "program_id": 4,
            "school_name": "Koshi Valley School",
            "amount": 2200.0,
            "category": "Uniforms",
            "status": InvoiceStatus.pending,
            "items": [{"description": "Winter uniforms", "amount": 2200}],
            "date": datetime(2026, 2, 25),
            "approved_date": None,
            "tx_hash": None,
        },
    ]
    for invoice_data in invoices_data:
        await upsert(db, Invoice, invoice_data)
    await reset_seq(db, "invoices")


async def seed_allocations(db):
    """Seed 4 allocations."""
    allocations_data = [
        {
            "id": 1,
            "ngo_id": 1,
            "student_id": 1,
            "program_id": 1,
            "amount": 3500.0,
            "date": datetime(2026, 1, 28),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 2,
            "ngo_id": 1,
            "student_id": 2,
            "program_id": 1,
            "amount": 2800.0,
            "date": datetime(2026, 2, 5),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 3,
            "ngo_id": 2,
            "student_id": 3,
            "program_id": 3,
            "amount": 5200.0,
            "date": datetime(2026, 2, 12),
            "tx_hash": secrets.token_hex(32),
        },
        {
            "id": 4,
            "ngo_id": 4,
            "student_id": 4,
            "program_id": 4,
            "amount": 1800.0,
            "date": datetime(2026, 2, 18),
            "tx_hash": secrets.token_hex(32),
        },
    ]
    for allocation_data in allocations_data:
        await upsert(db, Allocation, allocation_data)
    await reset_seq(db, "allocations")


async def seed_activity_log(db):
    """Seed 8 activity log entries with timestamps relative to now."""
    now = datetime.utcnow()
    entries = [
        {
            "id": 1,
            "type": ActivityType.donation,
            "color": "green",
            "text": "Sarah Mitchell donated $2,500 to Mountain Girls Scholarship",
            "timestamp": now - timedelta(hours=2),
            "actor_id": None,
        },
        {
            "id": 2,
            "type": ActivityType.invoice,
            "color": "amber",
            "text": "Shree Janapriya School submitted invoice for winter uniforms ($4,200)",
            "timestamp": now - timedelta(hours=5),
            "actor_id": None,
        },
        {
            "id": 3,
            "type": ActivityType.verify,
            "color": "blue",
            "text": "Children First Nepal's registration is pending verification",
            "timestamp": now - timedelta(days=1),
            "actor_id": None,
        },
        {
            "id": 4,
            "type": ActivityType.allocation,
            "color": "green",
            "text": "Bright Future Foundation allocated $3,500 to Aarati Tamang",
            "timestamp": now - timedelta(days=1, hours=1),
            "actor_id": None,
        },
        {
            "id": 5,
            "type": ActivityType.invoice,
            "color": "green",
            "text": "Tuition invoice from Annapurna Secondary School approved",
            "timestamp": now - timedelta(days=2),
            "actor_id": None,
        },
        {
            "id": 6,
            "type": ActivityType.program,
            "color": "blue",
            "text": "Teacher Training Initiative program launched by Nepal Education Alliance",
            "timestamp": now - timedelta(days=3),
            "actor_id": None,
        },
        {
            "id": 7,
            "type": ActivityType.donation,
            "color": "green",
            "text": "James Chen donated $8,000 to Teacher Training Initiative",
            "timestamp": now - timedelta(days=3, hours=2),
            "actor_id": None,
        },
        {
            "id": 8,
            "type": ActivityType.blacklist,
            "color": "red",
            "text": "Learn & Grow Trust's application was rejected due to incomplete documents",
            "timestamp": now - timedelta(days=5),
            "actor_id": None,
        },
    ]
    for entry in entries:
        await upsert(db, ActivityLog, entry)
    await reset_seq(db, "activity_logs")


async def main():
    """Main seeding function - runs all seed functions in order."""
    async with AsyncSessionLocal() as db:
        print("Seeding users...")
        await seed_users(db)
        print("Seeding NGOs...")
        await seed_ngos(db)
        print("Seeding schools...")
        await seed_schools(db)
        print("Seeding programs...")
        await seed_programs(db)
        print("Seeding students...")
        await seed_students(db)
        print("Seeding donors...")
        await seed_donors(db)
        print("Seeding donations...")
        await seed_donations(db)
        print("Seeding invoices...")
        await seed_invoices(db)
        print("Seeding allocations...")
        await seed_allocations(db)
        print("Seeding activity log...")
        await seed_activity_log(db)
        await db.commit()
        print("✓ Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
