# FinCluster AI Research Links

*Last verified: 2026-08-08*

This file keeps the important datasets, papers, standards, documentation, and technical references discussed for the FinCluster AI research project.

---

## 1. Primary Dataset Candidates

### MoMTSim — Recommended dataset candidate to inspect next

**Mendeley Data — Version 2 (recommended source)**
https://data.mendeley.com/datasets/zhj366m53p/2

**Dataset DOI**
https://doi.org/10.17632/zhj366m53p.2

**Data in Brief dataset article — “A labeled synthetic mobile money transaction dataset”**
https://doi.org/10.1016/j.dib.2025.111534

**ScienceDirect article page**
https://www.sciencedirect.com/science/article/pii/S2352340925002665

**MoMTSim simulator paper — IEEE Access**
https://doi.org/10.1109/ACCESS.2024.3439012

**MoMTSim GitHub repository**
https://github.com/aiinfinancegroup/MoMTSim

**Kaggle mirror of the MoMTSim-generated dataset**
https://www.kaggle.com/datasets/denishazamuke/synthetic-mobile-money-transaction-dataset

### Why we are considering MoMTSim

* Mobile-money specific.
* Generated using the MoMTSim multi-agent simulator.
* The simulator was calibrated using real mobile-money transaction information.
* The dataset authors report statistical validation against real-data properties.
* Mendeley Data Version 2 is licensed under CC BY 4.0.
* Transaction types include deposits, withdrawals, transfers, payments, and debits.

---

## 2. PaySim Dataset

### Main PaySim dataset currently inspected

**Kaggle — Synthetic Financial Datasets For Fraud Detection**
https://www.kaggle.com/datasets/ealaxi/paysim1/data

**Official PaySim GitHub repository**
https://github.com/EdgarLopezPhD/PaySim

**Original PaySim conference paper — EMSS 2016**
https://www.msc-les.org/proceedings/emss/emss2016/emss2016_249.html

### Why PaySim is useful

* Very widely used mobile-money benchmark.
* Contains millions of synthetic transactions.
* Transaction types: CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER.
* Useful for transaction attributes and traffic distributions.
* It does not contain measured CPU, memory, or per-transaction processing latency.
* `isFraud` must not be treated directly as our Heavy/Light or latency target.

---

## 3. Mobile-Money Processing / Pipeline References

### GSMA Mobile Money API

**GSMA Mobile Money API main page**
https://www.gsma.com/solutions-and-impact/connectivity-for-good/mobile-for-development/mobile-money/mobile-money-api-2/

**GSMA Mobile Money API Developer Portal — Version 1.2**
https://developer.mobilemoneyapi.io/api-versions-1.2/get-started.html

Useful topics in the developer portal:

* API field/schema validation
* Client correlation ID
* Duplicate-request handling
* Amount validation
* Request/response behavior
* Merchant payments
* P2P transfers
* Agent services
* International transfers
* Error handling

### How we use GSMA references

GSMA is used to justify the general transaction semantics and API-processing concepts in the FinCluster Reference Transaction Processing Pipeline.

We do **not** claim that every real bank or MFS provider uses our exact internal sequence of stages.

---

## 4. Database Transaction / ACID References

### PostgreSQL Transactions Tutorial

https://www.postgresql.org/docs/16/tutorial-transactions.html

### Current PostgreSQL Transaction Processing Documentation

https://www.postgresql.org/docs/current/transactions.html

Useful for:

* BEGIN
* COMMIT
* ROLLBACK
* All-or-nothing database updates
* Preventing partial financial-state changes

---

## 5. Controlled Node / Docker Benchmark References

### Docker Resource Constraints

https://docs.docker.com/engine/containers/resource_constraints/

Useful for creating controlled experimental node profiles with:

* CPU limits
* Memory limits
* Resource-constrained containers

Possible FinCluster research profiles may later include low-, medium-, and high-capacity nodes, but exact configurations must be experimentally justified and documented.

---

## 6. Hugging Face Dataset Inspection Documentation

### Hugging Face Datasets — Loading

https://huggingface.co/docs/datasets/loading

### Hugging Face Datasets — Streaming

https://huggingface.co/docs/datasets/main/stream

Useful for:

* Loading CSV/Parquet datasets
* Inspecting large datasets without downloading everything
* Using `streaming=True`
* Taking small samples for initial inspection

---

## 7. Current Research Dataset Decision Status

### Not final yet

We have **not yet permanently selected the final dataset**.

Current candidates:

1. **MoMTSim v2** — strong academic provenance and recent validation.
2. **PaySim** — older but extremely well-known and widely used.

Recommended immediate action:

1. Inspect MoMTSim v2.
2. Compare its schema, documentation, size, license, transaction types, and usability with PaySim.
3. Select one as the primary input dataset.
4. Optionally use the second dataset later for external replication/generalisation.

---

## 8. Important Methodological Reminder

The external dataset will provide transaction attributes and transaction distributions.

It will **not** provide our final latency ground truth.

Our intended research flow is:

```text
External mobile-money transaction dataset
        ↓
FinCluster Reference Transaction Processing Pipeline
        ↓
Controlled execution on documented node profiles
        ↓
Repeated measurement of actual service_time_ms
        ↓
Measured transaction-node dataset
        ↓
Multiple regression models
        ↓
Best latency-prediction model
        ↓
ML-based routing
        ↓
Comparison with traditional routing strategies
```

No arbitrary processing-unit scores should be presented as measured ground truth.

---

## 9. File Maintenance Rule

Whenever a new important dataset, paper, standard, library, benchmark, or implementation reference is accepted for the research, add:

* Name
* Direct URL / DOI
* Why it is relevant
* Whether it is confirmed, candidate, or deprecated
* Date checked

This file should be kept with the FinCluster research backup.
