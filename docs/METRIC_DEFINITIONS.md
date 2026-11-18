# Metric Definitions (V2.1)

Every metric states its population, numerator and denominator. Zero
denominators yield `None` (rendered `n/a`), never 0.0 or 1.0. Proportions
carry 95% Wilson score intervals (`evalstats.wilson`).

## Claim-level states

SUPPORTED, CONTRADICTED, NOT_SUPPORTED, UNCERTAIN (abstention),
EXTRACTION_FAILED, EVALUATION_ERROR (error states).
Resolved = SUPPORTED + CONTRADICTED + NOT_SUPPORTED.

## End-to-end metrics (evaluate / evaluate-v2)

| Metric | Numerator | Denominator |
|---|---|---|
| Faithfulness | SUPPORTED verdicts | resolved verdicts of answerable, non-refused answers |
| Hallucination rate (answerable) | CONTRADICTED + NOT_SUPPORTED | same as faithfulness |
| Fabrication rate (unanswerable) | unanswerable questions answered | unanswerable questions |
| Answer relevancy | judge score sum (0–1 each) | all questions (refusals on unanswerable = 1.0) |
| Context precision | AP-weighted relevant passages | per-question AP then mean over answerable questions; V2 judge independent of reranker |
| Context recall | reference sentences attributed | reference sentences of answerable questions |
| Refusal accuracy | correct refusals | unanswerable questions |
| Over-refusal rate | wrong refusals | answerable questions |
| Citation coverage | answers with ≥1 valid citation | answerable non-refused answers |
| Citation validity rate | 1 − invalid attempts / all attempts | all citation attempts (invalid tracked, not filtered away) |
| Claim extraction success rate | answer_state OK | answerable non-refused answers |
| Evaluation error rate | answer_state EVALUATION_ERROR | answerable non-refused answers |

Faithfulness is `None` when extraction/verification fails or nothing resolved —
fail-closed, never a manufactured score.

## Fixture benchmark metrics (adversarial / grid)

| Metric | Numerator | Denominator |
|---|---|---|
| Adversarial detection rate | expected ∈ {CONTRADICTED, NOT_SUPPORTED} predicted in same set | adversarial-expected resolved cases |
| False acceptance rate (FAR) | adversarial-expected predicted SUPPORTED | adversarial-expected resolved cases |
| False rejection rate (FRR) | SUPPORTED-expected predicted ∈ {CONTRADICTED, NOT_SUPPORTED} | SUPPORTED-expected resolved cases |
| Exact status accuracy | expected == predicted | resolved cases |
| Uncertain rate | predicted UNCERTAIN | resolved cases |
| Evaluation error rate | error-state records | all records |
| Contradiction precision | TP | TP + FP (binary CONTRADICTED vs rest) |
| Contradiction recall | TP | TP + FN |
| Contradiction F1 | 2PR/(P+R) | — (None if P or R undefined) |
| Coverage | resolved records | all records |
| Accuracy (resolved only) | correct resolved | resolved records |
| Injection flagged | injection cases with security flag | injection cases |

Raw TP/FP/TN/FN and the 4×4 confusion matrix (expected × predicted) are
included; error-state records are excluded from the matrix and counted
separately. Macro averages = unweighted mean of per-category values (categories
with undefined values skipped, counts reported); micro = pooled counts.

## Retrieval probes / grid retrieval side

Evidence hit@10 = cases with ≥1 gold evidence passage in top-10 / cases;
MRR = mean reciprocal rank of first gold passage (0 if absent);
evidence recall@4 = mean |gold ∩ top-4| / |gold|. No LLM judge involved.

## Red-team metamorphic metrics

Pass rate = pairs satisfying their relation property / pairs executed.
Properties: equivalent → outcome preserved; contradicts → outcome changed and
not SUPPORTED; unsupported → not SUPPORTED. Deterministic mode executes only
mutations it can decide (lexical/numeric/modality); role swaps and paraphrase
invariance require the semantic stage and are labeled accordingly.

## Uncertainty language

With n = 72 adversarial-expected cases, FAR 0.000 has Wilson 95% upper bound
≈ 0.051. Statements like "zero false acceptances" always refer to the observed
sample; universal reliability is NOT claimed.