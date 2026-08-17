# Regression Model Comparison Plan v0.1

## Research Question

Which machine-learning regression model most accurately and efficiently predicts MFS transaction `service_time_ms` across controlled node profiles?

## Candidate Models

### Core / high-priority

1. Linear Regression
2. Ridge Regression
3. KNN Regressor
4. Decision Tree Regressor
5. Random Forest Regressor
6. Extra Trees Regressor
7. Gradient Boosting Regressor
8. HistGradientBoosting Regressor
9. XGBoost Regressor
10. CatBoost Regressor

### Additional candidates when feasible

11. LightGBM Regressor
12. Support Vector Regression (SVR)
13. MLP Regressor

The final benchmark can remove models only for documented feasibility/methodological reasons. More models are useful only if the comparison remains fair.

## Prediction Metrics

- MAE
- RMSE
- R-squared
- Median Absolute Error
- P95 absolute error

## Efficiency Metrics

- training time
- mean inference latency
- P95 inference latency
- model size
- peak memory where feasible

## Fairness Rules

All models must use:

- the same versioned dataset;
- the same grouped train/validation/test split by `transaction_id`;
- the same leakage-safe feature set;
- the same preprocessing policy where applicable;
- documented random seeds;
- a comparable hyperparameter-tuning budget;
- the final held-out test set only after model/threshold/hyperparameter selection is complete.

## Important Distinction

K-Means is not part of this regression ranking. It belongs to optional workload-band clustering analysis.
