# Research Day 2 Summary

## Completed

- Discussed the revised node-aware service-time regression direction with the mentor.
- Received mentor preference for PaySim as the transaction-data source.
- Received mentor support for measured `service_time_ms` as the stronger target.
- Recorded the requirement to consider security while preserving the layered transaction-processing pipeline.
- Confirmed that repeated execution may be used when it improves measurement reliability.
- Confirmed that a focused research scope does not require deleting unrelated FinCluster development features.
- Confirmed the need for a unique transaction ID.
- Confirmed grouped train/test handling by transaction ID.
- Confirmed that model prediction should be evaluated before the system-level routing experiment.
- Confirmed multiple routing baselines and preservation of ACID properties.
- Began local PaySim schema inspection.

## Current PaySim Facts

```text
Filename: PS_20174392719_1491204439457_log.csv
Observed columns: 11
Observed transaction types:
- CASH_IN
- CASH_OUT
- DEBIT
- PAYMENT
- TRANSFER
```

Exact row count, missing-value counts, dtypes, duplicate count, and distributions are still pending programmatic inspection.

## Current ML Task

```text
Transaction features + Node features -> Regression model -> Predicted service_time_ms
```

`service_time_ms` is target `y`, not an input feature.

## Current Measurement Plan

```text
Each selected transaction
-> every controlled node profile
-> 2 warm-up executions (provisional)
-> 5 measured executions (provisional)
-> median measured service_time_ms per transaction-node pair
```

## Current Workload-Band Plan

Light / Moderate / Heavy is a secondary interpretation layer, not the primary target.

K-Means may be evaluated later for grouping measured/reference service times. KNN Regressor remains one candidate regression model for predicting service time.

## Immediate Next Step

Complete the PaySim inspection, freeze the processing pipeline and pilot node profiles, and run a small service-time measurement pilot before training regression models.
