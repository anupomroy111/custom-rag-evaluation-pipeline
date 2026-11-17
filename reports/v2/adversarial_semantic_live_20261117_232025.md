# Adversarial Benchmark Report (V2)

- **Generated:** 2026-11-17 23:20:25
- **Mode:** semantic  |  **Judge:** live
- **Cases:** 104  |  **Claim records:** 104
- **Provenance:** synthetic-author-reviewed fixtures; no independent human validation

## Summary

| Metric | Value |
|---|---|
| Adversarial detection rate | 0.986 |
| False acceptance rate | 0.000 |
| False rejection rate | 0.062 |
| Exact status accuracy | 0.903 |
| Uncertain rate | 0.049 |
| Evaluation error rate | 0.010 |
| Deterministic/semantic disagreements | 5 |
| Injection cases flagged | 13/13 |

## Contradiction detection (binary)

TP=51 FP=3 FN=1 · precision=0.944 recall=0.981 F1=0.962

## Per-category accuracy (exact status match)

| Category | n | Accuracy | Uncertain |
|---|---|---|---|
| context_injection | 13 | 1.000 | 0 |
| entity_attribution | 13 | 0.846 | 1 |
| modality | 13 | 1.000 | 0 |
| multi_hop | 13 | 0.846 | 0 |
| negation_flip | 13 | 1.000 | 0 |
| numerical | 12 | 1.000 | 0 |
| role_reversal | 13 | 0.769 | 2 |
| temporal | 13 | 0.769 | 2 |

## Confusion matrix (expected rows × predicted columns)

| expected \ predicted | SUPPORTED | CONTRADICTED | NOT_SUPPORTED | UNCERTAIN |
|---|---|---|---|---|
| SUPPORTED | 26 | 0 | 2 | 4 |
| CONTRADICTED | 0 | 51 | 0 | 1 |
| NOT_SUPPORTED | 0 | 3 | 16 | 0 |
| UNCERTAIN | 0 | 0 | 0 | 0 |

Excluded error-state records: 0

## Misclassified / unresolved claims

- **ROLE-007** [role_reversal] expected SUPPORTED, got UNCERTAIN: "Alice approved Bob's request."
  - flags: role_reversal: object precedes subject in 'Bob's request was approved by Alice.'
- **ROLE-010** [role_reversal] expected SUPPORTED, got UNCERTAIN: "Bob met Alice."
  - flags: role_reversal: object precedes subject in 'Alice met Bob.'
- **ROLE-011** [role_reversal] expected NOT_SUPPORTED, got CONTRADICTED: "Bob approved his own request."
- **ENT-007** [entity_attribution] expected SUPPORTED, got UNCERTAIN: "The model was developed by Company A."
  - flags: role_reversal: object precedes subject in 'Company A developed the model.'
- **ENT-012** [entity_attribution] expected NOT_SUPPORTED, got CONTRADICTED: "Alice is the account manager."
- **NUM-012** [numerical] expected NOT_SUPPORTED, got EVALUATION_ERROR: "The maximum image size is 10 MB."
- **TEMP-005** [temporal] expected CONTRADICTED, got UNCERTAIN: "v2.4.0 will be released on 2026-09-10."
  - flags: temporal: planned/completed reversal vs 'v2.4.0 was released on 2026-09-10.'
- **TEMP-008** [temporal] expected SUPPORTED, got NOT_SUPPORTED: "PostgreSQL 16 has been used after June 2026."
- **TEMP-012** [temporal] expected SUPPORTED, got UNCERTAIN: "The dry-run flag shipped before v2.3.0."
  - flags: entity: 'v2.3.0' absent from evidence
- **HOP-003** [multi_hop] expected SUPPORTED, got NOT_SUPPORTED: "The Builder caches layers in S3-compatible storage."
- **HOP-011** [multi_hop] expected NOT_SUPPORTED, got CONTRADICTED: "Service C depends on service A."
