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

NODES = ('low', 'medium', 'high')


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
        f'=== V0.6 ENVIRONMENT SNAPSHOT: {label} ===',
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
    node = args.node.lower()
    batch = args.batch.lower()
    tag = f'v06_pinned_{node}_{batch}'

    required = [RUNNER, ROOT / 'scripts' / 'reference_processor.py', SELECTION]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f'Required file not found: {path}')

    raw = RAW_DIR / f'{tag}_service_time_runs.csv'
    processed = PROCESSED_DIR / f'{tag}_transaction_node_dataset.csv'
    results = RESULTS_DIR / tag
    snapshot = results / 'environment_snapshot.txt'

    # Evidence-preservation guard: never silently overwrite a completed/raw batch.
    if raw.exists() and raw.stat().st_size > 0:
        raise FileExistsError(
            f'Raw output already exists: {raw}\n'
            'This script will not overwrite research evidence. Ask before rerunning this batch.'
        )

    results.mkdir(parents=True, exist_ok=True)
    before = environment_snapshot('BEFORE')
    snapshot.write_text(before, encoding='utf-8')
    print(before, flush=True)

    cmd = [
        sys.executable,
        str(RUNNER),
        '--node-profile', node,
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

    # Immediate structural sanity check.
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


def load_raw(node: str, batch: str) -> pd.DataFrame:
    path = RAW_DIR / f'v06_pinned_{node}_{batch}_service_time_runs.csv'
    if not path.exists():
        raise FileNotFoundError(f'Missing required file: {path}')
    df = pd.read_csv(path)
    required = {'transaction_id', 'status', 'service_time_ms', 'repetition'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'{path.name} missing columns: {sorted(missing)}')
    return df


def batch_stats(df: pd.DataFrame, node: str, batch: str):
    success = df[df['status'] == 'SUCCESS'].copy()
    if len(df) != 50:
        raise ValueError(f'{node} Batch {batch.upper()}: expected 50 raw rows, found {len(df)}')
    if len(success) != 50:
        raise ValueError(f'{node} Batch {batch.upper()}: expected 50 successful rows, found {len(success)}')

    counts = success.groupby('transaction_id').size()
    if len(counts) != 10 or not (counts == 5).all():
        raise ValueError(
            f'{node} Batch {batch.upper()}: expected 10 transactions x 5 measured runs; '
            f'found {len(counts)} transaction groups with counts {sorted(counts.unique().tolist())}'
        )

    grouped = success.groupby('transaction_id')['service_time_ms']
    per_tx = pd.DataFrame({
        'median_ms': grouped.median(),
        'mean_ms': grouped.mean(),
        'std_ms': grouped.std(ddof=1),
    })
    per_tx['cv_pct'] = per_tx['std_ms'] / per_tx['mean_ms'] * 100.0
    per_tx = per_tx.reset_index()

    return per_tx, {
        'node': node,
        'batch': batch.upper(),
        'raw_rows': len(df),
        'successful_rows': len(success),
        'median_within_batch_cv_pct': per_tx['cv_pct'].median(),
        'mean_within_batch_cv_pct': per_tx['cv_pct'].mean(),
        'max_within_batch_cv_pct': per_tx['cv_pct'].max(),
        'pairs_cv_gt_10': int((per_tx['cv_pct'] > 10).sum()),
    }


def analyze() -> int:
    out_dir = RESULTS_DIR / 'v06_pinned_analysis'
    out_dir.mkdir(parents=True, exist_ok=True)

    batch_summary = []
    repro_summary = []
    pair_tables = []

    for node in NODES:
        raw_a = load_raw(node, 'a')
        raw_b = load_raw(node, 'b')
        a, stats_a = batch_stats(raw_a, node, 'a')
        b, stats_b = batch_stats(raw_b, node, 'b')
        batch_summary.extend([stats_a, stats_b])

        if set(a['transaction_id']) != set(b['transaction_id']):
            raise ValueError(f'{node}: Batch A and B transaction IDs do not match exactly.')

        pairs = a[['transaction_id', 'median_ms', 'cv_pct']].merge(
            b[['transaction_id', 'median_ms', 'cv_pct']],
            on='transaction_id',
            suffixes=('_A', '_B'),
            validate='one_to_one',
        )
        pairs['signed_diff_pct'] = (
            (pairs['median_ms_B'] - pairs['median_ms_A']) / pairs['median_ms_A'] * 100.0
        )
        pairs['abs_diff_pct'] = pairs['signed_diff_pct'].abs()
        pairs.insert(0, 'node', node)
        pair_tables.append(pairs)

        median_abs = float(pairs['abs_diff_pct'].median())
        gt10 = int((pairs['abs_diff_pct'] > 10).sum())
        passed = median_abs <= 5.0 and gt10 <= 2

        repro_summary.append({
            'node': node,
            'median_abs_A_B_diff_pct': median_abs,
            'mean_abs_A_B_diff_pct': float(pairs['abs_diff_pct'].mean()),
            'max_abs_A_B_diff_pct': float(pairs['abs_diff_pct'].max()),
            'pairs_abs_diff_gt_10': gt10,
            'median_signed_A_to_B_diff_pct': float(pairs['signed_diff_pct'].median()),
            'working_gate_median_le_5': median_abs <= 5.0,
            'working_gate_pairs_gt10_le_2': gt10 <= 2,
            'working_gate_PASS': passed,
        })

    batch_df = pd.DataFrame(batch_summary)
    repro_df = pd.DataFrame(repro_summary)
    pairs_df = pd.concat(pair_tables, ignore_index=True)

    batch_df.to_csv(out_dir / 'v06_batch_stability_summary.csv', index=False)
    repro_df.to_csv(out_dir / 'v06_reproducibility_summary.csv', index=False)
    pairs_df.to_csv(out_dir / 'v06_pairwise_A_B_details.csv', index=False)

    print('\n=== V0.6 WITHIN-BATCH STABILITY ===')
    print(batch_df.to_string(index=False, float_format=lambda x: f'{x:.3f}'))
    print('\n=== V0.6 A/B REPRODUCIBILITY ===')
    print(repro_df.to_string(index=False, float_format=lambda x: f'{x:.3f}'))

    overall = bool(repro_df['working_gate_PASS'].all())
    print('\n=== WORKING DECISION GATE ===')
    print('Criterion: median absolute A/B difference <= 5% AND <= 2/10 pairs above 10% per node.')
    print('OVERALL:', 'PASS' if overall else 'FAIL')
    print(f'CSV outputs: {out_dir}')
    return 0 if overall else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='FinCluster v0.6 pinned-CPU run/analyze helper.')
    sub = parser.add_subparsers(dest='command', required=True)

    run_p = sub.add_parser('run')
    run_p.add_argument('--node', choices=NODES, required=True)
    run_p.add_argument('--batch', choices=('A', 'B', 'a', 'b'), required=True)
    run_p.add_argument('--cpu-meta', type=float, required=True)
    run_p.add_argument('--memory-mb', type=int, required=True)

    sub.add_parser('analyze')
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == 'run':
        return run_experiment(args)
    return analyze()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'V0.6 ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
