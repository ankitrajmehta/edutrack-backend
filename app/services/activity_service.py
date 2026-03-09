"""
Activity logging service.

Called by all Phase 2+ services BEFORE db.commit() to ensure
the log entry and the triggering action are in the same transaction.

Usage:
    await activity_service.log(db, "verify", "NGO 'CARE' verified", current_user.id)
    await db.commit()  # logs and action committed atomically
"""

from sqlalchemy.ext.asyncio import AsyncSession

# Color per activity type — used by Phase 4 public feed
COLOR_MAP: dict[str, str] = {
    "verify": "blue",
    "blacklist": "red",
    "program": "blue",
    "allocation": "purple",
    "donation": "green",
    "invoice": "amber",
}


async def log(db: AsyncSession, type: str, text: str, actor_id: int) -> None:
    """
    Write an ActivityLog entry to the current session (does NOT commit).

    Args:
        db: The current AsyncSession — MUST be the same session as the caller's transaction.
        type: ActivityType string value (e.g. "verify", "blacklist", "program", "allocation").
        text: Human-readable description (e.g. "NGO 'CARE' verified").
        actor_id: ID of the authenticated user performing the action.

    CRITICAL: This function does NOT call db.commit(). The caller commits AFTER calling log(),
    ensuring atomicity: if the triggering action fails, the log entry is also rolled back.
    """
    # Late import to avoid circular dependency (models import database, service imports models)
    from app.models.activity_log import ActivityLog

    entry = ActivityLog(
        type=type,
        text=text,
        actor_id=actor_id,
        color=COLOR_MAP.get(type, "gray"),
    )
    db.add(entry)
    # DO NOT call await db.commit() here — caller owns the transaction boundary
