# FinCluster Reference Transaction Processing Pipeline v0.1

## Purpose and Boundary

This is a controlled reference implementation for FinCluster research experiments.

It does **not** claim to reproduce the exact private processing pipeline of every bank or Mobile Financial Services provider.

The same locked pipeline version must be used across all node profiles in one experiment so that performance differences are attributable to the controlled environment rather than different correctness/security logic.

## Security and Integrity Rule

Security and integrity work must not be selectively disabled to make one node/profile appear faster.

The baseline pipeline includes a documented security/authentication/authorization control stage. Because PaySim does not contain real credentials, this stage is a controlled reference operation rather than real customer authentication.

ACID database behavior remains part of the design for state-changing operations.

## Timing Boundary

For the baseline measurement dataset:

```text
T0: immediately before the first reference-pipeline server-side processing stage
T1: after commit/rollback and the final response-generation work included by the locked pipeline
service_time_ms = (T1 - T0) in milliseconds
```

Client/network delay and queue waiting are excluded from this regression target.

## Common Stages

1. Request/schema validation
2. Controlled authentication/authorization/security validation
3. Unique transaction-ID / idempotency / duplicate check
4. Initiating account/party lookup
5. Basic transaction and transaction-type validation

### Schema Validation

Common checks may include:

- transaction ID exists;
- transaction type is supported;
- amount exists and is positive;
- required account/entity identifiers exist;
- required fields match the transaction type;
- values are correctly formatted.

### Unique Transaction Identity

Every experimental transaction receives a stable unique `transaction_id`.

The ID is used for:

- idempotency/duplicate checks;
- grouping all node observations for train/validation/test splitting;
- traceability;
- later safe-reroute/attempt tracking.

It is not used as an ML predictor.

## Conditional Processing Stages

Depending on transaction type and documented policy:

6. destination / merchant / agent / bank lookup;
7. balance/fund-availability validation;
8. transaction-limit and policy validation;
9. additional verification when required.

Risk-model inference is **not** part of the baseline v0.1 timing pipeline unless a later experiment explicitly enables and documents it. This prevents introducing a second ML problem before the latency-prediction methodology is validated.

## ACID Completion Stages

For state-changing transactions:

10. begin database transaction;
11. apply required debit/credit/state changes;
12. create/update ledger record;
13. write audit record;
14. commit on success or roll back on failure;
15. generate final processing response.

### ACID Interpretation

- **Atomicity:** all related financial state changes succeed together or roll back together.
- **Consistency:** defined balance/ledger invariants remain valid.
- **Isolation:** concurrent transactions should not create invalid shared state.
- **Durability:** committed test state persists according to the chosen database setup.

Idempotency is separate from ACID and protects against processing one transaction successfully more than once.

# Transaction-Type Processing Paths

## CASH_IN

Purpose: add money to a customer's mobile-money balance through a cash-in operation.

1. Schema validation
2. Controlled authentication/authorization/security validation
3. Transaction-ID / idempotency / duplicate check
4. Customer account lookup
5. Basic transaction validation
6. Agent/merchant lookup
7. Transaction-limit and policy validation
8. Additional verification if required by the locked policy
9. Begin database transaction
10. Credit customer wallet
11. Ledger update
12. Audit-log write
13. Commit or rollback
14. Response generation

A normal customer source-balance sufficiency check is not required in the same way as CASH_OUT because the customer balance is being increased. Agent-float validation may be added only in a later explicitly versioned pipeline.

## CASH_OUT

Purpose: withdraw money from a customer's mobile-money balance through an agent/merchant.

1. Schema validation
2. Controlled authentication/authorization/security validation
3. Transaction-ID / idempotency / duplicate check
4. Customer account lookup
5. Basic transaction validation
6. Agent/merchant lookup
7. Customer balance/fund-availability validation
8. Transaction-limit and policy validation
9. Additional verification if required by the locked policy
10. Begin database transaction
11. Debit customer wallet
12. Ledger update
13. Audit-log write
14. Commit or rollback
15. Response generation

## DEBIT

Purpose: move money from the customer's mobile-money balance toward an external debit destination represented by the reference pipeline.

1. Schema validation
2. Controlled authentication/authorization/security validation
3. Transaction-ID / idempotency / duplicate check
4. Customer account lookup
5. Basic transaction validation
6. Destination lookup
7. Customer balance/fund-availability validation
8. Transaction-limit and policy validation
9. Additional verification if required by the locked policy
10. Begin database transaction
11. Debit customer wallet and record destination-side operation
12. Ledger update
13. Audit-log write
14. Commit or rollback
15. Response generation

## PAYMENT

Purpose: pay a merchant using the customer's mobile-money balance.

1. Schema validation
2. Controlled authentication/authorization/security validation
3. Transaction-ID / idempotency / duplicate check
4. Customer account lookup
5. Basic transaction validation
6. Merchant lookup/status validation
7. Customer balance/fund-availability validation
8. Transaction-limit and policy validation
9. Additional verification if required by the locked policy
10. Begin database transaction
11. Debit customer wallet
12. Credit/record merchant-side payment
13. Ledger update
14. Audit-log write
15. Commit or rollback
16. Response generation

## TRANSFER

Purpose: transfer money from one mobile-money customer account to another.

1. Schema validation
2. Controlled authentication/authorization/security validation
3. Transaction-ID / idempotency / duplicate check
4. Source customer lookup
5. Basic transaction validation
6. Destination customer lookup
7. Source/destination account validation
8. Source balance/fund-availability validation
9. Transaction-limit and policy validation
10. Additional verification if required by the locked policy
11. Begin database transaction
12. Debit source wallet
13. Credit destination wallet
14. Ledger update
15. Audit-log write
16. Commit or rollback
17. Response generation

## Baseline Risk-Screening Decision

Risk-model inference is disabled in the baseline v0.1 research timing pipeline.

A later version may explicitly add pre-routing risk indicators or risk screening, but that change must create a new pipeline version and be evaluated separately.
