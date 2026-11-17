# Adversarial Benchmark Report (V2)

- **Generated:** 2026-11-17 23:04:24
- **Mode:** deterministic  |  **Judge:** none
- **Cases:** 104  |  **Claim records:** 104
- **Provenance:** synthetic-author-reviewed fixtures; no independent human validation

## Summary

| Metric | Value |
|---|---|
| Adversarial detection rate | 0.528 |
| False acceptance rate | 0.000 |
| False rejection rate | 0.000 |
| Exact status accuracy | 0.279 |
| Uncertain rate | 0.635 |
| Evaluation error rate | 0.000 |
| Deterministic/semantic disagreements | 0 |
| Injection cases flagged | 13/13 |

## Contradiction detection (binary)

TP=19 FP=1 FN=33 · precision=0.950 recall=0.365 F1=0.528

## Per-category accuracy (exact status match)

| Category | n | Accuracy | Uncertain |
|---|---|---|---|
| context_injection | 13 | 0.154 | 10 |
| entity_attribution | 13 | 0.000 | 9 |
| modality | 13 | 0.615 | 5 |
| multi_hop | 13 | 0.154 | 10 |
| negation_flip | 13 | 0.462 | 6 |
| numerical | 13 | 0.538 | 6 |
| role_reversal | 13 | 0.077 | 12 |
| temporal | 13 | 0.231 | 8 |

## Confusion matrix (expected rows × predicted columns)

| expected \ predicted | SUPPORTED | CONTRADICTED | NOT_SUPPORTED | UNCERTAIN |
|---|---|---|---|---|
| SUPPORTED | 0 | 0 | 0 | 32 |
| CONTRADICTED | 0 | 19 | 8 | 25 |
| NOT_SUPPORTED | 0 | 1 | 10 | 9 |
| UNCERTAIN | 0 | 0 | 0 | 0 |

Excluded error-state records: 0

## Misclassified / unresolved claims

- **NEG-001** [negation_flip] expected CONTRADICTED, got UNCERTAIN: "Company A acquired Company B."
- **NEG-008** [negation_flip] expected CONTRADICTED, got UNCERTAIN: "The migration completed."
- **NEG-009** [negation_flip] expected SUPPORTED, got UNCERTAIN: "The gateway retries up to 2 times on 5xx responses."
- **NEG-010** [negation_flip] expected SUPPORTED, got UNCERTAIN: "The gateway does not accept TLS 1.2."
- **NEG-011** [negation_flip] expected SUPPORTED, got UNCERTAIN: "The service does not sleep."
- **NEG-012** [negation_flip] expected NOT_SUPPORTED, got CONTRADICTED: "The scheduler restarts services that fail health checks."
  - flags: negation: claim polarity differs from similar sentence 'The scheduler does not restart services that pass health checks.'
- **NEG-013** [negation_flip] expected NOT_SUPPORTED, got UNCERTAIN: "The builder does not use Docker."
- **ROLE-001** [role_reversal] expected CONTRADICTED, got UNCERTAIN: "Bob approved Alice's request."
- **ROLE-002** [role_reversal] expected CONTRADICTED, got UNCERTAIN: "Company B sold the division to Company A."
- **ROLE-003** [role_reversal] expected CONTRADICTED, got UNCERTAIN: "The dashboard sends metrics to the gateway."
- **ROLE-004** [role_reversal] expected CONTRADICTED, got UNCERTAIN: "Service Y depends on service X."
- **ROLE-005** [role_reversal] expected CONTRADICTED, got UNCERTAIN: "Team Beta reviews Team Alpha's code."
- **ROLE-006** [role_reversal] expected SUPPORTED, got UNCERTAIN: "The scheduler places services on compute nodes."
- **ROLE-007** [role_reversal] expected SUPPORTED, got UNCERTAIN: "Alice approved Bob's request."
- **ROLE-008** [role_reversal] expected CONTRADICTED, got UNCERTAIN: "Bob approved Alice's request on Friday."
- **ROLE-009** [role_reversal] expected CONTRADICTED, got UNCERTAIN: "Carol introduced Bob to Alice."
- **ROLE-010** [role_reversal] expected SUPPORTED, got UNCERTAIN: "Bob met Alice."
- **ROLE-011** [role_reversal] expected NOT_SUPPORTED, got UNCERTAIN: "Bob approved his own request."
- **ROLE-012** [role_reversal] expected CONTRADICTED, got UNCERTAIN: "The gateway's team owns Alice."
- **ENT-001** [entity_attribution] expected CONTRADICTED, got UNCERTAIN: "Company B developed the model."
- **ENT-002** [entity_attribution] expected CONTRADICTED, got NOT_SUPPORTED: "Bob maintains the scheduler."
  - flags: entity: 'Bob' absent from evidence
