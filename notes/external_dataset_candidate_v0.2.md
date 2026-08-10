# External Dataset Candidate - Version 0.2

## Candidate

A PaySim-style synthetic mobile-money transaction dataset hosted on a documented public platform, with the exact repository/version and license to be verified before experimentation.

Current inspection candidate:

```text
purulalwani/Synthetic-Financial-Datasets-For-Fraud-Detection
```

## Why It Is Relevant

- mobile-money transaction context;
- multiple transaction types;
- amounts and account-balance fields;
- external transaction distribution rather than a team-created random generator;
- privacy-safe synthetic records;
- reproducible public access, subject to source/version verification.

## Important Limitation

The dataset contains fraud-related fields. It does **not** contain:

- transaction-processing latency;
- CPU demand;
- memory demand;
- node-profile measurements;
- a validated Heavy/Light workload label.

The fraud label must not be used directly as a workload or latency target.

## Proposed Use

PaySim supplies transaction attributes and distribution. FinCluster supplies measured execution labels.

```text
PaySim transaction row
-> FinCluster reference processing pipeline
-> controlled node profile
-> measured service_time_ms
```

The resulting research dataset will combine:

- pre-routing transaction features;
- controlled node-profile features;
- measured service-time target;
- supporting resource and stage-level measurements.

## Expected Transaction Types

The exact transaction types will be confirmed after inspection of the selected dataset version. No type will be permanently labelled Heavy or Light solely by name.

## Leakage Risks to Review

- `isFraud`
- `isFlaggedFraud`
- post-transaction balance fields
- raw source/destination identifiers
- any field that is unavailable at routing time

## Required Inspection Outputs

- row count or official metadata count;
- column names;
- data types;
- missing values;
- duplicate rows in the inspected sample;
- transaction-type distribution;
- fraud-label distribution;
- amount distribution;
- identifier cardinality;
- license and provenance notes.

## Questions to Resolve With the Mentor

1. Which exact PaySim repository/version should be used?
2. Does the selected source provide a clear license and provenance?
3. Should the full dataset or a reproducible sample be used?
4. Which pre-routing features are methodologically valid?
5. How many transaction rows are feasible for the controlled execution experiment?
6. Should the external dataset be the primary source or an external-validation source?

## Current Status

Dataset selected as a candidate only. Inspection has not yet been completed and no model has been trained on it.
