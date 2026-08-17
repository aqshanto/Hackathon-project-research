# Latency Target and Measurement Definition - Version 0.2 (Updated Notes)

## 1. Primary Machine-Learning Task

The primary task is **node-aware service-time regression**.

```text
Pre-routing transaction features
+ controlled node-profile features
-> Predicted service_time_ms
```

Dynamic runtime-condition features may be added later only if they are measured before routing and deliberately included in the experimental design.

## 2. Primary Target

```text
service_time_ms
```

`service_time_ms` is the measured server-side time required to execute the documented FinCluster reference processing pipeline for one transaction on one controlled node profile.

It is the dependent variable/target `y`. It must not be included in model input `X`.

## 3. Measurement Boundary

Recommended baseline boundary:

```text
Timer starts immediately before the reference processing pipeline begins.
Timer stops after the pipeline reaches its final processing state and response-generation work included by the locked protocol is complete.
```

The exact timer location must remain identical for all node profiles and all measurements in a dataset version.

Unrelated client/network delay is excluded from the regression target.

## 4. Service Time vs End-to-End Latency

### Service Time - ML Target

```text
processing start -> processing completion
```

### End-to-End Latency - System Metric

```text
transaction arrival
+ queue waiting
+ routing decision
+ model inference
+ selected-node processing
+ response completion
```

Queue waiting is not included in the primary service-time label because it depends on traffic and scheduler state.

## 5. Input Features

### Current PaySim Candidates

- `type`
- `amount`
- `oldbalanceOrg`
- `oldbalanceDest`
- `step` (candidate; evaluate usefulness)

### Current PaySim Exclusions

- `nameOrig`
- `nameDest`
- `newbalanceOrig`
- `newbalanceDest`
- `isFraud`
- `isFlaggedFraud`

VPN is not present in the verified current PaySim schema and is not part of the baseline feature set.

### Node Features

- `node_profile`
- `cpu_limit`
- `memory_limit`
- optional `concurrency_limit` after pilot approval

Potential later dynamic features, if recorded before routing:

- current queue length;
- current CPU load;
- current memory load;
- node health state.

## 6. Unique Transaction Identity and Grouping

Every selected transaction receives a stable unique `transaction_id`.

The ID is used for grouping, traceability, idempotency, and later safe-reroute logic, but is not an ML predictor.

All observations derived from the same transaction must remain in one train/validation/test split group.

## 7. Reference Processing Pipeline

The pipeline is a **FinCluster reference implementation**, not a claim that every bank or MFS provider uses the same internal sequence.

Baseline categories include:

1. schema/request validation;
2. security/authentication/authorization control as defined by the baseline;
3. transaction-ID/idempotency/duplicate check;
4. account/entity lookup and transaction-type validation;
5. balance/fund and transaction-limit/policy checks when applicable;
6. optional conditional verification defined by policy;
7. begin database transaction;
8. required debit/credit/state changes;
9. ledger update;
10. audit-log write;
11. commit or rollback;
12. response/final processing completion.

All compared node profiles must run the same locked security and integrity logic. Performance gains must not be created by disabling security/ACID steps on one profile.

## 8. ACID and Integrity

The processing design preserves:

- **Atomicity:** related state updates either commit together or roll back.
- **Consistency:** defined account/ledger invariants remain valid.
- **Isolation:** concurrent transaction execution must not corrupt shared financial state.
- **Durability:** committed experiment state should persist according to the selected test database design.

Idempotency/exactly-once concerns are related but separate from ACID. A stable transaction ID and idempotency check are required for duplicate protection.

## 9. Repeated Measurement Procedure

For every selected transaction and every node profile:

1. perform warm-up executions;
2. execute the same processing path multiple measured times;
3. record every raw run separately;
4. randomize/interleave node-profile run order where feasible to reduce time-order bias;
5. calculate a robust aggregate for that transaction-node pair;
6. store the aggregate as the ground-truth `service_time_ms` for model training;
7. retain raw runs for variance and reproducibility analysis.

### Provisional Pilot Protocol

```text
Warm-up runs: 2
Measured repetitions: 5
Primary aggregate: median service_time_ms
```

The final repetition count must be decided after pilot variance analysis.

## 10. Important Correction: KNN/K-Means Do Not Create the Ground-Truth Time

Incorrect flow:

```text
Repeated runs -> KNN/K-Means -> final service_time_ms
```

Correct flow:

```text
Repeated runs -> median -> measured ground-truth service_time_ms
```

Then:

```text
Transaction + node features -> regression models -> predicted service_time_ms
```

Separately, optional:

```text
Measured/reference service-time distribution -> K-Means -> workload bands
```

## 11. Supporting Measurements

Useful analysis columns that are not automatically online model inputs:

- CPU time;
- peak memory;
- database time;
- stage-level timing;
- query count;
- count of executed verification stages;
- commit/rollback state;
- experiment host/process information.

## 12. Controlled Node Profiles

Low-, Medium-, and High-capacity profiles will be created using controlled resource settings, likely Docker resource limits on the same host.

Exact CPU/memory/concurrency values remain provisional until the host machine is inspected and a pilot is run.

The same transaction must be executed on every selected node profile to avoid transaction-distribution bias.

## 13. Candidate Regression Models

### Core benchmark

- Linear Regression
- Ridge Regression
- KNN Regressor
- Decision Tree Regressor
- Random Forest Regressor
- Extra Trees Regressor
- Gradient Boosting Regressor
- HistGradientBoosting Regressor
- XGBoost Regressor
- CatBoost Regressor

### Additional justified candidates

- LightGBM Regressor
- Support Vector Regression (SVR)
- MLP Regressor

More models should only be retained if the comparison remains fair and computationally feasible.

## 14. Model-Level Metrics

### Prediction quality

- MAE - primary interpretable error metric
- RMSE - penalizes large errors
- R-squared
- Median Absolute Error
- P95 absolute prediction error

### Efficiency

- training time
- mean inference latency
- P95 inference latency
- model size
- peak memory where feasible

All models must use the same grouped splits, preprocessing policy, seeds, and comparable tuning budget.

## 15. Secondary Workload Band

Light / Moderate / Heavy is not the primary target.

An optional secondary layer may use measured/reference service-time distributions to derive interpretable workload bands. K-Means is one candidate clustering method.

If clustering is used, evaluate separation/stability and do not force a three-cluster result without evidence.

Desired dashboard-style output may contain both:

```text
Predicted Service Time: 37.386 ms
Workload Band: Moderate
```

## 16. System-Level Experiment Comes Later

After the prediction benchmark is complete, selected model(s) will be integrated into routing and compared with multiple baselines using:

- average/p50/p95/p99 end-to-end latency;
- throughput;
- queue wait;
- SLA-violation rate;
- simulated cost;
- node utilization;
- optional failure/recovery metrics.

## 17. Current Limitations

- Exact PaySim provenance/license still requires documentation.
- Full programmatic PaySim inspection is not yet recorded.
- Reference pipeline is specified but not yet implemented as the research measurement harness.
- Exact node-profile limits are not final.
- No measured service-time dataset has been collected yet.
- No regression model result exists yet.
- Any workload clusters remain proposed until enough measured data exist.
