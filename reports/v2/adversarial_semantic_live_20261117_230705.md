# Adversarial Benchmark Report (V2)

- **Generated:** 2026-11-17 23:07:05
- **Mode:** semantic  |  **Judge:** live
- **Cases:** 2  |  **Claim records:** 2
- **Provenance:** synthetic-author-reviewed fixtures; no independent human validation

## Summary

| Metric | Value |
|---|---|
| Adversarial detection rate | 1.000 |
| False acceptance rate | 0.000 |
| False rejection rate | n/a |
| Exact status accuracy | 1.000 |
| Uncertain rate | 0.000 |
| Evaluation error rate | 0.000 |
| Deterministic/semantic disagreements | 0 |
| Injection cases flagged | 0/0 |

## Contradiction detection (binary)

TP=2 FP=0 FN=0 · precision=1.000 recall=1.000 F1=1.000

## Per-category accuracy (exact status match)

| Category | n | Accuracy | Uncertain |
|---|---|---|---|
| negation_flip | 2 | 1.000 | 0 |

## Confusion matrix (expected rows × predicted columns)

| expected \ predicted | SUPPORTED | CONTRADICTED | NOT_SUPPORTED | UNCERTAIN |
|---|---|---|---|---|
| SUPPORTED | 0 | 0 | 0 | 0 |
| CONTRADICTED | 0 | 2 | 0 | 0 |
| NOT_SUPPORTED | 0 | 0 | 0 | 0 |
| UNCERTAIN | 0 | 0 | 0 | 0 |

Excluded error-state records: 0
