# Research Package Changelog

## Version 0.3 - 11 August 2026

- Recorded Research Day 2 mentor feedback as the current methodological guidance.
- Confirmed PaySim as the preferred transaction-data source for the research workflow.
- Confirmed measured `service_time_ms` as the preferred primary target over handcrafted Heavy/Light labels.
- Recorded the local PaySim filename `PS_20174392719_1491204439457_log.csv`, its 11-column schema status, and the observed transaction types.
- Added the initial PaySim candidate-feature and excluded-feature decisions.
- Explicitly removed VPN from the current feature set because it is not part of the verified PaySim schema.
- Clarified that repeated execution produces raw timing measurements and the median creates one ground-truth `service_time_ms` per transaction-node pair.
- Clarified that `service_time_ms` is target `y`, not an input feature.
- Added the correct separate roles of KNN Regressor and K-Means clustering.
- Added the optional `Predicted Service Time + Workload Band` presentation layer.
- Added unique transaction-ID and grouped-split requirements.
- Added ACID and security-control consistency requirements to the reference processing pipeline.
- Expanded the candidate regression-model plan and evaluation metrics in response to mentor guidance.
- Added Research Day 2 summary/decision log, workload-band methodology note, measurement protocol, pilot node-profile note, model-comparison plan, and data-folder guidance.
- Updated the PaySim inspection script to support a local CSV directly and to perform a chunked full-file scan for row count, missing values, blank strings, and key distributions while using a bounded sample for heavier exploratory statistics.
- Corrected the package manifest so it matches files actually included in the archive.
- Preserved the formal proposal v0.2 as a historical formal snapshot; no experimental result is claimed.

## Version 0.2 - 7 August 2026

- Revised the paper direction from fixed Heavy/Light workload classification to node-aware `service_time_ms` regression.
- Preserved the multi-model comparison objective using regression models.
- Added winner-model routing and traditional-routing comparison as the system-level evaluation.
- Added normal and festival-surge traffic as the primary system scenarios.
- Kept node degradation and failure as optional scope pending mentor approval.
- Replaced arbitrary work units with repeated measured processing time from a documented FinCluster reference pipeline.
- Added a PaySim inspection notebook and Python script.
- Added updated data, measurement, leakage, bias-control, and hardware-calibration notes.
- Updated the project master context at that stage.
- Preserved superseded v0.1 research documents for history.
