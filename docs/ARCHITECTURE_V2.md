# Architecture V2

V2 adds a fail-closed, auditable verification layer and an adversarial benchmark
engine on top of the V1 retrieval/generation core, which is preserved unchanged.

## Layer map

```
V1 core (preserved)
  ingest → embeddings cache → HybridRetriever (BM25 + dense + RRF)
  → llm_rerank → generate_answer (citations, refusal, invalid-citation tracking)

V2 verification layer (ragpipe/verify/)
  schemas.py   Pydantic models + explicit verdict states
  checks.py    deterministic evidence checks (LLM-free)
  engine.py    VerificationEngine: multi-stage, fail-closed

V2 evaluation layer
  evaluate/metrics.py    V1 judges, now fail-closed (explicit error states)
  evaluate/runner_v2.py  end-to-end V2 runner (engine + independent precision judge)
  adversarial/dataset.py   104 synthetic fixtures, schema-validated
  adversarial/benchmark.py fixture benchmark (deterministic | semantic | mocked)
  adversarial/metrics.py   confusion matrices, detection/FAR/FRR, PRF, per-category
  adversarial/probes.py    retrieval-variant probes on adversarial evidence
```

## Verification pipeline (engine.verify_claims)

1. **Deterministic analysis** per claim: negation cues, modality ladder,
   capitalized entities, normalized numbers (time/data/count/percent dimensions),
   dates. No LLM call.
2. **Semantic stage** (semantic mode only): ONE structured Gemini call returning
   per-claim normalized claim, subject/predicate/object, negation, modality,
   entities AND entailment status + ordinal confidence + explanation.
   Prompt frames passages as UNTRUSTED DATA (injection resistance).
3. **Citation mapping**: deterministic overlap of claim tokens/entities against
   retrieved passage ids only — the LLM never invents citations.
4. **Deterministic evidence checks** on injection-cleaned evidence:
   numerical contradiction, negation flip, modality overstatement, temporal
   reversal, role reversal (SPO order), entity absence. All checks are
   **support-aware**: a conflict flag requires that no similar sentence
   supports the claim (multi-fact contexts do not self-contradict); negation
   polarity is compared within the best-matching clause. Injection sentences
   are excluded from evidence but recorded as security flags over the FULL
   context.
5. **Resolution rules**:
   - deterministic mode: flags map to CONTRADICTED / NOT_SUPPORTED; no flag →
     UNCERTAIN (never a guessed SUPPORTED).
   - semantic mode: semantic status stands, except when deterministic evidence
     flags conflict with a semantic SUPPORTED → disagreement=True; exact
     numerical conflicts resolve to CONTRADICTED (reliable deterministic
     evidence), other conflicts resolve to UNCERTAIN for explicit review.
   - missing semantic verdict → UNCERTAIN; API/schema failure →
     EVALUATION_ERROR with score None.
6. **Scoring**: faithfulness = SUPPORTED / resolved verdicts
   (SUPPORTED+CONTRADICTED+NOT_SUPPORTED). UNCERTAIN and error states are
   excluded from the score and reported separately. No resolved verdicts or any
   error state → score None (fail-closed).

## Explicit states

Claim level: SUPPORTED, CONTRADICTED, NOT_SUPPORTED, UNCERTAIN,
EXTRACTION_FAILED, EVALUATION_ERROR.
Answer level: OK, REFUSED, NO_CLAIMS, EXTRACTION_FAILED, EVALUATION_ERROR.

## Reliability & performance (llm.py)

- Explicit 120 s request timeout; retries on 429/500/503 AND transport
  failures (httpx/httpx2 TimeoutException, TransportError).
- Empty/blocked completions raise EmptyResponseError — never silently become
  empty answers or perfect scores.
- Disk response cache keyed by (model, system, prompt, temperature, json_mode):
  benchmark re-runs are quota-free and reproducible.
- Usage accounting: generate/embed request counts, cache hits, prompt/output
  tokens, latency, retries, errors — included in V2 reports.
- Separate pacing budgets for generate (RAG_RPM) and embed (RAG_EMBED_RPM).
- Deterministic checks run before any LLM call; semantic analysis+entailment
  merged into one structured call to halve judge traffic.

## What V2 deliberately does NOT do

- No FAISS/NumPy (host Application Control blocks native DLLs); pure-Python
  retrieval remains O(N·d) — fine for this corpus scale, documented limit.
- No concurrency: free-tier RPM limits make parallelism counterproductive.
- No calibrated probabilities: judge confidence is ordinal and labeled as such.
- No composite "overall robustness score": incompatible metric populations are
  reported separately.