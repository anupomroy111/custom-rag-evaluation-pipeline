# Adversarial Benchmark Report (V2)

- **Generated:** 2026-11-18 08:07:20
- **Mode:** deterministic  |  **Judge:** none
- **Cases:** 20  |  **Claim records:** 20
- **Provenance:** synthetic-author-reviewed fixtures; no independent human validation

## Summary

| Metric | Value |
|---|---|
| Adversarial detection rate | 0.250 |
| False acceptance rate | 0.000 |
| False rejection rate | 0.125 |
| Exact status accuracy | 0.250 |
| Uncertain rate | 0.800 |
| Evaluation error rate | 0.000 |
| Deterministic/semantic disagreements | 0 |
| Injection cases flagged | 0/0 |

## Contradiction detection (binary)

TP=1 FP=1 FN=3 · precision=0.500 recall=0.250 F1=0.333

## Per-category accuracy (exact status match)

| Category | n | Accuracy | Uncertain |
|---|---|---|---|
| entity_attribution | 6 | 0.333 | 5 |
| multi_hop | 4 | 0.000 | 4 |
| negation_flip | 2 | 0.500 | 1 |
| paraphrase_equivalence | 3 | 0.000 | 2 |
| role_reversal | 1 | 0.000 | 1 |
| scope_ambiguity | 4 | 0.500 | 3 |

## Confusion matrix (expected rows × predicted columns)

| expected \ predicted | SUPPORTED | CONTRADICTED | NOT_SUPPORTED | UNCERTAIN |
|---|---|---|---|---|
| SUPPORTED | 0 | 0 | 1 | 7 |
| CONTRADICTED | 0 | 1 | 0 | 3 |
| NOT_SUPPORTED | 0 | 0 | 1 | 3 |
| UNCERTAIN | 0 | 1 | 0 | 3 |

Excluded error-state records: 0

## Misclassified / unresolved claims

- **F21-02** [scope_ambiguity] expected UNCERTAIN, got CONTRADICTED: "The gateway may not be unavailable for retries."
  - flags: negation: claim polarity differs from similar sentence 'The gateway retries up to 2 times on 5xx responses.'
- **F21-04** [scope_ambiguity] expected SUPPORTED, got UNCERTAIN: "The gateway retries up to 2 times on 5xx responses."
- **F21-05** [negation_flip] expected SUPPORTED, got UNCERTAIN: "It is not true that the gateway does not retry on 5xx responses."
- **F22-01** [paraphrase_equivalence] expected SUPPORTED, got NOT_SUPPORTED: "The Scheduler restarts services after 3 consecutive failures."
  - flags: entity: 'The Scheduler' absent from evidence
- **F22-03** [paraphrase_equivalence] expected SUPPORTED, got UNCERTAIN: "It probes /healthz every 10 seconds."
- **F23-01** [multi_hop] expected SUPPORTED, got UNCERTAIN: "Service A depends on service C."
- **F23-02** [multi_hop] expected CONTRADICTED, got UNCERTAIN: "Service C depends on service A."
- **F23-03** [multi_hop] expected NOT_SUPPORTED, got UNCERTAIN: "Service A depends on service D."
- **F23-04** [role_reversal] expected CONTRADICTED, got UNCERTAIN: "Service B depends on service A."
- **F23-05** [multi_hop] expected SUPPORTED, got UNCERTAIN: "Service A depends on service B."
- **F24-01** [entity_attribution] expected CONTRADICTED, got UNCERTAIN: "The sales team authored the security policy."
- **F24-02** [entity_attribution] expected NOT_SUPPORTED, got UNCERTAIN: "The platform team owns application secrets."
- **F24-03** [entity_attribution] expected SUPPORTED, got UNCERTAIN: "Vault stores application secrets."
- **F24-04** [paraphrase_equivalence] expected SUPPORTED, got UNCERTAIN: "The security policy was authored by the platform team."
- **F24-05** [entity_attribution] expected NOT_SUPPORTED, got UNCERTAIN: "The sales team maintains the security policy."
