"""
FinCluster Literature Review v1 - screening and review table.

Joins hand-written screening decisions with OpenAlex metadata from
triage_ranked.csv and writes the review table in the same column shape used by
the earlier DR literature review, plus explicit screening columns.

Every paper listed here had its abstract read before the decision was made.
Two otherwise-promising works were excluded because OpenAlex holds no abstract
for them and an inclusion could not be justified at abstract level.

Run from the Research root:
    python experiments\\literature_review_v1\\build_review.py

Output:
    literature/literature_review.csv
    literature/screening_log.md
"""

import csv
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# theme | title prefix | problem | method | main result | limitation | gap | relevance | full-text
INCLUDED = [
 # ---------------- T1  execution-time prediction: ML vs analytical ----------------
 ("T1", "Predicting query execution time: Are optimizer",
  "Is ML necessary to predict query execution time?",
  "Calibrated optimizer cost model vs published ML predictors; cardinality refinement",
  "A properly calibrated analytical cost model is competitive with and often better than the best reported ML results",
  "Database queries only; needs optimizer internals; no synthetic-generator analysis",
  "Establishes that a non-ML baseline can beat ML at execution-time prediction, but on a genuinely hard task",
  "STRONGEST PRIOR AGAINST OPTION B. The headline claim of Option B is already made here, in 2013, at ICDE.",
  "YES"),
 ("T1", "Towards predicting query execution time for concurrent",
  "Predicting execution time for dynamic concurrent workloads",
  "Optimizer cost model plus queueing and buffer-pool model, compared against an ML variant",
  "Analytic modelling gives competitive and often better accuracy than the ML counterpart",
  "Database-specific; assumes optimizer cost model is available",
  "Second independent demonstration that analytical models beat ML here",
  "SECOND STRONGEST PRIOR AGAINST B. Also a precedent for queue modelling, so partly supports C.",
  "YES"),
 ("T1", "Learning-based Query Performance Modeling",
  "Can learned models predict query latency better than analytical cost models?",
  "Plan-level and operator-level learned models, plus a hybrid, static features only",
  "Learned models outperform analytical cost models for latency; hybrid trades accuracy for generality",
  "Contradicted by the 2013 calibration work; static/dynamic split",
  "The pro-ML pole of the debate Option B would be entering",
  "Defines the debate FinCluster's RQ1 sits inside. FinCluster's result lands on the anti-ML side.",
  "YES"),
 ("T1", "Robust estimation of resource consumption for SQL",
  "Do statistical resource-estimation models generalise beyond their training workload?",
  "Statistical models for SQL resource consumption, tested for robustness",
  "Proposed approaches lack robustness and do not generalise well to unseen queries",
  "Resource consumption rather than wall-clock service time",
  "Generalisation failure of learned performance models is documented",
  "Relevant to the leakage/generalisation argument, and to why grouped splitting matters.",
  "NO"),
 ("T1", "Uncertainty aware query execution time",
  "Point predictions hide prediction uncertainty",
  "Treats selectivities and cost constants as random variables to infer an error distribution",
  "Estimated prediction errors correlate strongly with actual errors",
  "Cost-model dependent",
  "Uncertainty reporting is established practice that FinCluster does not yet do",
  "Methodological gap in FinCluster: only point MAE/RMSE are reported, no uncertainty.",
  "NO"),
 ("T1", "Same Queries, Different Data",
  "Predicting runtime for fixed query sets over varying input data",
  "Per-segment ML estimates composed into a global analytical model",
  "Under 25 percent error for 90 percent of predictions using minimal input statistics",
  "MapReduce-specific; fixed dataflows",
  "Fixed-workload/varying-data setting is close to FinCluster's fixed-processor/varying-transaction setting",
  "Structurally the closest analogue to the FinCluster experimental design.",
  "NO"),
 ("T1", "Contender: A Resource Modeling",
  "Predicting query performance under concurrency",
  "Resource-contention modelling with Concurrent Query Intensity metrics; low training requirement",
  "Effective predictions for both static and dynamic concurrent workloads",
  "Analytical workloads; no learned routing policy",
  "Concurrency-aware performance prediction predates FinCluster's queue-aware idea",
  "IMPORTANT FOR OPTION C. Prior art for predicting under contention rather than in isolation.",
  "YES"),
 ("T1", "Stage: Query Execution Time Prediction in Amazon",
  "Production execution-time prediction with cold-start and drift problems",
  "Predictor deployed in Amazon Redshift for admission, scheduling, resource control",
  "Addresses cold start and robustness against workload/data change",
  "Proprietary system; database domain",
  "Shows the task is live and unsolved in production, not a toy problem",
  "Evidence that execution-time prediction has real operational value - supports the premise, not the novelty.",
  "YES"),
 ("T1", "Execution Time Prediction for Cypher",
  "Execution time prediction for graph queries",
  "Learned model over Cypher query features on Neo4j",
  "SQL-oriented QPP methods do not transfer directly to Cypher",
  "Single database engine",
  "Shows QPP methods are re-derived per engine",
  "Demonstrates the field's habit of re-running the same comparison in a new setting - which is what Option B risks being.",
  "NO"),
 ("T1", "Quick Execution Time Predictions for Spark",
  "Fast execution-time estimates for Spark applications under varying resources",
  "Lightweight predictive models over executor cores and data size",
  "Enables schedulers to configure applications for a target execution time",
  "Spark-specific",
  "Resource-count as an input feature, analogous to FinCluster's node profile",
  "Parallel to FinCluster's node_profile feature; useful for framing node capacity as a predictor.",
  "NO"),
 ("T1", "A Machine Learning Approach to SPARQL",
  "SPARQL query performance prediction without data statistics",
  "Query feature vectors, k-NN regression and nu-SVR",
  "Accurate prediction without underlying RDF statistics",
  "Linked Data setting",
  "Feature-vector framing of queries",
  "Another instance of the same comparison template; supports the crowding argument.",
  "NO"),
 ("T1", "Application of Machine Learning Algorithms for the Query",
  "Relationship between system load/throughput and query response time in OLTP",
  "ML algorithms over a real OLTP system",
  "Load and throughput are central to response time in short-transaction systems",
  "Single production system",
  "Load-dependence of response time in transactional systems",
  "DIRECTLY SUPPORTS OPTION C: in real transaction systems, response time is driven by load, not just transaction content.",
  "NO"),
 ("T1", "Runtime prediction of high-performance computing jobs",
  "Predicting HPC job runtime for backfill scheduling",
  "Ensemble learning over job logs from three real HPC systems",
  "LightGBM gives higher accuracy and faster computation than compared models",
  "Log-based; user-supplied estimates are biased",
  "Model-comparison studies on real logs are standard and well populated",
  "Shows the model-comparison genre is saturated - reinforces that Option B's RQ1 form adds little.",
  "NO"),
 ("T1", "PREP: Predicting Job Runtime",
  "User-supplied runtime estimates are overestimated, harming backfilling",
  "Job running path features from historical logs",
  "Improves runtime prediction over prior log-feature approaches",
  "Supercomputer scheduling context",
  "Prediction feeding a scheduling decision",
  "Precedent for the prediction-then-scheduling pipeline FinCluster proposes.",
  "NO"),

 # ---------------- T2  container performance and measurement methodology ----------------
 ("T2", "Investigating the Impact of Isolation on Synchronized",
  "Which isolation mechanism makes cloud benchmarking reliable under contention?",
  "Compares cgroups plus CPU pinning, Docker containers, and Firecracker microVMs against an unisolated baseline with a noise generator",
  "Process isolation lowered false positives; Docker containers were MORE susceptible to noise despite using cgroups and pinning internally",
  "Duet benchmarking context; no prediction task",
  "cgroups plus CPU pinning as a benchmark isolation strategy is already evaluated",
  "STRONGEST PRIOR AGAINST FINCLUSTER'S PROTOCOL NOVELTY. The exact mechanism combination FinCluster arrived at in v0.6 is already published, and this paper finds Docker specifically weaker.",
  "YES"),
 ("T2", "KVM, Xen and Docker",
  "Performance comparison of virtualisation and container technologies",
  "Benchmark suite across KVM, Xen, Docker on ARM",
  "Quantifies container versus hypervisor overhead",
  "ARM/NFV specific; dated",
  "Container overhead characterisation is long established",
  "Background for why container measurement needs care; not a novelty threat.",
  "NO"),
 ("T2", "Rusty: Runtime Interference-Aware Predictive Monitoring",
  "Predicting workload sensitivity to interference in multi-tenant containers",
  "Runtime observability and forecasting of interference effects",
  "Finer-grained interference modelling than prior coarse-grained approaches",
  "No controlled ground-truth measurement protocol",
  "Interference prediction is mature; controlled measurement of it is less so",
  "Nearest neighbour on the systems side; shows the community FinCluster should target.",
  "YES"),
 ("T2", "Evaluating the impact of fine-scale burstiness",
  "Does fine-scale workload burstiness change measured elasticity?",
  "Workload models reproducing empirical burstiness; experimental case study",
  "Fine-scale burstiness materially affects elasticity measurements",
  "Elasticity rather than service time",
  "Benchmark realism affects measured outcomes",
  "Supports the general argument that generator design determines measured results - conceptually adjacent to FinCluster's finding.",
  "NO"),
 ("T2", "Performance interference of co-allocated applications",
  "Systematic review of performance interference in co-allocated applications",
  "Systematic literature review of prediction/analysis techniques and input metrics",
  "Maps the techniques, metrics and tools used across the field",
  "Review, not primary evidence",
  "Provides the field map FinCluster's related-work section needs",
  "Best single entry point for positioning FinCluster in the systems literature.",
  "YES"),
 ("T2", "Machine Learning based Interference Modelling",
  "Predicting interference before co-locating containers",
  "ML models over co-located container workloads",
  "Interference level can be predicted before sharing a VM",
  "Prediction target is interference, not service time",
  "Pre-placement prediction is established",
  "Close to FinCluster's routing premise, using interference instead of service time.",
  "NO"),
 ("T2", "Does Linux Provide Performance Isolation for NVMe",
  "Whether cgroup configuration actually delivers storage performance isolation",
  "Systematic evaluation of cgroup configurations for NVMe SSDs",
  "No uniform configuration achieves isolation across properties; trade-off with utilisation",
  "Storage rather than CPU",
  "cgroup isolation is imperfect and this is documented for storage",
  "The storage analogue of FinCluster's CPU throttling finding - shows this style of result is publishable but also already being done.",
  "YES"),
 ("T2", "CloudScope: Diagnosing and Managing",
  "Lightweight diagnosis of interference in multi-tenant clouds",
  "Discrete-time Markov chain model of interference",
  "Interference diagnosis without heavy micro-benchmarking or online training",
  "VM-level, pre-container era",
  "Analytical interference modelling precedent",
  "Shows analytical modelling is a live alternative to ML in this domain too.",
  "NO"),
 ("T2", "Characterizing Container Performance in Edge",
  "Docker overhead characterisation on constrained edge hardware",
  "Micro and macro benchmarks on Raspberry Pi nodes",
  "Spin-up delays for short tasks, isolation/performance trade-offs",
  "Edge hardware; no prediction task",
  "Container measurement characterisation continues to be published",
  "Recent evidence that container measurement studies remain publishable.",
  "NO"),
 ("T2", "Real-Time Interference-Aware CPU and I/O Capping",
  "Maintaining QoS under contention in multi-tenant containers",
  "Real-time interference-aware CPU and I/O capping mechanism",
  "Conventional static capping is insufficient under high contention",
  "Mechanism paper, not a measurement-methodology paper",
  "Dynamic capping as an alternative to static quotas",
  "Suggests FinCluster's static-quota node model is a simplification reviewers may question.",
  "NO"),

 # ---------------- T3  benchmark validity and degeneracy ----------------
 ("T3", "Shortcut to Nowhere",
  "Spurious correlations in CONTINUOUS regression targets, not classification",
  "Defines Deep Spurious Regression; exploits similarity among spurious attributes in label and feature space",
  "Fills the benchmark and technique gap for spurious correlation in continuous prediction",
  "Evaluated on computer vision, environmental sensing and LLM regression - NOT systems",
  "Spurious regression is now named and benchmarked, but never in a systems/performance-prediction setting",
  "CLOSEST CONCEPTUAL PRIOR TO FINCLUSTER'S FINDING, and simultaneously the clearest evidence that the systems instance is unoccupied.",
  "YES"),
 ("T3", "SynQL",
  "Existing benchmarks offer too few fixed templates for statistical generalisation",
  "Deterministic schema-graph traversal to synthesise diverse executable SQL workloads",
  "Produces near-maximally diverse workloads where fixed templates and LLM generation fail",
  "SQL domain; proposes a generator rather than diagnosing a degenerate one",
  "The problem FinCluster hit - a generator too template-bound to support generalisation - is acknowledged, but as motivation for a better generator, not as a measured failure",
  "MOST IMPORTANT SINGLE PAPER FOR THE NOVELTY BOUNDARY. It states the premise; FinCluster measures the consequence.",
  "YES"),

 # ---------------- T4  prediction-driven routing and scheduling ----------------
 ("T4", "Predicting the End-to-End Tail Latency",
  "Predicting end-to-end tail latency of containerised microservice workflows",
  "ML over resource metrics from multiple cloud layers; KVM, Docker, Kubernetes on Chameleon",
  "High prediction accuracy even under multi-tenant interference",
  "Sock Shop benchmark; no routing policy evaluated",
  "Latency prediction in containers is established; using it to route is less so",
  "DEFINES OPTION C'S ACADEMIC HOME. Closest venue-and-community match for FinCluster.",
  "YES"),
 ("T4", "SLO-Aware Inference Scheduler",
  "Mapping concurrent ML inference to heterogeneous edge processors under SLOs",
  "SLO-aware scheduling across GPU, DSP and accelerators",
  "Scheduling heterogeneous computation under constrained budgets",
  "Edge inference domain",
  "Heterogeneous-processor scheduling with predicted cost",
  "Precedent for routing across heterogeneous nodes using predicted execution cost - Option C's core mechanism.",
  "YES"),
 ("T4", "IRIS: Interference and Resource Aware",
  "Interference- and resource-aware scheduling of ML inference in the cloud",
  "Predictive inference scheduling framework",
  "Balances QoS against operator cost under interference",
  "ML inference workloads specifically",
  "Prediction-driven placement is an active area",
  "Direct competitor framing for Option C; shows the baseline set reviewers will expect.",
  "NO"),
 ("T4", "QoS-Aware Co-Scheduling",
  "Co-scheduling long-running containerised applications on shared clusters",
  "QoS-aware co-scheduling accounting for latency propagation across microservices",
  "Detects and mitigates QoS violations under network and dependency uncertainty",
  "Cluster scheduling, not per-request routing",
  "Queue and dependency effects dominate at system level",
  "Supports Option C's premise that queueing, not service time, drives system outcomes.",
  "YES"),
 ("T4", "Adrias: Interference-Aware Memory",
  "Orchestration for disaggregated cloud infrastructure under interference",
  "Deep learning over low-level performance events",
  "Additional scheduling knobs for disaggregated resources",
  "Memory disaggregation focus",
  "Low-level event features for orchestration",
  "Peripheral; included to map the orchestration community.",
  "NO"),
 ("T4", "Niyama: Node scheduling",
  "Protecting latency-sensitive tasks from CPU bandwidth contention",
  "Modified deadline scheduling with estimated deadlines per interval",
  "Secures CPU bandwidth for latency-sensitive tasks without explicit deadlines",
  "Requires deadline estimation",
  "CPU bandwidth contention handled at scheduler rather than quota level",
  "Alternative to FinCluster's quota-based node emulation; a reviewer may ask why quotas were chosen.",
  "NO"),
 ("T4", "AGILE: elastic distributed",
  "Scaling resources ahead of demand without application knowledge",
  "Wavelet-based medium-term resource demand prediction",
  "Enough lead time to start instances before SLO violation",
  "VM scaling, not request routing",
  "Prediction horizon and lead time as design parameters",
  "Highly cited anchor for prediction-driven resource decisions.",
  "NO"),
 ("T4", "From distributed tracing to proactive SLO",
  "Moving from post-hoc analysis to predicting SLO risk before a request finishes",
  "Mini-review of trace-based proactive SLO management",
  "Queue buildup and downstream slowdown propagate to tail latency; early warning from partial traces",
  "Review; microservice tracing context",
  "Predicting completion before a request finishes is an active industrial demand",
  "STRONGLY SUPPORTS OPTION C's target choice - completion time predicted from observable pre-completion state.",
  "YES"),
]

