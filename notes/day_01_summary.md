# Day 1 Research Summary - Revised Version 0.2

## Completed

- Created the FinCluster research workspace.
- Prepared the original proposal and research questions.
- Identified limitations in fixed Heavy/Light labels generated from handcrafted rules.
- Selected a PaySim-style external synthetic mobile-money dataset as a candidate transaction source.
- Documented that fraud labels are not workload labels.
- Replaced arbitrary work-unit prediction with experimentally measured service-time prediction.
- Revised the primary ML task to node-aware regression.
- Preserved the original plan to compare multiple ML models.
- Added a second evaluation layer: integrating the best model into the routing engine.
- Selected traditional routing baselines for comparison.
- Prepared an updated mentor-question list, team-role plan, literature keywords, and dataset-inspection tools.

## Confirmed Working Decisions

```text
Primary ML task:
Node-aware service-time regression

Primary target:
Measured service_time_ms

Transaction source:
PaySim-style external synthetic mobile-money data

Label source:
Controlled execution of a FinCluster reference processing pipeline

Model comparison:
Multiple regression models

System evaluation:
Winner model vs traditional routing

Main scenarios:
Normal traffic and festival surge
```

## Deprecated or Replaced Ideas

- Fixed Heavy/Light labels based only on transaction type.
- Direct use of `isFraud` as a workload label.
- Arbitrary work units assigned without measurement.
- Claiming latency predictions are universal across all company hardware.

## Main Uncertainties

- Exact PaySim repository/version and license.
- Final reference-pipeline stages.
- Exact Docker node profiles.
- Measurement repetition count after pilot testing.
- Valid pre-routing feature set.
- Dataset sample size feasible for repeated execution.
- Whether node degradation and failure will be included in the first paper.
- Target publication type and venue.

## Next Step

Present proposal v0.2 to the mentor and freeze the research scope before implementing the processing pipeline or training models.
