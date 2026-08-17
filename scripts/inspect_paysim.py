"""Inspect a PaySim-style dataset without training a model.

The script supports either:
1) a local CSV/Parquet file; or
2) a streamed Hugging Face dataset sample.

For a local CSV, use --full-scan to chunk-scan the complete file for:
- exact row count,
- missing values,
- blank-string counts,
- transaction-type distribution,
- fraud/flagged-fraud distributions.

Heavier exploratory statistics (duplicates, identifier cardinality, quantiles,
plots) are intentionally calculated on a bounded sample so the script remains
usable on the ~multi-million-row PaySim file without requiring all rows in RAM.

No model is trained and fraud labels are never converted into workload labels.

Example from project root:
    python Research/scripts/inspect_paysim.py \
        --local-file "Research/data/raw/PS_20174392719_1491204439457_log.csv" \
        --full-scan
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Final

import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_DATASET_ID: Final[str] = (
    "purulalwani/Synthetic-Financial-Datasets-For-Fraud-Detection"
)
DEFAULT_SAMPLE_SIZE = int(os.getenv("PAYSIM_SAMPLE_SIZE", "100000"))
DEFAULT_RANDOM_SEED = int(os.getenv("PAYSIM_RANDOM_SEED", "42"))
DEFAULT_CHUNK_SIZE = int(os.getenv("PAYSIM_CHUNK_SIZE", "250000"))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "Research" / "results" / "paysim_inspection"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect PaySim data; no model training.")
    parser.add_argument(
        "--local-file",
        default=os.getenv("PAYSIM_LOCAL_FILE"),
        help="Path to local CSV/Parquet. If omitted, a Hugging Face sample is streamed.",
    )
    parser.add_argument(
        "--dataset-id",
        default=os.getenv("PAYSIM_DATASET_ID", DEFAULT_DATASET_ID),
        help="Hugging Face dataset ID used only when --local-file is omitted.",
    )
    parser.add_argument(
        "--split",
        default=os.getenv("PAYSIM_SPLIT", "train"),
        help="Hugging Face split name.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help="Bounded sample size used for exploratory statistics/plots.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help="Random seed for streamed sampling.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Rows per chunk for a local CSV full scan.",
    )
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help="For a local CSV, scan the entire file in chunks for exact row/missing/type counts.",
    )
    return parser.parse_args()


def load_local_sample(path: Path, sample_size: int) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, nrows=sample_size)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path).head(sample_size)
    raise ValueError(f"Unsupported local file type: {suffix}")


def load_huggingface_sample(dataset_id: str, split: str, sample_size: int, seed: int) -> pd.DataFrame:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "The 'datasets' package is required. Install Research/requirements_research.txt."
        ) from exc

    stream = load_dataset(dataset_id, split=split, streaming=True)
    stream = stream.shuffle(seed=seed, buffer_size=max(sample_size * 2, 10000))
    rows = list(stream.take(sample_size))
    if not rows:
        raise RuntimeError("No rows were returned by the selected dataset and split.")
    return pd.DataFrame(rows)


def full_scan_local_csv(path: Path, chunk_size: int) -> dict:
    """Chunk-scan exact row/missing/blank/type/label counts without loading all data."""
    total_rows = 0
    columns: list[str] | None = None
    missing_counts: Counter[str] = Counter()
    blank_counts: Counter[str] = Counter()
    type_counts: Counter[object] = Counter()
    fraud_counts: Counter[object] = Counter()
    flagged_counts: Counter[object] = Counter()

    for chunk in pd.read_csv(path, chunksize=chunk_size):
        total_rows += len(chunk)
        if columns is None:
            columns = list(chunk.columns)

        for column, count in chunk.isna().sum().items():
            missing_counts[str(column)] += int(count)

        for column in chunk.select_dtypes(include=["object", "string"]).columns:
            values = chunk[column].astype("string")
            count = int(values.str.strip().eq("").fillna(False).sum())
            blank_counts[str(column)] += count

        if "type" in chunk.columns:
            type_counts.update(chunk["type"].value_counts(dropna=False).to_dict())
        if "isFraud" in chunk.columns:
            fraud_counts.update(chunk["isFraud"].value_counts(dropna=False).to_dict())
        if "isFlaggedFraud" in chunk.columns:
            flagged_counts.update(
                chunk["isFlaggedFraud"].value_counts(dropna=False).to_dict()
            )

    columns = columns or []
    missing_df = pd.DataFrame(
        {
            "missing_count": [missing_counts.get(c, 0) for c in columns],
            "missing_percent": [
                round(missing_counts.get(c, 0) / total_rows * 100, 8) if total_rows else 0.0
                for c in columns
            ],
        },
        index=columns,
    )

    blank_df = pd.DataFrame(
        {
            "blank_string_count": [blank_counts.get(c, 0) for c in columns],
            "blank_string_percent": [
                round(blank_counts.get(c, 0) / total_rows * 100, 8) if total_rows else 0.0
                for c in columns
            ],
        },
        index=columns,
    )

    return {
        "total_rows": total_rows,
        "columns": columns,
        "missing_df": missing_df,
        "blank_df": blank_df,
        "type_counts": type_counts,
        "fraud_counts": fraud_counts,
        "flagged_counts": flagged_counts,
    }


def save_distribution(counts: pd.Series, stem: str, title: str, xlabel: str, denominator: int) -> None:
    distribution = pd.DataFrame(
        {
            "count": counts,
            "percent": (counts / denominator * 100).round(8) if denominator else 0,
        }
    )
    distribution.to_csv(OUTPUT_DIR / f"{stem}.csv")

    ax = counts.plot(kind="bar", figsize=(8, 5), title=title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{stem}.png", dpi=200)
    plt.close()


def counter_to_series(counter: Counter) -> pd.Series:
    if not counter:
        return pd.Series(dtype="int64")
    return pd.Series(dict(counter)).sort_values(ascending=False)


def main() -> None:
    args = parse_args()

    print("PaySim inspection only - no model training will be performed.")
    print(f"Output directory: {OUTPUT_DIR}")

    full_scan = None
    if args.local_file:
        source = Path(args.local_file).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Local dataset not found: {source}")
        print(f"Loading bounded exploratory sample from: {source}")
        df = load_local_sample(source, args.sample_size)
        source_description = str(source)

        if args.full_scan and source.suffix.lower() == ".csv":
            print(f"Running chunked full CSV scan (chunk size={args.chunk_size:,})...")
            full_scan = full_scan_local_csv(source, args.chunk_size)
            print(f"Exact data-row count from full scan: {full_scan['total_rows']:,}")
        elif args.full_scan:
            print("--full-scan exact chunk mode is currently implemented for CSV only; sample metrics will be used.")
    else:
        print(f"Streaming dataset sample: {args.dataset_id} [{args.split}]")
        df = load_huggingface_sample(args.dataset_id, args.split, args.sample_size, args.seed)
        source_description = f"hf://{args.dataset_id}/{args.split}"
        print("Note: streamed mode reports sample-based inspection statistics.")

    print(f"Exploratory sample shape: {df.shape}")

    schema = pd.DataFrame(
        {"column": df.columns, "dtype": [str(dtype) for dtype in df.dtypes]}
    )
    schema.to_csv(OUTPUT_DIR / "schema.csv", index=False)

    if full_scan is not None:
        missing = full_scan["missing_df"]
        blank = full_scan["blank_df"]
        inspection_rows = int(full_scan["total_rows"])
        inspection_scope = "full_local_csv_for_row_missing_blank_type_label_counts"
    else:
        missing = pd.DataFrame(
            {
                "missing_count": df.isna().sum(),
                "missing_percent": (df.isna().mean() * 100).round(8),
            }
        )
        blank_counts = {}
        for column in df.select_dtypes(include=["object", "string"]).columns:
            values = df[column].astype("string")
            blank_counts[column] = int(values.str.strip().eq("").fillna(False).sum())
        blank = pd.DataFrame(
            {
                "blank_string_count": [blank_counts.get(c, 0) for c in df.columns],
                "blank_string_percent": [
                    round(blank_counts.get(c, 0) / len(df) * 100, 8) if len(df) else 0.0
                    for c in df.columns
                ],
            },
            index=df.columns,
        )
        inspection_rows = int(len(df))
        inspection_scope = "bounded_sample"

    missing.sort_values("missing_count", ascending=False).to_csv(
        OUTPUT_DIR / "missing_values.csv"
    )
    blank.sort_values("blank_string_count", ascending=False).to_csv(
        OUTPUT_DIR / "blank_strings.csv"
    )

    duplicate_count = int(df.duplicated().sum())
    duplicate_summary = {
        "scope": "bounded_exploratory_sample",
        "sample_rows": int(len(df)),
        "duplicate_rows": duplicate_count,
        "duplicate_percent": round(
            (duplicate_count / len(df) * 100) if len(df) else 0.0, 8
        ),
        "note": "This is not claimed as an exact full-file duplicate count.",
    }
    (OUTPUT_DIR / "duplicate_summary.json").write_text(
        json.dumps(duplicate_summary, indent=2), encoding="utf-8"
    )

    if full_scan is not None and full_scan["type_counts"]:
        type_counts = counter_to_series(full_scan["type_counts"])
        type_denominator = inspection_rows
    elif "type" in df.columns:
        type_counts = df["type"].value_counts(dropna=False)
        type_denominator = len(df)
    else:
        type_counts = pd.Series(dtype="int64")
        type_denominator = 0

    if not type_counts.empty:
        save_distribution(
            type_counts,
            "transaction_type_distribution",
            "Transaction Type Distribution",
            "Transaction Type",
            type_denominator,
        )

    if full_scan is not None and full_scan["fraud_counts"]:
        fraud_counts = counter_to_series(full_scan["fraud_counts"])
        fraud_denominator = inspection_rows
    elif "isFraud" in df.columns:
        fraud_counts = df["isFraud"].value_counts(dropna=False)
        fraud_denominator = len(df)
    else:
        fraud_counts = pd.Series(dtype="int64")
        fraud_denominator = 0

    if not fraud_counts.empty:
        save_distribution(
            fraud_counts,
            "fraud_distribution",
            "Fraud Label Distribution",
            "isFraud",
            fraud_denominator,
        )

    if full_scan is not None and full_scan["flagged_counts"]:
        flagged_counts = counter_to_series(full_scan["flagged_counts"])
        flagged_denominator = inspection_rows
    elif "isFlaggedFraud" in df.columns:
        flagged_counts = df["isFlaggedFraud"].value_counts(dropna=False)
        flagged_denominator = len(df)
    else:
        flagged_counts = pd.Series(dtype="int64")
        flagged_denominator = 0

    if not flagged_counts.empty:
        distribution = pd.DataFrame(
            {
                "count": flagged_counts,
                "percent": (flagged_counts / flagged_denominator * 100).round(8),
            }
        )
        distribution.to_csv(OUTPUT_DIR / "flagged_fraud_distribution.csv")

    if "amount" in df.columns:
        numeric_amount = pd.to_numeric(df["amount"], errors="coerce")
        amount_summary = numeric_amount.describe(
            percentiles=[0.01, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
        )
        amount_summary.to_csv(OUTPUT_DIR / "amount_summary.csv")

        upper_limit = numeric_amount.quantile(0.99)
        numeric_amount.clip(upper=upper_limit).plot(
            kind="hist",
            bins=50,
            figsize=(9, 5),
            title="Amount Distribution up to the 99th Percentile (Sample)",
        )
        plt.xlabel("Transaction Amount")
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "amount_distribution_p99.png", dpi=200)
        plt.close()

    identifier_rows = []
    for column in ("nameOrig", "nameDest"):
        if column in df.columns:
            unique_count = int(df[column].nunique(dropna=False))
            identifier_rows.append(
                {
                    "column": column,
                    "scope": "bounded_exploratory_sample",
                    "sample_rows": int(len(df)),
                    "unique_values": unique_count,
                    "unique_percent": round(unique_count / len(df) * 100, 8) if len(df) else 0.0,
                }
            )
    pd.DataFrame(identifier_rows).to_csv(
        OUTPUT_DIR / "identifier_cardinality.csv", index=False
    )

    df.head(1000).to_csv(OUTPUT_DIR / "sample_1000_rows.csv", index=False)

    leakage_candidates = [
        column
        for column in (
            "isFraud",
            "isFlaggedFraud",
            "newbalanceOrig",
            "newbalanceDest",
            "nameOrig",
            "nameDest",
        )
        if column in df.columns
    ]
    (OUTPUT_DIR / "leakage_candidates.json").write_text(
        json.dumps(leakage_candidates, indent=2), encoding="utf-8"
    )

    dataset_summary = {
        "source": source_description,
        "inspection_scope": inspection_scope,
        "exact_full_data_rows_if_available": int(full_scan["total_rows"]) if full_scan is not None else None,
        "exploratory_sample_rows": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "random_seed_for_streaming": args.seed,
        "sample_size_limit": args.sample_size,
        "full_scan_requested": bool(args.full_scan),
        "important_note": "Fraud labels were inspected only; they were not converted into workload labels.",
    }
    (OUTPUT_DIR / "dataset_summary.json").write_text(
        json.dumps(dataset_summary, indent=2), encoding="utf-8"
    )

    print("Inspection completed.")
    print(f"Columns: {list(df.columns)}")
    print("Candidate research inputs are documented separately in Research/notes/feature_definition_v0.1.md")
    print("Important: fraud labels were inspected only and were not used as workload labels.")


if __name__ == "__main__":
    main()