EXCLUDED_NOTES = [
 ("Runtime prediction of parallel applications with workload-aware clustering (2017)",
  "EXCLUDED - OpenAlex holds no abstract; inclusion could not be justified at abstract level. Retrieve manually if T1 needs strengthening."),
 ("Interference Analysis of Co-Located Container Workloads (2020)",
  "EXCLUDED - same reason: no abstract available."),
 ("Beyond accuracy: Measures for assessing machine learning models, pitfalls (2019)",
  "EXCLUDED - neuroimaging evaluation methodology; the pitfalls discussed are classification metrics, not benchmark degeneracy."),
 ("All shortcut-learning papers except Shortcut to Nowhere (approx. 30 works)",
  "EXCLUDED - vision, audio, deepfake, graph, LLM and medical-imaging domains. None address systems or performance prediction. Their absence is itself the evidence for the T3 gap."),
 ("AI-Powered Payment Gateways and similar (approx. 20 works in C4)",
  "EXCLUDED - not peer-reviewed research; no method, dataset or evaluation. Confirms there is no academic payment-routing literature to position against."),
 ("Medical, agricultural, climate and education works surfaced by keyword search (approx. 300 works)",
  "EXCLUDED - off-domain false positives from OpenAlex relevance ranking; removed by the computer-science field filter and triage penalties."),
]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    lit = os.path.join(os.path.dirname(os.path.dirname(here)), "literature")

    meta = {}
    for r in csv.DictReader(open(os.path.join(lit, "triage_ranked.csv"), encoding="utf-8")):
        meta[r["title"].lower()] = r

    def lookup(prefix):
        p = prefix.lower()[:32]
        for t, r in meta.items():
            if t.startswith(p):
                return r
        return None

    cols = ["Theme", "Author/Year", "Title", "Venue", "Year", "Cited by",
            "OA status", "URL", "Problem", "Method", "Algorithm", "Main Result",
            "Limitation", "Research Gap", "Relevance to my research",
            "Decision", "Full text needed"]

    rows, missing = [], []
    for (theme, prefix, problem, method, result, limitation, gap, relevance, ft) in INCLUDED:
        m = lookup(prefix)
        if not m:
            missing.append(prefix)
            continue
        rows.append({
            "Theme": theme,
            "Author/Year": "%s" % (m["year"] or "n.d."),
            "Title": m["title"],
            "Venue": m["venue"] or "-",
            "Year": m["year"],
            "Cited by": m["cited_by"],
            "OA status": m["oa_status"],
            "URL": m["oa_url"] or ("https://doi.org/" + m["doi"] if m["doi"] else ""),
            "Problem": problem,
            "Method": method,
            "Algorithm": "",
            "Main Result": result,
            "Limitation": limitation,
            "Research Gap": gap,
            "Relevance to my research": relevance,
            "Decision": "INCLUDE",
            "Full text needed": ft,
        })

    rows.sort(key=lambda r: (r["Theme"], -int(r["Cited by"] or 0)))

    out = os.path.join(lit, "literature_review.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    with open(os.path.join(lit, "screening_log.md"), "w", encoding="utf-8") as fh:
        fh.write("# FinCluster Literature Review v1 - screening log\n\n")
        fh.write("Pool: 724 unique works (216 keyword + 508 snowball, deduplicated).\n")
        fh.write("Included: %d. Every included work had its abstract read.\n\n" % len(rows))
        fh.write("## Exclusion decisions\n\n")
        for what, why in EXCLUDED_NOTES:
            fh.write("- **%s**\n  %s\n\n" % (what, why))
        fh.write("## Flagged for full text\n\n")
        for r in rows:
            if r["Full text needed"] == "YES":
                fh.write("- [%s] %s (%s) - %s\n" % (r["Theme"], r["Title"], r["Year"], r["URL"] or "no OA url"))

    print("INCLUDED = %d" % len(rows))
    for t in ("T1", "T2", "T3", "T4"):
        print("  %s : %d" % (t, sum(1 for r in rows if r["Theme"] == t)))
    print("FULL_TEXT_FLAGGED = %d" % sum(1 for r in rows if r["Full text needed"] == "YES"))
    if missing:
        print("NOT MATCHED: %s" % missing)
    print("WROTE %s" % out)


if __name__ == "__main__":
    main()
