# FinCluster Research Questions - Version 0.2

## Current Status

The regression-based direction remains the current working research direction after Research Day 2 mentor feedback. The mentor supported PaySim, measured `service_time_ms`, prediction-first evaluation, multiple models, multiple baselines, grouped observations by transaction ID, and preserving ACID properties. The exact final paper scope/venue and optional failure question remain open.

## RQ1 - Model-Level Performance

**Which machine-learning regression model most accurately predicts Mobile Financial Services transaction processing time across controlled node profiles?**

Primary/strong supporting metrics currently planned:

- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- Coefficient of Determination (R-squared)
- Median Absolute Error
- P95 absolute prediction error
- model inference latency (mean and P95)
- training time
- model size
- peak memory where feasible

## RQ2 - Operational Impact of the Winner Model

**Does routing based on the best latency-prediction model improve end-to-end latency, throughput, SLA compliance, and simulated infrastructure cost?**

Model prediction evaluation is performed before this system-level experiment.

## RQ3 - Routing-Strategy Comparison

**How does ML-based routing compare with Round Robin, Weighted Round Robin, Least-Loaded, and rule-based routing during normal and festival-surge traffic?**

Shortest Queue is also recommended as an additional baseline if implementation remains feasible.

## Optional RQ4 - Robustness

**How robust is ML-based routing during node degradation and complete node failure?**

This remains optional for the first paper because it increases implementation and experimental scope.

## Optional RQ1b - External-Data Generalisation

**Do the relative performance rankings of the evaluated regression models remain consistent when transaction attributes are drawn from different documented transaction-data distributions?**

This question remains provisional and is only meaningful if multiple transaction-data distributions are adapted using the same reproducible processing/measurement procedure.

## Future Research Question - Concept Drift and Retraining

**Can human-reviewed and quality-gated retraining recover latency-prediction and routing performance after concept drift?**

This is currently outside the preferred core of the first paper.

## Secondary Workload-Band Analysis - Not a Main RQ Yet

A secondary interpretability analysis may examine whether measured/reference service times form stable Light / Moderate / Heavy groups using clustering. K-Means is a candidate method. This does not replace the regression target and is not yet promoted to a formal research question.
