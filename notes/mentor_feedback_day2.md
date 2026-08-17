# Mentor Feedback - Research Day 2

## Date

Research discussion completed before the 11 August 2026 package update.

## Confirmed / Recommended by Mentor

1. **Use PaySim.** PaySim is preferred as the transaction-data source.
2. **Measure service time.** Using measured `service_time_ms` is preferred over handcrafted Heavy/Light labels.
3. **Consider security.** The layered transaction-processing pipeline must be designed so that the research measurement does not weaken security or silently remove security-related work.
4. **Repeated runs are acceptable.** Multiple executions may be used when they improve measurement reliability.
5. **Research scope is not the same as development scope.** A paper can focus on one contribution without deleting unrelated existing project features. New research-driven features can be added while the full FinCluster system continues to contain other modules.
6. **Use a unique transaction ID.** Every transaction requires a stable unique identity.
7. **Keep transaction observations grouped.** If one transaction is measured on multiple nodes, all node-level observations for that transaction must stay together in train/validation/test splitting. The same transaction must not be partly in training and partly in testing.
8. **Maintain research quality and compare multiple justified models.** More models can strengthen the benchmark when the comparison remains fair and methodologically controlled.
9. **Use strong relevant metrics.** Include metrics that materially strengthen the research paper rather than limiting evaluation to a single score.
10. **Prediction first, system experiment second.** Complete the service-time prediction/model benchmark before the end-to-end routing experiment.
11. **Use multiple routing baselines.** Do not compare only against Round Robin.
12. **Keep ACID properties.** ACID transaction properties remain technically appropriate in the reference transaction-processing design.

## Mentor Idea Requiring Methodological Refinement

The mentor suggested exploring whether measured processing times can be grouped into ranges such as Light, Moderate, and Heavy, and whether an algorithmic method could help create those ranges.

Current technical interpretation:

- continuous `service_time_ms` remains the primary ground-truth target;
- repeated timing runs are aggregated with a robust statistic such as the median, not with KNN/K-Means;
- KNN Regressor can be one supervised service-time prediction model;
- K-Means can be evaluated separately as an unsupervised method for deriving workload bands from measured/reference service times;
- KNN and K-Means should not be directly ranked as if they solve the same task;
- if workload bands are used, their stability and separation must be validated rather than forcing exactly three clusters without evidence.

## Development-Scope Interpretation

The mentor's camera example was interpreted as follows:

> A focused research paper does not require the whole software project to contain only the paper's contribution. Existing features can remain, and new research-derived features can be added, unless a new feature explicitly replaces an older one.

Therefore FinCluster development may continue to include routing, dashboard, safe-reroute concepts, human review, ACID handling, security controls, node monitoring, and other modules while the first paper focuses primarily on measured service-time prediction and routing impact.

## Questions Not Yet Asked / Still Open

- Exact Low/Medium/High node resource limits.
- Exact final reference-pipeline stages and security implementation details.
- Whether node degradation and complete failure belong in paper 1.
- Whether human-reviewed retraining remains future work.
- Final target publication type/venue.
- Exact author order and mentor contribution role.
- Final sample size and final repetition count after pilot variance analysis.
- Exact clustering methodology, if workload bands are retained.
