from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import statistics
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path('/app/Research')
SCRIPT_DIR = ROOT / 'scripts'
RUNNER = SCRIPT_DIR / 'run_service_time_pilot.py'
PROCESSOR = SCRIPT_DIR / 'reference_processor.py'
DOCKERFILE = ROOT / 'Dockerfile.pilot'
SOURCE = ROOT / 'data' / 'source' / 'PS_20174392719_1491204439457_log.csv'
BASE = ROOT / 'data' / 'final_candidate_v1'
SELECTION_DIR = BASE / 'selection'
BLOCK_DIR = SELECTION_DIR / 'blocks'
RAW_DIR = BASE / 'raw'
PROCESSED_DIR = BASE / 'processed'
RESULTS = ROOT / 'results' / 'final_candidate_v1'
MASTER_SELECTION = SELECTION_DIR / 'final_candidate_v1_selected_transactions.csv'
RAW_OUTPUT = RAW_DIR / 'final_candidate_v1_service_time_runs.csv'
PROCESSED_OUTPUT = PROCESSED_DIR / 'final_candidate_v1_transaction_node_dataset.csv'
SAMPLING_MANIFEST = RESULTS / 'sampling_manifest.json'

TRANSACTION_TYPES = ('CASH_IN', 'CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER')
SELECTION_COLUMNS = [
    'transaction_id', 'source_row_index', 'step', 'type', 'amount', 'nameOrig',
    'oldbalanceOrg', 'nameDest', 'oldbalanceDest'
]
SEED = 20260829
ROWS_PER_TYPE = 200
BLOCKS = 10
ROWS_PER_TYPE_PER_BLOCK = 20
TOTAL_TRANSACTIONS = ROWS_PER_TYPE * len(TRANSACTION_TYPES)
MEASURED_RUNS = 5
WARMUPS = 2
CHUNK_SIZE = 250_000

NODE_CONFIG = {
    'low': {'label': 'Low', 'cpu_meta': 0.60, 'memory_mb': 1024},
    'medium': {'label': 'Medium', 'cpu_meta': 0.75, 'memory_mb': 2048},
    'high': {'label': 'High', 'cpu_meta': 1.00, 'memory_mb': 4096},
}

REQUIRED_SOURCE_COLUMNS = {
    'step', 'type', 'amount', 'nameOrig', 'oldbalanceOrg', 'nameDest', 'oldbalanceDest'
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        while True:
            chunk = fh.read(chunk_bytes)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def normalize_type(value: Any) -> str:
    return str(value).strip().upper().replace('-', '_')


def valid_for_reference_processor(row: pd.Series) -> bool:
    tx_type = normalize_type(row['type'])
    try:
        amount = float(row['amount'])
        old_origin = float(row['oldbalanceOrg'])
        old_dest = float(row['oldbalanceDest'])
    except (TypeError, ValueError):
        return False

    if not math.isfinite(amount) or not math.isfinite(old_origin) or not math.isfinite(old_dest):
        return False
    if amount <= 0 or old_origin < 0 or old_dest < 0:
        return False
    if tx_type in {'CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER'} and old_origin < amount:
        return False
    if tx_type == 'TRANSFER' and str(row['nameOrig']) == str(row['nameDest']):
        return False
    return bool(str(row['nameOrig']).strip()) and bool(str(row['nameDest']).strip())


def deterministic_transaction_id(source_name: str, source_row_index: int, row: pd.Series) -> str:
    identity = '|'.join([
        source_name,
        str(source_row_index),
        str(row['step']),
        normalize_type(row['type']),
        str(row['amount']),
        str(row['nameOrig']),
        str(row['nameDest']),
    ])
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'fincluster-pilot:{identity}'))


