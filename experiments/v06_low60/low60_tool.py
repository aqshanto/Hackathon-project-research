from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path('/app/Research')
RAW_DIR = ROOT / 'data' / 'raw'
PROCESSED_DIR = ROOT / 'data' / 'processed'
RESULTS_DIR = ROOT / 'results'
SELECTION = RAW_DIR / 'validation_v05_selected_transactions.csv'
RUNNER = ROOT / 'scripts' / 'run_service_time_pilot.py'


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: str) -> str:
    p = Path(path)
    try:
        return p.read_text(encoding='utf-8').strip()
    except Exception as exc:
        return f'UNAVAILABLE ({exc})'


def environment_snapshot(label: str) -> str:
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else 'N/A'
    parts = [
        f'=== LOW60 ENVIRONMENT SNAPSHOT: {label} ===',
        f'utc_time = {utc_now()}',
        f'os.cpu_count() = {os.cpu_count()}',
        f'sched affinity = {affinity}',
        f"OMP_NUM_THREADS = {os.getenv('OMP_NUM_THREADS')}",
        f"OPENBLAS_NUM_THREADS = {os.getenv('OPENBLAS_NUM_THREADS')}",
        f"MKL_NUM_THREADS = {os.getenv('MKL_NUM_THREADS')}",
        f"NUMEXPR_NUM_THREADS = {os.getenv('NUMEXPR_NUM_THREADS')}",
        f"cpu.max = {read_text('/sys/fs/cgroup/cpu.max')}",
        f"cpuset.cpus.effective = {read_text('/sys/fs/cgroup/cpuset.cpus.effective')}",
        f"memory.max = {read_text('/sys/fs/cgroup/memory.max')}",
        'cpu.stat:',
        read_text('/sys/fs/cgroup/cpu.stat'),
    ]
    return '\n'.join(parts) + '\n'


def run_experiment(args: argparse.Namespace) -> int:
    batch = args.batch.lower()
    tag = f'v06_low60_{batch}'

    required = [RUNNER, ROOT / 'scripts' / 'reference_processor.py', SELECTION]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f'Required file not found: {path}')

    raw = RAW_DIR / f'{tag}_service_time_runs.csv'
    processed = PROCESSED_DIR / f'{tag}_transaction_node_dataset.csv'
    results = RESULTS_DIR / tag
    snapshot = results / 'environment_snapshot.txt'

    if raw.exists() and raw.stat().st_size > 0:
        raise FileExistsError(
            f'Raw output already exists: {raw}\n'
            'This script will not overwrite research evidence. Ask before rerunning this batch.'
        )

    results.mkdir(parents=True, exist_ok=True)
    before = environment_snapshot('BEFORE')
    snapshot.write_text(before, encoding='utf-8')
    print(before, flush=True)

    # The existing runner uses the logical node label "low". The actual 60% CPU
    # capacity is externally enforced by Docker and recorded via --cpu-limit 0.60.
    cmd = [
        sys.executable,
        str(RUNNER),
        '--node-profile', 'low',
        '--cpu-limit', str(args.cpu_meta),
        '--memory-mb', str(args.memory_mb),
        '--warmups', '2',
        '--measured-runs', '5',
        '--rows-per-type', '2',
        '--selection-file', str(SELECTION),
        '--raw-output', str(raw),
        '--processed-output', str(processed),
        '--results-dir', str(results),
    ]

    print('=== RUNNER COMMAND (inside pinned container) ===', flush=True)
    print(' '.join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd='/app')

    after = environment_snapshot('AFTER')
    with snapshot.open('a', encoding='utf-8') as fh:
        fh.write('\n' + after)
        fh.write(f'runner_exit_code = {completed.returncode}\n')
    print(after, flush=True)
    print(f'runner_exit_code = {completed.returncode}', flush=True)

    if completed.returncode != 0:
        return completed.returncode

    df = pd.read_csv(raw)
    success = df[df['status'] == 'SUCCESS']
    print('=== STRUCTURAL CHECK ===')
    print(f'raw_rows = {len(df)}')
    print(f'successful_rows = {len(success)}')
    print(f'unique_transactions = {success["transaction_id"].nunique()}')
    if len(df) != 50 or len(success) != 50 or success['transaction_id'].nunique() != 10:
        print('STRUCTURAL_CHECK = FAIL', file=sys.stderr)
        return 3
    counts = success.groupby('transaction_id').size()
    if not (counts == 5).all():
        print(f'STRUCTURAL_CHECK = FAIL; repetition counts = {sorted(counts.unique().tolist())}', file=sys.stderr)
        return 3
    print('STRUCTURAL_CHECK = PASS')
    print(f'raw_output = {raw}')
    print(f'processed_output = {processed}')
    print(f'environment_snapshot = {snapshot}')
    return 0


def load_raw(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f'Missing required file: {path}')
    df = pd.read_csv(path)
    required = {'transaction_id', 'status', 'service_time_ms', 'repetition'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'{path.name} missing columns: {sorted(missing)}')
    return df


def per_tx_stats(df: pd.DataFrame, label: str):
    success = df[df['status'] == 'SUCCESS'].copy()
    if len(df) != 50 or len(success) != 50:
        raise ValueError(f'{label}: expected 50 raw and 50 successful rows; got {len(df)} / {len(success)}')
    counts = success.groupby('transaction_id').size()
    if len(counts) != 10 or not (counts == 5).all():
        raise ValueError(f'{label}: expected 10 transactions x 5 measured runs')
    grouped = success.groupby('transaction_id')['service_time_ms']
    out = pd.DataFrame({
        'median_ms': grouped.median(),
        'mean_ms': grouped.mean(),
        'std_ms': grouped.std(ddof=1),
    })
    out['cv_pct'] = out['std_ms'] / out['mean_ms'] * 100.0
    return out.reset_index()


