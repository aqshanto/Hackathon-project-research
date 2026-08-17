# External Dataset Candidate - Version 0.2 (Updated Status)

## Current Decision

The mentor recommended **PaySim** as the preferred transaction-data source.

A local file has been identified:

```text
PS_20174392719_1491204439457_log.csv
```

The exact provenance, download source, dataset version, and license for this local copy must still be verified and recorded before final experimentation/publication.

## Previously Noted Public Candidate

```text
purulalwani/Synthetic-Financial-Datasets-For-Fraud-Detection
```

This remains a previously discussed hosting candidate, but the project must not assume that the local CSV came from this exact host/version unless that provenance is verified.

## Why PaySim Is Relevant

- synthetic mobile-money transaction context;
- multiple transaction types;
- transaction amounts and balance fields;
- privacy-safe data suitable for controlled research;
- provides transaction distributions independently of the FinCluster timing experiment.

## Current Local Schema Facts

- local filename identified;
- 11 columns observed/expected;
- transaction types observed: `CASH_IN`, `CASH_OUT`, `DEBIT`, `PAYMENT`, `TRANSFER`;
- no verified VPN feature;
- full programmatic inspection still pending.

## Important Limitation

PaySim does **not** provide:

- transaction-processing latency;
- CPU demand;
- memory demand;
- node-profile measurements;
- a validated Light/Moderate/Heavy processing-workload label.

Fraud labels must not be converted directly into workload labels.

## Proposed Use

```text
PaySim transaction row
-> assign FinCluster transaction_id
-> execute FinCluster reference processing pipeline
-> controlled node profile
-> repeated measurements
-> median measured service_time_ms
-> regression research dataset
```

## Initial Candidate Transaction Inputs

- `type`
- `amount`
- `oldbalanceOrg`
- `oldbalanceDest`
- `step` (candidate)

## Initial Exclusions

- `nameOrig`
- `nameDest`
- `newbalanceOrig`
- `newbalanceDest`
- `isFraud`
- `isFlaggedFraud`

The raw source file remains unchanged; exclusion applies only to model input.

## Required Inspection Outputs

- exact row count;
- exact column names and dtypes;
- missing values;
- blank strings;
- sample duplicate count;
- transaction-type distribution;
- fraud-label distribution;
- amount distribution;
- identifier cardinality;
- exact provenance/version/license notes.

## Current Status

**Mentor-preferred dataset family; local file identified; partial schema inspection completed; full programmatic inspection and provenance/license verification pending.**
