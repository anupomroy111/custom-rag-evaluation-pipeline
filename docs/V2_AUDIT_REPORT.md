# V2 Audit Report — Custom RAG & Evaluation Pipeline

Audit date: 2026-11-17 · Auditor: automated repository inspection (all modules read in full)
Scope: pre-upgrade audit for "RAG Evaluation Pipeline V2.0 — Adversarial & Semantic Faithfulness Testing".
No implementation was modified before this report was completed.

## 1. Repository structure (as audited)

```
ragpipe/
  config.py        settings dataclass, .env loading
  llm.py           GeminiClient (pacing, retry, JSON mode), parse_json
  ingest.py        document loading, recursive chunking, chunk persistence
  embeddings.py    JSON vector cache, pure-Python normalize
  retrieval.py     Okapi BM25 (pure Python), dense cosine, RRF fusion
  rerank.py        listwise LLM reranking with 0–3 grades
  generator.py     grounded generation, citation extraction, refusal marker
  pipeline.py      index build + end-to-end orchestration
  evaluate/
    metrics.py     claim extraction/verification, relevancy, precision, recall judges
    runner.py      golden-dataset runner, variants, summarize, checkpointing
    report.py      Markdown report rendering
  cli.py           ingest / ask / evaluate
data/docs/         7-document sample corpus (13 chunks)
data/golden_dataset.json   12 questions (10 answerable, 2 unanswerable)
tests/             32 unit tests (all passing at audit time)
reports/           V1 live reports (base, ablation, merged comparison)
```

Dependencies: `google-genai`, `python-dotenv`, `pytest`. Pure-Python retrieval
(NumPy unavailable on this host: Windows Application Control blocks its DLL).
Python 3.15, no GPU. LLM: `gemini-3.5-flash-lite` via v1beta (2.5-flash free tier
is 20 req/day and closed to new keys).

## 2. Execution flow

`ingest` → chunk → embed (cached) → `index/`.
`ask`/`evaluate` → HybridRetriever.search (BM25 and/or dense → RRF) → optional
llm_rerank (top-4) → generate_answer (citations, refusal) → evaluate.metrics
judges (extract claims → verify; relevancy; precision; recall) → runner
aggregates → JSON + Markdown reports, per-item checkpoint.

## 3. Strengths (preserve in V2)

- Correct Okapi BM25 and standard RRF (`1/(k+rank)`), fully inspectable, no native deps.
- Rank-based fusion avoids score calibration between BM25 and cosine.
- Deterministic citation filtering against actually-retrieved ids (generator.py:30-38).
- Explicit refusal protocol for unanswerable questions; refusal accuracy tracked.
- Per-claim audit trail in every report; checkpoint after each item.
- Embedding cache keyed by chunk id + model + dim; client-side RPM pacing + backoff.
- Ablation framework (4 retrieval variants) with honest reporting of null results.
- 32 passing unit tests covering chunking, BM25, RRF math, rerank, citations, metrics math.

## 4. Critical bugs — fail-open and silent failure paths

