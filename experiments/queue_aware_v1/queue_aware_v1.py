#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from pathlib import Path
from heapq import heapify, heappop, heappush

import numpy as np
import pandas as pd


SEED = 20260830
WORKERS_PER_NODE = 10
STATE_REPLICAS = 3


def find_col(df, names):
    lower = {str(c).lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def detect_columns(df):
    tx = find_col(df, ["transaction_id", "tx_id", "transaction_uuid", "uuid"])
    typ = find_col(df, ["type", "transaction_type", "tx_type"])
    node = find_col(df, ["node_profile", "node", "node_label", "profile"])
    target = find_col(df, ["service_time_ms", "median_service_time_ms", "service_time_ms_median", "median_ms"])
    missing = [name for name, col in [("transaction_id", tx), ("type", typ), ("node_profile", node), ("service_time_ms", target)] if col is None]
    if missing:
        raise RuntimeError(f"Required column(s) not found: {missing}")
    return tx, typ, node, target


def load_train_validation(root: Path):
    split_dir = root / "data/final_training_data_v1/splits"
    train_path = split_dir / "train.csv"
    val_path = split_dir / "validation.csv"
    test_path = split_dir / "test.csv"

    if not train_path.exists() or not val_path.exists():
        raise FileNotFoundError("Frozen train/validation split not found.")
    if not test_path.exists():
        raise FileNotFoundError("Frozen test split file is expected to exist, but it will NOT be loaded.")

    train = pd.read_csv(train_path)
    val = pd.read_csv(val_path)
    return train, val, test_path


def build_train_service_pools(train, node_col, service_col):
    pools = {}
    for node, g in train.groupby(node_col):
        vals = pd.to_numeric(g[service_col], errors="raise").astype(float).to_numpy()
        vals = vals[np.isfinite(vals) & (vals > 0)]
        if len(vals) == 0:
            raise RuntimeError(f"No positive train service times for node {node}")
        pools[str(node)] = vals
    return pools


def sample_state(rng: np.random.Generator):
    """
    Controlled queue-state simulator.
    We sample a latent workload regime, then expose only pre-routing observable
    state (active_workers, queue_length) to the model.

    Queue waiting time itself is NEVER used as an input feature.
    """
    u = rng.random()
    if u < 0.20:  # idle/light
        active = int(rng.integers(0, 5))  # 0..4
        qlen = 0
        regime = "idle"
    elif u < 0.55:  # normal
        active = int(rng.integers(5, 10))  # 5..9
        qlen = 0
        regime = "normal"
    elif u < 0.85:  # busy
        active = WORKERS_PER_NODE
        qlen = int(rng.integers(0, 11))  # 0..10
        regime = "busy"
    else:  # surge
        active = WORKERS_PER_NODE
        qlen = int(rng.integers(11, 31))  # 11..30
        regime = "surge"
    return active, qlen, regime


def counterfactual_wait_ms(rng, node_pool, active_workers, queue_length):
    """
    Approximate FCFS multi-worker waiting time from a synthetic but
    internally consistent queue state.

    - Free workers have availability 0.
    - Busy workers get residual service sampled from TRAIN-only node service
      distribution times a random residual fraction.
    - Jobs already waiting ahead sample service demand from the same TRAIN-only
      node pool.
    - The candidate transaction joins after those queued jobs.

    The resulting wait is a TARGET component, not an input feature.
    """
    worker_avail = [0.0] * WORKERS_PER_NODE

    if active_workers > 0:
        sampled = rng.choice(node_pool, size=active_workers, replace=True)
        residual_fraction = rng.uniform(0.05, 1.0, size=active_workers)
        residual = sampled * residual_fraction
        for i in range(active_workers):
            worker_avail[i] = float(residual[i])

    heapify(worker_avail)

    # Under FCFS, waiting jobs only exist when all workers are occupied.
    if active_workers < WORKERS_PER_NODE and queue_length != 0:
        raise RuntimeError("Invalid simulated state: queue exists while a worker is free.")

    if queue_length > 0:
        queued_services = rng.choice(node_pool, size=queue_length, replace=True)
        for s in queued_services:
            avail = heappop(worker_avail)
            heappush(worker_avail, float(avail + s))

    # Candidate starts at earliest worker availability after all jobs ahead.
    return float(worker_avail[0])


def make_dynamic_rows(df, split_name, pools, tx_col, type_col, node_col, service_col):
    rows = []

    # Independent deterministic RNG stream by split; validation does not share
    # generated states with train.
    split_offset = 0 if split_name == "train" else 100_000
    rng = np.random.default_rng(SEED + split_offset)

    # Stable order avoids dependence on source CSV row order changes.
    work = df.copy()
    work["_tx_s"] = work[tx_col].astype(str)
    work["_node_s"] = work[node_col].astype(str)
    work = work.sort_values(["_tx_s", "_node_s"]).reset_index(drop=True)

    for _, r in work.iterrows():
        node = str(r[node_col])
        if node not in pools:
            raise RuntimeError(f"Node {node!r} not found in TRAIN service pool.")
        actual_service = float(r[service_col])
        if not np.isfinite(actual_service) or actual_service <= 0:
            raise RuntimeError("Invalid service time encountered.")

        for replica in range(STATE_REPLICAS):
            active, qlen, regime = sample_state(rng)
            wait = counterfactual_wait_ms(rng, pools[node], active, qlen)
            completion = wait + actual_service

            rows.append({
                "split": split_name,
                "transaction_id": str(r[tx_col]),
                "state_replica": replica,
                "type": str(r[type_col]),
                "node_profile": node,
                "active_workers": int(active),
                "queue_length": int(qlen),
                # Keep the latent regime only for simulator audit; the model
                # feature policy below does not use it.
                "simulator_regime": regime,
                # Ground-truth components: retained for audit/evaluation only.
                "service_time_ms": actual_service,
                "actual_queue_wait_ms": wait,
                "completion_time_ms": completion,
            })
    return pd.DataFrame(rows)


def best_node_audit(dynamic_df):
    # One candidate row for each node per transaction x state_replica.
    gcols = ["transaction_id", "state_replica"]
    counts = dynamic_df.groupby(gcols)["node_profile"].nunique()
    if not (counts == 3).all():
        raise RuntimeError("Each transaction-state group must contain exactly 3 node candidates.")

    idx = dynamic_df.groupby(gcols)["completion_time_ms"].idxmin()
    winners = dynamic_df.loc[idx, ["transaction_id", "state_replica", "node_profile", "completion_time_ms"]].copy()
    dist = winners["node_profile"].value_counts().to_dict()
    non_high = int((winners["node_profile"].str.lower() != "high").sum())
    return winners, dist, non_high, len(winners)


def prepare(root: Path):
    out_dir = root / "data/queue_aware_v1"
    result_dir = root / "results/queue_aware_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    train, val, test_path = load_train_validation(root)
    tx, typ, node, target = detect_columns(train)
    txv, typv, nodev, targetv = detect_columns(val)

    if [tx, typ, node, target] != [txv, typv, nodev, targetv]:
        # Column names should be identical across frozen splits.
        raise RuntimeError("Train/validation schema mismatch.")

    train_ids = set(train[tx].astype(str))
    val_ids = set(val[tx].astype(str))
    overlap = train_ids & val_ids
    if overlap:
        raise RuntimeError(f"Train-validation transaction leakage: {len(overlap)}")

    pools = build_train_service_pools(train, node, target)

    dyn_train = make_dynamic_rows(train, "train", pools, tx, typ, node, target)
    dyn_val = make_dynamic_rows(val, "validation", pools, tx, typ, node, target)

    # Structural checks.
    expected_train = len(train) * STATE_REPLICAS
    expected_val = len(val) * STATE_REPLICAS
    if len(dyn_train) != expected_train or len(dyn_val) != expected_val:
        raise RuntimeError("Unexpected dynamic row count.")

    if set(dyn_train["transaction_id"]) & set(dyn_val["transaction_id"]):
        raise RuntimeError("Dynamic train-validation group leakage detected.")

    for df_name, d in [("train", dyn_train), ("validation", dyn_val)]:
        bad = (~np.isfinite(d["completion_time_ms"])) | (d["completion_time_ms"] <= 0)
        if bad.any():
            raise RuntimeError(f"{df_name}: invalid completion times.")
        if (d["actual_queue_wait_ms"] < 0).any():
            raise RuntimeError(f"{df_name}: negative queue wait.")
        if not np.allclose(
            d["completion_time_ms"].to_numpy(),
            d["actual_queue_wait_ms"].to_numpy() + d["service_time_ms"].to_numpy(),
            rtol=0, atol=1e-9
        ):
            raise RuntimeError(f"{df_name}: completion identity check failed.")

    train_winners, train_dist, train_non_high, train_groups = best_node_audit(dyn_train)
    val_winners, val_dist, val_non_high, val_groups = best_node_audit(dyn_val)

    dyn_train.to_csv(out_dir / "train_queue_aware.csv", index=False)
    dyn_val.to_csv(out_dir / "validation_queue_aware.csv", index=False)
    train_winners.to_csv(result_dir / "train_best_node_by_completion.csv", index=False)
    val_winners.to_csv(result_dir / "validation_best_node_by_completion.csv", index=False)

    feature_policy = {
        "target": "completion_time_ms",
        "ground_truth_components_not_used_as_features": [
            "actual_queue_wait_ms",
            "service_time_ms",
            "simulator_regime",
        ],
        "feature_sets": {
            "node_only": ["node_profile"],
            "type_node": ["type", "node_profile"],
            "type_node_queue": ["type", "node_profile", "active_workers", "queue_length"],
        },
        "test_set_loaded": False,
        "workers_per_node": WORKERS_PER_NODE,
        "state_replicas_per_transaction_node": STATE_REPLICAS,
        "seed": SEED,
        "note": (
            "Queue waiting time is a generated target component, not an input. "
            "The queue-aware model sees only pre-routing observable queue state."
        ),
    }
    (result_dir / "feature_policy.json").write_text(json.dumps(feature_policy, indent=2), encoding="utf-8")

    def stats(d):
        return {
            "rows": int(len(d)),
            "transactions": int(d["transaction_id"].nunique()),
            "queue_wait_positive_pct": float((d["actual_queue_wait_ms"] > 0).mean() * 100),
            "queue_wait_median_ms": float(d["actual_queue_wait_ms"].median()),
            "queue_wait_p95_ms": float(np.percentile(d["actual_queue_wait_ms"], 95)),
            "completion_median_ms": float(d["completion_time_ms"].median()),
            "completion_p95_ms": float(np.percentile(d["completion_time_ms"], 95)),
        }

    manifest = {
        "status": "PREPARED",
        "test_set_loaded": False,
        "source_test_file_checked_exists_but_not_read": str(test_path),
        "train_validation_group_leakage": 0,
        "train": stats(dyn_train),
        "validation": stats(dyn_val),
        "train_best_node_distribution": train_dist,
        "validation_best_node_distribution": val_dist,
        "train_non_high_best_pct": train_non_high / train_groups * 100,
        "validation_non_high_best_pct": val_non_high / val_groups * 100,
        "feature_policy": feature_policy,
    }
    (result_dir / "prepare_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("=" * 78)
    print("FinCluster QUEUE-AWARE v1 | PREPARE")
    print("=" * 78)
    print("Frozen service-time TRAIN + VALIDATION only.")
    print("TEST_SET_LOADED = FALSE")
    print(f"Workers per node = {WORKERS_PER_NODE}")
    print(f"Queue-state replicas per transaction-node = {STATE_REPLICAS}")
    print(f"Dynamic train rows / transactions = {len(dyn_train)} / {dyn_train['transaction_id'].nunique()}")
    print(f"Dynamic validation rows / transactions = {len(dyn_val)} / {dyn_val['transaction_id'].nunique()}")
    print("TRAIN_VALIDATION_GROUP_LEAKAGE = 0")
    print("")
    print("Target = completion_time_ms = actual_queue_wait_ms + service_time_ms")
    print("IMPORTANT: actual_queue_wait_ms is NOT a model input.")
    print("")
    print("Queue-state coverage:")
    print(
        f"  Train      wait>0={manifest['train']['queue_wait_positive_pct']:.1f}% | "
        f"median_wait={manifest['train']['queue_wait_median_ms']:.3f} ms | "
        f"P95_wait={manifest['train']['queue_wait_p95_ms']:.3f} ms"
    )
    print(
        f"  Validation wait>0={manifest['validation']['queue_wait_positive_pct']:.1f}% | "
        f"median_wait={manifest['validation']['queue_wait_median_ms']:.3f} ms | "
        f"P95_wait={manifest['validation']['queue_wait_p95_ms']:.3f} ms"
    )
    print("")
    print("Best node by ACTUAL completion time (counterfactual state audit):")
    print(f"  Train      {train_dist} | non-High best = {train_non_high}/{train_groups} ({train_non_high/train_groups*100:.1f}%)")
    print(f"  Validation {val_dist} | non-High best = {val_non_high}/{val_groups} ({val_non_high/val_groups*100:.1f}%)")
    print("")
    print("Feature sets prepared:")
    print("  node_only       = ['node_profile']")
    print("  type_node       = ['type', 'node_profile']")
    print("  type_node_queue = ['type', 'node_profile', 'active_workers', 'queue_length']")
    print("")
    print("PREPARE_STATUS = PASS")
    print("STOP HERE. Review queue-state distribution before model screening.")
    print(f"Output data: {out_dir}")
    print(f"Output audit: {result_dir}")
    print("=" * 78)


def import_sklearn():
    global ColumnTransformer, ExtraTreesRegressor, HistGradientBoostingRegressor
    global RandomForestRegressor, SimpleImputer, LinearRegression
    global mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
    global Pipeline, OneHotEncoder, StandardScaler, DecisionTreeRegressor
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.tree import DecisionTreeRegressor


def metric_row(y, p):
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    ae = np.abs(y - p)
    return {
        "MAE_ms": float(mean_absolute_error(y, p)),
        "RMSE_ms": float(math.sqrt(mean_squared_error(y, p))),
        "R2": float(r2_score(y, p)),
        "MedianAE_ms": float(median_absolute_error(y, p)),
        "P95AE_ms": float(np.percentile(ae, 95)),
        "MaxAE_ms": float(np.max(ae)),
    }


def screen(root: Path):
    import_sklearn()

    data_dir = root / "data/queue_aware_v1"
    result_dir = root / "results/queue_aware_v1"
    train_path = data_dir / "train_queue_aware.csv"
    val_path = data_dir / "validation_queue_aware.csv"

    if not train_path.exists() or not val_path.exists():
        raise FileNotFoundError("Run prepare mode first.")

    train = pd.read_csv(train_path)
    val = pd.read_csv(val_path)
    overlap = set(train["transaction_id"].astype(str)) & set(val["transaction_id"].astype(str))
    if overlap:
        raise RuntimeError(f"Train-validation leakage: {len(overlap)}")

    target = "completion_time_ms"
    feature_sets = {
        "node_only": ["node_profile"],
        "type_node": ["type", "node_profile"],
        "type_node_queue": ["type", "node_profile", "active_workers", "queue_length"],
    }

    models = {
        "LinearRegression": LinearRegression(),
        "DecisionTree": DecisionTreeRegressor(random_state=SEED),
        "RandomForest": RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=-1),
        "ExtraTrees": ExtraTreesRegressor(n_estimators=300, random_state=SEED, n_jobs=-1),
        "HistGradientBoosting": HistGradientBoostingRegressor(max_iter=200, random_state=SEED),
    }

    rows = []
    pred_rows = []

    print("=" * 78)
    print("FinCluster QUEUE-AWARE v1 | SCREEN")
    print("=" * 78)
    print("TRAIN + VALIDATION only. TEST is not loaded.")
    print("TEST_SET_LOADED = FALSE")
    print("Target = completion_time_ms")
    print("")

    for fs_name, features in feature_sets.items():
        cat = [c for c in features if c in ["type", "node_profile"]]
        num = [c for c in features if c not in cat]

        transformers = []
        if cat:
            try:
                ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
            except TypeError:
                ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)
            transformers.append(("cat", ohe, cat))
        if num:
            num_pipe = Pipeline([
                ("impute", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
            ])
            transformers.append(("num", num_pipe, num))

        prep = ColumnTransformer(transformers=transformers, remainder="drop")
        Xtr = train[features]
        Xv = val[features]
        ytr = train[target].astype(float)
        yv = val[target].astype(float)

        for model_name, model in models.items():
            pipe = Pipeline([("prep", prep), ("model", model)])

            t0 = time.perf_counter()
            pipe.fit(Xtr, ytr)
            fit_s = time.perf_counter() - t0

            t1 = time.perf_counter()
            pv = pipe.predict(Xv)
            infer_s = time.perf_counter() - t1

            pt = pipe.predict(Xtr)
            vm = metric_row(yv, pv)
            tm = metric_row(ytr, pt)

            model_file = result_dir / f"SCREENING_ONLY_{fs_name}_{model_name}.pkl"
            with open(model_file, "wb") as f:
                pickle.dump(pipe, f)

            row = {
                "feature_set": fs_name,
                "model": model_name,
                **vm,
                "Train_MAE_ms": tm["MAE_ms"],
                "fit_time_s": fit_s,
                "validation_inference_ms_per_row": infer_s / len(val) * 1000.0,
                "serialized_size_bytes": model_file.stat().st_size,
            }
            rows.append(row)

            for i, p in enumerate(pv):
                pred_rows.append({
                    "feature_set": fs_name,
                    "model": model_name,
                    "transaction_id": str(val.iloc[i]["transaction_id"]),
                    "state_replica": int(val.iloc[i]["state_replica"]),
                    "node_profile": str(val.iloc[i]["node_profile"]),
                    "actual_completion_time_ms": float(yv.iloc[i]),
                    "prediction_ms": float(p),
                    "abs_error_ms": float(abs(yv.iloc[i] - p)),
                })

            print(
                f"{fs_name:15s} | {model_name:20s} | "
                f"MAE={vm['MAE_ms']:.4f} RMSE={vm['RMSE_ms']:.4f} "
                f"R2={vm['R2']:.4f} P95AE={vm['P95AE_ms']:.4f}"
            )

    res = pd.DataFrame(rows).sort_values(["MAE_ms", "RMSE_ms"])
    preds = pd.DataFrame(pred_rows)
    res.to_csv(result_dir / "queue_aware_validation_screening_results.csv", index=False)
    preds.to_csv(result_dir / "queue_aware_validation_predictions.csv", index=False)

    best = res.iloc[0]
    print("")
    print("=" * 78)
    print("QUEUE-AWARE v1 SCREENING COMPLETE")
    print("=" * 78)
    print("TEST_SET_LOADED = FALSE")
    print("GROUP_LEAKAGE_CHECK = PASS")
    print(f"Models evaluated = {len(res)}")
    print(f"Top validation candidate: {best['feature_set']} + {best['model']}")
    print(
        f"Validation MAE={best['MAE_ms']:.4f} ms | RMSE={best['RMSE_ms']:.4f} ms | "
        f"R2={best['R2']:.4f} | P95AE={best['P95AE_ms']:.4f} ms"
    )
    print("SCREENING_STATUS = PASS")
    print("STOP HERE and review before any tuning or test-set use.")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "screen"])
    parser.add_argument("--root", default="/app/Research")
    args = parser.parse_args()

    root = Path(args.root)
    if args.mode == "prepare":
        prepare(root)
    else:
        screen(root)


if __name__ == "__main__":
    main()
