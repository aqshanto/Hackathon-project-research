"""
FinCluster Research — Reference Processing Pipeline v0.3 (Rebalanced)

Purpose
-------
Execute a PaySim-format transaction through a controlled, documented processing
pipeline and measure service_time_ms under externally enforced Docker CPU/RAM
limits.

Why v0.3 exists
---------------
v0.2 successfully created clear Low/Medium/High node separation, but its common
500,000-iteration PBKDF2 workload dominated the total service time. As a result,
different PaySim transaction types had almost identical latency on the same node.

v0.3 rebalances the controlled benchmark:
- common security/compliance work is reduced;
- each transaction type executes a documented set of workflow-integrity modules;
- every module performs real PBKDF2-HMAC-SHA256 work plus an audit write;
- no amount threshold, fraud label, random delay, sleep(), or node-specific
  Python rule controls the workload.

This creates two measurable effects:
1. external Docker resource limits create node-level performance differences;
2. different transaction workflows create transaction-type-level differences.

IMPORTANT METHODOLOGY NOTE
--------------------------
The workflow-module counts below are a CONTROLLED REFERENCE-SYSTEM abstraction.
They are NOT claimed to reproduce bKash, Nagad, Rocket, or any real MFS provider's
internal processing complexity. They must be disclosed exactly in the paper.
The measured target is still produced by executing code under controlled
resources; it is not assigned from a precomputed Heavy/Light label formula.

Important research rules
------------------------
1. Controlled simulation only — NOT production banking code.
2. No time.sleep() or hidden artificial delay is used.
3. No amount-based "make this transaction slower" rule exists.
4. PaySim isFraud/isFlaggedFraud are NOT workload labels and are not used here.
5. PaySim newbalanceOrig/newbalanceDest are NOT used to decide processing.
6. Node performance differences come from external Docker/OS resource limits.
7. Common security work is identical for every transaction.
8. Type-specific work is determined only by the documented workflow path.
9. Benchmark state reset happens OUTSIDE service_time_ms.
10. service_time_ms includes:
       schema validation
       common HMAC + PBKDF2 security/compliance work
       authorization/account checks
       explicit DB transaction
       idempotency check
       type-specific workflow-integrity modules
       type-specific validation and state changes
       ledger and audit writes
       completion record
       COMMIT or ROLLBACK
11. Queue wait, client/network latency, ML inference, and routing-decision time
    are NOT part of service_time_ms.
12. The iteration counts are calibration parameters. Freeze and document them
    before collecting the final research dataset.

Supported PaySim transaction types
----------------------------------
CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from time import perf_counter_ns
from typing import Any, Dict, Mapping, Optional


PIPELINE_VERSION = "0.3"
SUPPORTED_TYPES = {"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}

# Transparent controlled reference-workflow definitions.
# These names describe simulated processing modules; they are NOT assertions
# about any real MFS provider's proprietary implementation.
TYPE_WORKFLOW_MODULES = {
    "CASH_IN": (
        "cash_in_agent_validation",
        "cash_in_receipt_proof",
    ),
    "PAYMENT": (
        "merchant_validation",
        "payment_receipt_proof",
        "payment_settlement_proof",
    ),
    "CASH_OUT": (
        "cash_out_agent_validation",
        "cash_out_policy_validation",
        "cash_out_receipt_proof",
        "cash_out_settlement_proof",
    ),
    "DEBIT": (
        "debit_mandate_validation",
        "bank_destination_validation",
        "debit_instruction_proof",
        "bank_settlement_proof",
        "debit_reconciliation_proof",
    ),
    "TRANSFER": (
        "destination_account_validation",
        "transfer_policy_validation",
        "transfer_debit_leg_proof",
        "transfer_credit_leg_proof",
        "transfer_settlement_proof",
        "transfer_reconciliation_proof",
    ),
}


class ProcessingError(Exception):
    """Base exception for controlled transaction-processing failures."""


class ValidationError(ProcessingError):
    """Input/schema/policy validation failure."""


class DuplicateTransactionError(ProcessingError):
    """Raised when an already-completed transaction_id is processed again."""


class InsufficientFundsError(ProcessingError):
    """Raised when a debit-like transaction has insufficient origin balance."""


@dataclass(frozen=True)
class NodeProfile:
    """
    Metadata describing the externally controlled node.

    IMPORTANT:
    cpu_limit and memory_mb do not throttle Python by themselves.
    Enforce them with Docker/OS resource limits.
    """

    name: str
    cpu_limit: float
    memory_mb: int


@dataclass(frozen=True)
class ProcessingPolicy:
    """
    Transparent controlled-simulation policy.

    v0.3 calibration defaults:
    - base_crypto_iterations: common work executed by EVERY transaction.
    - workflow_module_iterations: work executed once per documented workflow
      module in TYPE_WORKFLOW_MODULES.

    Neither value depends on amount, balances, fraud labels, or node profile.
    These are controlled benchmark parameters, not production-security guidance.
    """

    absolute_amount_limit: Decimal = Decimal("1000000000.00")
    base_crypto_iterations: int = 80_000
    workflow_module_iterations: int = 20_000


@dataclass
class TransactionRecord:
    transaction_id: str
    step: int
    type: str
    amount: Decimal
    nameOrig: str
    oldbalanceOrg: Decimal
    nameDest: str
    oldbalanceDest: Decimal

    @classmethod
    def from_mapping(
        cls,
        row: Mapping[str, Any],
        transaction_id: Optional[str] = None,
    ) -> "TransactionRecord":
        """
        Build a controlled transaction from a PaySim row.

        nameOrig/nameDest are retained only for operational account lookup.
        They should not be raw regression features.
        """
        return cls(
            transaction_id=transaction_id or str(uuid.uuid4()),
            step=int(row["step"]),
            type=str(row["type"]).strip().upper().replace("-", "_"),
            amount=_money(row["amount"]),
            nameOrig=str(row["nameOrig"]).strip(),
            oldbalanceOrg=_money(row["oldbalanceOrg"]),
            nameDest=str(row["nameDest"]).strip(),
            oldbalanceDest=_money(row["oldbalanceDest"]),
        )


@dataclass
class ProcessingResult:
    transaction_id: str
    attempt_id: str
    node_profile: str
    status: str
    transaction_type: str
    amount: float
    service_time_ms: float
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    origin_balance_before: Optional[float] = None
    origin_balance_after: Optional[float] = None
    destination_balance_before: Optional[float] = None
    destination_balance_after: Optional[float] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StageTimer:
    def __init__(self, timings: Dict[str, float], name: str):
        self.timings = timings
        self.name = name
        self.started_ns = 0

    def __enter__(self):
        self.started_ns = perf_counter_ns()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        elapsed_ms = (perf_counter_ns() - self.started_ns) / 1_000_000.0
        self.timings[self.name] = self.timings.get(self.name, 0.0) + elapsed_ms
        return False


def _money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _cents(value: Decimal) -> int:
    return int(
        (value * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def _amount_from_cents(value: int) -> float:
    return float(Decimal(value) / Decimal(100))


class ReferenceProcessor:
    """
    Controlled FinCluster reference transaction processor.

    Default storage is in-memory SQLite. For independent benchmark repetitions,
    reset_state() must be called before process_transaction().
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        policy: Optional[ProcessingPolicy] = None,
        benchmark_security_key: bytes = b"fincluster-research-v0.3",
    ):
        self.db_path = db_path
        self.policy = policy or ProcessingPolicy()
        self.security_key = benchmark_security_key

        if self.policy.base_crypto_iterations < 1:
            raise ValueError("base_crypto_iterations must be at least 1")
        if self.policy.workflow_module_iterations < 1:
            raise ValueError("workflow_module_iterations must be at least 1")

        self.conn = sqlite3.connect(self.db_path, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.isolation_level = None  # explicit BEGIN / COMMIT / ROLLBACK
        self._create_schema()

    def close(self) -> None:
        self.conn.close()

    def reset_state(self) -> None:
        """
        Reset benchmark state.

        This must happen OUTSIDE the measured region before each independent
        transaction-node execution.
        """
        self.conn.executescript(
            """
            DROP TABLE IF EXISTS audit_log;
            DROP TABLE IF EXISTS ledger;
            DROP TABLE IF EXISTS merchant_receipts;
            DROP TABLE IF EXISTS bank_transfers;
            DROP TABLE IF EXISTS counterparty_events;
            DROP TABLE IF EXISTS processed_transactions;
            DROP TABLE IF EXISTS accounts;
            """
        )
        self._create_schema()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                balance_cents INTEGER NOT NULL,
                account_kind TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE'
            );

            CREATE TABLE IF NOT EXISTS processed_transactions (
                transaction_id TEXT PRIMARY KEY,
                attempt_id TEXT NOT NULL,
                tx_type TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                node_profile TEXT NOT NULL,
                status TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                direction TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                balance_after_cents INTEGER
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                action TEXT NOT NULL,
                payload_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS merchant_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                amount_cents INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bank_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                bank_destination TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS counterparty_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                counterparty_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                amount_cents INTEGER NOT NULL
            );
            """
        )

    def _security_message(self, tx: TransactionRecord) -> bytes:
        payload = {
            "transaction_id": tx.transaction_id,
            "step": tx.step,
            "type": tx.type,
            "amount": str(tx.amount),
            "nameOrig": tx.nameOrig,
            "nameDest": tx.nameDest,
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def _prepare_state(self, tx: TransactionRecord) -> str:
        """
        Benchmark harness setup; deliberately EXCLUDED from service_time_ms.

        Seeds the PaySim pre-transaction balances and creates a request signature
        that will be verified inside the measured pipeline.
        """
        destination_kind = (
            "MERCHANT"
            if tx.nameDest.startswith("M")
            else "COUNTERPARTY"
        )

        for account_id, balance, kind in (
            (tx.nameOrig, tx.oldbalanceOrg, "CUSTOMER"),
            (tx.nameDest, tx.oldbalanceDest, destination_kind),
        ):
            self.conn.execute(
                """
                INSERT INTO accounts(
                    account_id, balance_cents, account_kind, status
                )
                VALUES (?, ?, ?, 'ACTIVE')
                ON CONFLICT(account_id) DO UPDATE SET
                    balance_cents = excluded.balance_cents,
                    account_kind = excluded.account_kind,
                    status = 'ACTIVE'
                """,
                (account_id, _cents(balance), kind),
            )

        return hmac.new(
            self.security_key,
            self._security_message(tx),
            hashlib.sha256,
        ).hexdigest()

    def _validate_schema(self, tx: TransactionRecord) -> None:
        if not tx.transaction_id:
            raise ValidationError("transaction_id is required")
        if tx.type not in SUPPORTED_TYPES:
            raise ValidationError(f"unsupported transaction type: {tx.type}")
        if tx.step < 0:
            raise ValidationError("step must be non-negative")
        if tx.amount <= 0:
            raise ValidationError("amount must be positive")
        if tx.amount > self.policy.absolute_amount_limit:
            raise ValidationError("amount exceeds controlled absolute limit")
        if not tx.nameOrig or not tx.nameDest:
            raise ValidationError("origin and destination identifiers are required")
        if tx.oldbalanceOrg < 0 or tx.oldbalanceDest < 0:
            raise ValidationError("pre-transaction balances cannot be negative")

    def _fixed_crypto_security_work(self, tx: TransactionRecord) -> None:
        """
        Common computational security/compliance workload.

        Every transaction uses the SAME base iteration count. This stage is
        independent of transaction type, amount, balances, fraud status, and
        node profile.

        PBKDF2-HMAC-SHA256 performs real CPU work and can be throttled/preempted
        by Docker CPU quotas. No sleep() is used.
        """
        message = self._security_message(tx)
        salt = b"fincluster-reference-pipeline-v0.3-common"

        derived = hashlib.pbkdf2_hmac(
            "sha256",
            message,
            salt,
            self.policy.base_crypto_iterations,
            dklen=32,
        )

        if len(derived) != 32:
            raise ProcessingError("common cryptographic workload failed")

    def _run_type_workflow_modules(self, tx: TransactionRecord) -> None:
        """
        Execute the documented type-specific reference workflow.

        Each module:
        - uses the SAME workflow_module_iterations parameter;
        - performs real PBKDF2-HMAC-SHA256 work;
        - writes one audit record inside the active DB transaction.

        The number of modules differs because the simulated business workflow
        differs by transaction type. There is NO amount/balance threshold and
        no random or node-specific Python delay.

        This is a controlled benchmark abstraction and must be disclosed in the
        methodology; it is not a claim about any real provider's internals.
        """
        modules = TYPE_WORKFLOW_MODULES.get(tx.type)
        if not modules:
            raise ValidationError(f"no workflow modules defined for: {tx.type}")

        message = self._security_message(tx)

        for module_name in modules:
            salt = (
                f"fincluster-v0.3-workflow:{module_name}"
            ).encode("utf-8")

            proof = hashlib.pbkdf2_hmac(
                "sha256",
                message,
                salt,
                self.policy.workflow_module_iterations,
                dklen=32,
            )

            proof_hash = hashlib.sha256(proof).hexdigest()

            self.conn.execute(
                """
                INSERT INTO audit_log(
                    transaction_id,
                    action,
                    payload_hash
                )
                VALUES (?, ?, ?)
                """,
                (
                    tx.transaction_id,
                    f"WORKFLOW_MODULE:{module_name}",
                    proof_hash,
                ),
            )

    def _verify_security(self, tx: TransactionRecord, signature: str) -> None:
        """
        Measured security/authorization stage.

        HMAC integrity verification + fixed cryptographic workload + active
        origin-account authorization.
        """
        expected = hmac.new(
            self.security_key,
            self._security_message(tx),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValidationError(
                "request integrity/signature verification failed"
            )

        # Same fixed amount of cryptographic work for every transaction.
        self._fixed_crypto_security_work(tx)

        origin = self.conn.execute(
            "SELECT status FROM accounts WHERE account_id = ?",
            (tx.nameOrig,),
        ).fetchone()

        if origin is None or origin["status"] != "ACTIVE":
            raise ValidationError(
                "origin account is not authorized/active"
            )

    def _account(self, account_id: str) -> sqlite3.Row:
        row = self.conn.execute(
            """
            SELECT account_id, balance_cents, account_kind, status
            FROM accounts
            WHERE account_id = ?
            """,
            (account_id,),
        ).fetchone()

        if row is None:
            raise ValidationError(f"account not found: {account_id}")

        return row

    def _type_validation(
        self,
        tx: TransactionRecord,
        origin: sqlite3.Row,
        destination: sqlite3.Row,
        amount_cents: int,
    ) -> None:
        """
        Transaction-specific correctness checks.

        NOTE:
        There is NO amount-triggered extra CPU work in v0.3.
        Valid transactions then execute their documented type workflow modules.
        """
        if tx.type in {"CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}:
            if int(origin["balance_cents"]) < amount_cents:
                raise InsufficientFundsError(
                    "insufficient origin balance"
                )

        if tx.type == "TRANSFER" and tx.nameOrig == tx.nameDest:
            raise ValidationError(
                "TRANSFER source and destination must differ"
            )

        if destination["status"] != "ACTIVE":
            raise ValidationError(
                "destination/counterparty is not active"
            )

        # The transaction is valid. Execute its documented reference workflow.
        # This happens inside the explicit DB transaction and is included in
        # service_time_ms through the type_specific_validation stage.
        self._run_type_workflow_modules(tx)

    def _change_balance(self, account_id: str, delta_cents: int) -> int:
        self.conn.execute(
            """
            UPDATE accounts
            SET balance_cents = balance_cents + ?
            WHERE account_id = ?
            """,
            (delta_cents, account_id),
        )
        return int(self._account(account_id)["balance_cents"])

    def _apply_state(
        self,
        tx: TransactionRecord,
        amount_cents: int,
    ) -> tuple[int, int]:
        """
        Apply controlled type-specific state transitions.

        Returns:
            (origin_balance_after_cents, destination_balance_after_cents)
        """
        origin_before = int(
            self._account(tx.nameOrig)["balance_cents"]
        )
        destination_before = int(
            self._account(tx.nameDest)["balance_cents"]
        )

        origin_after = origin_before
        destination_after = destination_before

        if tx.type == "CASH_IN":
            # Controlled abstraction: initiating account receives value.
            origin_after = self._change_balance(
                tx.nameOrig,
                amount_cents,
            )

            self.conn.execute(
                """
                INSERT INTO counterparty_events(
                    transaction_id,
                    counterparty_id,
                    event_type,
                    amount_cents
                )
                VALUES (?, ?, 'CASH_IN_AGENT_EVENT', ?)
                """,
                (
                    tx.transaction_id,
                    tx.nameDest,
                    amount_cents,
                ),
            )

        elif tx.type == "CASH_OUT":
            origin_after = self._change_balance(
                tx.nameOrig,
                -amount_cents,
            )

            self.conn.execute(
                """
                INSERT INTO counterparty_events(
                    transaction_id,
                    counterparty_id,
                    event_type,
                    amount_cents
                )
                VALUES (?, ?, 'CASH_OUT_AGENT_EVENT', ?)
                """,
                (
                    tx.transaction_id,
                    tx.nameDest,
                    amount_cents,
                ),
            )

        elif tx.type == "DEBIT":
            origin_after = self._change_balance(
                tx.nameOrig,
                -amount_cents,
            )

            self.conn.execute(
                """
                INSERT INTO bank_transfers(
                    transaction_id,
                    bank_destination,
                    amount_cents,
                    status
                )
                VALUES (?, ?, ?, 'CREATED')
                """,
                (
                    tx.transaction_id,
                    tx.nameDest,
                    amount_cents,
                ),
            )

        elif tx.type == "PAYMENT":
            origin_after = self._change_balance(
                tx.nameOrig,
                -amount_cents,
            )

            self.conn.execute(
                """
                INSERT INTO merchant_receipts(
                    transaction_id,
                    merchant_id,
                    amount_cents
                )
                VALUES (?, ?, ?)
                """,
                (
                    tx.transaction_id,
                    tx.nameDest,
                    amount_cents,
                ),
            )

        elif tx.type == "TRANSFER":
            origin_after = self._change_balance(
                tx.nameOrig,
                -amount_cents,
            )
            destination_after = self._change_balance(
                tx.nameDest,
                amount_cents,
            )

        else:
            raise ValidationError(
                f"unsupported transaction type: {tx.type}"
            )

        return origin_after, destination_after

    def _write_ledger(
        self,
        tx: TransactionRecord,
        amount_cents: int,
        origin_after: int,
        destination_after: int,
    ) -> None:
        if tx.type == "CASH_IN":
            rows = [
                (
                    tx.nameOrig,
                    "CREDIT",
                    origin_after,
                )
            ]
        else:
            rows = [
                (
                    tx.nameOrig,
                    "DEBIT",
                    origin_after,
                )
            ]

            if tx.type == "TRANSFER":
                rows.append(
                    (
                        tx.nameDest,
                        "CREDIT",
                        destination_after,
                    )
                )
            elif tx.type == "PAYMENT":
                rows.append(
                    (
                        tx.nameDest,
                        "MERCHANT_RECEIPT",
                        None,
                    )
                )
            elif tx.type == "DEBIT":
                rows.append(
                    (
                        tx.nameDest,
                        "BANK_SETTLEMENT",
                        None,
                    )
                )
            elif tx.type == "CASH_OUT":
                rows.append(
                    (
                        tx.nameDest,
                        "CASH_OUT_COUNTERPARTY",
                        None,
                    )
                )

        for account_id, direction, balance_after in rows:
            self.conn.execute(
                """
                INSERT INTO ledger(
                    transaction_id,
                    account_id,
                    direction,
                    amount_cents,
                    balance_after_cents
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    tx.transaction_id,
                    account_id,
                    direction,
                    amount_cents,
                    balance_after,
                ),
            )

    def _write_audit(self, tx: TransactionRecord) -> None:
        payload_hash = hashlib.sha256(
            self._security_message(tx)
        ).hexdigest()

        self.conn.execute(
            """
            INSERT INTO audit_log(
                transaction_id,
                action,
                payload_hash
            )
            VALUES (?, 'TRANSACTION_PROCESSED', ?)
            """,
            (
                tx.transaction_id,
                payload_hash,
            ),
        )

    def process_transaction(
        self,
        tx: TransactionRecord,
        node_profile: NodeProfile,
    ) -> ProcessingResult:
        """
        Execute one transaction and return measured service time.

        Benchmark pattern:
            processor.reset_state()     # outside timing
            result = processor.process_transaction(tx, node)

        The same logical transaction may be measured repeatedly only after
        reset_state(), otherwise idempotency correctly rejects it.
        """
        attempt_id = str(uuid.uuid4())

        # Harness setup is intentionally outside service_time_ms.
        signature = self._prepare_state(tx)

        timings: Dict[str, float] = {}
        total_start_ns = perf_counter_ns()
        in_db_transaction = False

        origin_before: Optional[int] = None
        destination_before: Optional[int] = None
        origin_after: Optional[int] = None
        destination_after: Optional[int] = None

        try:
            with StageTimer(timings, "schema_validation"):
                self._validate_schema(tx)

            # Includes HMAC + common PBKDF2 workload + authorization lookup.
            with StageTimer(timings, "security_authorization"):
                self._verify_security(tx, signature)

            with StageTimer(timings, "begin_db_transaction"):
                self.conn.execute("BEGIN IMMEDIATE")
                in_db_transaction = True

            with StageTimer(timings, "idempotency_check"):
                existing = self.conn.execute(
                    """
                    SELECT 1
                    FROM processed_transactions
                    WHERE transaction_id = ?
                    """,
                    (tx.transaction_id,),
                ).fetchone()

                if existing is not None:
                    raise DuplicateTransactionError(
                        "transaction already completed: "
                        f"{tx.transaction_id}"
                    )

            with StageTimer(timings, "account_lookup"):
                origin = self._account(tx.nameOrig)
                destination = self._account(tx.nameDest)

                origin_before = int(
                    origin["balance_cents"]
                )
                destination_before = int(
                    destination["balance_cents"]
                )

            amount_cents = _cents(tx.amount)

            with StageTimer(
                timings,
                "type_specific_validation",
            ):
                self._type_validation(
                    tx,
                    origin,
                    destination,
                    amount_cents,
                )

            with StageTimer(timings, "state_update"):
                (
                    origin_after,
                    destination_after,
                ) = self._apply_state(
                    tx,
                    amount_cents,
                )

            with StageTimer(timings, "ledger_update"):
                self._write_ledger(
                    tx,
                    amount_cents,
                    origin_after,
                    destination_after,
                )

            with StageTimer(timings, "audit_log"):
                self._write_audit(tx)

            with StageTimer(timings, "completion_record"):
                self.conn.execute(
                    """
                    INSERT INTO processed_transactions(
                        transaction_id,
                        attempt_id,
                        tx_type,
                        amount_cents,
                        node_profile,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, 'SUCCESS')
                    """,
                    (
                        tx.transaction_id,
                        attempt_id,
                        tx.type,
                        amount_cents,
                        node_profile.name,
                    ),
                )

            with StageTimer(timings, "commit"):
                self.conn.execute("COMMIT")
                in_db_transaction = False

            total_ms = (
                perf_counter_ns() - total_start_ns
            ) / 1_000_000.0

            return ProcessingResult(
                transaction_id=tx.transaction_id,
                attempt_id=attempt_id,
                node_profile=node_profile.name,
                status="SUCCESS",
                transaction_type=tx.type,
                amount=float(tx.amount),
                service_time_ms=total_ms,
                stage_timings_ms=timings,
                origin_balance_before=(
                    _amount_from_cents(origin_before)
                    if origin_before is not None
                    else None
                ),
                origin_balance_after=(
                    _amount_from_cents(origin_after)
                    if origin_after is not None
                    else None
                ),
                destination_balance_before=(
                    _amount_from_cents(destination_before)
                    if destination_before is not None
                    else None
                ),
                destination_balance_after=(
                    _amount_from_cents(destination_after)
                    if destination_after is not None
                    else None
                ),
            )

        except Exception as exc:
            if in_db_transaction:
                rollback_started_ns = perf_counter_ns()

                try:
                    self.conn.execute("ROLLBACK")
                finally:
                    timings["rollback"] = (
                        perf_counter_ns()
                        - rollback_started_ns
                    ) / 1_000_000.0

            total_ms = (
                perf_counter_ns() - total_start_ns
            ) / 1_000_000.0

            return ProcessingResult(
                transaction_id=tx.transaction_id,
                attempt_id=attempt_id,
                node_profile=node_profile.name,
                status="FAILED",
                transaction_type=tx.type,
                amount=float(tx.amount),
                service_time_ms=total_ms,
                stage_timings_ms=timings,
                origin_balance_before=(
                    _amount_from_cents(origin_before)
                    if origin_before is not None
                    else None
                ),
                origin_balance_after=(
                    _amount_from_cents(origin_after)
                    if origin_after is not None
                    else None
                ),
                destination_balance_before=(
                    _amount_from_cents(destination_before)
                    if destination_before is not None
                    else None
                ),
                destination_balance_after=(
                    _amount_from_cents(destination_after)
                    if destination_after is not None
                    else None
                ),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
