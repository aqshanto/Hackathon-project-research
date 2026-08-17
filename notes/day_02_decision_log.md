# Research Day 2 Decision Log

| ID | Decision | Status | Reason | Next Validation |
|---|---|---|---|---|
| D11 | Use PaySim as the preferred transaction-data source | Mentor-confirmed direction | Provides a documented external synthetic mobile-money distribution | Verify exact provenance/license and run full local inspection |
| D12 | Use measured `service_time_ms` as the primary ML target | Mentor-supported / current | More defensible than handcrafted workload labels | Implement and pilot reference pipeline measurement |
| D13 | Preserve security-related processing rather than making speed gains by disabling controls | Current design rule | Performance comparison must not be obtained by weakening security | Freeze security stage(s) in the reference pipeline |
| D14 | Use repeated timing runs when beneficial | Mentor-supported | System timing is noisy | Pilot 2 warm-ups + 5 measured runs and inspect variance |
| D15 | Use a unique transaction ID | Mentor-confirmed | Required for grouping, traceability, idempotency, and safe handling | Use stable UUID/transaction identifier in the measurement dataset |
| D16 | Group all node observations for one transaction in the same split | Mentor-confirmed | Prevents leakage across train/test | Use grouped splitting by `transaction_id` |
| D17 | Compare multiple justified regression models | Mentor-confirmed direction | Stronger comparative research if fairness is preserved | Freeze benchmark list and equal evaluation protocol |
| D18 | Complete model prediction evaluation before system-level routing experiments | Mentor-confirmed | Separates predictive quality from operational impact | Finish dataset + model benchmark first |
| D19 | Use multiple routing baselines | Mentor-confirmed | Avoid weak RR-only comparison | Implement RR, WRR, Least-Loaded, Rule-Based; consider Shortest Queue |
| D20 | Preserve ACID properties | Mentor-confirmed | Financial transaction correctness remains technically important | Implement/reference atomic commit/rollback, consistency, isolation, durability |
| D21 | Keep continuous service time primary; treat workload bands as secondary | Current methodological interpretation | Avoid replacing measured target with arbitrary class labels | Validate clustering only after enough measured data exist |
| D22 | KNN Regressor and K-Means have separate roles | Confirmed technical clarification | Supervised regression and unsupervised clustering are not the same task | Compare KNN only with regression models; compare K-Means only with clustering alternatives if needed |