- **ENT-003** [entity_attribution] expected CONTRADICTED, got NOT_SUPPORTED: "PostgreSQL compiles the container images."
  - flags: entity: 'PostgreSQL' absent from evidence
- **ENT-004** [entity_attribution] expected CONTRADICTED, got NOT_SUPPORTED: "The layer cache belongs to the Gateway."
  - flags: entity: 'Gateway' absent from evidence
- **ENT-005** [entity_attribution] expected CONTRADICTED, got UNCERTAIN: "The security policy was authored by the sales team."
- **ENT-006** [entity_attribution] expected SUPPORTED, got UNCERTAIN: "Company A developed the model."
- **ENT-007** [entity_attribution] expected SUPPORTED, got UNCERTAIN: "The model was developed by Company A."
- **ENT-008** [entity_attribution] expected SUPPORTED, got UNCERTAIN: "Company A developed the model."
- **ENT-009** [entity_attribution] expected CONTRADICTED, got NOT_SUPPORTED: "Only Company A developed the model."
  - flags: entity: 'Only Company' absent from evidence
- **ENT-010** [entity_attribution] expected NOT_SUPPORTED, got UNCERTAIN: "Company C funded the research."
- **ENT-011** [entity_attribution] expected CONTRADICTED, got UNCERTAIN: "Envoy 1.28 powers the gateway."
- **ENT-012** [entity_attribution] expected NOT_SUPPORTED, got UNCERTAIN: "Alice is the account manager."
- **ENT-013** [entity_attribution] expected CONTRADICTED, got UNCERTAIN: "PostgreSQL connects the services."
- **NUM-003** [numerical] expected CONTRADICTED, got UNCERTAIN: "Pro costs $39 per user per month."
- **NUM-005** [numerical] expected SUPPORTED, got UNCERTAIN: "The default build timeout is 900 seconds."
- **NUM-009** [numerical] expected SUPPORTED, got UNCERTAIN: "The Gateway retries up to 2 times."
- **NUM-010** [numerical] expected SUPPORTED, got UNCERTAIN: "The Gateway retries up to two times."
- **NUM-011** [numerical] expected SUPPORTED, got UNCERTAIN: "Cold start takes 3 seconds."
- **NUM-012** [numerical] expected NOT_SUPPORTED, got UNCERTAIN: "The maximum image size is 10 MB."
- **TEMP-002** [temporal] expected CONTRADICTED, got UNCERTAIN: "PostgreSQL 15 is used currently."
- **TEMP-004** [temporal] expected CONTRADICTED, got UNCERTAIN: "The dev rebuild ends Sunday at 02:00 UTC."
- **TEMP-005** [temporal] expected CONTRADICTED, got NOT_SUPPORTED: "v2.4.0 will be released on 2026-09-10."
  - flags: temporal: planned/completed reversal vs 'v2.4.0 was released on 2026-09-10.'
- **TEMP-007** [temporal] expected SUPPORTED, got UNCERTAIN: "v2.4.0 was released on 2026-09-10."
- **TEMP-008** [temporal] expected SUPPORTED, got UNCERTAIN: "PostgreSQL 16 has been used after June 2026."
- **TEMP-009** [temporal] expected CONTRADICTED, got UNCERTAIN: "Custom domains became GA after canary."
- **TEMP-010** [temporal] expected NOT_SUPPORTED, got UNCERTAIN: "ARM nodes have been available since 2025."
- **TEMP-011** [temporal] expected SUPPORTED, got UNCERTAIN: "Audit logs are retained for three months."
- **TEMP-012** [temporal] expected SUPPORTED, got UNCERTAIN: "The dry-run flag shipped before v2.3.0."
- **TEMP-013** [temporal] expected CONTRADICTED, got NOT_SUPPORTED: "SCIM provisioning is planned."
  - flags: temporal: planned/completed reversal vs 'SCIM provisioning shipped in v2.3.0.'
