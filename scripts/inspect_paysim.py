"""Initial PaySim-style dataset inspection.

This script performs exploratory inspection only. It does not train a model
and does not convert fraud labels into workload labels.

Run from the project directory:
    python Research/scripts/inspect_paysim.py

Optional environment variables:
    PAYSIM_DATASET_ID=<Hugging Face dataset ID>
    PAYSIM_SPLIT=train
    PAYSIM_SAMPLE_SIZE=100000
    PAYSIM_RANDOM_SEED=42
    PAYSIM_LOCAL_FILE=/path/to/local.csv-or-parquet
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_DATASET_ID: Final[str] = (
    "purulalwani/Synthetic-Financial-Datasets-For-Fraud-Detection"
)
DATASET_ID = os.getenv("PAYSIM_DATASET_ID", DEFAULT_DATASET_ID)
SPLIT = os.getenv("PAYSIM_SPLIT", "train")
SAMPLE_SIZE = int(os.getenv("PAYSIM_SAMPLE_SIZE", "100000"))
RANDOM_SEED = int(os.getenv("PAYSIM_RANDOM_SEED", "42"))
LOCAL_FILE = os.getenv("PAYSIM_LOCAL_FILE")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "Research" / "results" / "paysim_inspection"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_local_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, nrows=SAMPLE_SIZE)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path).head(SAMPLE_SIZE)
    raise ValueError(f"Unsupported local file type: {suffix}")


def load_huggingface_sample() -> pd.DataFrame:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "The 'datasets' package is required. Install Research/requirements_research.txt."
        ) from exc

    stream = load_dataset(DATASET_ID, split=SPLIT, streaming=True)
    stream = stream.shuffle(seed=RANDOM_SEED, buffer_size=max(SAMPLE_SIZE * 2, 10000))
    rows = list(stream.take(SAMPLE_SIZE))
    if not rows:
        raise RuntimeError("No rows were returned by the selected dataset and split.")
    return pd.DataFrame(rows)


def save_plot(series: pd.Series, title: str, xlabel: str, filename: str) -> None:
    ax = series.plot(kind="bar", figsize=(8, 5), title=title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=200)
    plt.close()


def main() -> None:
    print("PaySim inspection only - no model training will be performed.")
    print(f"Output directory: {OUTPUT_DIR}")

    if LOCAL_FILE:
        source = Path(LOCAL_FILE).expanduser().resolve()
        print(f"Loading local file: {source}")
        df = load_local_file(source)
        source_description = str(source)
    else:
        print(f"Streaming dataset: {DATASET_ID} [{SPLIT}]")
        df = load_huggingface_sample()
        source_description = f"hf://{DATASET_ID}/{SPLIT}"

    print(f"Loaded sample shape: {df.shape}")

    schema = pd.DataFrame(
        {"column": df.columns, "dtype": [str(dtype) for dtype in df.dtypes]}
    )
    schema.to_csv(OUTPUT_DIR / "schema.csv", index=False)

    missing = pd.DataFrame(
        {
            "missing_count": df.isna().sum(),
            "missing_percent": (df.isna().mean() * 100).round(6),
        }
    ).sort_values("missing_count", ascending=False)
    missing.to_csv(OUTPUT_DIR / "missing_values.csv")

    duplicate_count = int(df.duplicated().sum())
    duplicate_summary = {
        "source": source_description,
        "sample_rows": int(len(df)),
        "duplicate_rows": duplicate_count,
        "duplicate_percent": round(
            (duplicate_count / len(df) * 100) if len(df) else 0.0, 6
        ),
        "random_seed": RANDOM_SEED,
    }
    (OUTPUT_DIR / "duplicate_summary.json").write_text(
        json.dumps(duplicate_summary, indent=2), encoding="utf-8"
    )

    if "type" in df.columns:
        type_counts = df["type"].value_counts(dropna=False)
        type_distribution = pd.DataFrame(
            {
                "count": type_counts,
                "percent": (type_counts / len(df) * 100).round(6),
            }
        )
        type_distribution.to_csv(OUTPUT_DIR / "transaction_type_distribution.csv")
        save_plot(
            type_counts,
            "Transaction Type Distribution",
            "Transaction Type",
            "transaction_type_distribution.png",
        )

    if "isFraud" in df.columns:
        fraud_counts = df["isFraud"].value_counts(dropna=False)
        fraud_distribution = pd.DataFrame(
            {
                "count": fraud_counts,
                "percent": (fraud_counts / len(df) * 100).round(8),
            }
        )
        fraud_distribution.to_csv(OUTPUT_DIR / "fraud_distribution.csv")
        save_plot(
            fraud_counts,
            "Fraud Label Distribution",
            "isFraud",
            "fraud_distribution.png",
        )

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
            title="Amount Distribution up to the 99th Percentile",
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
                    "unique_values": unique_count,
                    "unique_percent": round(unique_count / len(df) * 100, 6),
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

    print("Inspection completed.")
    print("Important: fraud labels were inspected only and were not used as workload labels.")


if __name__ == "__main__":
    main()
