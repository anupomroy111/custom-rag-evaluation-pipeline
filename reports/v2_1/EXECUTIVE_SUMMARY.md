# V2.1 Executive Summary (reviewer-ready)

All numbers below come from executed runs; execution status is labeled
per stage. Nothing mocked is presented as a benchmark.

## Executed-run inventory

| Stage | Status | Source |
|---|---|---|
| End-to-end ablation (4 variants × 12 Q) | live | eval_v2_20261118_071158.json |
| Ablation grid (4 variants × 3 splits) | mixed-replay | newest reports/v2_1/grid_*.json |
| Red-team metamorphic (deterministic) | executed | redteam_deterministic.json |
| Adversarial deterministic floor | executed | newest adversarial_deterministic_none_*.json |
| Red-team semantic (live) | not-run (quota reserved) | — |

## End-to-end ablation (original golden set, live judge)

| Variant | Faithfulness | Halluc. (answ.) | Fabrication (unansw.) | Ctx precision | Ctx recall | Refusal acc | Citation validity |
|---|---|---|---|---|---|---|---|
| bm25 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | 1.000 | 0.000 | 0.000 | 0.925 | 1.000 | 1.000 | 1.000 |
| hybrid | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid+rerank | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Ablation grid — verification against retrieved evidence

| Split | Variant | Judge | Detection | FAR (95% CI) | FRR | Exact |
|---|---|---|---|---|---|---|
| adversarial | bm25 | none | 0.569 | 0.000 [0.000, 0.051] | 0.156 | 0.288 |
| adversarial | dense | none | 0.569 | 0.000 [0.000, 0.051] | 0.156 | 0.308 |
| adversarial | hybrid | none | 0.583 | 0.000 [0.000, 0.051] | 0.156 | 0.308 |
| adversarial | hybrid+rerank | none | 0.583 | 0.000 [0.000, 0.051] | 0.156 | 0.308 |
| development | bm25 | none | 0.629 | 0.000 [0.000, 0.099] | 0.174 | 0.367 |
| development | dense | none | 0.629 | 0.000 [0.000, 0.099] | 0.174 | 0.367 |
| development | hybrid | none | 0.629 | 0.000 [0.000, 0.099] | 0.174 | 0.367 |
| development | hybrid+rerank | cached-live | 1.000 | 0.000 [0.000, 0.099] | 0.000 | 0.850 |
| heldout | bm25 | none | 0.459 | 0.000 [0.000, 0.043] | 0.204 | 0.300 |
| heldout | dense | none | 0.459 | 0.000 [0.000, 0.043] | 0.204 | 0.307 |
| heldout | hybrid | none | 0.459 | 0.000 [0.000, 0.043] | 0.204 | 0.300 |
| heldout | hybrid+rerank | cached-live | 1.000 | 0.000 [0.000, 0.043] | 0.000 | 0.786 |

### Held-out live semantic (hybrid+rerank) — headline

- Detection 1.000 [0.957, 1.000]
- FAR 0.000 [0.000, 0.043] (n=85)
- FRR 0.000 [0.000, 0.080]
- Exact accuracy 0.786 [0.711, 0.846]
- Contradiction F1 0.852
- Abstentions: 9 uncertain, 0 errors; coverage 0.936

Per-category (held-out, live):

| Category | n | Exact | Uncertain |
|---|---|---|---|
| causal_inference | 8 | 0.875 | 0 |
| citation_manipulation | 10 | 1.000 | 0 |
| context_injection | 10 | 0.900 | 0 |
| entity_attribution | 16 | 0.688 | 0 |
| modality | 11 | 0.909 | 0 |
| multi_hop | 11 | 0.727 | 0 |
| negation_flip | 21 | 0.667 | 7 |
| numerical | 14 | 1.000 | 0 |
| paraphrase_equivalence | 11 | 0.909 | 1 |
| role_reversal | 4 | 1.000 | 0 |
| scope_ambiguity | 10 | 0.000 | 0 |
| temporal | 14 | 0.929 | 1 |

## Red-team metamorphic (deterministic)

- Pairs 22, passed 22, rate 1.000

## Deterministic floor (104 fixtures, zero judge calls)

- Detection 0.583, FAR 0.000 n/a, FRR 0.000
- Exact 0.317, uncertain 0.596

## Failure analysis & limitations

- Misclassified/unresolved claims are listed per report (grid JSON `records`, benchmark Markdown sections).
- Known limitations: docs/LIMITATIONS.md (15 items).
- Metric denominators & CIs: docs/METRIC_DEFINITIONS.md.
- Provenance manifests embedded in every V2.1 report.
