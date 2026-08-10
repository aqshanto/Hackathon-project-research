# FinCluster Research Questions - Version 0.2

## RQ1 - Model-Level Performance

**Which machine-learning regression model most accurately predicts Mobile Financial Services transaction processing time across controlled node profiles?**

The primary comparison metrics will be:

- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- Coefficient of Determination (R-squared)
- Model inference latency
- Model size

## RQ2 - Operational Impact of the Winner Model

**Does routing based on the best latency-prediction model improve end-to-end latency, throughput, SLA compliance, and simulated infrastructure cost?**

## RQ3 - Routing-Strategy Comparison

**How does ML-based routing compare with Round Robin, Weighted Round Robin, Least-Loaded, and rule-based routing during normal and festival-surge traffic?**

## Optional RQ4 - Robustness

**How robust is ML-based routing during node degradation and complete node failure?**

This question is optional for the first paper and requires mentor approval because it increases the implementation and experimental scope.

## Optional RQ1b - External-Data Generalisation

**Do the relative performance rankings of the evaluated regression models remain consistent when transaction attributes are drawn from different documented transaction-data distributions?**

This question is provisional. It can only be included if the external-dataset adaptation and measurement process are consistent and reproducible.

## Future Research Question - Concept Drift and Retraining

**Can human-reviewed and quality-gated retraining recover latency-prediction and routing performance after concept drift?**

This is currently outside the preferred scope of the first paper.
