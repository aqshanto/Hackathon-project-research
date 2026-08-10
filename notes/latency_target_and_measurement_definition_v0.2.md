# Latency Target and Measurement Definition - Version 0.2

## 1. Primary Machine-Learning Task

The primary task is **node-aware service-time regression**.

The model will estimate how long a transaction is expected to require on a known controlled node profile.

```text
Transaction features
+ Node-profile features
+ Controlled runtime-condition features
-> Predicted service_time_ms
```

## 2. Primary Target

The proposed primary target is:

```text
service_time_ms
```

`service_time_ms` means the time spent executing the FinCluster reference processing pipeline after the transaction begins processing and before the response is produced.

It should not include unrelated client-network delay.

## 3. Difference Between Service Time and End-to-End Latency

### Service Time

Used as the ML target:

```text
Processing start -> Processing completion
```

### End-to-End Latency

Used as a system-level evaluation metric:

```text
Transaction arrival
+ queue waiting
+ routing decision
+ model inference
+ node processing
+ response completion
```

Queue waiting time is not the transaction's intrinsic workload label. It depends on traffic and scheduler behaviour.

## 4. Input Features

### Transaction Features

Only attributes available before routing should be considered, for example:

- transaction type
- amount
- pre-transaction source balance
- pre-transaction destination balance, when available
- step or time-window feature
- derived balance-consistency indicators that do not use future information
- pre-routing risk or verification indicators, when legitimately available

### Node Features

The feature columns stay the same for all rows; only the values change between node profiles.

Examples:

- CPU quota or allocated CPU count
- memory limit
- node profile identifier
- concurrency level
- current queue length, when measured at routing time
- current CPU-load band, when controlled and recorded

### Columns Requiring Leakage Review

- `isFraud`
- `isFlaggedFraud`
- post-transaction balance columns
- raw account identifiers
- measurements generated after execution

## 5. Reference Processing Pipeline

The pipeline is a **FinCluster reference implementation**, not a claim that all banks or MFS providers use the exact same internal sequence.

The provisional common stages are:

1. common request/schema validation;
2. transaction-ID and idempotency lookup;
3. required account and entity lookup;
4. balance, limit, and transaction-rule checks;
5. optional risk-model inference or enhanced verification;
6. database transaction and ledger update;
7. audit-log write;
8. response generation.

Transaction-type-specific validation and processing branches may add or skip stages. The exact policy must be documented and mentor-reviewed before data collection.

## 6. Why Schema Validation Can Differ

Every transaction uses common validation, but type-specific fields differ.

Examples:

- a balance inquiry may require one account identifier;
- a payment may require a merchant identifier;
- a cash-out may require an agent identifier;
- a transfer may require valid source and destination accounts.

This variation does not create a model-training problem. It creates measurable variation that the model can learn, provided the relevant pre-routing transaction features are included.

## 7. Measurement Procedure

For every selected transaction and node profile:

1. run warm-up executions;
2. execute the same processing path multiple measured times;
3. randomise the order of node-profile runs;
4. record every raw run;
5. use the median measured service time as the stable target;
6. record the exact pipeline version, software environment, and node profile.

Proposed initial protocol:

```text
Warm-up runs: 2
Measured repetitions: 5
Primary aggregate: median service_time_ms
```

This protocol is provisional and may be revised after a pilot benchmark.

## 8. Supporting Measurements

These measurements support analysis but are not automatically model inputs:

- CPU time
- peak memory
- database time
- model-inference time inside the pipeline
- count of executed validation or verification stages
- query count
- rollback/commit status

Stage-level execution times are mainly explanatory columns because they are not known before the transaction executes.

## 9. Controlled Node Profiles

Docker resource limits can create reproducible node profiles on the same host, such as low-, medium-, and high-capacity profiles.

The exact profiles have not yet been approved. They must be selected through a pilot experiment and documented precisely.

Results measured on one host are valid for that documented System Under Test. A company using different servers would need to:

- run a local calibration benchmark;
- collect local processing measurements; and
- recalibrate or retrain the latency model.

The first paper should not claim universal accuracy on unseen hardware.

## 10. Bias and Data-Splitting Controls

To avoid confounding node capability with transaction type:

- each sampled transaction should be executed on every selected node profile;
- node-profile sample counts should be balanced;
- run order should be randomised;
- the same transaction ID must not appear in both training and test sets;
- all repetitions of one transaction should remain in the same split group;
- models must use the same train/validation/test partitions.

## 11. Candidate Regression Models

- Linear Regression
- Decision Tree Regressor
- Random Forest Regressor
- Extra Trees Regressor
- HistGradientBoosting Regressor
- XGBoost Regressor
- CatBoost Regressor

Optional later models may be added only if they provide a justified baseline or research value.

## 12. Model-Level Metrics

- MAE - primary prediction-error metric
- RMSE - gives higher penalty to large errors
- R-squared - explains variance captured by the model
- model inference latency
- model size

## 13. Derived Routing Category

Heavy/Light is no longer the primary training label.

A compatibility label may be derived later from predicted latency and an agreed SLA or node threshold:

```text
Predicted latency on a low-capacity node <= SLA
-> low-capacity compatible

Predicted latency on a low-capacity node > SLA
-> higher-capacity candidate
```

The SLA or threshold must be defined before final evaluation and must not be tuned on the test set.

## 14. Current Limitations

- The reference pipeline is not yet implemented or mentor-validated.
- The exact Docker profiles are not final.
- No measured latency dataset has been collected yet.
- The design will initially model known controlled profiles rather than unseen company hardware.
- PaySim provides transaction attributes, not processing-time ground truth.