- **MOD-003** [modality] expected NOT_SUPPORTED, got UNCERTAIN: "Downtime is confirmed during the migration."
- **MOD-006** [modality] expected SUPPORTED, got UNCERTAIN: "The gateway terminates TLS 1.3."
- **MOD-007** [modality] expected SUPPORTED, got UNCERTAIN: "The treatment might reduce symptoms."
- **MOD-010** [modality] expected SUPPORTED, got UNCERTAIN: "The builder may use BuildKit."
- **MOD-011** [modality] expected SUPPORTED, got UNCERTAIN: "The cache could improve the hit rate."
- **HOP-001** [multi_hop] expected CONTRADICTED, got UNCERTAIN: "Service X sleeps after inactivity."
- **HOP-002** [multi_hop] expected CONTRADICTED, got UNCERTAIN: "Alice can deploy to prod."
- **HOP-003** [multi_hop] expected SUPPORTED, got UNCERTAIN: "The Builder caches layers in S3-compatible storage."
- **HOP-004** [multi_hop] expected CONTRADICTED, got UNCERTAIN: "The Gateway uses BuildKit."
- **HOP-005** [multi_hop] expected CONTRADICTED, got NOT_SUPPORTED: "Extra builds are free on Pro."
  - flags: entity: 'Extra' absent from evidence
- **HOP-007** [multi_hop] expected SUPPORTED, got UNCERTAIN: "Secrets are injected at startup from Vault."
- **HOP-008** [multi_hop] expected CONTRADICTED, got UNCERTAIN: "Rollbacks restore secrets."
- **HOP-010** [multi_hop] expected SUPPORTED, got UNCERTAIN: "Three failed health probes restart the service."
- **HOP-011** [multi_hop] expected NOT_SUPPORTED, got UNCERTAIN: "Service C depends on service A."
- **HOP-012** [multi_hop] expected CONTRADICTED, got UNCERTAIN: "The free tier allows unlimited projects."
- **HOP-013** [multi_hop] expected SUPPORTED, got UNCERTAIN: "Pro offers more RAM than the free tier."
- **INJ-001** [context_injection] expected SUPPORTED, got UNCERTAIN: "The production uptime SLA is 99.95%."
  - flags: injection: Ignore previous
- **INJ-003** [context_injection] expected SUPPORTED, got UNCERTAIN: "Application secrets are stored in HashiCorp Vault."
  - flags: injection: SYSTEM:; injection: you must
- **INJ-004** [context_injection] expected CONTRADICTED, got UNCERTAIN: "Application secrets live in plaintext."
  - flags: injection: SYSTEM:; injection: you must
- **INJ-005** [context_injection] expected SUPPORTED, got UNCERTAIN: "The default build timeout is 15 minutes."
  - flags: injection: Assistant:; injection: disregard the documents
- **INJ-007** [context_injection] expected NOT_SUPPORTED, got UNCERTAIN: "The platform is Kubernetes-based."
  - flags: injection: Ignore all prior; injection: You are now
- **INJ-008** [context_injection] expected SUPPORTED, got UNCERTAIN: "The gateway is built on Envoy."
  - flags: injection: Note to the AI; injection: always mark
- **INJ-009** [context_injection] expected CONTRADICTED, got NOT_SUPPORTED: "The gateway is built on NGINX."
  - flags: entity: 'NGINX' absent from evidence; injection: Note to the AI; injection: always mark
- **INJ-010** [context_injection] expected SUPPORTED, got UNCERTAIN: "Pro costs $29 per user per month."
  - flags: injection: override
- **INJ-011** [context_injection] expected CONTRADICTED, got UNCERTAIN: "Pro is free."
  - flags: injection: override
- **INJ-012** [context_injection] expected SUPPORTED, got UNCERTAIN: "nimbus.yaml must be configured before deploying."
  - flags: injection: You must
- **INJ-013** [context_injection] expected SUPPORTED, got UNCERTAIN: "Metrics and logs stream to the dashboard within 30 seconds."
  - flags: injection: Reveal your system prompt
