# Day 1 Decision Log

| ID | Decision | Status | Reason | Next Validation |
|---|---|---|---|---|
| D01 | Use a PaySim-style external synthetic dataset as the transaction source candidate | Proposed | More documented and reproducible than an undocumented team-created random generator | Verify exact source, version, provenance, and license |
| D02 | Do not use fraud as a Heavy/Light workload label | Confirmed | Fraud status and processing demand are different concepts | Preserve in methodology and feature-leakage checks |
| D03 | Replace fixed Heavy/Light classification with node-aware service-time regression | Working decision | Measured milliseconds provide a more defensible target than arbitrary labels | Mentor approval required |
| D04 | Compare several regression models | Confirmed working plan | Original research goal was comparative model evaluation | Finalise tuning budget and metrics |
| D05 | Integrate the best model into routing | Confirmed working plan | Demonstrates whether prediction quality creates operational benefit | Define routing policy and baselines |
| D06 | Use controlled Docker node profiles | Proposed | Creates repeatable resource differences on one host | Pilot and document exact profiles |
| D07 | Treat latency results as environment-specific | Confirmed | Processing time changes across hardware | Add calibration/retraining requirement for new hardware |
| D08 | Keep normal and festival-surge scenarios in the first paper | Working decision | Provides both stable and burst-traffic evaluation | Finalise traffic configuration |
| D09 | Keep node degradation/failure optional | Pending mentor decision | Valuable but may make first-paper scope too large | Decide after feasibility review |
| D10 | Keep human-reviewed retraining as future work | Working decision | Avoids excessive first-paper scope | Revisit after core paper is complete |
