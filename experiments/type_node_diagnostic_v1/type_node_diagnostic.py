#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline


def find_col(df, names):
    m = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n.lower() in m:
            return m[n.lower()]
    return None


def detect_tx(df):
    c = find_col(df, ["transaction_id", "tx_id", "transaction_uuid", "uuid"])
    if c is None:
        raise RuntimeError("transaction_id column not found")
    return c


def detect_target(df):
    c = find_col(df, ["service_time_ms", "median_service_time_ms", "service_time_ms_median", "median_ms"])
    if c is None:
        raise RuntimeError("service-time target column not found")
    return c


def detect_type(df):
    c = find_col(df, ["type", "transaction_type", "tx_type"])
    if c is None:
        raise RuntimeError("type column not found")
    return c


def detect_node(df):
    c = find_col(df, ["node_profile", "node", "node_label", "profile"])
    if c is None:
        raise RuntimeError("node profile column not found")
    return c


def metrics(y, p):
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    ae = np.abs(y - p)
    return {
        "MAE_ms": float(mean_absolute_error(y, p)),
        "RMSE_ms": float(math.sqrt(mean_squared_error(y, p))),
        "R2": float(r2_score(y, p)),
        "MedianAE_ms": float(median_absolute_error(y, p)),
        "P95_AE_ms": float(np.percentile(ae, 95)),
        "MaxAE_ms": float(np.max(ae)),
    }


