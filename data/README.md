# Research Data Directory

## Important

The PaySim CSV itself is **not bundled** in this research ZIP.

Recommended local placement:

```text
Research/data/raw/PS_20174392719_1491204439457_log.csv
```

Do not modify the original raw CSV in place.

## Directory Roles

### `raw/`

Store immutable source data and raw measurement logs.

Examples:

```text
PS_20174392719_1491204439457_log.csv
pilot_service_time_runs.csv
```

### `processed/`

Store reproducibly generated analysis/model datasets.

Example:

```text
pilot_transaction_node_dataset.csv
```

## Target Dataset Rule

The processed regression dataset must contain transaction/node input features plus measured target:

```text
X: pre-routing transaction features + controlled node features
y: service_time_ms
```

`service_time_ms` is never an input feature.
