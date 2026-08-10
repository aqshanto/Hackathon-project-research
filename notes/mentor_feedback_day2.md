# Mentor Feedback — Research Day 2

## Confirmed / Recommended

1. PaySim is preferred as the transaction-data source.
2. Measured `service_time_ms` is preferred over handcrafted Heavy/Light labels.
3. Security implications of the layered transaction-processing pipeline must be considered.
4. Multiple execution runs may be used if they improve measurement reliability.
5. Development scope does not need to be reduced just because the research paper has a focused scope.
6. Every transaction should have a unique transaction ID.
7. All node-level observations belonging to the same transaction must remain in the same train/test group.
8. Research quality should remain high; comparing more models is encouraged when feasible.
9. Strong and relevant evaluation metrics should be included.
10. Prediction/model evaluation should be completed before system-level routing experiments.
11. Multiple routing baselines should be used.
12. ACID properties should remain in the system design.

## Ideas Requiring Methodological Validation

- Deriving Light / Moderate / Heavy workload bands from measured service time.
- Comparing clustering methods for workload characterization.
- Exact node-resource configurations.
- Exact number of repeated measurements.
