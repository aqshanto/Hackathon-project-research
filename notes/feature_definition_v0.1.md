Group A — সম্ভবত model input

যে তথ্য routing decision-এর আগে পাওয়া যায়:
- type
- amount
- step
- selected pre-transaction balance information

Exact list dataset inspect করার পরে হবে।
Group B — Node features
আমাদের নিজেদের controlled environment থেকে:

- Exact list dataset inspect করার পরে হবে।
- Group B — Node features
- আমাদের নিজেদের controlled environment থেকে:

Group C — বাদ যাবে
বিশেষ করে:
- service_time_ms      ← Target, feature না
- isFraud              ← Workload target না
- isFlaggedFraud       ← review required
- post-execution data  ← leakage হতে পারে
- raw account IDs      ← probably unnecessary