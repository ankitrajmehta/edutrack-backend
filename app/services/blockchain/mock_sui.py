"""
Mock Sui blockchain implementation.

Simulates Sui Move contract calls with realistic async latency and
deterministic-enough responses for demo purposes.

DO NOT import this module directly in callers.
Use: blockchain: BlockchainService = Depends(get_blockchain)
"""

import asyncio
import hashlib
import logging
import secrets
from random import uniform

from app.services.blockchain.base import BlockchainService, TxResult, WalletResult

logger = logging.getLogger(__name__)


class MockSuiService:
    """
    Mock implementation of BlockchainService using random hex values.

    Simulates Sui Move contract interactions:
    - Async latency: 0.1–0.4s per call
    - tx_hash: 64-char hex (secrets.token_hex(32))
    - object_id: "0x" + 32-char hex (secrets.token_hex(16))
    - wallet_address: 32-char hex (secrets.token_hex(16))
    - get_balance: deterministic float based on wallet_id hash

    All calls emit structured log lines for observability.
    """

    async def _simulate_latency(self) -> None:
        """Simulate blockchain network latency (0.1–0.4 seconds)."""
        await asyncio.sleep(uniform(0.1, 0.4))

    def _make_tx_result(self, status: str = "success") -> TxResult:
        tx_hash = secrets.token_hex(32)  # 64-char hex
        object_id = "0x" + secrets.token_hex(16)  # "0x" + 32-char hex
        return TxResult(tx_hash=tx_hash, object_id=object_id, status=status)

    async def create_wallet(self, student_id: str) -> WalletResult:
        """Create a mock blockchain wallet for a student."""
        await self._simulate_latency()
        wallet_address = secrets.token_hex(16)  # 32-char mock address
        tx_hash = secrets.token_hex(32)  # 64-char hex
        logger.info(
            "[BLOCKCHAIN] create_wallet | studentId: %s | walletAddress: %s | txHash: %s",
            student_id,
            wallet_address,
            tx_hash,
        )
        return WalletResult(wallet_address=wallet_address, tx_hash=tx_hash)

    async def donate(
        self, donor_id: str, target_type: str, target_id: str, amount: float
    ) -> TxResult:
        """Record a donation on the mock blockchain."""
        await self._simulate_latency()
        result = self._make_tx_result()
        logger.info(
            "[BLOCKCHAIN] donate | donorId: %s | target: %s/%s | amount: %.2f | txHash: %s",
            donor_id,
            target_type,
            target_id,
            amount,
            result.tx_hash,
        )
        return result

    async def allocate_funds(
        self, ngo_id: str, program_id: str, student_id: str, amount: float
    ) -> TxResult:
        """Allocate funds from NGO program escrow to student wallet."""
        await self._simulate_latency()
        result = self._make_tx_result()
        logger.info(
            "[BLOCKCHAIN] allocate_funds | ngoId: %s | programId: %s | studentId: %s | amount: %.2f | txHash: %s",
            ngo_id,
            program_id,
            student_id,
            amount,
            result.tx_hash,
        )
        return result

    async def settle_invoice(
        self, ngo_id: str, school_id: str, invoice_id: str, amount: float
    ) -> TxResult:
        """Settle a school invoice on the mock blockchain."""
        await self._simulate_latency()
        result = self._make_tx_result()
        logger.info(
            "[BLOCKCHAIN] settle_invoice | ngoId: %s | schoolId: %s | invoiceId: %s | amount: %.2f | txHash: %s",
            ngo_id,
            school_id,
            invoice_id,
            amount,
            result.tx_hash,
        )
        return result

    async def get_balance(self, wallet_id: str) -> float:
        """
        Get wallet balance — deterministic based on wallet_id hash.
        Consistent across calls for the same wallet_id.
        """
        await self._simulate_latency()
        # Deterministic: sha256 of wallet_id → take first 4 bytes as int → scale to realistic USD amount
        digest = hashlib.sha256(wallet_id.encode()).digest()
        raw = int.from_bytes(digest[:4], "big")
        balance = (raw % 50000) / 100.0  # 0.00 – 499.99
        logger.info(
            "[BLOCKCHAIN] get_balance | walletId: %s | balance: %.2f",
            wallet_id,
            balance,
        )
        return balance
