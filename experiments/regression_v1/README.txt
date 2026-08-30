FinCluster Regression Pipeline v1
==================================

Install to:
C:\Users\abdul\Desktop\code\Hackathon Project\Research\experiments\regression_v1\

Files:
  regression.ps1
  regression_v1.py
  README.txt

FIRST COMMAND ONLY:
.\experiments\regression_v1\regression.ps1 inspect

Send the inspect output to ChatGPT before running screen.

Feature sets:
  node_only
  type_node
  full_no_step
  full_with_step (if step exists)

Forbidden default predictors:
  transaction_id
  service-time target or target-derived timing fields
  stage timings
  newbalanceOrig / newbalanceDest
  isFraud / isFlaggedFraud
  nameOrig / nameDest
  future queue/service information

Screening models:
  Linear Regression
  Decision Tree
  Random Forest
  Extra Trees
  HistGradientBoosting

Screening metrics:
  MAE, RMSE, R2, MedianAE, P95AE, MaxAE,
  training time, validation inference time, serialized model size.

TEST-SET RULE:
inspect and screen do NOT load test.csv.
Do not use the test set until screening is reviewed and the tuning/model-selection
protocol is frozen.
