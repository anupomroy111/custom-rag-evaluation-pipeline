# Evaluation Methodology (V2)

## Principles

1. **Fail-closed.** Every failure mode (empty extraction, malformed JSON, API
   timeout, missing verdicts, blocked completion) produces an explicit state
   and a `None` score — never a manufactured 1.0 or 0.0.
2. **Auditable.** Every score decomposes into per-claim verdicts with
   explanations, deterministic flags, semantic status and disagreement markers.
3. **No circular judges.** V2 context precision uses an independent relevance
   judge, never the reranker's own grades (V1 audit finding M1).
4. **No incompatible aggregation.** Answerable hallucination rate and
   unanswerable fabrication rate are separate metrics; no composite score.
5. **Ordinal confidence.** LLM confidence is recorded but never treated as a
   calibrated probability.
6. **Untrusted evidence.** Retrieved passages are data, not instructions;
   injection-bearing sentences are excluded from deterministic evidence checks
   and flagged as security signals.

## Metric definitions

### End-to-end (evaluate-v2)

- **Faithfulness** = SUPPORTED / (SUPPORTED + CONTRADICTED + NOT_SUPPORTED)
  over engine verdicts; `None` when unresolved or errored.
- **Hallucination rate (answerable)** = 1 − faithfulness, same population.
- **Fabrication rate (unanswerable)** = fraction of unanswerable questions
  answered instead of refused.
- **Answer relevancy** — independent LLM judge, 0–1; correct refusals = 1.0.
- **Context precision** — AP-style rank weighting over an INDEPENDENT LLM
  relevance judgment of the final passages.
- **Context recall** — fraction of reference-answer sentences attributable to
  retrieved context (LLM judge).
- **Refusal accuracy / over-refusal rate** — deterministic from refusal flags.
- **Citation coverage** — fraction of answered items carrying ≥1 valid citation.
- **Citation validity rate** = 1 − invalid citation attempts / all attempts
  (invalid attempts are now tracked, not silently filtered).
- **Claim extraction success rate** — fraction of answered items whose
  extraction state is OK.
- **Evaluation error rate** — fraction of answered items in EVALUATION_ERROR.

### Adversarial fixture benchmark

- **Confusion matrix** over {SUPPORTED, CONTRADICTED, NOT_SUPPORTED, UNCERTAIN};
  error-state records excluded and counted separately.
- **Adversarial detection rate** = adversarial-expected cases predicted
  CONTRADICTED or NOT_SUPPORTED / adversarial-expected cases.
- **False acceptance rate** = adversarial-expected predicted SUPPORTED /
  adversarial-expected.
- **False rejection rate** = SUPPORTED-expected predicted CONTRADICTED or
  NOT_SUPPORTED / SUPPORTED-expected.
- **Contradiction precision/recall/F1** — binary CONTRADICTED vs rest, with
  TP/FP/FN counts.
- **Per-category exact-match accuracy** with n and UNCERTAIN counts.
- **Injection flagged** — security-signal coverage over injection cases.

### Retrieval probes

- **Evidence hit@10**, **MRR**, **evidence recall@4** — deterministic set
  operations against gold evidence passage ids; no LLM involvement.

## Disagreement handling

When deterministic evidence flags conflict with a semantic SUPPORTED verdict,
the claim is marked `disagreement=True`. Exact numerical conflicts resolve to
CONTRADICTED (deterministic arithmetic is reliable); all other conflicts resolve
to UNCERTAIN and are listed in reports for explicit human review. Disagreement
counts are reported per run.

## Reproducibility

- Deterministic mode and all unit/integration tests run with zero API calls.
- Semantic responses are cached on disk keyed by (model, system, prompt,
  temperature, json_mode); re-running a benchmark replays cached judgments.
- Reports record model names, mode, judge label (live/mocked/none), timestamp
  and API usage stats.
- V1 reports in `reports/` are immutable history; V2 writes to `reports/v2/`.

## Threats to validity

- Synthetic fixtures authored by one person; label bias possible. Controls and
  documented edge cases mitigate but do not eliminate this.
- LLM judge is itself fallible; disagreement flags and deterministic
  cross-checks bound but do not remove judge error.
- Free-tier quota limits live run sizes; partial runs are labeled, never
  silently completed with mocks. (Incident: gemini-3.5-flash-lite 500 req/day
  cap exhausted mid-ablation; hybrid/hybrid+rerank V2 end-to-end variants
  remain not-run-live, documented in FINAL_V2_REPORT.md.)
- Verifier heuristics themselves can be wrong: incident B16 (multi-fact
  contexts producing false contradiction flags) was caught by mid-run audit,
  fixed with support-aware checks, and covered by regression tests. Interim
  scores produced by the buggy verifier were invalidated and regenerated.
- 12-question original golden set and 104 fixtures are small samples; rates
  carry wide confidence intervals and are reported with counts.