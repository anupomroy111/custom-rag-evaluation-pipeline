# Architecture V2.1

V2.1 adds independent-validation infrastructure on top of V2 without breaking
V1/V2 interfaces.

```
Public API (ragpipe/api.py)
  RAGEvaluator(config, llm, retrieval, extractor, verifier, metrics)
     │  adapter protocols: LLMAdapter / RetrievalAdapter / ClaimExtractor /
     │  VerificationStrategy / metric callables
     ▼
Verification engine (ragpipe/verify/)
  schemas.py   ClaimAnalysis: agent, patient, subject, object, predicate,
               negation, tense, aspect, voice, modality, entities, coreference,
               attributions, numbers, temporal refs, citations
               EventTuple: normalized evidence events (roles, state, order)
               VerdictStatus: SUPPORTED / CONTRADICTED / NOT_SUPPORTED /
               UNCERTAIN / EXTRACTION_FAILED / EVALUATION_ERROR
  checks.py    deterministic layer: normalized numbers + unit conversion,
               date normalization, negation parity + clause scope,
               scope-ambiguity → UNCERTAIN, support-aware contradiction flags,
               tuple-based role / attribution / temporal consistency,
               numerical_support (positive evidence), injection screening
  engine.py    stages: deterministic analysis → semantic stage (one structured
               call: claim tuples + entailment + evidence events) → citation
               mapping → deterministic cross-checks → resolution with
               disagreement flags → optional secondary judge (three-way)
               PROMPT_VERSION = "v2.1" (hashed into manifests)

Evaluation science
  evalstats.py        Wilson intervals, raw TP/FP/TN/FN, macro/micro,
                      abstention-aware accuracy, zero-denominator → None
  adversarial/        dataset splits + leakage-gated fixtures, benchmark modes,
                      confusion matrices, per-category metrics
  redteam.py          structured scenario bank → paired mutations (both
                      directions) + metamorphic invariance/sensitivity checks
  evaluate/
    runner_v2.py      resumable end-to-end runner, BLOCKED_BY_QUOTA status,
                      per-stage latency, manifests
    ablation_v21.py   4 retrieval variants × {adversarial, development, heldout}
                      grid; retrieval feeds verification evidence

Provenance & quality
  manifest.py         run id, git commit, python/dep versions, dataset hashes,
                      prompt version+hash, model config, seed, API status
  scripts/            check_leakage.py, regression_gate.py, dataset builders
  .github/workflows/  offline CI (lint/type/tests/schema/leakage/gates/secrets),
                      optional live workflow, full-benchmark workflow
```

## Resolution rules (unchanged fail-closed core, extended signals)

- Deterministic mode: contradiction flags → CONTRADICTED / NOT_SUPPORTED;
  no flags → UNCERTAIN, except normalized-number positive evidence → SUPPORTED;
  ambiguous negation scope → UNCERTAIN (never guessed).
- Semantic mode: semantic status stands; deterministic conflict with semantic
  SUPPORTED → disagreement; exact numerical or tuple role/attribution swaps
  override to CONTRADICTED; other conflicts → UNCERTAIN for review.
- Equivalent paraphrases: normalized tuple match clears surface word-order
  flags; passive/active handled by role-normalized event tuples.
- Missing verdicts → UNCERTAIN; API/schema failures → EVALUATION_ERROR, score None.
- Secondary judge (optional): three-way disagreement recorded per claim;
  judges are NOT assumed statistically independent.

## Data flow for a reviewer trace

question → retrieved ids (probes/grid records `retrieved_ids`) → generated
answer → atomic claims (`claim_analyses`) → evidence events + mapped citations
→ per-claim verdicts with flags/confidence/explanation → metrics with
denominators and Wilson intervals → manifest (commit, hashes, config).