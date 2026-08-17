# Service-Time Measurement Protocol v0.1

## Purpose

Generate reproducible ground-truth `service_time_ms` values for node-aware regression.

## Unit of Measurement

One **transaction-node pair**.

Example:

```text
TX001 + Medium Node
```

## Provisional Pilot Protocol

For each selected transaction on each selected node profile:

1. execute 2 warm-up runs;
2. execute 5 measured runs;
3. save every measured run separately;
4. compute the median of the 5 measured runs;
5. use that median as the ground-truth `service_time_ms` for the transaction-node pair.

The final repetition count is not frozen until pilot variance is reviewed.

## Initial Pilot Size

```text
Transactions: 10
Node profiles: 3
Measured repetitions: 5
Raw measured observations: 10 x 3 x 5 = 150
Warm-up executions: 10 x 3 x 2 = 60
Total executions including warm-up: 210
Aggregated transaction-node rows: 10 x 3 = 30
```

## Raw Measurement File

Recommended path:

```text
Research/data/raw/pilot_service_time_runs.csv
```

Recommended columns:

```text
transaction_id
node_profile
repetition
service_time_ms
pipeline_version
node_profile_version
run_timestamp_or_order
```

Additional transaction/source metadata may be joined using `transaction_id` rather than copied inconsistently across repeated-run rows.

## Aggregated Dataset

Recommended path:

```text
Research/data/processed/pilot_transaction_node_dataset.csv
```

Each row represents one transaction-node pair and contains:

```text
transaction_id
selected pre-routing PaySim features
node features
service_time_ms  # median target
```

## Variance Review

Before model training, inspect:

- median;
- mean;
- standard deviation;
- min/max;
- coefficient of variation where meaningful;
- outlier runs;
- whether timing differences among node profiles are larger than measurement noise.

If repeated timings are unstable, investigate background processes, Docker scheduling, database cache/warm-up, insufficient workload duration, thermal effects, or measurement-code error before scaling the dataset.

## Run-Order Control

Do not always execute every Low-node run first, then every Medium run, then every High run for the entire dataset. Randomize/interleave transaction-node order where feasible so that time, caching, and thermal effects do not systematically favor one profile.

## Ground-Truth Rule

```text
5 measured runs -> median -> one measured service_time_ms target
```

No regression/clustering algorithm is used to create this target.
