"""
Blockchain service abstraction layer.

All callers use BlockchainService Protocol — never import mock_sui directly.
To swap to real Sui SDK: implement SuiBlockchainService in sui.py,
change the binding in app/core/dependencies.py get_blockchain(). Zero other changes.
"""

import hashlib
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class WalletResult:
    """Result of creating a student blockchain wallet."""

    wallet_address: str  # 32-char mock or real Sui address
    tx_hash: str  # 64-char hex transaction hash


@dataclass
class TxResult:
    """Result of any blockchain transaction."""

    tx_hash: str  # 64-char hex string, Sui-style
    object_id: str  # "0x" + 32-char hex, Sui object reference
    status: str  # "success" | "pending" | "failed"


@runtime_checkable
class BlockchainService(Protocol):
    """
    Port interface for blockchain operations.
    Implement this Protocol to swap mock → real Sui SDK.
    """

    async def create_wallet(self, student_id: str) -> WalletResult:
        """Create a blockchain wallet for a student. Returns wallet address + tx hash."""
        ...

    async def donate(
        self, donor_id: str, target_type: str, target_id: str, amount: float
    ) -> TxResult:
        """
        Record a donation on-chain.
        target_type: "ngo" | "program" | "student"
        """
        ...

    async def allocate_funds(
        self, ngo_id: str, program_id: str, student_id: str, amount: float
    ) -> TxResult:
        """Allocate funds from NGO program escrow to student wallet."""
        ...

    async def settle_invoice(
        self, ngo_id: str, school_id: str, invoice_id: str, amount: float
    ) -> TxResult:
        """Settle a school invoice — transfer from NGO to school."""
        ...

    async def get_balance(self, wallet_id: str) -> float:
        """Get current wallet balance. Returns float (USD equivalent)."""
        ...