def row_record(source_row_index: int, row: pd.Series) -> dict[str, Any]:
    return {
        'transaction_id': deterministic_transaction_id(SOURCE.name, source_row_index, row),
        'source_row_index': int(source_row_index),
        'step': int(row['step']),
        'type': normalize_type(row['type']),
        'amount': float(row['amount']),
        'nameOrig': str(row['nameOrig']),
        'oldbalanceOrg': float(row['oldbalanceOrg']),
        'nameDest': str(row['nameDest']),
        'oldbalanceDest': float(row['oldbalanceDest']),
    }


def ensure_clean_prepare_targets() -> None:
    conflicts = []
    for p in [MASTER_SELECTION, SAMPLING_MANIFEST]:
        if p.exists():
            conflicts.append(p)
    if BLOCK_DIR.exists() and any(BLOCK_DIR.glob('block_*.csv')):
        conflicts.append(BLOCK_DIR)
    if conflicts:
        lines = '\n'.join(f'  - {p}' for p in conflicts)
        raise FileExistsError(
            'Final-candidate sampling outputs already exist. They will not be overwritten.\n' + lines
        )


def prepare_sample() -> int:
    print('=== FinCluster FINAL-CANDIDATE v1 sampling ===')
    print('This creates a controlled balanced benchmark sample; it is NOT yet FINAL TRAINING DATA.')
    print(f'Source: {SOURCE}')
    print(f'Seed: {SEED}')
    print(f'Sample: {TOTAL_TRANSACTIONS} transactions = {ROWS_PER_TYPE} per type')
    print(f'Blocks: {BLOCKS} x 100 transactions = {ROWS_PER_TYPE_PER_BLOCK} per type per block')

    if not SOURCE.exists():
        raise FileNotFoundError(
            f'PaySim source not found: {SOURCE}\n'
            'Place PS_20174392719_1491204439457_log.csv in Research/data/source/ first.'
        )
    for p in [RUNNER, PROCESSOR, DOCKERFILE]:
        if not p.exists():
            raise FileNotFoundError(f'Required research file not found: {p}')
    ensure_clean_prepare_targets()

    header = pd.read_csv(SOURCE, nrows=0)
    missing = REQUIRED_SOURCE_COLUMNS - set(header.columns)
    if missing:
        raise ValueError(f'PaySim source is missing required columns: {sorted(missing)}')

    reservoirs: dict[str, list[dict[str, Any]]] = {t: [] for t in TRANSACTION_TYPES}
    eligible_counts = {t: 0 for t in TRANSACTION_TYPES}
    observed_counts = {t: 0 for t in TRANSACTION_TYPES}
    rngs = {t: random.Random(SEED + (i + 1) * 100_003) for i, t in enumerate(TRANSACTION_TYPES)}

    usecols = ['step', 'type', 'amount', 'nameOrig', 'oldbalanceOrg', 'nameDest', 'oldbalanceDest']
    rows_scanned = 0

    print('Scanning PaySim once with per-type reservoir sampling...')
    for chunk_no, chunk in enumerate(pd.read_csv(SOURCE, usecols=usecols, chunksize=CHUNK_SIZE), start=1):
        rows_scanned += len(chunk)
        for source_row_index, row in chunk.iterrows():
            tx_type = normalize_type(row['type'])
            if tx_type not in reservoirs:
                continue
            observed_counts[tx_type] += 1
            if not valid_for_reference_processor(row):
                continue

            eligible_counts[tx_type] += 1
            seen = eligible_counts[tx_type]
            rec = row_record(int(source_row_index), row)
            bucket = reservoirs[tx_type]
            if len(bucket) < ROWS_PER_TYPE:
                bucket.append(rec)
            else:
                j = rngs[tx_type].randrange(seen)
                if j < ROWS_PER_TYPE:
                    bucket[j] = rec

        if chunk_no % 5 == 0:
            print(f'  scanned {rows_scanned:,} rows...', flush=True)

    shortages = {t: ROWS_PER_TYPE - len(reservoirs[t]) for t in TRANSACTION_TYPES if len(reservoirs[t]) < ROWS_PER_TYPE}
    if shortages:
        raise RuntimeError(f'Insufficient eligible rows for balanced sample: {shortages}')

    # Deterministically shuffle each type reservoir and split it across 10 blocks.
    for i, tx_type in enumerate(TRANSACTION_TYPES):
        random.Random(SEED + 900_000 + i).shuffle(reservoirs[tx_type])

    SELECTION_DIR.mkdir(parents=True, exist_ok=True)
    BLOCK_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    master_rows: list[dict[str, Any]] = []
    block_summaries = []
    for block_no in range(1, BLOCKS + 1):
        start = (block_no - 1) * ROWS_PER_TYPE_PER_BLOCK
        end = block_no * ROWS_PER_TYPE_PER_BLOCK
        by_type = {t: reservoirs[t][start:end] for t in TRANSACTION_TYPES}

        # Interleave transaction types to avoid long same-type runs inside a block.
        block_rows = []
        for occurrence in range(ROWS_PER_TYPE_PER_BLOCK):
            for tx_type in TRANSACTION_TYPES:
                block_rows.append(by_type[tx_type][occurrence])

        block_df = pd.DataFrame(block_rows, columns=SELECTION_COLUMNS)
        block_path = BLOCK_DIR / f'block_{block_no:02d}.csv'
        block_df.to_csv(block_path, index=False)

        tagged = block_df.copy()
        tagged.insert(0, 'final_block', block_no)
        master_rows.extend(tagged.to_dict(orient='records'))
        block_summaries.append({
            'block': block_no,
            'transactions': len(block_df),
            **{f'{t}_count': int((block_df['type'] == t).sum()) for t in TRANSACTION_TYPES},
        })

    master = pd.DataFrame(master_rows)
    if len(master) != TOTAL_TRANSACTIONS:
        raise AssertionError(f'Expected {TOTAL_TRANSACTIONS} master rows; found {len(master)}')
    if master['transaction_id'].nunique() != TOTAL_TRANSACTIONS:
        raise AssertionError('Selected transaction IDs are not unique.')
    counts = master['type'].value_counts().to_dict()
    expected = {t: ROWS_PER_TYPE for t in TRANSACTION_TYPES}
    if counts != expected:
        raise AssertionError(f'Type balance mismatch: {counts} != {expected}')

    master.to_csv(MASTER_SELECTION, index=False)

    sample_stats = {}
    for tx_type in TRANSACTION_TYPES:
        part = master[master['type'] == tx_type]
        sample_stats[tx_type] = {
            'count': int(len(part)),
            'amount_min': float(part['amount'].min()),
            'amount_median': float(part['amount'].median()),
            'amount_p95': float(part['amount'].quantile(0.95)),
            'amount_max': float(part['amount'].max()),
            'step_min': int(part['step'].min()),
            'step_max': int(part['step'].max()),
        }

    print('Computing SHA-256 checksums for publication/reproducibility metadata...')
    source_sha = sha256_file(SOURCE)
    processor_sha = sha256_file(PROCESSOR)
    runner_sha = sha256_file(RUNNER)
    dockerfile_sha = sha256_file(DOCKERFILE)
    selection_sha = sha256_file(MASTER_SELECTION)

    manifest = {
        'created_at_utc': utc_now(),
        'status': 'FINAL_COLLECTION_CANDIDATE_SELECTION_NOT_YET_APPROVED_AS_TRAINING_DATA',
        'sampling': {
            'method': 'deterministic per-transaction-type reservoir sampling across the full PaySim file',
            'seed': SEED,
            'total_transactions': TOTAL_TRANSACTIONS,
            'rows_per_type': ROWS_PER_TYPE,
            'blocks': BLOCKS,
            'transactions_per_block': TOTAL_TRANSACTIONS // BLOCKS,
            'rows_per_type_per_block': ROWS_PER_TYPE_PER_BLOCK,
            'within_block_order': 'interleaved CASH_IN,CASH_OUT,DEBIT,PAYMENT,TRANSFER',
            'note': 'Balanced benchmark sampling intentionally does not preserve natural PaySim transaction-type prevalence.',
        },
        'eligibility': {
            'rule': 'same validity constraints as current run_service_time_pilot.py/reference processor',
            'rows_scanned': rows_scanned,
            'observed_counts_by_type': observed_counts,
            'eligible_counts_by_type': eligible_counts,
            'selected_sample_stats_by_type': sample_stats,
        },
        'source': {
            'path': str(SOURCE),
            'size_bytes': SOURCE.stat().st_size,
            'sha256': source_sha,
        },
        'frozen_code': {
            'reference_processor_path': str(PROCESSOR),
            'reference_processor_sha256': processor_sha,
            'runner_path': str(RUNNER),
            'runner_sha256': runner_sha,
            'dockerfile_path': str(DOCKERFILE),
            'dockerfile_sha256': dockerfile_sha,
            'docker_image_tag': 'fincluster-pilot:0.3',
        },
        'measurement_protocol': {
            'processor_pipeline': 'v0.3 Rebalanced (per project evidence)',
            'cpu_period_us': 10000,
            'cpuset_cpu': '0',
            'thread_limits': {'OMP': 1, 'OPENBLAS': 1, 'MKL': 1, 'NUMEXPR': 1},
            'warmups_per_transaction_node_pair': WARMUPS,
            'measured_runs_per_transaction_node_pair': MEASURED_RUNS,
            'aggregation': 'median of successful repeated service_time_ms measurements',
            'nodes': {
                'Low': {'cpu_quota': '6000/10000', 'cpu_metadata': 0.60, 'memory_mb': 1024},
                'Medium': {'cpu_quota': '7500/10000', 'cpu_metadata': 0.75, 'memory_mb': 2048},
                'High': {'cpu_quota': '10000/10000', 'cpu_metadata': 1.00, 'memory_mb': 4096},
            },
            'node_order_policy': 'rotating by block: LMH, MHL, HLM, repeat',
            'session_plan': 'recommended two clean host sessions: blocks 1-5, restart/clean setup, blocks 6-10',
        },
        'outputs': {
            'master_selection': str(MASTER_SELECTION),
            'master_selection_sha256': selection_sha,
            'block_directory': str(BLOCK_DIR),
            'block_summaries': block_summaries,
        },
    }
    SAMPLING_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    print('\n=== SAMPLING STRUCTURAL CHECK ===')
    print(f'rows_scanned = {rows_scanned:,}')
    print(f'selected_transactions = {len(master)}')
    print(f'unique_transactions = {master["transaction_id"].nunique()}')
    print(f'type_counts = {counts}')
    print(f'blocks_written = {len(list(BLOCK_DIR.glob("block_*.csv")))}')
    print(f'source_sha256 = {source_sha}')
    print(f'selection_sha256 = {selection_sha}')
    print(f'master_selection = {MASTER_SELECTION}')
    print(f'sampling_manifest = {SAMPLING_MANIFEST}')
    print('SAMPLING_CHECK = PASS')
    return 0


