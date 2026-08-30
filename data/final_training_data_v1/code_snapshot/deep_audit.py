from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path('/app/Research')
BASE = ROOT / 'data' / 'final_candidate_v1'
RAW = BASE / 'raw' / 'final_candidate_v1_service_time_runs.csv'
PROCESSED = BASE / 'processed' / 'final_candidate_v1_transaction_node_dataset.csv'
SELECTION = BASE / 'selection' / 'final_candidate_v1_selected_transactions.csv'
OUT = ROOT / 'results' / 'final_candidate_v1' / 'deep_audit'

EXPECTED_NODES = ['Low', 'Medium', 'High']


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def q(s: pd.Series, p: float) -> float:
    return float(s.quantile(p))


def mad(series: pd.Series) -> float:
    med = float(series.median())
    return float((series - med).abs().median())


def robust_z(group: pd.Series) -> pd.Series:
    med = float(group.median())
    m = mad(group)
    if m == 0:
        return pd.Series(0.0, index=group.index)
    return 0.67448975 * (group - med) / m


def main() -> int:
    for p in (RAW, PROCESSED, SELECTION):
        if not p.exists():
            raise FileNotFoundError(f'Required file not found: {p}')

    OUT.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(RAW)
    processed = pd.read_csv(PROCESSED)
    selection = pd.read_csv(SELECTION)
    success = raw[raw['status'] == 'SUCCESS'].copy()

    tx_block = selection[['transaction_id', 'final_block']].copy()
    tx_block['transaction_id'] = tx_block['transaction_id'].astype(str)
    for df in (success, processed):
        df['transaction_id'] = df['transaction_id'].astype(str)

    success = success.merge(tx_block, on='transaction_id', how='left', validate='many_to_one')
    processed = processed.merge(tx_block, on='transaction_id', how='left', validate='many_to_one')

    # 1) Repeat stability / CV localization.
    pair = (success.groupby(['transaction_id','node_profile','type','final_block'])['service_time_ms']
            .agg(['count','median','mean','std','min','max']).reset_index())
    pair['cv_pct'] = pair['std'] / pair['mean'] * 100.0
    pair['range_pct_of_median'] = (pair['max'] - pair['min']) / pair['median'] * 100.0

    cv_by_node = pair.groupby('node_profile')['cv_pct'].agg(
        count='count', median='median', mean='mean', max='max'
    ).reset_index()
    extra = []
    for node, g in pair.groupby('node_profile'):
        s = g['cv_pct']
        extra.append({
            'node_profile': node,
            'p90': q(s, .90), 'p95': q(s, .95), 'p99': q(s, .99),
            'pairs_cv_gt_10': int((s > 10).sum()),
            'pairs_cv_gt_15': int((s > 15).sum()),
            'pairs_cv_gt_20': int((s > 20).sum()),
        })
    cv_by_node = cv_by_node.merge(pd.DataFrame(extra), on='node_profile')

    cv_block = (pair.assign(cv_gt10=pair['cv_pct'] > 10)
                .groupby(['final_block','node_profile'])
                .agg(pairs=('transaction_id','count'), median_cv_pct=('cv_pct','median'),
                     mean_cv_pct=('cv_pct','mean'), max_cv_pct=('cv_pct','max'),
                     pairs_cv_gt_10=('cv_gt10','sum')).reset_index())
    cv_type = (pair.assign(cv_gt10=pair['cv_pct'] > 10)
               .groupby(['type','node_profile'])
               .agg(pairs=('transaction_id','count'), median_cv_pct=('cv_pct','median'),
                    mean_cv_pct=('cv_pct','mean'), max_cv_pct=('cv_pct','max'),
                    pairs_cv_gt_10=('cv_gt10','sum')).reset_index())

    # 2) Block drift normalized by type+node to reduce transaction-type composition effects.
    baselines = (processed.groupby(['type','node_profile'])['service_time_ms']
                 .median().rename('type_node_global_median').reset_index())
    norm = processed.merge(baselines, on=['type','node_profile'], how='left', validate='many_to_one')
    norm['normalized_ratio'] = norm['service_time_ms'] / norm['type_node_global_median']
    norm['normalized_deviation_pct'] = (norm['normalized_ratio'] - 1.0) * 100.0

    block_node = (norm.groupby(['final_block','node_profile'])['normalized_deviation_pct']
                  .agg(['count','median','mean','min','max']).reset_index())
    block_overall = (norm.groupby('final_block')['normalized_deviation_pct']
                     .agg(['count','median','mean','min','max']).reset_index())

    # Actual collection sessions reported in the conversation: block 1 before restart;
    # blocks 2-10 after restart. This is descriptive only, not a causal experiment.
    norm['actual_session'] = norm['final_block'].map(lambda b: 'S1_block01' if int(b) == 1 else 'S2_blocks02_10')
    session_node = (norm.groupby(['actual_session','node_profile'])['normalized_deviation_pct']
                    .agg(['count','median','mean']).reset_index())

    # 3) Node ordering and separation margins for each transaction.
    piv = processed.pivot(index='transaction_id', columns='node_profile', values='service_time_ms')
    piv = piv.dropna(subset=EXPECTED_NODES).copy()
    piv['ordering_ok'] = (piv['Low'] > piv['Medium']) & (piv['Medium'] > piv['High'])
    piv['low_minus_medium_ms'] = piv['Low'] - piv['Medium']
    piv['medium_minus_high_ms'] = piv['Medium'] - piv['High']
    piv['low_vs_medium_pct'] = (piv['Low'] - piv['Medium']) / piv['Medium'] * 100.0
    piv['medium_vs_high_pct'] = (piv['Medium'] - piv['High']) / piv['High'] * 100.0

    sep_summary = {
        'ordering_ok': int(piv['ordering_ok'].sum()),
        'transactions': int(len(piv)),
        'low_vs_medium_pct_median': float(piv['low_vs_medium_pct'].median()),
        'low_vs_medium_pct_p05': q(piv['low_vs_medium_pct'], .05),
        'low_vs_medium_pct_min': float(piv['low_vs_medium_pct'].min()),
        'medium_vs_high_pct_median': float(piv['medium_vs_high_pct'].median()),
        'medium_vs_high_pct_p05': q(piv['medium_vs_high_pct'], .05),
        'medium_vs_high_pct_min': float(piv['medium_vs_high_pct'].min()),
    }

    # 4) Processed service-time distributions and robust outlier review.
    dist_rows = []
    processed['robust_z_type_node'] = 0.0
    for (tx_type, node), idx in processed.groupby(['type','node_profile']).groups.items():
        s = processed.loc[idx, 'service_time_ms']
        processed.loc[idx, 'robust_z_type_node'] = robust_z(s).values
        dist_rows.append({
            'type': tx_type, 'node_profile': node, 'n': int(len(s)),
            'min': float(s.min()), 'p05': q(s,.05), 'median': float(s.median()),
            'mean': float(s.mean()), 'p95': q(s,.95), 'max': float(s.max()),
            'mad': mad(s),
        })
    dist = pd.DataFrame(dist_rows)
    processed['abs_robust_z'] = processed['robust_z_type_node'].abs()
    robust_outliers = processed[processed['abs_robust_z'] > 3.5].sort_values('abs_robust_z', ascending=False)

    # Top repeat-instability pairs for manual review.
    top_cv = pair.sort_values('cv_pct', ascending=False).head(50)

    # Save outputs.
    pair.to_csv(OUT / 'pair_repeat_stability_all.csv', index=False)
    cv_by_node.to_csv(OUT / 'cv_distribution_by_node.csv', index=False)
    cv_block.to_csv(OUT / 'cv_localization_by_block_node.csv', index=False)
    cv_type.to_csv(OUT / 'cv_localization_by_type_node.csv', index=False)
    block_node.to_csv(OUT / 'block_drift_normalized_by_type_node.csv', index=False)
    block_overall.to_csv(OUT / 'block_drift_overall_normalized.csv', index=False)
    session_node.to_csv(OUT / 'actual_session_diagnostic_by_node.csv', index=False)
    piv.reset_index().to_csv(OUT / 'node_separation_by_transaction.csv', index=False)
    dist.to_csv(OUT / 'service_time_distribution_by_type_node.csv', index=False)
    robust_outliers.to_csv(OUT / 'robust_outliers_type_node.csv', index=False)
    top_cv.to_csv(OUT / 'top_50_repeat_cv_pairs.csv', index=False)

    summary = {
        'created_at_utc': utc_now(),
        'status': 'DEEP_AUDIT_DESCRIPTIVE_NOT_AN_AUTOMATIC_APPROVAL_GATE',
        'raw_success_rows': int(len(success)),
        'processed_rows': int(len(processed)),
        'unique_transactions': int(processed['transaction_id'].nunique()),
        'node_separation': sep_summary,
        'repeat_stability': {
            row['node_profile']: {
                k: (int(v) if k.startswith('pairs_') or k == 'count' else float(v))
                for k, v in row.items() if k != 'node_profile'
            } for row in cv_by_node.to_dict(orient='records')
        },
        'block_drift': {
            'max_abs_block_node_median_normalized_deviation_pct': float(block_node['median'].abs().max()),
            'max_abs_block_overall_median_normalized_deviation_pct': float(block_overall['median'].abs().max()),
        },
        'robust_outliers_abs_z_gt_3_5': int(len(robust_outliers)),
        'actual_session_note': 'S1=block01; S2=blocks02-10, based on the recorded execution history. Descriptive only; session is confounded with block/sample.',
        'decision_note': 'Do not change acceptance criteria post hoc. Review block/session drift, CV localization, outliers, node separation, and provenance before promoting the candidate to FINAL TRAINING DATA.',
    }
    (OUT / 'deep_audit_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print('=== DEEP AUDIT: REPEAT STABILITY ===')
    print(cv_by_node.to_string(index=False, float_format=lambda x: f'{x:.3f}'))
    print('\n=== DEEP AUDIT: CV >10% LOCALIZATION BY BLOCK/NODE ===')
    print(cv_block.to_string(index=False, float_format=lambda x: f'{x:.3f}'))
    print('\n=== DEEP AUDIT: NORMALIZED BLOCK DRIFT ===')
    print(block_overall.to_string(index=False, float_format=lambda x: f'{x:.3f}'))
    print(f"max_abs_block_node_median_deviation_pct = {summary['block_drift']['max_abs_block_node_median_normalized_deviation_pct']:.3f}")
    print('\n=== DEEP AUDIT: ACTUAL SESSION DIAGNOSTIC ===')
    print(session_node.to_string(index=False, float_format=lambda x: f'{x:.3f}'))
    print('\n=== DEEP AUDIT: NODE SEPARATION ===')
    for k, v in sep_summary.items():
        print(f'{k} = {v:.3f}' if isinstance(v, float) else f'{k} = {v}')
    print('\n=== DEEP AUDIT: ROBUST OUTLIER REVIEW ===')
    print(f'processed_rows_with_abs_robust_z_gt_3.5 = {len(robust_outliers)}')
    print(f'Outputs = {OUT}')
    print('DEEP_AUDIT_STATUS = REVIEW_OUTPUTS_WITH_CHATGPT_BEFORE_DATASET_PROMOTION')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'DEEP-AUDIT ERROR: {exc}')
        raise SystemExit(1)
