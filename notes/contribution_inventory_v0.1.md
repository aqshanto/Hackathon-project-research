# FinCluster Contribution Inventory v0.1

**Created:** 2026-09-07
**Status:** WORKING DOCUMENT — decision input, not a frozen decision
**Purpose:** State exactly what this project has produced, tag every claim with the file that
proves it, and lay out the candidate paper framings so one can be chosen before the
literature review starts.

## 0. Origin of the "Candidate A / B / C" labels

These labels do not appear in any earlier project document. They were introduced here to
compare framings side by side. Their sources:

- **Candidate A** = RQ1 exactly as written in `proposal/research_questions_v0.2.md`.
- **Candidate C** = RQ2 + RQ3 from the same file, upgraded by the `queue_aware_v1`
  experiment of 2026-08-30, which changed the target from service time to completion time.
  This upgrade is not yet reflected in any RQ document.
- **Candidate B** = a reframing. `MASTER_PROJECT_CONTEXT_v2.3.md` §11 already lists the
  measurement methodology as expected contribution #1, but no RQ exists for it, and §37
  lists measurement stability as `BLOCKED` — i.e. as an obstacle, not a result.

## 1. What this project has actually produced

Every row below is backed by a file in this repository. Nothing here is an estimate.

### 1.1 A validated measurement protocol — COMPLETE

| Claim | Evidence |
|---|---|
| CFS quota throttling occurs even at a nominal one-CPU quota: `nr_throttled` 1 to 136, 135 of 341 periods throttled (~39.6%) | `results/instrumented_high_v05/`, master context section 5 |
| Quota and scheduler affinity are independent: 8 logical CPUs eligible under `cpu.max = 10000 10000` | master context section 38, terminal evidence |
| CPU pinning (`--cpuset-cpus="0"`) plus thread limits resolved batch-level drift | `results/v06_pinned_analysis/v06_reproducibility_summary.csv` |
| Low at 50% CPU failed the reproducibility gate (median A/B 6.18%, 2 pairs >10%) | same file |
| Low at 60% CPU passed (median A/B 2.08%, 0 pairs >10%) | `results/v06_low60_analysis/low60_reproducibility_summary.csv` |
| Medium 75% passed at 1.98%; High 100% passed at 1.52% | `results/v06_pinned_analysis/v06_reproducibility_summary.csv` |

The acceptance rule (median A/B difference at most 5%, at most 2/10 pairs above 10%) was
**predeclared before** the batches ran. That ordering is what makes it a gate rather than a
rationalisation after the fact.

### 1.2 A frozen, hash-verified dataset — COMPLETE

Source: `data/final_training_data_v1/FREEZE_REPORT.txt`

- 15,000 raw measured timings, 3,000 transaction-node rows, 1,000 unique transactions
- Grouped split by `transaction_id`: 700 / 150 / 150, **0 leakage across splits**
- Node ordering Low > Medium > High held for **1000/1000** transactions
- Median within-pair CV: High 1.477%, Low 6.266%, Medium 6.254%
- 48/3000 rows flagged as robust outliers, **none removed**
- SHA-256 checksums, run manifests, and a code snapshot frozen alongside the data
- Held-out test set has **never been loaded** (every script checks existence only)

### 1.3 A negative result — COMPLETE, and the most important finding here

Source: `results/regression_v1/ablation_best_per_feature_set.csv`,
`results/regression_v1/type_node_diagnostic/`

| Feature set | Best model | MAE (ms) | R-squared |
|---|---|---|---|
| `type + node_profile` | RandomForest | **0.922** | 0.984 |
| `+ amount, balances, step` | HistGradientBoosting | 0.997 | 0.981 |
| `node_profile` alone | RandomForest | 5.735 | 0.528 |

- Adding numeric transaction features **degrades** accuracy by 0.075 ms MAE.
- A non-ML lookup table (`TypeNodeMedianLookup`) scores **MAE 0.898 ms** — better than every
  trained model.
