# FINAL V2 REPORT — Adversarial & Semantic Faithfulness Testing

Generated: 2026-11-17 23:38:52 · Model: gemini-3.5-flash-lite (live) · Fixtures: 104 synthetic, author-reviewed

## 1. Adversarial verification benchmark (104 cases)

| Metric | Deterministic (0 API calls) | Semantic (live judge) |
|---|---|---|
| Adversarial detection rate | 0.583 | 0.986 |
| False acceptance rate | 0.000 | 0.000 |
| False rejection rate | 0.000 | 0.062 |
| Exact status accuracy | 0.317 | 0.903 |
| Uncertain rate | 0.596 | 0.049 |
| Evaluation error rate | 0.000 | 0.010 |
| Injection cases flagged | 13/13 | 13/13 |

Semantic contradiction detection: precision 0.944, recall 0.981, F1 0.962 (TP=51 FP=3 FN=1). Deterministic/semantic disagreements flagged: 5.

### Per-category exact accuracy (semantic live)

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

## 2. Retrieval probes on adversarial evidence (no LLM judge)

| Variant | n | Evidence hit@10 | MRR | Evidence recall@4 |
|---|---|---|---|---|
| bm25 | 104 | 0.9904 | 0.7776 | 0.9231 |
| dense | 104 | 0.9904 | 0.8067 | 0.9615 |
| hybrid | 104 | 0.9904 | 0.8099 | 0.9423 |

Reranking is benchmarked end-to-end (section 3), not in retrieval-only probes.

## 3. End-to-end ablation V2 (original 12-question golden set)

| Variant | Status | n | Faithfulness | Halluc. (answerable) | Fabrication (unanswerable) | Ctx precision | Ctx recall | Refusal acc | Citation validity |
|---|---|---|---|---|---|---|---|---|---|
| bm25 | live-complete | 12 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | live-partial-insufficient | 1 | 1.000 | 0.000 | n/a | 1.000 | 1.000 | n/a | 1.000 |
| hybrid | not-run-quota | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| hybrid+rerank | not-run-quota | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

**Quota incident:** the gemini-3.5-flash-lite free tier allows 500 generate requests/day. The cap was reached during the dense variant (question 2); hybrid and hybrid+rerank were NOT run live and no mocked numbers are presented as benchmarks. Reset was ~14 h away at failure. Complete them after reset with:

```bash
python -m ragpipe.cli evaluate-v2 --variants dense,hybrid,hybrid+rerank
```

The dense row (n=1) is shown only to document partial coverage; it is statistically meaningless.

## 4. Verifier bug incident (B16) — why interim numbers were invalid

Mid-run inspection showed bm25 faithfulness 0.838. Root cause: deterministic checks flagged the number of a claim against a *different* number in another sentence of the same multi-fact context (and negation in unrelated clauses), overriding correct semantic SUPPORTED verdicts. Fixed with support-aware flags (conflict AND no supporting sentence), clause-scoped negation, and a tightened injection regex; three regression tests added. Final bm25 faithfulness: 1.000 (28 SUPPORTED, 1 UNCERTAIN, 1 disagreement). All reports above were regenerated with the fixed code via the disk response cache (zero additional quota).

## 5. Reproduce

```bash
python -m pytest tests/ -q                                  # 98 tests, no API
python -m ragpipe.cli adversarial --mode deterministic      # 0 API calls
python -m ragpipe.cli adversarial --mode semantic           # cached replays are free
python -m ragpipe.cli probes-v2
python -m ragpipe.cli evaluate-v2 --variants bm25,dense,hybrid,hybrid+rerank
```

Source reports: adversarial_deterministic_none_20261117_233359.json, adversarial_semantic_live_20261117_233359.json, probes_20261117_233524.json, eval_v2_20261117_233626.json, eval_v2_20261117_233524.json
