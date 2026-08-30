FinCluster FINAL_TRAINING_DATA_v1 Freeze + Grouped Split
===============================================================

PURPOSE
-------
This package does NOT collect timing measurements.
It validates the completed final_candidate_v1 evidence, freezes a versioned copy,
creates the fixed grouped train/validation/test split, and writes hashes/manifests.

FROZEN DECISIONS
----------------
Candidate approval:
  APPROVED_WITH_DOCUMENTED_RESIDUAL_VARIABILITY

Measurement profiles:
  Low    = 60% CPU / 1 GB
  Medium = 75% CPU / 2 GB
  High   = 100% CPU / 4 GB
  CPU period = 10,000 us
  CPU pin = logical CPU 0
  OMP / OpenBLAS / MKL / NumExpr thread limits = 1
  Warmups = 2
  Measured repetitions = 5
  Target = median successful service_time_ms per transaction-node pair

Sampling:
  1,000 PaySim transactions
  200 per transaction type
  Sampling seed = 20260829

Split:
  Group key = transaction_id
  Exact type-stratified split
  Train      = 700 transactions = 2,100 TX-node rows
  Validation = 150 transactions =   450 TX-node rows
  Test       = 150 transactions =   450 TX-node rows
  Each type  = 140 / 30 / 30 transactions
  Split seed = 20260830
  Assignment uses deterministic SHA-256 ranking within each type.

IMPORTANT LEAKAGE RULE
----------------------
All Low/Medium/High rows for the same original transaction stay in the same split.
transaction_id is NOT an ML predictor.

INSTALL
-------
Extract this package to:

C:\Users\abdul\Desktop\code\Hackathon Project\Research\experiments\freeze_dataset_v1\

Expected files:
  freeze_and_split.ps1
  freeze_and_split.py
  verify_frozen.ps1
  README.txt

RUN
---
Open PowerShell in the Research root:

PS C:\Users\abdul\Desktop\code\Hackathon Project\Research>

Then run:

.\experiments\freeze_dataset_v1\freeze_and_split.ps1

The command will refuse to overwrite an existing final_training_data_v1 freeze.

EXPECTED FINAL LINES
--------------------
DATASET_STATUS = FINAL_TRAINING_DATA_v1_APPROVED
APPROVAL = APPROVED_WITH_DOCUMENTED_RESIDUAL_VARIABILITY
Train = 700 transactions / 2100 rows
Validation = 150 transactions / 450 rows
Test = 150 transactions / 450 rows
GROUP_LEAKAGE_CHECK = PASS

VERIFY AFTER FREEZE
-------------------
Run:

.\experiments\freeze_dataset_v1\verify_frozen.ps1

Expected:
  FROZEN_DATASET_INTEGRITY = PASS
  GROUP_LEAKAGE_CHECK = PASS

OUTPUT
------
data\final_training_data_v1\
  raw\
  processed\
  selection\
  splits\
    transaction_split_assignments.csv
    train.csv
    validation.csv
    test.csv
  manifests\
  checksums\
  evidence\
  code_snapshot\
  FREEZE_REPORT.txt

results\final_training_data_v1\
  DATASET_APPROVAL.txt

DO NOT
------
- Do not delete CV/outlier-flagged rows from the primary frozen dataset.
- Do not reshuffle the train/validation/test split later because model results look better.
- Do not use transaction_id as a predictor.
- Do not tune models on the held-out test set.
- Do not overwrite FINAL_TRAINING_DATA_v1; create a new version if a scientifically justified change is required.
