| Processing Operation            | CASH_IN     | CASH_OUT        | DEBIT       | PAYMENT | TRANSFER |
| ------------------------------- | ----------- | --------------- | ----------- | ------- | -------- |
| Schema validation               | ✅          | ✅              | ✅          | ✅      | ✅       |
| Unique TX ID check              | ✅          | ✅              | ✅          | ✅      | ✅       |
| Idempotency check               | ✅          | ✅              | ✅          | ✅      | ✅       |
| Authorization/security check    | ✅          | ✅              | ✅          | ✅      | ✅       |
| Origin account lookup           | ✅          | ✅              | ✅          | ✅      | ✅       |
| Destination/counterparty lookup | ✅          | ✅              | ✅          | ✅      | ✅       |
| Amount validation               | ✅          | ✅              | ✅          | ✅      | ✅       |
| Balance sufficiency check       | Conditional | ✅              | ✅          | ✅      | ✅       |
| Transaction limit check         | ✅          | ✅              | ✅          | ✅      | ✅       |
| Type-specific validation        | ✅          | ✅              | ✅          | ✅      | ✅       |
| Begin DB transaction            | ✅          | ✅              | ✅          | ✅      | ✅       |
| Debit origin                    | ❌          | ✅              | ✅          | ✅      | ✅       |
| Credit/update destination       | ✅          | ✅/State update | Bank record | ✅      | ✅       |
| Ledger update                   | ✅          | ✅              | ✅          | ✅      | ✅       |
| Audit log                       | ✅          | ✅              | ✅          | ✅      | ✅       |
| Commit / rollback               | ✅          | ✅              | ✅          | ✅      | ✅       |

```
Timer START
    ↓
Schema validation
Security/authorization
Transaction ID + idempotency
Account lookups
Transaction-specific validation
Database operations
Ledger update
Audit log
Commit / rollback
    ↓
Timer STOP
```

service_time_ms = (stop_time - start_time) × 1000

service_time_ms-এর মধ্যে থাকবে
validation
security check
lookup
transaction processing
DB operation
ledger
audit
commit/rollback

থাকবে না
Queue waiting time
Network/client latency
ML inference time
Routing decision time

এগুলো পরে system-level experiment-এ আলাদা measure করব।
