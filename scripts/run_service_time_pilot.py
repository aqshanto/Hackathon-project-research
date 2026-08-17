"""
FinCluster Research — Service-Time Pilot Runner v0.1

Purpose
-------
1. Select a fixed pilot set of 10 valid PaySim transactions:
   2 CASH_IN, 2 CASH_OUT, 2 DEBIT, 2 PAYMENT, 2 TRANSFER.
2. Run the SAME selected transactions on ONE externally controlled node profile.
3. For each transaction-node pair:
      - 2 warm-up executions (not recorded as research measurements)
      - 5 measured executions
      - reset processor state before every execution
4. Save/update immutable-style raw measured-run rows.
5. After all three node profiles are collected, aggregate the 5 measured runs
   into one ground-truth row per transaction-node pair using the MEDIAN.

IMPORTANT RESEARCH RULE
-----------------------
This script does NOT make Low/Medium/High nodes faster or slower in Python.
The actual CPU/RAM limits must be enforced externally (for example with Docker).
Run this script once inside each correctly limited environment using:
    --node-profile low
    --node-profile medium
    --node-profile high

Running all three labels on the same unrestricted host would only rename the
same machine and would NOT constitute a valid node-comparison experiment.

Expected project location
-------------------------
Research/
  scripts/
    reference_processor.py
    run_service_time_pilot.py
  data/
    raw/
      PS_20174392719_1491204439457_log.csv
      pilot_selected_transactions.csv
      pilot_service_time_runs.csv
    processed/
      pilot_transaction_node_dataset.csv
  results/
    pilot_service_time/
      run_manifest_<node>.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import statistics
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from reference_processor import NodeProfile, ReferenceProcessor, TransactionRecord


TRANSACTION_TYPES = ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER")

DEFAULT_NODE_PROFILES = {
    "low": NodeProfile(name="Low", cpu_limit=1.0, memory_mb=1024),
    "medium": NodeProfile(name="Medium", cpu_limit=2.0, memory_mb=2048),
    "high": NodeProfile(name="High", cpu_limit=4.0, memory_mb=4096),
}

PAYSIM_REQUIRED_COLUMNS = {
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "nameDest",
    "oldbalanceDest",
}

SELECTION_COLUMNS = [
    "transaction_id",
    "source_row_index",
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "nameDest",
    "oldbalanceDest",
]

RAW_COLUMNS = [
    "transaction_id",
    "source_row_index",
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "oldbalanceDest",
    "node_profile",
    "cpu_limit",
    "memory_mb",
    "repetition",
    "status",
    "service_time_ms",
    "schema_validation_ms",
    "security_authorization_ms",
    "begin_db_transaction_ms",
    "idempotency_check_ms",
    "account_lookup_ms",
    "type_specific_validation_ms",
    "state_update_ms",
    "ledger_update_ms",
    "audit_log_ms",
    "completion_record_ms",
    "commit_ms",
    "rollback_ms",
    "error_type",
    "error_message",
]

PROCESSED_COLUMNS = [
    "transaction_id",
    "source_row_index",
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "oldbalanceDest",
    "node_profile",
    "cpu_limit",
    "memory_mb",
    "service_time_ms",
    "mean_service_time_ms",
    "std_service_time_ms",
    "min_service_time_ms",
    "max_service_time_ms",
    "n_successful_runs",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect FinCluster service-time pilot measurements."
    )
    parser.add_argument(
        "--paysim-file",
        type=Path,
        default=Path("Research/data/raw/PS_20174392719_1491204439457_log.csv"),
        help="Path to the PaySim CSV.",
    )
    parser.add_argument(
        "--node-profile",
        choices=("low", "medium", "high"),
        help=(
            "Node profile measured in this run. Required for collection. "
            "Actual resource limits must be enforced externally."
        ),
    )
    parser.add_argument(
        "--cpu-limit",
        type=float,
        default=None,
        help="Override node CPU metadata to match the actual external limit.",
    )
    parser.add_argument(
        "--memory-mb",
        type=int,
        default=None,
        help="Override node RAM metadata to match the actual external limit.",
    )
    parser.add_argument(
        "--warmups",
        type=int,
        default=2,
        help="Warm-up executions per transaction-node pair (default: 2).",
    )
    parser.add_argument(
        "--measured-runs",
        type=int,
        default=5,
        help="Measured executions per transaction-node pair (default: 5).",
    )
    parser.add_argument(
        "--rows-per-type",
        type=int,
        default=2,
        help="Pilot transactions selected per PaySim type (default: 2).",
    )
    parser.add_argument(
        "--selection-file",
        type=Path,
        default=Path("Research/data/raw/pilot_selected_transactions.csv"),
        help="Persistent fixed pilot transaction selection.",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=Path("Research/data/raw/pilot_service_time_runs.csv"),
        help="Combined measured-run output across nodes.",
    )
    parser.add_argument(
        "--processed-output",
        type=Path,
        default=Path("Research/data/processed/pilot_transaction_node_dataset.csv"),
        help="Aggregated transaction-node dataset.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("Research/results/pilot_service_time"),
        help="Run-manifest output directory.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=250_000,
        help="PaySim chunk size used only when creating the pilot selection.",
    )
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="Skip collection and rebuild processed CSV from existing raw rows.",
    )
    parser.add_argument(
        "--force-reselect",
        action="store_true",
        help="Delete/recreate the fixed 10-transaction pilot selection.",
    )
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_type(value: Any) -> str:
    return str(value).strip().upper().replace("-", "_")


def valid_for_reference_processor(row: pd.Series) -> bool:
    """Avoid selecting rows that are invalid for the current v0.1 processor."""
    tx_type = normalize_type(row["type"])

    try:
        amount = float(row["amount"])
        old_origin = float(row["oldbalanceOrg"])
        old_dest = float(row["oldbalanceDest"])
    except (TypeError, ValueError):
        return False

    if not math.isfinite(amount) or not math.isfinite(old_origin) or not math.isfinite(old_dest):
        return False
    if amount <= 0 or old_origin < 0 or old_dest < 0:
        return False

    # Debit-like operations require enough source funds in reference_processor.py.
    if tx_type in {"CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}:
        if old_origin < amount:
            return False

    if tx_type == "TRANSFER" and str(row["nameOrig"]) == str(row["nameDest"]):
        return False

    return bool(str(row["nameOrig"]).strip()) and bool(str(row["nameDest"]).strip())


def deterministic_transaction_id(
    source_name: str,
    source_row_index: int,
    row: pd.Series,
) -> str:
    """
    Stable UUID5 so every node run uses the exact same logical transaction ID.
    """
    identity = "|".join(
        [
            source_name,
            str(source_row_index),
            str(row["step"]),
            normalize_type(row["type"]),
            str(row["amount"]),
            str(row["nameOrig"]),
            str(row["nameDest"]),
        ]
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"fincluster-pilot:{identity}"))


def create_selection(
    paysim_file: Path,
    selection_file: Path,
    rows_per_type: int,
    chunk_size: int,
) -> pd.DataFrame:
    """
    Stream the 6M+ row PaySim CSV and select the first valid rows needed
    for each transaction type. The selection is persisted and reused unchanged.
    """
    if not paysim_file.exists():
        raise FileNotFoundError(f"PaySim file not found: {paysim_file}")

    selected: dict[str, list[dict[str, Any]]] = {
        tx_type: [] for tx_type in TRANSACTION_TYPES
    }

    header = pd.read_csv(paysim_file, nrows=0)
    missing_columns = PAYSIM_REQUIRED_COLUMNS.difference(header.columns)
    if missing_columns:
        raise ValueError(
            "PaySim CSV is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    global_row_offset = 0

    usecols = [
        "step",
        "type",
        "amount",
        "nameOrig",
        "oldbalanceOrg",
        "nameDest",
        "oldbalanceDest",
    ]

    for chunk in pd.read_csv(paysim_file, usecols=usecols, chunksize=chunk_size):
        for local_index, row in chunk.iterrows():
            tx_type = normalize_type(row["type"])

            if tx_type not in selected:
                continue
            if len(selected[tx_type]) >= rows_per_type:
                continue
            if not valid_for_reference_processor(row):
                continue

            # iterrows() index retains the source row index under normal chunked read.
            source_row_index = int(local_index)

            selected[tx_type].append(
                {
                    "transaction_id": deterministic_transaction_id(
                        paysim_file.name,
                        source_row_index,
                        row,
                    ),
                    "source_row_index": source_row_index,
                    "step": int(row["step"]),
                    "type": tx_type,
                    "amount": float(row["amount"]),
                    "nameOrig": str(row["nameOrig"]),
                    "oldbalanceOrg": float(row["oldbalanceOrg"]),
                    "nameDest": str(row["nameDest"]),
                    "oldbalanceDest": float(row["oldbalanceDest"]),
                }
            )

        if all(len(rows) >= rows_per_type for rows in selected.values()):
            break

        global_row_offset += len(chunk)

    shortages = {
        tx_type: rows_per_type - len(rows)
        for tx_type, rows in selected.items()
        if len(rows) < rows_per_type
    }
    if shortages:
        raise RuntimeError(f"Could not build balanced pilot selection: {shortages}")

    ordered: list[dict[str, Any]] = []
    # Interleave by occurrence number so the selection is easy to inspect.
    for occurrence in range(rows_per_type):
        for tx_type in TRANSACTION_TYPES:
            ordered.append(selected[tx_type][occurrence])

    df = pd.DataFrame(ordered, columns=SELECTION_COLUMNS)
    ensure_parent(selection_file)
    df.to_csv(selection_file, index=False)

    print(f"Created fixed pilot selection: {selection_file}")
    print(f"Selected rows: {len(df)} ({rows_per_type} per transaction type)")
    return df


def load_or_create_selection(args: argparse.Namespace) -> pd.DataFrame:
    if args.force_reselect and args.selection_file.exists():
        args.selection_file.unlink()

    if args.selection_file.exists():
        df = pd.read_csv(args.selection_file)
        missing = set(SELECTION_COLUMNS).difference(df.columns)
        if missing:
            raise ValueError(
                f"Selection file is missing columns: {sorted(missing)}"
            )

        counts = df["type"].map(normalize_type).value_counts().to_dict()
        expected = {tx_type: args.rows_per_type for tx_type in TRANSACTION_TYPES}
        if counts != expected:
            raise ValueError(
                "Existing selection does not match requested balanced pilot. "
                f"Found {counts}; expected {expected}. "
                "Use --force-reselect only if you intentionally want a new pilot set."
            )

        print(f"Reusing fixed pilot selection: {args.selection_file}")
        return df[SELECTION_COLUMNS].copy()

    return create_selection(
        paysim_file=args.paysim_file,
        selection_file=args.selection_file,
        rows_per_type=args.rows_per_type,
        chunk_size=args.chunk_size,
    )


def resolve_node_profile(args: argparse.Namespace) -> NodeProfile:
    if not args.node_profile:
        raise ValueError("--node-profile is required unless --aggregate-only is used")

    base = DEFAULT_NODE_PROFILES[args.node_profile]
    return NodeProfile(
        name=base.name,
        cpu_limit=args.cpu_limit if args.cpu_limit is not None else base.cpu_limit,
        memory_mb=args.memory_mb if args.memory_mb is not None else base.memory_mb,
    )


def to_transaction_record(row: pd.Series) -> TransactionRecord:
    return TransactionRecord.from_mapping(
        {
            "step": int(row["step"]),
            "type": normalize_type(row["type"]),
            "amount": row["amount"],
            "nameOrig": row["nameOrig"],
            "oldbalanceOrg": row["oldbalanceOrg"],
            "nameDest": row["nameDest"],
            "oldbalanceDest": row["oldbalanceDest"],
        },
        transaction_id=str(row["transaction_id"]),
    )


def stage_value(result, stage: str) -> float | None:
    value = result.stage_timings_ms.get(stage)
    return float(value) if value is not None else None


def result_to_raw_row(
    selection_row: pd.Series,
    node: NodeProfile,
    repetition: int,
    result,
) -> dict[str, Any]:
    return {
        "transaction_id": str(selection_row["transaction_id"]),
        "source_row_index": int(selection_row["source_row_index"]),
        "step": int(selection_row["step"]),
        "type": normalize_type(selection_row["type"]),
        "amount": float(selection_row["amount"]),
        "oldbalanceOrg": float(selection_row["oldbalanceOrg"]),
        "oldbalanceDest": float(selection_row["oldbalanceDest"]),
        "node_profile": node.name,
        "cpu_limit": node.cpu_limit,
        "memory_mb": node.memory_mb,
        "repetition": repetition,
        "status": result.status,
        "service_time_ms": float(result.service_time_ms),
        "schema_validation_ms": stage_value(result, "schema_validation"),
        "security_authorization_ms": stage_value(result, "security_authorization"),
        "begin_db_transaction_ms": stage_value(result, "begin_db_transaction"),
        "idempotency_check_ms": stage_value(result, "idempotency_check"),
        "account_lookup_ms": stage_value(result, "account_lookup"),
        "type_specific_validation_ms": stage_value(
            result, "type_specific_validation"
        ),
        "state_update_ms": stage_value(result, "state_update"),
        "ledger_update_ms": stage_value(result, "ledger_update"),
        "audit_log_ms": stage_value(result, "audit_log"),
        "completion_record_ms": stage_value(result, "completion_record"),
        "commit_ms": stage_value(result, "commit"),
        "rollback_ms": stage_value(result, "rollback"),
        "error_type": result.error_type,
        "error_message": result.error_message,
    }


def update_combined_raw_file(
    raw_output: Path,
    new_rows: pd.DataFrame,
    node_name: str,
    selected_tx_ids: set[str],
) -> None:
    """
    Idempotent at node+selected-transaction level:
    rerunning Low replaces previous Low pilot rows instead of duplicating them.
    """
    ensure_parent(raw_output)

    if raw_output.exists():
        old = pd.read_csv(raw_output)
        if not old.empty:
            keep_mask = ~(
                (old["node_profile"] == node_name)
                & (old["transaction_id"].astype(str).isin(selected_tx_ids))
            )
            old = old.loc[keep_mask].copy()
            combined = pd.concat([old, new_rows], ignore_index=True)
        else:
            combined = new_rows.copy()
    else:
        combined = new_rows.copy()

    combined = combined[RAW_COLUMNS]
    combined.sort_values(
        by=["transaction_id", "node_profile", "repetition"],
        inplace=True,
        kind="stable",
    )
    combined.to_csv(raw_output, index=False)


def write_manifest(
    results_dir: Path,
    node: NodeProfile,
    args: argparse.Namespace,
    selection: pd.DataFrame,
    new_rows: pd.DataFrame,
) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = results_dir / f"run_manifest_{node.name.lower()}.json"

    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "FinCluster service-time pilot; not a final research result",
        "node_profile": {
            "name": node.name,
            "cpu_limit_metadata": node.cpu_limit,
            "memory_mb_metadata": node.memory_mb,
            "external_limits_required": True,
        },
        "measurement_protocol": {
            "warmups_per_transaction_node_pair": args.warmups,
            "measured_runs_per_transaction_node_pair": args.measured_runs,
            "ground_truth_aggregation": "median",
            "processor_state_reset_before_every_execution": True,
        },
        "pilot_selection": {
            "transactions": int(len(selection)),
            "rows_per_type": args.rows_per_type,
            "transaction_types": list(TRANSACTION_TYPES),
            "selection_file": str(args.selection_file),
        },
        "outputs": {
            "raw_output": str(args.raw_output),
            "processed_output": str(args.processed_output),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "pid": os.getpid(),
        },
        "current_run": {
            "measured_rows_written": int(len(new_rows)),
            "successful_rows": int((new_rows["status"] == "SUCCESS").sum()),
            "failed_rows": int((new_rows["status"] != "SUCCESS").sum()),
        },
        "warning": (
            "cpu_limit and memory_mb are metadata only in Python. "
            "The actual process/container must be externally constrained to match."
        ),
    }

    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def collect_for_node(
    args: argparse.Namespace,
    selection: pd.DataFrame,
    node: NodeProfile,
) -> None:
    if args.warmups < 0:
        raise ValueError("--warmups cannot be negative")
    if args.measured_runs < 1:
        raise ValueError("--measured-runs must be at least 1")

    print()
    print("=" * 72)
    print("FinCluster Service-Time Pilot")
    print("=" * 72)
    print(f"Node label       : {node.name}")
    print(f"CPU metadata     : {node.cpu_limit}")
    print(f"Memory metadata  : {node.memory_mb} MB")
    print(f"Transactions     : {len(selection)}")
    print(f"Warmups / pair   : {args.warmups}")
    print(f"Measured / pair  : {args.measured_runs}")
    print()
    print("IMPORTANT: Verify this process is actually running under the")
    print("external CPU/RAM limits shown above. This script does not enforce them.")
    print("=" * 72)
    print()

    processor = ReferenceProcessor()
    measured_rows: list[dict[str, Any]] = []

    try:
        for tx_number, (_, row) in enumerate(selection.iterrows(), start=1):
            tx = to_transaction_record(row)
            label = f"{tx_number:02d}/{len(selection)} {tx.type} {tx.transaction_id[:8]}"

            # Warm-ups are deliberately not saved as research measurements.
            for _ in range(args.warmups):
                processor.reset_state()
                warmup = processor.process_transaction(tx, node)
                if warmup.status != "SUCCESS":
                    raise RuntimeError(
                        f"Warm-up failed for {tx.transaction_id}: "
                        f"{warmup.error_type}: {warmup.error_message}"
                    )

            current_times: list[float] = []

            for repetition in range(1, args.measured_runs + 1):
                processor.reset_state()
                result = processor.process_transaction(tx, node)

                measured_rows.append(
                    result_to_raw_row(
                        selection_row=row,
                        node=node,
                        repetition=repetition,
                        result=result,
                    )
                )

                if result.status == "SUCCESS":
                    current_times.append(float(result.service_time_ms))
                else:
                    print(
                        f"WARNING: measured failure: {tx.transaction_id} "
                        f"{result.error_type}: {result.error_message}"
                    )

            if current_times:
                median_ms = statistics.median(current_times)
                print(f"[{label}] median={median_ms:.6f} ms")
            else:
                print(f"[{label}] ALL MEASURED RUNS FAILED")

    finally:
        processor.close()

    new_df = pd.DataFrame(measured_rows, columns=RAW_COLUMNS)

    selected_tx_ids = set(selection["transaction_id"].astype(str))
    update_combined_raw_file(
        raw_output=args.raw_output,
        new_rows=new_df,
        node_name=node.name,
        selected_tx_ids=selected_tx_ids,
    )

    manifest = write_manifest(
        results_dir=args.results_dir,
        node=node,
        args=args,
        selection=selection,
        new_rows=new_df,
    )

    print()
    print(f"Raw measurements updated: {args.raw_output}")
    print(f"Run manifest saved       : {manifest}")


def aggregate_raw_measurements(
    raw_output: Path,
    processed_output: Path,
    measured_runs_expected: int | None,
) -> pd.DataFrame:
    if not raw_output.exists():
        raise FileNotFoundError(
            f"Raw pilot measurements not found: {raw_output}"
        )

    raw = pd.read_csv(raw_output)
    if raw.empty:
        raise ValueError("Raw pilot measurement file is empty")

    missing = set(RAW_COLUMNS).difference(raw.columns)
    if missing:
        raise ValueError(f"Raw file is missing expected columns: {sorted(missing)}")

    success = raw.loc[raw["status"] == "SUCCESS"].copy()

    group_cols = [
        "transaction_id",
        "source_row_index",
        "step",
        "type",
        "amount",
        "oldbalanceOrg",
        "oldbalanceDest",
        "node_profile",
        "cpu_limit",
        "memory_mb",
    ]

    rows: list[dict[str, Any]] = []

    for group_key, group in success.groupby(group_cols, dropna=False, sort=False):
        times = [float(v) for v in group["service_time_ms"].tolist()]
        if not times:
            continue

        record = dict(zip(group_cols, group_key))
        record.update(
            {
                # This is the primary ground-truth target.
                "service_time_ms": statistics.median(times),
                "mean_service_time_ms": statistics.mean(times),
                "std_service_time_ms": (
                    statistics.stdev(times) if len(times) >= 2 else 0.0
                ),
                "min_service_time_ms": min(times),
                "max_service_time_ms": max(times),
                "n_successful_runs": len(times),
            }
        )
        rows.append(record)

    processed = pd.DataFrame(rows, columns=PROCESSED_COLUMNS)
    processed.sort_values(
        by=["transaction_id", "node_profile"],
        inplace=True,
        kind="stable",
    )

    ensure_parent(processed_output)
    processed.to_csv(processed_output, index=False)

    print()
    print("=" * 72)
    print("Aggregation Summary")
    print("=" * 72)
    print(f"Raw measured rows        : {len(raw)}")
    print(f"Successful measured rows : {len(success)}")
    print(f"Failed measured rows     : {len(raw) - len(success)}")
    print(f"Aggregated TX-node rows  : {len(processed)}")
    print(f"Nodes currently present  : {sorted(processed['node_profile'].unique().tolist())}")

    counts = (
        success.groupby(["node_profile", "transaction_id"])
        .size()
        .rename("runs")
        .reset_index()
    )

    if measured_runs_expected is not None:
        bad = counts.loc[counts["runs"] != measured_runs_expected]
        if not bad.empty:
            print()
            print("WARNING: Some transaction-node pairs do not have the expected")
            print(f"{measured_runs_expected} successful measured runs:")
            print(bad.to_string(index=False))

    expected_nodes = {"Low", "Medium", "High"}
    present_nodes = set(processed["node_profile"].unique())
    missing_nodes = expected_nodes - present_nodes

    if missing_nodes:
        print()
        print(
            "Pilot is not complete yet. Still collect node(s): "
            + ", ".join(sorted(missing_nodes))
        )
    else:
        tx_node_counts = processed.groupby("transaction_id")["node_profile"].nunique()
        incomplete_tx = tx_node_counts.loc[tx_node_counts != 3]
        if incomplete_tx.empty:
            print()
            print("All selected transactions have observations for Low, Medium, High.")
            print("The pilot transaction-node dataset is structurally complete.")
        else:
            print()
            print("WARNING: Some transactions are missing one or more node observations.")

    print(f"Processed dataset saved  : {processed_output}")
    return processed


def main() -> None:
    args = parse_args()

    if args.rows_per_type < 1:
        raise ValueError("--rows-per-type must be at least 1")
    if args.chunk_size < 1:
        raise ValueError("--chunk-size must be at least 1")

    if args.aggregate_only:
        aggregate_raw_measurements(
            raw_output=args.raw_output,
            processed_output=args.processed_output,
            measured_runs_expected=args.measured_runs,
        )
        return

    selection = load_or_create_selection(args)
    node = resolve_node_profile(args)

    collect_for_node(
        args=args,
        selection=selection,
        node=node,
    )

    # Rebuild aggregate after every node run. It is okay if only 1/3 or 2/3
    # node profiles are currently present; the summary will say what remains.
    aggregate_raw_measurements(
        raw_output=args.raw_output,
        processed_output=args.processed_output,
        measured_runs_expected=args.measured_runs,
    )


if __name__ == "__main__":
    main()
