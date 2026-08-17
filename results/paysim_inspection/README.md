# PaySim Inspection Results

This folder contains generated inspection outputs. Do not manually edit generated CSV/JSON results and present them as script output.

## Recommended Local Run

Place the file at a known path, preferably:

```text
Research/data/raw/PS_20174392719_1491204439457_log.csv
```

Then run from the project root:

```bash
python Research/scripts/inspect_paysim.py --local-file "Research/data/raw/PS_20174392719_1491204439457_log.csv" --full-scan
```

## Expected Outputs

- `schema.csv`
- `dataset_summary.json`
- `missing_values.csv`
- `blank_strings.csv`
- `duplicate_summary.json` (bounded inspection sample unless explicitly extended)
- `transaction_type_distribution.csv`
- `fraud_distribution.csv`
- `flagged_fraud_distribution.csv` when available
- `amount_summary.csv` (bounded exploratory sample)
- `identifier_cardinality.csv` (bounded exploratory sample)
- `leakage_candidates.json`
- `sample_1000_rows.csv`
- optional PNG charts

## Scope Warning

For a local CSV with `--full-scan`, the script chunk-scans the full file for exact row count, missing values, blank strings, and key label/type distributions. Heavier exploratory statistics such as exact duplicates/cardinality/quantiles are calculated on a bounded sample unless separately implemented for the whole file.

No model training occurs in the inspection script.
