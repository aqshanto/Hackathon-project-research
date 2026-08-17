# FinCluster AI Research Workspace

## Working Title

**FinCluster: A Comparative Evaluation of Machine Learning Models for Node-Aware MFS Transaction Latency Prediction and Routing**

## Current Stage

**Research Day 2 completed; PaySim schema inspection has started; pilot service-time measurement preparation is now the active task.**

The earlier fixed Heavy/Light classification plan is no longer the primary research methodology. The current primary machine-learning task is **node-aware `service_time_ms` regression**.

## Current Research Direction

```text
PaySim transaction features
+ controlled node-profile features
-> regression model
-> predicted service_time_ms
```

The regression benchmark will be completed before the system-level routing experiment. After model comparison, the best model (and optionally another strong candidate if justified) will be integrated into the FinCluster routing simulator and compared with multiple traditional routing baselines.

## Mentor Feedback Confirmed on Research Day 2

1. PaySim is preferred as the transaction-data source.
2. Measured `service_time_ms` is preferred over handcrafted Heavy/Light labels.
3. Security implications of the layered processing pipeline must be considered.
4. Repeated execution is acceptable when it improves measurement reliability.
5. Research scope and development scope are different; existing project features do not need to be removed merely because the paper focuses on one contribution.
6. Every transaction must have a unique transaction ID.
7. All node-level observations belonging to the same transaction must remain in the same train/test group.
8. Research quality is the priority; comparing more justified models is encouraged.
9. Relevant metrics that strengthen the study should be recorded.
10. Prediction/model evaluation should be completed before system-level experiments.
11. Multiple routing baselines should be used.
12. ACID properties should remain part of the transaction-processing design.

See `notes/mentor_feedback_day2.md` for the detailed record.

## PaySim Inspection Status

A local PaySim CSV has been identified:

```text
PS_20174392719_1491204439457_log.csv
```

Observed schema information currently available:

- 11 columns;
- transaction types: `CASH_IN`, `CASH_OUT`, `DEBIT`, `PAYMENT`, `TRANSFER`;
- no VPN field is present in the verified PaySim schema seen so far;
- exact row count, missing-value counts, duplicate count, data types, and distributions still require programmatic inspection.

### Initial transaction-feature decision

Candidate inputs for the first benchmark:

- `type`
- `amount`
- `oldbalanceOrg`
- `oldbalanceDest`
- `step` (candidate; usefulness must be evaluated)

Initially excluded from model input:

- `nameOrig`
- `nameDest`
- `newbalanceOrig`
- `newbalanceDest`
- `isFraud`
- `isFlaggedFraud`

Additional FinCluster node features will include controlled node-profile information such as CPU and memory limits once the pilot profiles are frozen.

`transaction_id` is required for grouping, traceability, idempotency, and safe transaction handling, but it is **not** an ML input feature.

`service_time_ms` is the **prediction target**, not an input feature.

## Service-Time Measurement Flow

For data collection, the same selected transaction is executed on every controlled node profile. Each transaction-node pair is repeated multiple times.

Initial pilot protocol:

```text
Warm-up executions: 2
Measured executions: 5
Stable target per transaction-node pair: median service_time_ms
```

Example:

```text
TX001 + Low node    -> 5 raw measured service times -> median -> one ground-truth row
TX001 + Medium node -> 5 raw measured service times -> median -> one ground-truth row
TX001 + High node   -> 5 raw measured service times -> median -> one ground-truth row
```

KNN or K-Means is **not** used to create the final measured ground-truth service time. The median of repeated measurements is used.

## KNN and K-Means Roles

- **KNN Regressor:** one candidate supervised regression model that predicts `service_time_ms` from transaction + node features.
- **K-Means:** optional secondary unsupervised analysis for grouping measured/reference service times into interpretable workload bands such as Light / Moderate / Heavy.

They perform different tasks and should not be directly compared as if they were competing algorithms for the same target.

The desired human-facing output may include both:

```text
Predicted Service Time: 37.386 ms
Workload Band: Moderate
```

The workload band is secondary; continuous `service_time_ms` remains the primary research target.

## Core Evaluation Layers

1. **Model-level evaluation:** Which regression model predicts measured transaction processing time most accurately and efficiently?
2. **System-level evaluation:** Does prediction-based routing improve end-to-end performance compared with traditional routing strategies?
3. **Optional interpretability layer:** Can measured service-time distributions be summarized into stable Light / Moderate / Heavy workload bands without replacing the continuous target?

## Planned Routing Baselines

- Round Robin
- Weighted Round Robin
- Least-Loaded
- Shortest Queue (recommended additional baseline)
- Rule-Based Routing
- Prediction-Based Routing
- Optional Oracle Routing as a non-deployable upper-bound benchmark

## Main Scenarios

- Normal traffic
- Festival-surge traffic
- Optional: node degradation and complete node failure

## Formal Proposal Status

`proposal/FinCluster_Research_Proposal_v0.2.docx` and `.pdf` remain the last formal proposal snapshot. They are intentionally preserved rather than silently rewritten after mentor feedback. New Day 2 decisions are recorded in the notes and changelog. A formal proposal v0.3 should be created only when the remaining methodology decisions are frozen.

## Immediate Next Step

1. Put the PaySim CSV in a known local path (recommended: `Research/data/raw/`).
2. Run the updated inspection script against the local file.
3. Record exact row count, dtypes, missing values, blank strings, transaction-type distribution, fraud distribution, sample duplicates, amount statistics, and identifier cardinality.
4. Freeze the reference processing pipeline and security/ACID boundaries.
5. Freeze provisional Low/Medium/High node profiles after checking the host machine.
6. Run a small pilot (initially 10 transactions) with repeated service-time measurements.
7. Inspect run-to-run variance before any regression-model training.