| # | Severity | Location | Finding |
|---|---|---|---|
| B1 | CRITICAL | evaluate/metrics.py:70-71 | `if not claims: return FaithfulnessResult(score=1.0)` — extraction failure (malformed JSON, blocked response) is indistinguishable from a genuine refusal and receives a perfect score. Fail-open. |
| B2 | CRITICAL | evaluate/metrics.py:63 | `extract_claims` silently returns `[]` for non-dict responses or missing `claims` key; feeds B1. |
| B3 | HIGH | evaluate/metrics.py:79-85 | Missing/partial verdict entries become `supported=False` silently; verdicts aligned by position, not claim identity — misalignment corrupts scores without any error state. |
| B4 | HIGH | llm.py:48 | `resp.text or ""` — safety-blocked or empty completions become empty strings that flow downstream as valid answers/JSON inputs. |
| B5 | HIGH | llm.py:49-53, 78-81 | Retries catch only `errors.APIError`; transport failures (timeouts, connection resets) crash the run. No explicit request timeout configured. |
| B6 | HIGH | evaluate/runner.py:74-79 | Over-refusal on answerable questions sets `hallucination_rate=0.0`; the failure is invisible in the headline hallucination metric. |
| B7 | HIGH | evaluate/runner.py:149 | `hallucination_rate` averages two incompatible populations (answerable `1−faithfulness` and unanswerable fabrication flags) into one misleading number. |
| B8 | MEDIUM | llm.py:93-95 | `parse_json` greedy regex fallback can extract a wrong brace substring from prose and silently return a mis-shaped object. |
| B9 | MEDIUM | evaluate/metrics.py:93,121 | `float(...)`/`int(...)` on judge fields can raise uncaught ValueError/TypeError; malformed relevancy silently scores 0.0 with no error state. |
| B10 | MEDIUM | rerank.py:32-34 | Malformed grade entries silently skipped; ungraded candidates default to 0 — degraded ordering with no error signal. |
| B11 | MEDIUM | retrieval.py:78 | `zip(row, q)` silently truncates on embedding-dimension mismatch → wrong similarities, no validation. |
| B12 | MEDIUM | generator.py:50 | Refusal detected by substring; an answer quoting the marker misclassifies. Empty answer text + B1 yields faithfulness 1.0. |
| B13 | LOW | evaluate/runner.py:122-126 | Single global `checkpoint.json` overwritten by every run; concurrent/sequential runs clobber each other. |
| B14 | LOW | evaluate/report.py | Markdown cells not escaped; `|` in question text breaks tables. |
| B15 | LOW | tests/test_metrics_eval.py (`test_faithfulness_no_claims`) | Test encodes B1 as expected behavior — must be updated with documentation when B1 is fixed. |

## 5. Evaluation methodology limitations

- M1: **Circular precision judge** — `context_precision` uses the reranker's own
  grades as relevance ground truth when reranking is on (metrics.py:110-111).
  The component being evaluated supplies its own labels.
- M2: **Binary verdicts only** — no CONTRADICTED vs NOT_SUPPORTED distinction;
  contradiction (active falsehood) and silence (unsupported) collapse into one bit.
- M3: **No uncertainty/error states** — UNCERTAIN, EXTRACTION_FAILED,
  EVALUATION_ERROR do not exist; every path produces a number.
- M4: **No adversarial coverage** — negation flips, role reversals, entity
  misattribution, numerical/temporal/modality contradictions, multi-hop fallacies
  and prompt injection are untested. V1's perfect 1.0 scores on a lexically-aligned
  corpus do not demonstrate robustness to any of these.
- M5: **No citation validity metric** — invalid citation attempts are filtered out
  (generator.py:36-37) and never counted.
- M6: **LLM confidence treated as fact** — judge outputs are consumed without
  schema validation or disagreement checks against deterministic evidence.
- M7: **No extraction success / evaluation error rates** — failed evaluations are
  invisible in summaries (they become 1.0 or 0.0 via B1/B9).

## 6. Security & reliability concerns

- S1: **Prompt injection surface** — retrieved document text is interpolated
  directly into generator/rerank/judge prompts with no untrusted-data framing or
  instruction-resistance clause (generator.py:42-45, rerank.py:21-24,
  metrics.py:72-75). A corpus document containing instructions could steer
  answers or judgments. Retrieved text must be treated as data, never instructions.
- S2: No request timeouts (B5); a hung request stalls the whole evaluation.
- S3: No verdict/response cache — re-running a benchmark repays full API quota;
  on free tiers this makes iteration practically impossible.
- S4: No API usage accounting (requests, tokens, latency) — quota exhaustion is
  discovered only via 429 crashes.
- S5: Secrets handling is correct today (`.env` gitignored, verified 0 tracked
  secret files) — must be re-verified at V2 completion.

