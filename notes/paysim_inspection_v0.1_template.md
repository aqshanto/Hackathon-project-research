# PaySim Initial Inspection - Template

## Dataset

Dataset ID or local source:

```text
[ADD AFTER INSPECTION]
```

## Version and License

```text
[VERIFY AND ADD]
```

## Inspection Method

- Loading mode: streaming sample / local file / full dataset
- Sample size:
- Random seed:
- Inspection date:
- Code version or Git commit:

## Observed Schema

```text
[ADD COLUMN NAMES AND DATA TYPES]
```

## Missing Values

```text
[ADD FINDINGS]
```

## Duplicate Rows

```text
[ADD SAMPLE OR FULL-DATA FINDINGS]
```

## Transaction-Type Distribution

```text
[ADD FINDINGS]
```

## Fraud-Label Distribution

```text
[ADD FINDINGS]
```

## Amount Distribution

Record at least:

- minimum;
- median;
- mean;
- 95th percentile;
- 99th percentile;
- maximum.

## Identifier Cardinality

```text
[ADD FINDINGS]
```

## Leakage Risks

Review:

- `isFraud`
- `isFlaggedFraud`
- post-transaction balances
- raw account identifiers
- any post-outcome feature

## Interpretation

PaySim supplies transaction metadata and fraud-related labels. It does not supply transaction-processing latency or resource-demand ground truth.

## Next Decision

Finalise the FinCluster reference processing pipeline and controlled node profiles before collecting measured service-time labels.