def read_text(path: str) -> str:
    p = Path(path)
    try:
        return p.read_text(encoding='utf-8').strip()
    except Exception as exc:
        return f'UNAVAILABLE ({exc})'


def environment_snapshot(label: str, block: int, node: str) -> str:
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else 'N/A'
    return '\n'.join([
        f'=== FINAL-CANDIDATE ENVIRONMENT SNAPSHOT: {label} ===',
        f'utc_time = {utc_now()}',
        f'block = {block:02d}',
        f'node = {node}',
        f'os.cpu_count() = {os.cpu_count()}',
        f'sched affinity = {affinity}',
        f"OMP_NUM_THREADS = {os.getenv('OMP_NUM_THREADS')}",
        f"OPENBLAS_NUM_THREADS = {os.getenv('OPENBLAS_NUM_THREADS')}",
        f"MKL_NUM_THREADS = {os.getenv('MKL_NUM_THREADS')}",
        f"NUMEXPR_NUM_THREADS = {os.getenv('NUMEXPR_NUM_THREADS')}",
        f"docker_image_id = {os.getenv('FINCLUSTER_IMAGE_ID', 'UNKNOWN')}",
        f"cpu.max = {read_text('/sys/fs/cgroup/cpu.max')}",
        f"cpuset.cpus.effective = {read_text('/sys/fs/cgroup/cpuset.cpus.effective')}",
        f"memory.max = {read_text('/sys/fs/cgroup/memory.max')}",
        'cpu.stat:',
        read_text('/sys/fs/cgroup/cpu.stat'),
    ]) + '\n'