- **The mechanism is known, not guessed:** `scripts/reference_processor.py` v0.3 sets
  workload by transaction type only — 80,000 common PBKDF2 iterations plus 20,000 per
  workflow module (CASH_IN 2, PAYMENT 3, CASH_OUT 4, DEBIT 5, TRANSFER 6). `amount` never
  touches compute cost. The target is therefore a 5 x 3 = 15-cell lookup **by construction**.

This invalidates RQ1 as currently written.

### 1.4 Preliminary evidence that queue state restores the problem — SCREEN STAGE

Source: `results/queue_aware_v1/`

| Feature set | Best MAE (ms) | R-squared |
|---|---|---|
| `type + node + active_workers + queue_length` | **2.343** | 0.987 |
| `type + node` | 22.183 | 0.135 |

- Target changed to `completion_time_ms = queue_wait + service_time`.
- `actual_queue_wait_ms` correctly excluded as an input — it is a target component.
- High is **not** the best node 31.9% of the time, so routing stops being a constant answer.

**Known weakness:** the queue simulator is driven by train-split empirical service times, so
the model partly predicts its own generator. This must be stated openly in any write-up.

## 2. Candidate framings

| | Framing | Experiments still needed | Main risk | Fits under 2 months solo? |
|---|---|---|---|---|
| **A** | Which ML model best predicts service time? (RQ1 as written) | Redesign processor so `amount` costs compute; re-collect 15,000 measurements | Already answered, and the answer is that a lookup table wins | **No** — collection alone took about 3 weeks |
| **B** | A reproducible protocol for measuring container service time, plus the degeneracy result | **None.** Writing and literature positioning only | Container performance variability is well studied; novelty may rest on the domain and the negative result rather than the protocol | **Yes** |
| **C** | Queue-aware completion-time prediction for routing (RQ2/RQ3 upgraded) | Simulator validation, Round Robin / WRR / Least-Loaded baselines, system-level evaluation, statistics | Circularity: simulator built from own service times | **No**, not as the primary claim |

## 3. Recommendation

**Write B, with A's failure as the headline rather than a footnote.**

Working framing:

> A reproducible protocol for measuring transaction service time in containerised
> environments, and a cautionary result: under a synthetic reference processor,
> machine-learned latency prediction collapses to a fifteen-cell lookup.

Reasoning:

1. Every experiment it needs is already finished and hash-verified. It is the only candidate
   that fits the timeline.
2. It converts the project's biggest problem into its contribution. The degeneracy is a real
   warning for ML-for-systems benchmarking, and the evidence here is unusually clean:
   ablation, non-ML baselines, per-cell statistics, and a processor design that explains the
   mechanism.
3. The measurement rigour is above the norm: predeclared gates, throttling instrumentation,
   pinning validation, SHA-256 freeze with code snapshot.
4. Candidate C becomes a short "preliminary evidence and future work" section, using numbers
   that already exist.

## 4. Literature questions that confirm or kill this

The review is scoped to answer these, not to survey the whole field:

1. Is container CPU-quota throttling and its effect on benchmark reproducibility already
   thoroughly documented? **Expected answer: yes.** If so, the protocol alone is not the
   novelty.
2. Has anyone reported ML execution-time prediction **collapsing to a lookup** because the
   synthetic workload generator was a function of the categorical input? If yes, this paper
   has no claim. If no, this is the contribution.
3. Is there prior work on latency-predicted routing for payment or MFS transactions
   specifically, as opposed to generic cluster scheduling?
4. Do published container-benchmark methodologies use predeclared reproducibility gates, or
   only report variance after the fact?

Question 2 is decisive and should be answered first.

## 5. What this does not change

- No re-collection of measurement data.
- `FINAL_TRAINING_DATA_v1` stays frozen and unmodified.
- The held-out test set stays sealed until the research questions are frozen, then is used
  once for the final confirmatory number.
- All v0.3/v0.4/v0.5 diagnostic evidence and `archive/` remain untouched.
