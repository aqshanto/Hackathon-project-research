# External Dataset Candidate

## Candidate
PaySim-style Synthetic Mobile Money Dataset

## Why It Is Relevant
- Mobile-money transaction context
- Multiple transaction types
- Transaction amounts and account balances
- Widely used for fraud-related experimentation
- Privacy-safe and reproducible

## Important Limitation
The dataset contains fraud labels, not Heavy/Light workload labels.

## Proposed Use
Use transaction attributes as external input data and derive workload
ground truth through documented or measured processing demand.

## Questions to Resolve
- Which exact PaySim repository/version will be used?
- What license applies?
- How will workload ground truth be generated?
- Will the full dataset or a stratified subset be used?
- How will train/validation/test splitting avoid leakage?