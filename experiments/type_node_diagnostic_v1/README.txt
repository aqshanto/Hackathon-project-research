FinCluster Type x Node Diagnostic v1
=====================================

WHY THIS EXISTS
---------------
Regression screening showed a critical methodological pattern:
type + node profile predicts service time better than the fuller transaction feature sets.

Before tuning, this diagnostic tests whether the result is essentially just a
15-cell mapping:
  5 transaction types x 3 node profiles.

It adds transparent non-ML/simple baselines:
- TypeNodeMeanLookup
- TypeNodeMedianLookup
- TypeNodeInteractionLinear

It also compares:
- best node-only model
- best type+node model
- best full-feature model
- incremental MAE from adding numeric transaction features

IMPORTANT
---------
- TRAIN + VALIDATION only.
- TEST SET IS NOT LOADED.
- No tuning.
- No frozen data changes.

INSTALL
-------
Extract to:

C:\Users\abdul\Desktop\code\Hackathon Project\Research\experiments\type_node_diagnostic_v1\

RUN
---
From the Research root:

.\experiments\type_node_diagnostic_v1\run_diagnostic.ps1

Send the final terminal output to ChatGPT before any tuning or test-set use.