def summarize_batch(per_tx: pd.DataFrame, batch: str) -> dict:
    return {
        'profile': 'low60',
        'batch': batch,
        'median_within_batch_cv_pct': float(per_tx['cv_pct'].median()),
        'mean_within_batch_cv_pct': float(per_tx['cv_pct'].mean()),
        'max_within_batch_cv_pct': float(per_tx['cv_pct'].max()),
        'pairs_cv_gt_10': int((per_tx['cv_pct'] > 10).sum()),
    }


def analyze() -> int:
    out_dir = RESULTS_DIR / 'v06_low60_analysis'
    out_dir.mkdir(parents=True, exist_ok=True)

    a = per_tx_stats(load_raw(RAW_DIR / 'v06_low60_a_service_time_runs.csv'), 'Low60 A')
    b = per_tx_stats(load_raw(RAW_DIR / 'v06_low60_b_service_time_runs.csv'), 'Low60 B')
    if set(a['transaction_id']) != set(b['transaction_id']):
        raise ValueError('Low60 Batch A and B transaction IDs do not match exactly.')

    batch_df = pd.DataFrame([summarize_batch(a, 'A'), summarize_batch(b, 'B')])

    pairs = a[['transaction_id', 'median_ms', 'cv_pct']].merge(
        b[['transaction_id', 'median_ms', 'cv_pct']],
        on='transaction_id', suffixes=('_A', '_B'), validate='one_to_one'
    )
    pairs['signed_diff_pct'] = (pairs['median_ms_B'] - pairs['median_ms_A']) / pairs['median_ms_A'] * 100.0
    pairs['abs_diff_pct'] = pairs['signed_diff_pct'].abs()

    median_abs = float(pairs['abs_diff_pct'].median())
    gt10 = int((pairs['abs_diff_pct'] > 10).sum())
    passed = median_abs <= 5.0 and gt10 <= 2

    repro = pd.DataFrame([{
        'profile': 'low60',
        'median_abs_A_B_diff_pct': median_abs,
        'mean_abs_A_B_diff_pct': float(pairs['abs_diff_pct'].mean()),
        'max_abs_A_B_diff_pct': float(pairs['abs_diff_pct'].max()),
        'pairs_abs_diff_gt_10': gt10,
        'median_signed_A_to_B_diff_pct': float(pairs['signed_diff_pct'].median()),
        'working_gate_median_le_5': median_abs <= 5.0,
        'working_gate_pairs_gt10_le_2': gt10 <= 2,
        'working_gate_PASS': passed,
    }])

    batch_df.to_csv(out_dir / 'low60_batch_stability_summary.csv', index=False)
    repro.to_csv(out_dir / 'low60_reproducibility_summary.csv', index=False)
    pairs.to_csv(out_dir / 'low60_pairwise_A_B_details.csv', index=False)

    print('\n=== LOW60 WITHIN-BATCH STABILITY ===')
    print(batch_df.to_string(index=False, float_format=lambda x: f'{x:.3f}'))
    print('\n=== LOW60 A/B REPRODUIBILITY ===')
    print(repro.to_string(index=False, float_format=lambda x: f'{x:.3f}'))

    # Diagnostic ordering check against already completed v0.6 Medium75 and High100.
    order_rows = []
    for batch in ('a', 'b'):
        med_path = RAW_DIR / f'v06_pinned_medium_{batch}_service_time_runs.csv'
        high_path = RAW_DIR / f'v06_pinned_high_{batch}_service_time_runs.csv'
        if med_path.exists() and high_path.exists():
            low = a if batch == 'a' else b
            med = per_tx_stats(load_raw(med_path), f'Medium {batch.upper()}')
            high = per_tx_stats(load_raw(high_path), f'High {batch.upper()}')
            merged = low[['transaction_id', 'median_ms']].rename(columns={'median_ms':'low60_ms'})
            merged = merged.merge(med[['transaction_id','median_ms']].rename(columns={'median_ms':'medium75_ms'}), on='transaction_id')
            merged = merged.merge(high[['transaction_id','median_ms']].rename(columns={'median_ms':'high100_ms'}), on='transaction_id')
            merged['expected_order_low_gt_medium_gt_high'] = (
                (merged['low60_ms'] > merged['medium75_ms']) &
                (merged['medium75_ms'] > merged['high100_ms'])
            )
            merged.insert(0, 'batch', batch.upper())
            order_rows.append(merged)
            print(f'\nOrdering diagnostic Batch {batch.upper()}: '
                  f'{int(merged["expected_order_low_gt_medium_gt_high"].sum())}/10 transactions satisfy Low60 > Medium75 > High100')

    if order_rows:
        pd.concat(order_rows, ignore_index=True).to_csv(out_dir / 'low60_medium75_high100_ordering.csv', index=False)

    print('\n=== WORKING DECISION GATE ===')
    print('Criterion: median absolute A/B difference <= 5% AND <= 2/10 pairs above 10%.')
    print('LOW60:', 'PASS' if passed else 'FAIL')
    print(f'CSV outputs: {out_dir}')
    return 0 if passed else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='FinCluster Low60 candidate helper.')
    sub = p.add_subparsers(dest='command', required=True)
    rp = sub.add_parser('run')
    rp.add_argument('--batch', choices=('A','B','a','b'), required=True)
    rp.add_argument('--cpu-meta', type=float, required=True)
    rp.add_argument('--memory-mb', type=int, required=True)
    sub.add_parser('analyze')
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == 'run':
        return run_experiment(args)
    return analyze()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'LOW60 ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
