FinCluster Regression Pipeline v1 — FIXED
===========================================

WHY THIS FIX EXISTS
-------------------
The original inspect command failed because fincluster-pilot:0.3 does not contain
scikit-learn. That was an environment dependency issue, not a dataset issue.

This fixed version:
- lets INSPECT run without importing scikit-learn;
- uses a dedicated reproducible Docker image for SCREEN;
- pins scikit-learn==1.5.2.

INSTALL
-------
Replace the old files in:

C:\Users\abdul\Desktop\code\Hackathon Project\Research\experiments\regression_v1\

with these files:
  regression.ps1
  regression_v1.py
  Dockerfile.regression
  build_regression_image.ps1
  README.txt

FIRST
-----
Run INSPECT again:

.\experiments\regression_v1\regression.ps1 inspect

INSPECT does not load the test set and does not train models.

AFTER INSPECT PASSES
--------------------
Build the regression image once:

.\experiments\regression_v1\build_regression_image.ps1

Expected:
  REGRESSION_IMAGE_BUILD = PASS
  Image = fincluster-regression:1.0

Then, only after reviewing INSPECT with ChatGPT:

.\experiments\regression_v1\regression.ps1 screen

TEST-SET RULE
-------------
The held-out test set is not loaded by inspect or screen.
