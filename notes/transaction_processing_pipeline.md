1. Request/schema validation
        ↓
2. Authentication/authorization simulation
        ↓
3. Unique transaction ID / idempotency check
        ↓
4. Transaction-type validation
        ↓
5. Source-account lookup
        ↓
6. Destination-account lookup
        ↓
7. Balance validation
        ↓
8. Transaction-limit validation
        ↓
9. Required verification/risk processing
        ↓
10. Begin database transaction
        ↓
11. Debit operation
        ↓
12. Credit operation
        ↓
13. Ledger update
        ↓
14. Audit-log write
        ↓
15. Commit or rollback
        ↓
16. Processing complete