#!/usr/bin/env python3
"""
FinCluster FINAL_TRAINING_DATA_v1 freeze + grouped split utility.

Purpose
-------
1) Validate the completed final_candidate_v1 collection.
2) Freeze immutable copies of the candidate raw/processed/selection evidence.
3) Create a deterministic transaction-grouped, type-stratified 70/15/15 split.
4) Write manifests, validation reports, code/evidence snapshots, and SHA-256 sums.
5) Never overwrite an existing FINAL_TRAINING_DATA_v1 freeze.

This script performs analysis/file-copy work only. It does NOT collect timing data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DATASET_NAME = "FINAL_TRAINING_DATA_v1"
SAMPLING_SEED = 20260829
SPLIT_SEED = 20260830
EXPECTED_TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
EXPECTED_NODES = ["Low", "Medium", "High"]

EXPECTED = {
    "selected_transactions": 1000,
    "selected_per_type": 200,
    "processed_rows": 3000,
    "raw_rows": 15000,
    "measured_repetitions_per_tx_node": 5,
    "train_transactions": 700,
    "validation_transactions": 150,
    "test_transactions": 150,
    "train_rows": 2100,
    "validation_rows": 450,
    "test_rows": 450,
}

PROTOCOL = {
    "reference_processor": "v0.3 Rebalanced (must match captured script hash)",
    "node_profiles": {
        "Low": {"cpu_quota": 0.60, "cpu_period_us": 10000, "memory_mb": 1024},
        "Medium": {"cpu_quota": 0.75, "cpu_period_us": 10000, "memory_mb": 2048},
        "High": {"cpu_quota": 1.00, "cpu_period_us": 10000, "memory_mb": 4096},
    },
    "cpu_pin": "logical CPU 0",
    "thread_limits": {
        "OMP_NUM_THREADS": 1,
        "OPENBLAS_NUM_THREADS": 1,
        "MKL_NUM_THREADS": 1,
        "NUMEXPR_NUM_THREADS": 1,
    },
    "warmups_per_tx_node": 2,
    "measured_runs_per_tx_node": 5,
    "aggregation_target": "median successful service_time_ms per transaction-node pair",
    "host_collection_note": (
        "Block 01 was collected in session S1; the host was restarted after Block 01. "
        "Blocks 02-10 were collected in session S2. Deep audit found only small session-level "
        "normalized median shifts and no evidence requiring recollection."
    ),
}

REVIEWED_AUDIT_SUMMARY = {
    "decision": "APPROVED_WITH_DOCUMENTED_RESIDUAL_VARIABILITY",
    "structural_audit": "PASS",
    "ordering_low_gt_medium_gt_high": "1000/1000 transactions",
    "median_within_pair_cv_pct": {
        "High": 1.477,
        "Low": 6.266,
        "Medium": 6.254,
    },
    "pairs_cv_gt_10": {
        "High": 10,
        "Low": 130,
        "Medium": 144,
    },
    "max_abs_block_node_median_deviation_pct": 7.576,
    "robust_outlier_processed_rows_abs_z_gt_3_5": 48,
    "node_separation_median_pct": {
        "Low_vs_Medium": 25.718,
        "Medium_vs_High": 29.400,
    },
    "review_note": (
        "Residual variability is documented and retained; flagged rows are not deleted. "
        "Primary modeling should use the full frozen dataset. Sensitivity analyses may be run later."
    ),
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def find_col(df: pd.DataFrame, exact_candidates, contains_all=None):
    lower_map = {str(c).lower(): c for c in df.columns}
    for cand in exact_candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    if contains_all:
        for c in df.columns:
            lc = str(c).lower()
            if all(token.lower() in lc for token in contains_all):
                return c
    return None


def detect_tx_col(df):
    col = find_col(df, ["transaction_id", "tx_id", "transaction_uuid", "uuid"])
    if col is None:
        raise RuntimeError(
            f"Could not find transaction-id column. Columns: {list(df.columns)}"
        )
    return col


def detect_type_col(df):
    col = find_col(df, ["type", "transaction_type", "tx_type"])
    if col is None:
        raise RuntimeError(f"Could not find transaction type column. Columns: {list(df.columns)}")
    return col


def detect_node_col(df):
    col = find_col(df, ["node_profile", "node", "node_label", "profile"])
    if col is None:
        # fallback: node + profile words
        for c in df.columns:
            lc = str(c).lower()
            if "node" in lc and ("profile" in lc or "label" in lc):
                return c
        raise RuntimeError(f"Could not find node-profile column. Columns: {list(df.columns)}")
    return col


def detect_raw_service_col(df):
    col = find_col(df, ["service_time_ms", "total_service_time_ms", "elapsed_ms"])
    if col is not None:
        return col
    for c in df.columns:
        lc = str(c).lower()
        if "service" in lc and "time" in lc and ("ms" in lc or "millisecond" in lc):
            return c
    return None


def detect_processed_target_col(df):
    candidates = [
        "median_service_time_ms",
        "service_time_ms_median",
        "service_time_median_ms",
        "median_service_ms",
        "median_ms",
    ]
    col = find_col(df, candidates)
    if col is not None:
        return col
    for c in df.columns:
        lc = str(c).lower()
        if "median" in lc and ("service" in lc or "time" in lc):
            return c
    # Some runner versions may carry service_time_ms as the already-aggregated target.
    col = find_col(df, ["service_time_ms"])
    return col


def normalize_node(v):
    s = str(v).strip().lower()
    if s == "low":
        return "Low"
    if s == "medium":
        return "Medium"
    if s == "high":
        return "High"
    return str(v).strip()


def deterministic_rank(seed: int, txid: str) -> str:
    return hashlib.sha256(f"{seed}:{txid}".encode("utf-8")).hexdigest()


def require_file(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")


def safe_copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def safe_copy_tree_if_exists(src: Path, dst: Path):
    if src.exists() and src.is_dir():
        shutil.copytree(src, dst)


def make_report(lines, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_candidate(root: Path):
    raw_path = root / "data/final_candidate_v1/raw/final_candidate_v1_service_time_runs.csv"
    proc_path = root / "data/final_candidate_v1/processed/final_candidate_v1_transaction_node_dataset.csv"
    sel_path = root / "data/final_candidate_v1/selection/final_candidate_v1_selected_transactions.csv"
    sampling_manifest = root / "results/final_candidate_v1/sampling_manifest.json"

    require_file(raw_path, "candidate raw CSV")
    require_file(proc_path, "candidate processed CSV")
    require_file(sel_path, "candidate selection CSV")

    print("Loading candidate CSVs...")
    raw = pd.read_csv(raw_path)
    proc = pd.read_csv(proc_path)
    sel = pd.read_csv(sel_path)

    raw_tx = detect_tx_col(raw)
    raw_node = detect_node_col(raw)
    proc_tx = detect_tx_col(proc)
    proc_type = detect_type_col(proc)
    proc_node = detect_node_col(proc)
    sel_tx = detect_tx_col(sel)
    sel_type = detect_type_col(sel)
    raw_service = detect_raw_service_col(raw)
    proc_target = detect_processed_target_col(proc)

    raw[raw_node] = raw[raw_node].map(normalize_node)
    proc[proc_node] = proc[proc_node].map(normalize_node)

    report = []
    checks = {}

    def check(name, condition, detail):
        checks[name] = bool(condition)
        status = "PASS" if condition else "FAIL"
        report.append(f"{name}: {status} | {detail}")
        print(f"{name}: {status} | {detail}")
        if not condition:
            raise RuntimeError(f"Validation failed: {name} | {detail}")

    check("raw_row_count", len(raw) == EXPECTED["raw_rows"], f"{len(raw)} expected {EXPECTED['raw_rows']}")
    check("processed_row_count", len(proc) == EXPECTED["processed_rows"], f"{len(proc)} expected {EXPECTED['processed_rows']}")
    check("selection_row_count", len(sel) == EXPECTED["selected_transactions"], f"{len(sel)} expected 1000")
    check("selection_unique_transactions", sel[sel_tx].nunique() == 1000, f"{sel[sel_tx].nunique()} expected 1000")
    check("raw_unique_transactions", raw[raw_tx].nunique() == 1000, f"{raw[raw_tx].nunique()} expected 1000")
    check("processed_unique_transactions", proc[proc_tx].nunique() == 1000, f"{proc[proc_tx].nunique()} expected 1000")

    type_counts = sel[sel_type].astype(str).value_counts().to_dict()
    type_ok = all(type_counts.get(t, 0) == 200 for t in EXPECTED_TYPES)
    check("balanced_selection_by_type", type_ok, str(type_counts))

    node_counts = proc[proc_node].value_counts().to_dict()
    node_ok = all(node_counts.get(n, 0) == 1000 for n in EXPECTED_NODES)
    check("processed_node_counts", node_ok, str(node_counts))

    dup_proc = proc.duplicated(subset=[proc_tx, proc_node]).sum()
    check("processed_unique_tx_node_pairs", dup_proc == 0, f"duplicate tx-node rows={dup_proc}")

    proc_group_counts = proc.groupby(proc_tx)[proc_node].nunique()
    check(
        "each_transaction_has_three_nodes",
        bool((proc_group_counts == 3).all()),
        f"bad transactions={int((proc_group_counts != 3).sum())}",
    )

    raw_counts = raw.groupby([raw_tx, raw_node]).size()
    check(
        "raw_five_measured_rows_per_tx_node",
        bool((raw_counts == 5).all()) and len(raw_counts) == 3000,
        f"pairs={len(raw_counts)}, bad_pairs={int((raw_counts != 5).sum())}",
    )

    set_sel = set(sel[sel_tx].astype(str))
    set_raw = set(raw[raw_tx].astype(str))
    set_proc = set(proc[proc_tx].astype(str))
    check(
        "transaction_id_sets_match",
        set_sel == set_raw == set_proc,
        f"selection={len(set_sel)} raw={len(set_raw)} processed={len(set_proc)}",
    )

    # Type consistency between selection and processed
    sel_type_map = dict(zip(sel[sel_tx].astype(str), sel[sel_type].astype(str)))
    proc_types_per_tx = proc.assign(_tx=proc[proc_tx].astype(str)).groupby("_tx")[proc_type].nunique()
    check(
        "processed_type_consistent_within_tx",
        bool((proc_types_per_tx == 1).all()),
        f"bad transactions={int((proc_types_per_tx != 1).sum())}",
    )
    proc_type_map = (
        proc.assign(_tx=proc[proc_tx].astype(str))
        .drop_duplicates("_tx")
        .set_index("_tx")[proc_type]
        .astype(str)
        .to_dict()
    )
    mismatches = sum(sel_type_map.get(tx) != proc_type_map.get(tx) for tx in set_sel)
    check("selection_processed_type_match", mismatches == 0, f"mismatches={mismatches}")

    if proc_target is None:
        raise RuntimeError(
            "Could not detect the processed service-time target column. "
            "Refusing to freeze a training dataset without a verified target."
        )
    target_numeric = pd.to_numeric(proc[proc_target], errors="coerce")
    bad_target = int((~target_numeric.map(math.isfinite)).sum())
    check(
        "processed_target_numeric_finite",
        bad_target == 0,
        f"target={proc_target}, invalid={bad_target}",
    )

    # Verify node ordering using the detected target.
    tmp = proc[[proc_tx, proc_node]].copy()
    tmp["_target"] = target_numeric
    pivot = tmp.pivot(index=proc_tx, columns=proc_node, values="_target")
    ordering = (pivot["Low"] > pivot["Medium"]) & (pivot["Medium"] > pivot["High"])
    check(
        "node_ordering_low_gt_medium_gt_high",
        bool(ordering.all()),
        f"ordering_ok={int(ordering.sum())}/{len(ordering)}",
    )

    # Fresh CV diagnostic from raw if service_time_ms is detectable.
    cv_summary = None
    if raw_service is not None:
        raw_service_num = pd.to_numeric(raw[raw_service], errors="coerce")
        if raw_service_num.notna().all():
            raw2 = raw[[raw_tx, raw_node]].copy()
            raw2["_service"] = raw_service_num
            stats = raw2.groupby([raw_tx, raw_node])["_service"].agg(["mean", "std"])
            stats["cv_pct"] = stats["std"] / stats["mean"] * 100.0
            cv_summary = {}
            for node in EXPECTED_NODES:
                vals = stats.xs(node, level=raw_node)["cv_pct"]
                cv_summary[node] = {
                    "median_cv_pct": float(vals.median()),
                    "mean_cv_pct": float(vals.mean()),
                    "max_cv_pct": float(vals.max()),
                    "pairs_cv_gt_10": int((vals > 10).sum()),
                }

    return {
        "raw_path": raw_path,
        "processed_path": proc_path,
        "selection_path": sel_path,
        "sampling_manifest_path": sampling_manifest if sampling_manifest.exists() else None,
        "raw": raw,
        "processed": proc,
        "selection": sel,
        "columns": {
            "raw_transaction_id": raw_tx,
            "raw_node": raw_node,
            "raw_service_time": raw_service,
            "processed_transaction_id": proc_tx,
            "processed_type": proc_type,
            "processed_node": proc_node,
            "processed_target": proc_target,
            "selection_transaction_id": sel_tx,
            "selection_type": sel_type,
        },
        "checks": checks,
        "cv_summary_recomputed": cv_summary,
        "source_hashes": {
            "candidate_raw_sha256": sha256_file(raw_path),
            "candidate_processed_sha256": sha256_file(proc_path),
            "candidate_selection_sha256": sha256_file(sel_path),
        },
    }


def create_split(proc: pd.DataFrame, tx_col: str, type_col: str):
    tx_type = (
        proc.assign(_tx=proc[tx_col].astype(str), _type=proc[type_col].astype(str))
        .drop_duplicates("_tx")[["_tx", "_type"]]
        .rename(columns={"_tx": "transaction_id", "_type": "type"})
    )
    if len(tx_type) != 1000:
        raise RuntimeError(f"Expected 1000 unique transactions, got {len(tx_type)}")

    rows = []
    for t in EXPECTED_TYPES:
        ids = tx_type.loc[tx_type["type"] == t, "transaction_id"].tolist()
        if len(ids) != 200:
            raise RuntimeError(f"Expected 200 transactions for {t}, got {len(ids)}")
        ranked = sorted(ids, key=lambda x: deterministic_rank(SPLIT_SEED, x))
        groups = [
            ("train", ranked[:140]),
            ("validation", ranked[140:170]),
            ("test", ranked[170:200]),
        ]
        for split, subset in groups:
            for rank_within, txid in enumerate(subset, start=1):
                rows.append(
                    {
                        "transaction_id": txid,
                        "type": t,
                        "split": split,
                        "rank_within_type_split": rank_within,
                        "deterministic_rank_sha256": deterministic_rank(SPLIT_SEED, txid),
                    }
                )

    assignments = pd.DataFrame(rows)
    if assignments["transaction_id"].nunique() != 1000:
        raise RuntimeError("Split assignment contains duplicate/missing transaction IDs.")
    return assignments


def copy_evidence(root: Path, staging: Path):
    evidence = staging / "evidence"
    # Existing analysis evidence.
    candidates = [
        (root / "results/final_candidate_v1/audit", evidence / "candidate_structural_audit"),
        (root / "results/final_candidate_v1/deep_audit", evidence / "candidate_deep_audit"),
        (root / "results/final_candidate_v1/collection", evidence / "collection_environment_snapshots"),
    ]
    for src, dst in candidates:
        safe_copy_tree_if_exists(src, dst)

    # Reproducibility-relevant code/config snapshots (small files only).
    code_snapshot = staging / "code_snapshot"
    files = [
        root / "scripts/reference_processor.py",
        root / "scripts/run_service_time_pilot.py",
        root / "Dockerfile.pilot",
        root / "requirements_research.txt",
        root / "experiments/final_candidate_v1/final.ps1",
        root / "experiments/final_candidate_v1/final_tool.py",
        root / "experiments/deep_audit_v1/deep_audit.ps1",
        root / "experiments/deep_audit_v1/deep_audit.py",
        root / "experiments/freeze_dataset_v1/freeze_and_split.py",
        root / "experiments/freeze_dataset_v1/freeze_and_split.ps1",
    ]
    for src in files:
        if src.exists() and src.is_file():
            safe_copy_file(src, code_snapshot / src.name)


def write_checksums(root_dir: Path, out_file: Path):
    rows = []
    for p in sorted(root_dir.rglob("*")):
        if p.is_file() and p.resolve() != out_file.resolve():
            rel = p.relative_to(root_dir).as_posix()
            rows.append((sha256_file(p), rel))
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(
        "".join(f"{h}  {rel}\n" for h, rel in rows),
        encoding="utf-8",
    )


def freeze(root: Path):
    root = root.resolve()
    final_dir = root / "data/final_training_data_v1"
    final_results = root / "results/final_training_data_v1"

    if final_dir.exists() or final_results.exists():
        raise RuntimeError(
            "FINAL_TRAINING_DATA_v1 destination already exists. Refusing to overwrite.\n"
            f"Data: {final_dir}\nResults: {final_results}\n"
            "Use verify mode instead. If a new freeze is scientifically required, create a new version."
        )

    print("=" * 72)
    print("FinCluster | FREEZE FINAL_TRAINING_DATA_v1 + GROUPED SPLIT")
    print("Analysis/copy only. No timing measurements.")
    print("=" * 72)

    v = validate_candidate(root)

    staging = root / f"data/.final_training_data_v1_staging_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    staging_results = root / f"results/.final_training_data_v1_staging_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    staging.mkdir(parents=True, exist_ok=False)
    staging_results.mkdir(parents=True, exist_ok=False)

    try:
        # Freeze primary evidence copies.
        raw_dst = staging / "raw/final_training_data_v1_service_time_runs.csv"
        proc_dst = staging / "processed/final_training_data_v1_transaction_node_dataset.csv"
        sel_dst = staging / "selection/final_training_data_v1_selected_transactions.csv"
        safe_copy_file(v["raw_path"], raw_dst)
        safe_copy_file(v["processed_path"], proc_dst)
        safe_copy_file(v["selection_path"], sel_dst)
        if v["sampling_manifest_path"] is not None:
            safe_copy_file(v["sampling_manifest_path"], staging / "manifests/sampling_manifest.json")

        # Grouped, type-stratified deterministic split.
        proc = v["processed"].copy()
        tx_col = v["columns"]["processed_transaction_id"]
        type_col = v["columns"]["processed_type"]

        assignments = create_split(proc, tx_col, type_col)
        assignments_path = staging / "splits/transaction_split_assignments.csv"
        assignments_path.parent.mkdir(parents=True, exist_ok=True)
        assignments.to_csv(assignments_path, index=False)

        assignment_map = assignments.set_index("transaction_id")["split"].to_dict()
        proc["_split"] = proc[tx_col].astype(str).map(assignment_map)
        if proc["_split"].isna().any():
            raise RuntimeError("Some processed rows did not receive a split.")

        split_row_counts = {}
        split_tx_counts = {}
        for split in ["train", "validation", "test"]:
            sdf = proc.loc[proc["_split"] == split].drop(columns=["_split"])
            out = staging / f"splits/{split}.csv"
            sdf.to_csv(out, index=False)
            split_row_counts[split] = int(len(sdf))
            split_tx_counts[split] = int(sdf[tx_col].nunique())

        expected_tx = {"train": 700, "validation": 150, "test": 150}
        expected_rows = {"train": 2100, "validation": 450, "test": 450}
        if split_tx_counts != expected_tx:
            raise RuntimeError(f"Unexpected split transaction counts: {split_tx_counts}")
        if split_row_counts != expected_rows:
            raise RuntimeError(f"Unexpected split row counts: {split_row_counts}")

        # Exact per-type split balance check.
        balance = assignments.groupby(["split", "type"]).size().unstack(fill_value=0)
        expected_balance = {
            "train": 140,
            "validation": 30,
            "test": 30,
        }
        for split, n in expected_balance.items():
            for t in EXPECTED_TYPES:
                got = int(balance.loc[split, t])
                if got != n:
                    raise RuntimeError(f"Split imbalance: {split}/{t} = {got}, expected {n}")

        # Leakage check.
        split_sets = {
            s: set(assignments.loc[assignments["split"] == s, "transaction_id"])
            for s in ["train", "validation", "test"]
        }
        leakage = (
            split_sets["train"] & split_sets["validation"]
            or split_sets["train"] & split_sets["test"]
            or split_sets["validation"] & split_sets["test"]
        )
        if leakage:
            raise RuntimeError(f"Transaction leakage across splits detected: {len(leakage)} IDs")

        # Copy supporting evidence/code snapshots.
        copy_evidence(root, staging)

        manifest = {
            "dataset_name": DATASET_NAME,
            "created_utc": utc_now(),
            "approval": REVIEWED_AUDIT_SUMMARY["decision"],
            "primary_target": (
                f"{v['columns']['processed_target']} "
                "(median repeated service time for transaction-node pair)"
            ),
            "sampling": {
                "source": "PaySim synthetic transaction dataset",
                "sampling_seed": SAMPLING_SEED,
                "balanced_transactions_total": 1000,
                "per_type": 200,
                "types": EXPECTED_TYPES,
                "note": (
                    "Balanced benchmark sampling is intentional and is not an estimate of "
                    "PaySim/production transaction-type prevalence."
                ),
            },
            "measurement_protocol": PROTOCOL,
            "candidate_validation": {
                "checks": v["checks"],
                "recomputed_cv_summary": v["cv_summary_recomputed"],
                "reviewed_deep_audit": REVIEWED_AUDIT_SUMMARY,
            },
            "split_policy": {
                "method": "transaction-grouped + exact type-stratified deterministic SHA-256 ranking",
                "split_seed": SPLIT_SEED,
                "ratios": {"train": 0.70, "validation": 0.15, "test": 0.15},
                "transaction_counts": split_tx_counts,
                "processed_row_counts": split_row_counts,
                "per_type_transaction_counts": {
                    split: {t: int(balance.loc[split, t]) for t in EXPECTED_TYPES}
                    for split in ["train", "validation", "test"]
                },
                "leakage_check": "PASS - zero transaction IDs shared across splits",
                "important": (
                    "transaction_id remains grouping/audit metadata and must NOT be used as an ML predictor."
                ),
            },
            "source_candidate_hashes": v["source_hashes"],
            "columns_detected": v["columns"],
            "methodological_notes": [
                "No candidate raw measurements were deleted because of CV or robust-outlier flags.",
                "The full frozen dataset is the primary modeling dataset.",
                "Any later outlier-excluded analysis must be labeled sensitivity analysis, not replacement ground truth.",
                "Do not refit preprocessing on validation/test data; fit preprocessing on training data only.",
                "Do not change the held-out test set after model comparison begins.",
            ],
        }

        manifest_path = staging / "manifests/dataset_freeze_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        split_manifest = {
            "created_utc": utc_now(),
            "seed": SPLIT_SEED,
            "method": "SHA256(seed:transaction_id) deterministic ranking within each transaction type",
            "train": {"transactions": 700, "rows": 2100, "per_type_transactions": 140},
            "validation": {"transactions": 150, "rows": 450, "per_type_transactions": 30},
            "test": {"transactions": 150, "rows": 450, "per_type_transactions": 30},
            "grouping_key": "transaction_id",
            "leakage_check": "PASS",
        }
        (staging / "manifests/split_manifest.json").write_text(
            json.dumps(split_manifest, indent=2), encoding="utf-8"
        )

        # Human-readable freeze report.
        report_lines = [
            "FinCluster FINAL_TRAINING_DATA_v1 FREEZE REPORT",
            "=" * 60,
            f"Created UTC: {manifest['created_utc']}",
            f"Approval: {manifest['approval']}",
            "",
            "DATASET",
            f"Raw measured rows: {len(v['raw'])}",
            f"Processed transaction-node rows: {len(v['processed'])}",
            f"Unique transactions: {v['processed'][tx_col].nunique()}",
            f"Target column: {v['columns']['processed_target']}",
            "",
            "SPLIT",
            "Train: 700 transactions / 2100 TX-node rows / 140 transactions per type",
            "Validation: 150 transactions / 450 TX-node rows / 30 transactions per type",
            "Test: 150 transactions / 450 TX-node rows / 30 transactions per type",
            "Transaction leakage across splits: 0",
            "",
            "KNOWN / DOCUMENTED QUALITY FINDINGS",
            "Node ordering Low > Medium > High: 1000/1000 transactions",
            "Median within-pair CV (%): High 1.477, Low 6.266, Medium 6.254",
            "Pairs CV >10%: High 10, Low 130, Medium 144",
            "Max absolute normalized block/node median deviation: 7.576%",
            "Robust-outlier flagged processed rows (|z|>3.5): 48 / 3000",
            "No rows removed because of these diagnostics.",
            "",
            "MODEL-LEAKAGE RULES",
            "- transaction_id is grouping/audit metadata, NOT a predictor.",
            "- newbalance* post-transaction fields are not default predictors.",
            "- target/stage timings are not predictor features.",
            "- final held-out test set must remain untouched during tuning.",
        ]
        make_report(report_lines, staging / "FREEZE_REPORT.txt")

        # Checksums last, after all frozen artifacts are present.
        write_checksums(staging, staging / "checksums/SHA256SUMS.txt")

        # Results-side pointer/decision snapshot.
        staging_results.mkdir(parents=True, exist_ok=True)
        (staging_results / "DATASET_APPROVAL.txt").write_text(
            "FINAL_TRAINING_DATA_v1\n"
            "STATUS = APPROVED_WITH_DOCUMENTED_RESIDUAL_VARIABILITY\n"
            f"Created UTC = {manifest['created_utc']}\n"
            "Primary modeling dataset = data/final_training_data_v1/processed/"
            "final_training_data_v1_transaction_node_dataset.csv\n"
            "Grouped split assignments = data/final_training_data_v1/splits/"
            "transaction_split_assignments.csv\n",
            encoding="utf-8",
        )

        # Promote staging directories atomically enough for this local workflow.
        staging.rename(final_dir)
        staging_results.rename(final_results)

        print()
        print("=" * 72)
        print("FREEZE + GROUPED SPLIT COMPLETE")
        print("=" * 72)
        print("DATASET_STATUS = FINAL_TRAINING_DATA_v1_APPROVED")
        print("APPROVAL = APPROVED_WITH_DOCUMENTED_RESIDUAL_VARIABILITY")
        print("Raw rows       = 15000")
        print("Processed rows = 3000")
        print("Transactions   = 1000")
        print("Train          = 700 transactions / 2100 rows")
        print("Validation     = 150 transactions / 450 rows")
        print("Test           = 150 transactions / 450 rows")
        print("Per type       = 140 train / 30 validation / 30 test")
        print("GROUP_LEAKAGE_CHECK = PASS")
        print(f"Frozen data: {final_dir}")
        print(f"Approval record: {final_results / 'DATASET_APPROVAL.txt'}")
        print("Do NOT alter these frozen split assignments once model comparison begins.")
        print("=" * 72)

    except Exception:
        # Keep failed staging for forensic inspection; do not silently delete evidence.
        print()
        print("FREEZE FAILED. Candidate source files were not modified.")
        print(f"Staging data (if created): {staging}")
        print(f"Staging results (if created): {staging_results}")
        raise


def verify(root: Path):
    root = root.resolve()
    frozen = root / "data/final_training_data_v1"
    manifest_path = frozen / "manifests/dataset_freeze_manifest.json"
    checksums_path = frozen / "checksums/SHA256SUMS.txt"
    require_file(manifest_path, "frozen dataset manifest")
    require_file(checksums_path, "SHA256SUMS")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print("=" * 72)
    print("VERIFY FINAL_TRAINING_DATA_v1")
    print("=" * 72)
    print(f"Manifest approval: {manifest.get('approval')}")

    bad = []
    lines = checksums_path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        if not line.strip():
            continue
        expected_hash, rel = line.split("  ", 1)
        path = frozen / rel
        if not path.exists():
            bad.append((rel, "MISSING"))
            continue
        actual = sha256_file(path)
        if actual != expected_hash:
            bad.append((rel, "HASH_MISMATCH"))

    if bad:
        print("FROZEN_DATASET_INTEGRITY = FAIL")
        for rel, reason in bad:
            print(f"  {reason}: {rel}")
        sys.exit(2)

    # Verify split counts and no leakage again.
    assignments = pd.read_csv(frozen / "splits/transaction_split_assignments.csv")
    counts = assignments.groupby("split")["transaction_id"].nunique().to_dict()
    if counts != {"test": 150, "train": 700, "validation": 150}:
        print(f"Unexpected split transaction counts: {counts}")
        sys.exit(3)

    sets = {
        s: set(assignments.loc[assignments["split"] == s, "transaction_id"].astype(str))
        for s in ["train", "validation", "test"]
    }
    if sets["train"] & sets["validation"] or sets["train"] & sets["test"] or sets["validation"] & sets["test"]:
        print("GROUP_LEAKAGE_CHECK = FAIL")
        sys.exit(4)

    print("FROZEN_DATASET_INTEGRITY = PASS")
    print("GROUP_LEAKAGE_CHECK = PASS")
    print("Split transactions = train 700 / validation 150 / test 150")
    print("=" * 72)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["freeze", "verify"])
    ap.add_argument("--root", required=True)
    args = ap.parse_args()

    root = Path(args.root)
    if args.mode == "freeze":
        freeze(root)
    else:
        verify(root)


if __name__ == "__main__":
    main()