def node_block_already_exists(raw_path: Path, block_selection: pd.DataFrame, node_label: str) -> bool:
    if not raw_path.exists() or raw_path.stat().st_size == 0:
        return False
    existing = pd.read_csv(raw_path, usecols=['transaction_id', 'node_profile'])
    txids = set(block_selection['transaction_id'].astype(str))
    mask = (existing['node_profile'] == node_label) & existing['transaction_id'].astype(str).isin(txids)
    return bool(mask.any())


def run_node(block: int, node: str) -> int:
    if not (1 <= block <= BLOCKS):
        raise ValueError(f'block must be 1..{BLOCKS}')
    if node not in NODE_CONFIG:
        raise ValueError(f'Unknown node: {node}')
    for p in [RUNNER, PROCESSOR, MASTER_SELECTION, SAMPLING_MANIFEST]:
        if not p.exists():
            raise FileNotFoundError(f'Required file not found: {p}. Run "final.ps1 prepare" first if needed.')

    block_path = BLOCK_DIR / f'block_{block:02d}.csv'
    if not block_path.exists():
        raise FileNotFoundError(f'Block selection missing: {block_path}')
    selection = pd.read_csv(block_path)
    if len(selection) != 100 or selection['transaction_id'].nunique() != 100:
        raise ValueError(f'{block_path.name} is not a valid 100-transaction block.')
    type_counts = selection['type'].value_counts().to_dict()
    expected_types = {t: ROWS_PER_TYPE_PER_BLOCK for t in TRANSACTION_TYPES}
    if type_counts != expected_types:
        raise ValueError(f'{block_path.name} type counts {type_counts}; expected {expected_types}')

    cfg = NODE_CONFIG[node]
    if node_block_already_exists(RAW_OUTPUT, selection, cfg['label']):
        raise FileExistsError(
            f'Raw evidence already contains block {block:02d} / node {cfg["label"]}. '
            'This tool will not overwrite it.'
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    run_dir = RESULTS / 'collection' / f'block_{block:02d}' / f'node_{node}'
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshot = run_dir / 'environment_snapshot.txt'

    before = environment_snapshot('BEFORE', block, node)
    snapshot.write_text(before, encoding='utf-8')
    print(before, flush=True)

    cmd = [
        sys.executable, str(RUNNER),
        '--node-profile', node,
        '--cpu-limit', str(cfg['cpu_meta']),
        '--memory-mb', str(cfg['memory_mb']),
        '--warmups', str(WARMUPS),
        '--measured-runs', str(MEASURED_RUNS),
        '--rows-per-type', str(ROWS_PER_TYPE_PER_BLOCK),
        '--selection-file', str(block_path),
        '--raw-output', str(RAW_OUTPUT),
        '--processed-output', str(PROCESSED_OUTPUT),
        '--results-dir', str(run_dir),
    ]

    print('=== RUNNER COMMAND (inside pinned container) ===', flush=True)
    print(' '.join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd='/app')

    after = environment_snapshot('AFTER', block, node)
    with snapshot.open('a', encoding='utf-8') as fh:
        fh.write('\n' + after)
        fh.write(f'runner_exit_code = {completed.returncode}\n')
    print(after, flush=True)
    print(f'runner_exit_code = {completed.returncode}', flush=True)
    if completed.returncode != 0:
        return completed.returncode

    raw = pd.read_csv(RAW_OUTPUT)
    txids = set(selection['transaction_id'].astype(str))
    subset = raw[(raw['node_profile'] == cfg['label']) & raw['transaction_id'].astype(str).isin(txids)].copy()
    success = subset[subset['status'] == 'SUCCESS']
    counts = success.groupby('transaction_id').size()

    print('=== BLOCK/NODE STRUCTURAL CHECK ===')
    print(f'block = {block:02d}')
    print(f'node = {cfg["label"]}')
    print(f'raw_rows_for_block_node = {len(subset)}')
    print(f'successful_rows_for_block_node = {len(success)}')
    print(f'unique_transactions = {success["transaction_id"].nunique()}')
    ok = (
        len(subset) == 500 and len(success) == 500 and
        success['transaction_id'].nunique() == 100 and len(counts) == 100 and (counts == MEASURED_RUNS).all()
    )
    print('STRUCTURAL_CHECK = ' + ('PASS' if ok else 'FAIL'))
    print(f'cumulative_raw_rows = {len(raw)}')
    print(f'raw_output = {RAW_OUTPUT}')
    print(f'processed_output = {PROCESSED_OUTPUT}')
    print(f'environment_snapshot = {snapshot}')
    return 0 if ok else 3


def audit() -> int:
    print('=== FinCluster FINAL-CANDIDATE v1 collection audit ===')
    if not RAW_OUTPUT.exists():
        raise FileNotFoundError(f'Raw final-candidate file not found: {RAW_OUTPUT}')
    if not PROCESSED_OUTPUT.exists():
        raise FileNotFoundError(f'Processed final-candidate file not found: {PROCESSED_OUTPUT}')
    if not MASTER_SELECTION.exists():
        raise FileNotFoundError(f'Master selection not found: {MASTER_SELECTION}')

    raw = pd.read_csv(RAW_OUTPUT)
    processed = pd.read_csv(PROCESSED_OUTPUT)
    selection = pd.read_csv(MASTER_SELECTION)

    expected_raw = TOTAL_TRANSACTIONS * 3 * MEASURED_RUNS
    expected_processed = TOTAL_TRANSACTIONS * 3
    success = raw[raw['status'] == 'SUCCESS'].copy()

    structural = {
        'expected_raw_rows': expected_raw,
        'raw_rows': int(len(raw)),
        'successful_raw_rows': int(len(success)),
        'failed_raw_rows': int(len(raw) - len(success)),
        'expected_processed_rows': expected_processed,
        'processed_rows': int(len(processed)),
        'selection_transactions': int(selection['transaction_id'].nunique()),
        'raw_transactions': int(success['transaction_id'].nunique()),
        'processed_transactions': int(processed['transaction_id'].nunique()),
    }

    pair_counts = success.groupby(['transaction_id', 'node_profile']).size().rename('runs').reset_index()
    tx_node_counts = processed.groupby('transaction_id')['node_profile'].nunique().rename('nodes').reset_index()
    expected_node_set = {'Low', 'Medium', 'High'}
    present_node_set = set(processed['node_profile'].dropna().unique())

    structural_pass = (
        len(raw) == expected_raw and
        len(success) == expected_raw and
        len(processed) == expected_processed and
        success['transaction_id'].nunique() == TOTAL_TRANSACTIONS and
        processed['transaction_id'].nunique() == TOTAL_TRANSACTIONS and
        len(pair_counts) == expected_processed and
        (pair_counts['runs'] == MEASURED_RUNS).all() and
        len(tx_node_counts) == TOTAL_TRANSACTIONS and
        (tx_node_counts['nodes'] == 3).all() and
        present_node_set == expected_node_set
    )

    # Within-pair CV diagnostics from raw repetitions.
    grouped = success.groupby(['transaction_id', 'node_profile'])['service_time_ms']
    pair_stats = grouped.agg(['median', 'mean', 'std', 'min', 'max', 'count']).reset_index()
    pair_stats['cv_pct'] = pair_stats['std'] / pair_stats['mean'] * 100.0
    cv_summary = pair_stats.groupby('node_profile')['cv_pct'].agg(['median', 'mean', 'max']).reset_index()
    gt10 = pair_stats.assign(gt10=pair_stats['cv_pct'] > 10).groupby('node_profile')['gt10'].sum().reset_index(name='pairs_cv_gt_10')
    cv_summary = cv_summary.merge(gt10, on='node_profile')

    # Node-ordering diagnostic using processed median targets.
    pivot = processed.pivot(index='transaction_id', columns='node_profile', values='service_time_ms')
    pivot['expected_order'] = (pivot['Low'] > pivot['Medium']) & (pivot['Medium'] > pivot['High'])
    order_count = int(pivot['expected_order'].sum())

    # Map transaction -> randomized collection block.
    tx_to_block = selection[['transaction_id', 'final_block']].copy()
    processed_block = processed.merge(tx_to_block, on='transaction_id', how='left', validate='many_to_one')
    block_node = processed_block.groupby(['final_block', 'node_profile'])['service_time_ms'].agg(['count', 'median', 'mean']).reset_index()
    type_node = processed.groupby(['type', 'node_profile'])['service_time_ms'].agg(['count', 'median', 'mean']).reset_index()

    out_dir = RESULTS / 'audit'
    out_dir.mkdir(parents=True, exist_ok=True)
    pair_stats.to_csv(out_dir / 'pair_repeat_stability.csv', index=False)
    cv_summary.to_csv(out_dir / 'cv_summary_by_node.csv', index=False)
    pivot.reset_index().to_csv(out_dir / 'node_ordering_by_transaction.csv', index=False)
    block_node.to_csv(out_dir / 'block_node_service_time_summary.csv', index=False)
    type_node.to_csv(out_dir / 'type_node_service_time_summary.csv', index=False)

    summary = {
        'created_at_utc': utc_now(),
        'status': 'FINAL_COLLECTION_CANDIDATE_AUDIT',
        'structural': structural,
        'structural_pass': bool(structural_pass),
        'expected_node_order_transactions': order_count,
        'total_transactions': TOTAL_TRANSACTIONS,
        'expected_node_order_fraction': order_count / TOTAL_TRANSACTIONS,
        'note': (
            'This audit does not automatically promote the dataset to FINAL TRAINING DATA. '
            'CV, block effects, outliers, feature distributions, provenance, and methodology must be reviewed before approval.'
        ),
    }
    (out_dir / 'audit_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print('\n=== STRUCTURAL AUDIT ===')
    for k, v in structural.items():
        print(f'{k} = {v}')
    print('STRUCTURAL_AUDIT = ' + ('PASS' if structural_pass else 'FAIL'))
    print('\n=== WITHIN-PAIR CV DIAGNOSTIC ===')
    print(cv_summary.to_string(index=False, float_format=lambda x: f'{x:.3f}'))
    print('\n=== NODE ORDERING DIAGNOSTIC ===')
    print(f'Low > Medium > High = {order_count}/{TOTAL_TRANSACTIONS} transactions')
    print(f'Audit outputs = {out_dir}')
    print('DATASET_STATUS = CANDIDATE_ONLY_NOT_YET_APPROVED_AS_FINAL_TRAINING_DATA')
    return 0 if structural_pass else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='FinCluster final-candidate v1 helper.')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare')
    rp = sub.add_parser('run-node')
    rp.add_argument('--block', type=int, required=True)
    rp.add_argument('--node', choices=('low', 'medium', 'high'), required=True)
    sub.add_parser('audit')
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == 'prepare':
        return prepare_sample()
    if args.command == 'run-node':
        return run_node(args.block, args.node)
    return audit()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'FINAL-CANDIDATE ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
