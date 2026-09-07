FinCluster Queue-Aware Regression v1
====================================

PURPOSE
-------
This is a SMALL controlled follow-up experiment for mentor review.

The existing frozen service-time dataset remains unchanged.

We add PRE-ROUTING OBSERVABLE queue state:
- active_workers
- queue_length

and change the target from raw service time to:

  completion_time_ms = actual_queue_wait_ms + service_time_ms

IMPORTANT METHODOLOGY RULE
--------------------------
actual_queue_wait_ms is NOT an input feature.
It is a future outcome / target component and using it as an input would leak the answer.

The model sees:
- transaction type
- candidate node profile
- current active worker count
- current queue length

The simulator uses 10 workers per node and TRAIN-only empirical service-time
distributions to create internally consistent FCFS queue states.

This is a controlled synthetic queue experiment for preliminary mentor review,
not yet a claim of a real production MFS queue trace.

DATA SAFETY
-----------
- Frozen service-time dataset is never modified.
- Only train.csv and validation.csv are loaded.
- test.csv existence is checked, but test data is NOT read.
- Train/validation transaction groups remain disjoint.

FEATURE SETS
------------
node_only:
  node_profile

type_node:
  type + node_profile

type_node_queue:
  type + node_profile + active_workers + queue_length

MODELS
------
When SCREEN is later authorized:
- Linear Regression
- Decision Tree
- Random Forest
- Extra Trees
- HistGradientBoosting

INSTALL
-------
Extract the folder as:

C:\Users\abdul\Desktop\code\Hackathon Project\Research\experiments\queue_aware_v1\

FIRST COMMAND ONLY
------------------
From the Research root run:

.\experiments\queue_aware_v1\queue_aware.ps1 prepare

Send the COMPLETE final terminal output to ChatGPT.

DO NOT run screen until the queue-state coverage and best-node distribution
have been reviewed.
