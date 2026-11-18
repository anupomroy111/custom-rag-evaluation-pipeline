# Adversarial Benchmark Report (V2)

- **Generated:** 2026-11-18 08:09:51
- **Mode:** semantic  |  **Judge:** live
- **Cases:** 20  |  **Claim records:** 20
- **Provenance:** synthetic-author-reviewed fixtures; no independent human validation

## Summary

| Metric | Value |
|---|---|
| Adversarial detection rate | 1.000 |
| False acceptance rate | 0.000 |
| False rejection rate | 0.000 |
| Exact status accuracy | 0.800 |
| Uncertain rate | 0.250 |
| Evaluation error rate | 0.000 |
| Deterministic/semantic disagreements | 2 |
| Injection cases flagged | 0/0 |

## Contradiction detection (binary)

TP=3 FP=2 FN=1 · precision=0.600 recall=0.750 F1=0.667

## Per-category accuracy (exact status match)

| Category | n | Accuracy | Uncertain |
|---|---|---|---|
| entity_attribution | 6 | 0.833 | 1 |
| multi_hop | 4 | 0.500 | 0 |
| negation_flip | 2 | 1.000 | 0 |
| paraphrase_equivalence | 3 | 0.667 | 1 |
| role_reversal | 1 | 1.000 | 0 |
| scope_ambiguity | 4 | 1.000 | 3 |

## Confusion matrix (expected rows × predicted columns)

| expected \ predicted | SUPPORTED | CONTRADICTED | NOT_SUPPORTED | UNCERTAIN |
|---|---|---|---|---|
| SUPPORTED | 7 | 0 | 0 | 1 |
| CONTRADICTED | 0 | 3 | 1 | 0 |
| NOT_SUPPORTED | 0 | 2 | 2 | 0 |
| UNCERTAIN | 0 | 0 | 0 | 4 |

Excluded error-state records: 0

## Misclassified / unresolved claims

- **F22-01** [paraphrase_equivalence] expected SUPPORTED, got UNCERTAIN: "The Scheduler restarts services after 3 consecutive failures."
  - flags: entity: 'The Scheduler' absent from evidence; entity: 'Scheduler' absent from evidence
- **F23-02** [multi_hop] expected CONTRADICTED, got NOT_SUPPORTED: "Service C depends on service A."
  - flags: role_reversal: object precedes subject in 'Service B depends on service C.'
- **F23-03** [multi_hop] expected NOT_SUPPORTED, got CONTRADICTED: "Service A depends on service D."
  - flags: entity: 'service D' absent from evidence
- **F24-05** [entity_attribution] expected NOT_SUPPORTED, got CONTRADICTED: "The sales team maintains the security policy."
  - flags: entity: 'sales team' absent from evidence
