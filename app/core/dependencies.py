"""
FastAPI dependency injection hub.

Import all FastAPI dependencies from this module.
Never import from concrete implementations (mock_sui, database) in route handlers.
"""

import logging

from app.core.database import get_db  # noqa: F401 — re-exported for route handlers
from app.services.blockchain.base import BlockchainService
from app.services.blockchain.mock_sui import MockSuiService

logger = logging.getLogger(__name__)


def get_blockchain() -> BlockchainService:
    """
    Return the active BlockchainService implementation.

    To upgrade to real Sui SDK:
      1. pip install pysui
      2. Implement SuiBlockchainService in app/services/blockchain/sui.py
      3. Change return line to: return SuiBlockchainService(settings.SUI_PRIVATE_KEY)
      4. Zero other changes required in any route handler or service.
    """
    return MockSuiService()


# Plan 04 will add:
# - get_current_user(token, db) -> User
# - require_role(*roles: str) -> Callable
