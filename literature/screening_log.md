# FinCluster Literature Review v1 - screening log

Pool: 724 unique works (216 keyword + 508 snowball, deduplicated).
Included: 34. Every included work had its abstract read.

## Exclusion decisions

- **Runtime prediction of parallel applications with workload-aware clustering (2017)**
  EXCLUDED - OpenAlex holds no abstract; inclusion could not be justified at abstract level. Retrieve manually if T1 needs strengthening.

- **Interference Analysis of Co-Located Container Workloads (2020)**
  EXCLUDED - same reason: no abstract available.

- **Beyond accuracy: Measures for assessing machine learning models, pitfalls (2019)**
  EXCLUDED - neuroimaging evaluation methodology; the pitfalls discussed are classification metrics, not benchmark degeneracy.

- **All shortcut-learning papers except Shortcut to Nowhere (approx. 30 works)**
  EXCLUDED - vision, audio, deepfake, graph, LLM and medical-imaging domains. None address systems or performance prediction. Their absence is itself the evidence for the T3 gap.

- **AI-Powered Payment Gateways and similar (approx. 20 works in C4)**
  EXCLUDED - not peer-reviewed research; no method, dataset or evaluation. Confirms there is no academic payment-routing literature to position against.

- **Medical, agricultural, climate and education works surfaced by keyword search (approx. 300 works)**
  EXCLUDED - off-domain false positives from OpenAlex relevance ranking; removed by the computer-science field filter and triage penalties.

## Flagged for full text

- [T1] Learning-based Query Performance Modeling and Prediction (2012) - https://doi.org/10.1109/icde.2012.64
- [T1] Predicting query execution time: Are optimizer cost models really unusable? (2013) - https://doi.org/10.1109/icde.2013.6544899
- [T1] Towards predicting query execution time for concurrent and dynamic database workloads (2013) - https://doi.org/10.14778/2536206.2536219
- [T1] Contender: A Resource Modeling Approach for Concurrent Query Performance Prediction (2014) - https://doi.org/10.5441/002/edbt.2014.11
- [T1] Stage: Query Execution Time Prediction in Amazon Redshift (2024) - https://doi.org/10.1145/3626246.3653391
- [T2] Rusty: Runtime Interference-Aware Predictive Monitoring for Modern Multi-Tenant Systems (2020) - https://doi.org/10.1109/tpds.2020.3013948
- [T2] Performance interference of co-allocated applications: a systematic literature review (2023) - https://www.researchsquare.com/article/rs-3243462/latest.pdf
- [T2] Investigating the Impact of Isolation on Synchronized Benchmarks (2025) - https://arxiv.org/pdf/2511.03533
- [T2] Does Linux Provide Performance Isolation for NVMe SSDs? Configuring cgroups for I/O Control in the NVMe Era (2025) - https://research.vu.nl/en/publications/e2c27584-ebbf-4ccc-b97a-3f50572aa5f4
- [T3] Shortcut to Nowhere: Demystifying Deep Spurious Regression (2026) - https://arxiv.org/pdf/2606.01723
- [T3] SynQL: A Controllable and Scalable Rule-Based Framework for SQL Workload Synthesis for Performance Benchmarking (2026) - https://arxiv.org/pdf/2604.08021
- [T4] SLO-Aware Inference Scheduler for Heterogeneous Processors in Edge Platforms (2021) - https://dl.acm.org/doi/pdf/10.1145/3460352
- [T4] Predicting the End-to-End Tail Latency of Containerized Microservices in the Cloud (2019) - https://doi.org/10.1109/ic2e.2019.00034
- [T4] QoS-Aware Co-Scheduling for Distributed Long-Running Applications on Shared Clusters (2022) - https://ieeexplore.ieee.org/ielx7/71/9790018/09869329.pdf
- [T4] From distributed tracing to proactive SLO management: a mini-review of trace-driven performance prediction for cloud-native microservices (2026) - https://public-pages-files-2025.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2026.1783945/pdf