## 7. Performance bottlenecks

- P1: Sequential LLM calls with global 6 s pacing dominate runtime (~8 min per
  12-question run). Embedding calls share the generate pacing budget although
  their quota is separate.
- P2: Pure-Python dense search is O(N·d) per query — fine at 13 chunks,
  a bottleneck beyond ~10k chunks (documented limitation, not fixed in V2).
- P3: No caching of judge responses (S3); ablation re-runs repeat identical work.
- P4: No concurrency; acceptable for free-tier RPM limits, documented as a design
  choice rather than silently "optimized".

## 8. V2 remediation plan (maps to upgrade phases)

- Phase 2/4: `ragpipe/verify/` — Pydantic schemas; explicit verdict states
  (SUPPORTED, CONTRADICTED, NOT_SUPPORTED, UNCERTAIN, EXTRACTION_FAILED,
  EVALUATION_ERROR, plus answer-level NO_CLAIMS); fail-closed faithfulness
  (fixes B1–B3, B9, B12); multi-stage claim analysis (SPO, negation, modality,
  entities, numbers, temporal) + deterministic checks + semantic entailment with
  disagreement flagging; citation mapping restricted to retrieved ids (M2, M3, M6).
- Phase 2: llm.py — explicit timeouts, transport-error retries, empty-response
  detection, usage/latency accounting, disk response cache (B4, B5, B8, S2–S4).
- Phase 3: `ragpipe/adversarial/` — deterministic check battery for categories
  A–H + semantic fallback; injection detection treating corpus as untrusted (S1, M4).
- Phase 5: `data/adversarial_golden_dataset.json` — ≥100 synthetic, author-reviewed
  fixtures (≥10/category), labeled synthetic; no claim of independent human validation.
- Phase 6: confusion matrices, detection/FAR/FRR, per-category accuracy,
  precision/recall/F1 with sample counts; incompatible populations reported
  separately (B7, M5, M7); original metrics retained.
- Phase 7: `reports/v2/` — 4-variant ablation on original + adversarial evidence
  probes; V1 reports untouched; independent relevance judge for precision (M1);
  live vs mocked vs not-run explicitly labeled per section.
- Phase 8: failure-handling, schema, mock-API, regression and adversarial tests;
  B15 expectation updated with documentation.
- Phase 9: deterministic checks before LLM calls; response cache; usage stats in
  reports; separate embed pacing (P1, P3).
- Phase 10/11: docs suite, README update, full validation, secrets re-check,
  historical reports preserved.

## 9. Audit verdict

The V1 pipeline is a sound, honest baseline with a correct retrieval core, but its
evaluation layer is **fail-open**: several failure modes manufacture perfect or
zero scores instead of reporting errors, and it has never been tested against
adversarial evidence. V2 must make every evaluation outcome explicit and auditable
before adding adversarial benchmarks — otherwise new benchmarks would inherit the
same silent-failure pathology.

## 10. Addendum — bug found during V2 implementation (B16)

Mid-run inspection of the first live V2 ablation showed bm25 faithfulness 0.838
where V1 measured 1.0. Root cause: the new deterministic checks flagged a claim's
number against a *different* number in another sentence of the same multi-fact
context (and negation cues in unrelated clauses), and the disagreement rule let
those flags override correct semantic SUPPORTED verdicts. Fix: support-aware
contradiction flags (conflict AND no supporting sentence), clause-scoped negation,
support-aware modality/temporal/role checks, tightened injection regex (benign
"override the project default" no longer flagged). Three regression tests added
(`test_multifact_context_no_false_numerical_contradiction`,
`test_clause_scoped_negation_no_false_flag`, `test_benign_override_not_injection`).
All V2 reports were regenerated with the fixed code via the response cache;
final bm25 faithfulness 1.0. Interim pre-fix numbers are invalid and superseded.