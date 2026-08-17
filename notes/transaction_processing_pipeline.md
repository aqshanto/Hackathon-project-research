# FinCluster Transaction Processing Pipeline - Quick Flow

This is a compact view of `reference_processing_pipeline_v0.1.md`.

```text
1. Request/schema validation
        ↓
2. Controlled authentication/authorization/security validation
        ↓
3. Unique transaction ID / idempotency / duplicate check
        ↓
4. Transaction-type and initiating-account validation
        ↓
5. Required destination/merchant/agent lookup
        ↓
6. Balance/fund validation when applicable
        ↓
7. Transaction-limit and policy validation
        ↓
8. Additional verification when required by the locked policy
        ↓
9. Begin database transaction
        ↓
10. Required debit/credit/state operation
        ↓
11. Ledger update
        ↓
12. Audit-log write
        ↓
13. Commit on success or rollback on failure
        ↓
14. Response/final processing completion
```

## Measurement Boundary

```text
Timer start: immediately before step 1
Timer stop: after step 14 completes
```

Queue waiting and unrelated client/network delay are not part of the regression target.

## Fairness Rule

Every controlled node profile executes the same pipeline/security/ACID logic. A faster result must not be obtained by turning security or integrity checks off for one profile.
