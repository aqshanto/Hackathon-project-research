# FinCluster AI Research Workspace

## Working Title

**FinCluster: A Comparative Evaluation of Machine Learning Models for Node-Aware MFS Transaction Latency Prediction and Routing**

## Current Stage

Day 1 research foundation revised after the initial Heavy/Light-classification plan was reconsidered.

## Current Research Direction

The primary machine-learning task is now **node-aware service-time regression**:

```text
PaySim-style transaction features
+ controlled node-profile features
+ controlled runtime-condition features
-> predicted service_time_ms
```

Several regression models will be compared. The best-performing model, and possibly the top two models, will then be integrated into the FinCluster routing simulator and compared with traditional routing strategies.

## Core Evaluation Layers

1. **Model-level evaluation:** Which regression model predicts measured transaction processing time most accurately?
2. **System-level evaluation:** Does prediction-based routing improve the performance of the full routing system compared with Round Robin, Weighted Round Robin, Least-Loaded, and rule-based routing?

## Main Scenarios

- Normal traffic
- Festival-surge traffic
- Optional: node degradation and node failure

## Important Current Decisions

- Fixed Heavy/Light labels by transaction type are no longer the primary target.
- Arbitrary work units are not used as ground truth.
- Raw measured service time in milliseconds is the primary proposed target.
- PaySim is used as an external transaction-data source, not as a processing-latency dataset.
- The PaySim fraud label must not be converted directly into a workload label.
- Processing labels will be collected by executing a documented FinCluster reference processing pipeline under controlled node profiles.
- Results will be valid for the documented experimental environment; unseen company hardware would require local calibration or retraining.

## Day 1 Deliverables in This Package

- Revised proposal v0.2 in DOCX and PDF
- Revised research questions v0.2
- Latency-target and measurement definition
- External dataset candidate note
- Updated mentor questions and team roles
- Literature-search keywords
- Ready-to-run PaySim inspection notebook and Python script
- Updated Day 1 summary and decision log
- Project context and transfer materials

## Immediate Next Step

Review the revised proposal with the mentor and obtain approval for:

1. the node-aware latency-regression scope;
2. the provisional reference processing pipeline;
3. the controlled Docker node profiles;
4. the exact PaySim source/version and license;
5. whether optional failure scenarios belong in the first paper.
