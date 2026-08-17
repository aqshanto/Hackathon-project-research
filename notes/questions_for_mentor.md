# Questions for Mentor - Current Status After Research Day 2

## Answered / Direction Received

### 1. Dataset source

**Question:** Should PaySim be used as the transaction source?

**Mentor direction:** Yes, PaySim is preferred.

### 2. Primary target

**Question:** Is measured `service_time_ms` stronger than handcrafted Heavy/Light labels?

**Mentor direction:** Measuring service time is better.

### 3. Repeated execution

**Question:** Can the same transaction-node pair be executed multiple times for stable timing?

**Mentor direction:** Yes, if it improves the algorithm/measurement quality.

### 4. Development scope vs research scope

**Question:** Must unrelated project features be removed to keep the research paper narrow?

**Mentor direction:** No. A focused research contribution does not require deleting other development features.

### 5. Transaction identity and split

**Mentor direction:** Use a unique transaction ID, and keep all node-level observations for the same transaction together in one train/test group.

### 6. Models and metrics

**Mentor direction:** Maintain strong research quality; compare as many justified models as feasible and include relevant metrics that strengthen the paper.

### 7. Evaluation order

**Mentor direction:** First complete prediction/model evaluation; then perform system-level experiments.

### 8. Routing baselines

**Mentor direction:** Use multiple baselines.

### 9. ACID

**Mentor direction:** Keep ACID properties; this is technically correct.

## Remaining Questions for the Next Mentor Meeting

1. What exact security/authentication/authorization operations should the reference pipeline simulate so that the measurement remains defensible without claiming a real-bank security stack?
2. Do you approve the current baseline pipeline with risk-model inference disabled until a later version?
3. What Low/Medium/High Docker CPU and memory limits should be used, or should we determine them from a pilot based on the host machine?
4. Should the first model benchmark use only static node-profile features, or also dynamic queue/CPU-utilization features?
5. Is the proposed grouped split by `transaction_id` sufficient, and should a temporal holdout using PaySim `step` also be reported?
6. Should Light/Moderate/Heavy remain only a secondary visualization? If retained, should we evaluate K-Means/GMM/Agglomerative clustering rather than setting arbitrary thresholds?
7. Should node degradation and complete node failure be included in paper 1 or left as an extension?
8. Should human-reviewed retraining remain future work for this paper?
9. What publication type should be targeted first?
10. How should author roles/order and mentor contribution be documented?
11. After the 10-transaction pilot, what variance/stability criterion should we use to decide whether 5 measured repetitions are sufficient?
