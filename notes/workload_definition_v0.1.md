# Current Working Definition

## Light Transaction

A transaction that requires:

- Standard validation
- Limited verification steps
- Low computational demand
- Short processing time
- Low expected queue occupation

### Examples

```text
Balance inquiry
Small merchant payment
Low-value transfer
Established account transaction
```

## Heavy Transaction

A transaction that requires:

- Enhanced verification
- Additional fraud or risk checks
- More processing stages
- Higher computational demand
- Longer expected execution time

### Examples

```text
High-value cash-out
VPN-enabled high-value transfer
New-account cash-out
Risky merchant category
```

> **Warning:** Heavy does not mean confirmed fraud. Heavy means that the transaction requires more processing or verification.

## Research Concern

বর্তমান Heavy/Light label handcrafted rules বা synthetic formula থেকে তৈরি হলে model শুধু ওই formula শিখতে পারে।

## Proposed Improvement

Future ground truth should be based on measurable processing requirements such as:

```text
Execution time
CPU usage
Memory usage
Number of verification stages
Queue waiting time
```

## External Dataset Adaptation

An external financial transaction dataset may contain fraud labels,
but fraud and processing workload are different concepts.

The fraud label will not be directly converted into the Heavy/Light
workload label.

Instead, each transaction will be passed through a documented
processing workflow. Workload ground truth will be determined using:

- Number of validation stages
- Simulated or measured processing time
- CPU demand
- Memory demand
- Enhanced verification requirements
- Queue occupation

This separation is necessary to avoid presenting fraud prediction as
workload classification.