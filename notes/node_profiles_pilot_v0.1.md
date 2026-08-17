# Pilot Node Profiles v0.1

## Status

**Provisional design only. Exact CPU/RAM/concurrency values are not yet frozen because the host machine resources have not been documented in the current research package.**

## Goal

Create three controlled resource profiles on the same host:

- Low
- Medium
- High

The same FinCluster reference processing pipeline must run on all profiles.

## Candidate Configuration Template

| Profile | CPU limit | Memory limit | Concurrency | Status |
|---|---:|---:|---:|---|
| Low | TBD after host inspection | TBD | Initially fixed/TBD | Not frozen |
| Medium | TBD after host inspection | TBD | Initially fixed/TBD | Not frozen |
| High | TBD after host inspection | TBD | Initially fixed/TBD | Not frozen |

## Selection Rules

1. Profiles must be meaningfully different but feasible on the host machine.
2. The host itself must retain enough resources to avoid global starvation.
3. Database and shared-service placement must be documented.
4. Security and ACID logic must remain the same across profiles.
5. Pilot results must demonstrate a measurable node-capacity effect beyond timing noise.
6. Exact Docker/OS/hardware configuration must be recorded before final experiments.

## Next Action

Record the experiment host CPU, RAM, OS, Docker version, database location, and background-service policy, then select provisional limits and run the 10-transaction pilot.
