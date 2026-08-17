# Workload Band Method v0.1

## Goal

Keep the primary research output continuous while providing a human-readable secondary workload label:

```text
Predicted Service Time: 37.386 ms
Workload Band: Moderate
```

## Primary vs Secondary Output

Primary:

```text
predicted service_time_ms
```

Secondary, optional:

```text
Light / Moderate / Heavy
```

## KNN vs K-Means

### KNN Regressor

Supervised model. It is trained on transaction-node examples that already have measured `service_time_ms` targets.

```text
transaction + node features -> KNN Regressor -> predicted service_time_ms
```

KNN Regressor competes with other regression models such as Random Forest, XGBoost, CatBoost, etc.

### K-Means

Unsupervised clustering. It receives already-measured/reference service-time values and groups similar values.

```text
measured/reference service times -> K-Means -> clusters
```

If three stable clusters exist, they may be ordered by center and named Light, Moderate, Heavy.

## Why They Cannot Be Directly Compared

They solve different tasks and therefore do not share the same target or metrics.

- KNN Regressor -> MAE/RMSE/R2 and efficiency metrics.
- K-Means -> clustering separation/stability metrics.

## If Clustering Is Studied

Possible methods to compare:

- K-Means
- Gaussian Mixture Model
- Agglomerative Clustering

Possible metrics:

- Silhouette Score
- Davies-Bouldin Index
- Calinski-Harabasz Score
- stability across random seeds/resamples
- interpretability of cluster ordering

## Reference-Node Proposal

Because the same transaction can be fast on a High node and slow on a Low node, transaction-level workload bands may be derived from one fixed reference profile (for example, the eventual Medium profile).

This is proposed and must be validated after measured data exist.

## Important Rule

Do not use KNN or K-Means to replace the median of repeated timing measurements. The ground-truth service time is produced from actual repeated execution.
