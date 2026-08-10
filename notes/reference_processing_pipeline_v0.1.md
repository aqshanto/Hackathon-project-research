# FinCluster Reference Transaction Processing Pipeline v0.1

## Important Note

This pipeline is a controlled reference implementation designed for
FinCluster research experiments.

It does not claim to reproduce the exact internal processing pipeline
of every real-world bank or Mobile Financial Services provider.

The transaction semantics are aligned with the PaySim transaction model
and documented mobile-money use cases.

---

# Common Stages

These stages are performed for every transaction type.

1. Schema validation
2. Transaction-ID / idempotency / duplicate check
3. Initiating account or party lookup
4. Basic transaction validation

### Schema Validation

The stage exists for every transaction, but the required fields may
differ according to transaction type.

Examples:

- CASH_IN requires customer and agent/merchant information.
- CASH_OUT requires customer and agent/merchant information.
- DEBIT requires customer and destination bank information.
- PAYMENT requires customer and merchant information.
- TRANSFER requires source and destination customer information.

Common checks may include:

- Transaction ID exists
- Transaction type is supported
- Amount exists and is positive
- Required account identifiers exist
- Required transaction fields are correctly formatted

---

# Conditional Stages

These stages are executed depending on the transaction type and
transaction conditions.

5. Destination / merchant / agent / bank lookup
6. Balance or fund-availability validation
7. Transaction-limit and policy validation
8. Risk-model inference when required
9. Additional verification when required

Risk-model inference and additional verification are not automatically
executed simply because a transaction belongs to a particular type.

They should be triggered by a documented processing policy using
information available before transaction completion.

---

# Completion Stages

For transactions that modify balances or financial state:

10. Begin database transaction
11. Apply required balance/state changes
12. Ledger record creation/update
13. Audit-log write
14. Commit on success or rollback on failure
15. Response generation

The database transaction groups related state-changing operations so
that partial financial updates are not treated as successful
transactions.

---

# Transaction-Type Processing Paths

## CASH_IN

Purpose:
Add money to a customer's mobile-money balance through a cash-in
operation.

### Processing Stages

1. Schema validation
2. Transaction-ID / idempotency / duplicate check
3. Customer account lookup
4. Basic transaction validation
5. Agent / merchant lookup
6. Transaction-limit and policy validation
7. Risk screening — optional extension (disabled in baseline v0.1) by policy
8. Additional verification if required
9. Begin database transaction
10. Credit the customer wallet
11. Ledger record creation/update
12. Audit-log write
13. Commit on success or rollback on failure
14. Response generation

### Important Difference

A normal source-balance sufficiency check is not required in the same
way as CASH_OUT because CASH_IN increases the customer's wallet balance.

If agent float or liquidity is simulated in a later version of the
FinCluster pipeline, agent-float validation may be added as a separate
stage.

---

## CASH_OUT

Purpose:
Withdraw money from a customer's mobile-money balance through an
agent/merchant.

### Processing Stages

1. Schema validation
2. Transaction-ID / idempotency / duplicate check
3. Customer account lookup
4. Basic transaction validation
5. Agent / merchant lookup
6. Customer balance / fund-availability validation
7. Transaction-limit and policy validation
8. Risk screening — optional extension (disabled in baseline v0.1) by policy
9. Additional verification if required
10. Begin database transaction
11. Debit the customer wallet
12. Ledger record creation/update
13. Audit-log write
14. Commit on success or rollback on failure
15. Response generation

### Important Difference

Unlike CASH_IN, CASH_OUT reduces the customer's wallet balance.
Therefore sufficient-balance validation is required before successful
completion.

---

## DEBIT

Purpose:
Move money from the customer's mobile-money balance toward a bank or
external debit destination represented in the reference pipeline.

### Processing Stages

1. Schema validation
2. Transaction-ID / idempotency / duplicate check
3. Customer account lookup
4. Basic transaction validation
5. Destination bank / external account lookup
6. Customer balance / fund-availability validation
7. Transaction-limit and policy validation
8. Risk screening — optional extension (disabled in baseline v0.1) by policy
9. Additional verification if required
10. Begin database transaction
11. Debit the customer wallet and record the destination-side operation
12. Ledger record creation/update
13. Audit-log write
14. Commit on success or rollback on failure
15. Response generation

---

## PAYMENT

Purpose:
Pay a merchant for goods or services using the customer's mobile-money
balance.

### Processing Stages

1. Schema validation
2. Transaction-ID / idempotency / duplicate check
3. Customer account lookup
4. Basic transaction validation
5. Merchant lookup and merchant-status validation
6. Customer balance / fund-availability validation
7. Transaction-limit and policy validation
8. Risk screening — optional extension (disabled in baseline v0.1) by policy
9. Additional verification if required
10. Begin database transaction
11. Debit the customer wallet
12. Credit or record the merchant-side payment
13. Ledger record creation/update
14. Audit-log write
15. Commit on success or rollback on failure
16. Response generation

---

## TRANSFER

Purpose:
Transfer money from one mobile-money customer account to another
customer account.

### Processing Stages

1. Schema validation
2. Transaction-ID / idempotency / duplicate check
3. Source customer account lookup
4. Basic transaction validation
5. Destination customer account lookup
6. Source and destination account validation
7. Source balance / fund-availability validation
8. Transaction-limit and policy validation
9. Risk screening — optional extension (disabled in baseline v0.1) by policy
10. Additional verification if required
11. Begin database transaction
12. Debit the source customer wallet
13. Credit the destination customer wallet
14. Ledger record creation/update
15. Audit-log write
16. Commit on success or rollback on failure
17. Response generation

## Risk Screening

Risk-model inference is not part of the baseline FinCluster Reference
Pipeline v0.1.

It is reserved as an optional extension for a later experiment.
This avoids introducing a second machine-learning problem before
the latency-prediction and routing methodology is validated.

The reference pipeline may later incorporate risk-based screening,
where higher-risk transactions trigger additional verification.