def main():
    root = Path("/app/Research")
    split_dir = root / "data/final_training_data_v1/splits"
    results_dir = root / "results/regression_v1"
    out = root / "results/regression_v1/type_node_diagnostic"
    out.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(split_dir / "train.csv")
    val = pd.read_csv(split_dir / "validation.csv")
    # Intentionally do not read test.csv.

    tx = detect_tx(train)
    typ = detect_type(train)
    node = detect_node(train)
    target = detect_target(train)

    overlap = set(train[tx].astype(str)) & set(val[tx].astype(str))
    if overlap:
        raise RuntimeError(f"train-validation transaction leakage: {len(overlap)}")

    train["_group"] = train[typ].astype(str) + "||" + train[node].astype(str)
    val["_group"] = val[typ].astype(str) + "||" + val[node].astype(str)

    # 15-cell group summaries.
    group_stats = train.groupby([typ, node])[target].agg(
        count="count",
        mean_ms="mean",
        median_ms="median",
        std_ms="std",
        min_ms="min",
        max_ms="max",
    ).reset_index()

    if len(group_stats) != 15:
        raise RuntimeError(f"Expected 15 type-node cells, got {len(group_stats)}")

    mean_map = train.groupby("_group")[target].mean().to_dict()
    median_map = train.groupby("_group")[target].median().to_dict()

    if not set(val["_group"]).issubset(mean_map):
        missing = sorted(set(val["_group"]) - set(mean_map))
        raise RuntimeError(f"Unseen validation type-node groups: {missing}")

    yv = pd.to_numeric(val[target], errors="raise").to_numpy(float)
    pred_mean = val["_group"].map(mean_map).to_numpy(float)
    pred_median = val["_group"].map(median_map).to_numpy(float)

    mean_m = metrics(yv, pred_mean)
    median_m = metrics(yv, pred_median)

    # Interaction-only linear baseline: one-hot of the 15 combined cells.
    try:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)

    interaction = Pipeline([
        ("onehot", ohe),
        ("linear", LinearRegression()),
    ])
    interaction.fit(train[["_group"]], pd.to_numeric(train[target], errors="raise"))
    pred_interaction = interaction.predict(val[["_group"]])
    interaction_m = metrics(yv, pred_interaction)

    lookup_rows = []
    for name, mm in [
        ("TypeNodeMeanLookup", mean_m),
        ("TypeNodeMedianLookup", median_m),
        ("TypeNodeInteractionLinear", interaction_m),
    ]:
        lookup_rows.append({"model": name, **mm})
    lookup_df = pd.DataFrame(lookup_rows).sort_values("MAE_ms")
    lookup_df.to_csv(out / "type_node_simple_baselines.csv", index=False)
    group_stats.to_csv(out / "train_type_node_group_stats.csv", index=False)

    # Existing screening results.
    screening_path = results_dir / "validation_screening_results.csv"
    if not screening_path.exists():
        raise FileNotFoundError(screening_path)
    scr = pd.read_csv(screening_path)

    best_type_node = scr[scr["feature_set"] == "type_node"].sort_values(["MAE_ms", "RMSE_ms"]).iloc[0]
    full = scr[scr["feature_set"].isin(["full_no_step", "full_with_step"])].sort_values(["MAE_ms", "RMSE_ms"])
    best_full = full.iloc[0]
    best_node = scr[scr["feature_set"] == "node_only"].sort_values(["MAE_ms", "RMSE_ms"]).iloc[0]

    delta_full_vs_type = float(best_full["MAE_ms"] - best_type_node["MAE_ms"])
    rel_full_vs_type = float(delta_full_vs_type / best_type_node["MAE_ms"] * 100.0)

    # Validation residual variation within type-node cells.
    val_cell = val.groupby([typ, node])[target].agg(
        count="count",
        mean_ms="mean",
        median_ms="median",
        std_ms="std",
        min_ms="min",
        max_ms="max",
    ).reset_index()
    val_cell.to_csv(out / "validation_type_node_group_stats.csv", index=False)

    # Error breakdown of best simple median lookup.
    pred_df = val[[tx, typ, node, target]].copy()
    pred_df["prediction_ms"] = pred_median
    pred_df["abs_error_ms"] = np.abs(pred_df[target] - pred_df["prediction_ms"])
    pred_df.to_csv(out / "validation_type_node_median_lookup_predictions.csv", index=False)

    by_type = pred_df.groupby(typ).agg(
        count=("abs_error_ms", "size"),
        MAE_ms=("abs_error_ms", "mean"),
        MedianAE_ms=("abs_error_ms", "median"),
        P95_AE_ms=("abs_error_ms", lambda x: float(np.percentile(x, 95))),
    ).reset_index()
    by_node = pred_df.groupby(node).agg(
        count=("abs_error_ms", "size"),
        MAE_ms=("abs_error_ms", "mean"),
        MedianAE_ms=("abs_error_ms", "median"),
        P95_AE_ms=("abs_error_ms", lambda x: float(np.percentile(x, 95))),
    ).reset_index()
    by_type.to_csv(out / "median_lookup_metrics_by_type.csv", index=False)
    by_node.to_csv(out / "median_lookup_metrics_by_node.csv", index=False)

    summary = {
        "test_set_loaded": False,
        "train_validation_group_leakage": 0,
        "type_node_cells": 15,
        "best_existing_node_only": {
            "model": best_node["model"],
            "MAE_ms": float(best_node["MAE_ms"]),
            "R2": float(best_node["R2"]),
        },
        "best_existing_type_node": {
            "model": best_type_node["model"],
            "MAE_ms": float(best_type_node["MAE_ms"]),
            "RMSE_ms": float(best_type_node["RMSE_ms"]),
            "R2": float(best_type_node["R2"]),
            "P95_AE_ms": float(best_type_node["P95_AE_ms"]),
        },
        "best_existing_full": {
            "feature_set": best_full["feature_set"],
            "model": best_full["model"],
            "MAE_ms": float(best_full["MAE_ms"]),
            "RMSE_ms": float(best_full["RMSE_ms"]),
            "R2": float(best_full["R2"]),
            "P95_AE_ms": float(best_full["P95_AE_ms"]),
        },
        "full_minus_type_node_MAE_ms": delta_full_vs_type,
        "full_minus_type_node_MAE_relative_pct": rel_full_vs_type,
        "simple_baselines": {
            row["model"]: {
                k: float(row[k]) for k in ["MAE_ms", "RMSE_ms", "R2", "MedianAE_ms", "P95_AE_ms", "MaxAE_ms"]
            } for _, row in lookup_df.iterrows()
        },
        "interpretation_guardrail": (
            "If the 15-cell lookup baseline matches the best type+node tree model, "
            "the predictive task is largely a type-by-node mapping under the current synthetic processor. "
            "Do not claim that numeric transaction features add predictive value unless the ablation supports it."
        ),
    }
    (out / "diagnostic_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("=" * 78)
    print("FinCluster | TYPE x NODE DIAGNOSTIC")
    print("=" * 78)
    print("TEST_SET_LOADED = FALSE")
    print("TRAIN_VALIDATION_GROUP_LEAKAGE = 0")
    print("Type-node cells = 15")
    print("")
    print("Existing screening:")
    print(
        f"  Best node_only : {best_node['model']} | "
        f"MAE={best_node['MAE_ms']:.4f} | R2={best_node['R2']:.4f}"
    )
    print(
        f"  Best type_node : {best_type_node['model']} | "
        f"MAE={best_type_node['MAE_ms']:.4f} | RMSE={best_type_node['RMSE_ms']:.4f} | "
        f"R2={best_type_node['R2']:.4f}"
    )
    print(
        f"  Best full      : {best_full['feature_set']} + {best_full['model']} | "
        f"MAE={best_full['MAE_ms']:.4f} | RMSE={best_full['RMSE_ms']:.4f} | "
        f"R2={best_full['R2']:.4f}"
    )
    print(
        f"  Full - type_node MAE delta = {delta_full_vs_type:+.4f} ms "
        f"({rel_full_vs_type:+.2f}%)"
    )
    print("")
    print("Simple type-node baselines:")
    for _, row in lookup_df.iterrows():
        print(
            f"  {row['model']:26s} | MAE={row['MAE_ms']:.4f} | "
            f"RMSE={row['RMSE_ms']:.4f} | R2={row['R2']:.4f} | "
            f"P95AE={row['P95_AE_ms']:.4f}"
        )
    print("")
    print("DIAGNOSTIC_STATUS = PASS")
    print("STOP HERE. Review before any tuning or test-set use.")
    print(f"Outputs: {out}")
    print("=" * 78)


if __name__ == "__main__":
    main()
