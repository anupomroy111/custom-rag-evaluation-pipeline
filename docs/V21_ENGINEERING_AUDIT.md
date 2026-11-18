# V2.1 Engineering Audit

Audit date: 2026-11-18 · Scope: full repository inspection before V2.1 changes.
Method: structural scan of all modules/datasets/reports + line-level review of
verification, metrics, runner and LLM layers. No code modified before this document.

## 1. Current architecture (verified)

V1 core: ingest → embedding cache → BM25+dense+RRF → LLM rerank → grounded
generation. V2 layer: fail-closed VerificationEngine (deterministic support-aware
checks + one structured semantic judge call), 104-fixture adversarial benchmark
(deterministic/semantic/mocked), retrieval probes, V2 end-to-end runner with
independent precision judge, response cache, pacing/retries/timeouts, usage stats.
98 tests passing at audit time. Reports: V1 immutable, V2 in reports/v2/ with
FINAL_V2_REPORT.md as authoritative consolidation.

## 2. Findings

| # | Severity | Area | Finding |
|---|---|---|---|
| A1 | CRITICAL | Benchmark integrity | Single 104-fixture set serves as both development and reporting benchmark. No development/held-out split, no scenario-family metadata, no leakage control. Scores risk test-set overfitting; "never optimize only for the existing test dataset" is currently unenforceable. |
| A2 | HIGH | Metrics | No Wilson confidence intervals; binary contradiction PRF lacks TN; no macro/micro per-category aggregation; UNCERTAIN abstentions counted as misses inside exact accuracy without a separate abstention-aware denominator; fixture benchmark merges extraction and verification errors into one error rate. |
| A3 | HIGH | Reporting | FAR 0.000 presented in README/card without sample-size uncertainty qualification. With n=72 adversarial-expected cases, the 95% Wilson upper bound is ≈0.05 — "zero observed" is not "zero possible". |
| A4 | HIGH | Semantics | Claim schema lacks agent/patient distinction, tense, aspect, attribution relations and coreference. No evidence-event tuples: deterministic role check relies on surface word order; passive/active and paraphrase equivalence depend entirely on free-form LLM output. Role/temporal exact accuracy 0.769. |
| A5 | HIGH | Reproducibility | Judge prompts unversioned/unhashed; a prompt edit silently changes cross-run comparability. |
| A6 | MEDIUM | Judge reliability | No secondary-judge adapter; disagreement tracked only deterministic-vs-primary. |
| A7 | MEDIUM | Calibration | Confidence correctly labeled ordinal; no calibration evaluation exists — must NOT be described as calibrated (keep as-is, document). |
| A8 | HIGH | Reproducibility | No run manifest: git commit, dependency versions, dataset hashes, prompt hashes, model config, seed, retrieval/eval config, API status are not recorded with reports. |
| A9 | HIGH | Reliability | Runner checkpoint exists but no cross-process resume; quota crash lost hybrid/hybrid+rerank V2 runs; no BLOCKED_BY_QUOTA execution status. |
| A10 | MEDIUM | Performance | Only aggregate LLM latency measured; no per-stage (retrieval/rerank/extraction/verification) latency or memory accounting. |
| A11 | MEDIUM | Open source | No public Python API or adapter interfaces; external users must import internals; CLI-only entry points. |
| A12 | HIGH | CI/CD | No GitHub Actions; no offline quality gate, no benchmark regression gate, no dataset-schema or secret scanning in CI. |
| A13 | MEDIUM | Citations | Invalid citation attempts tracked end-to-end, but no citation-manipulation mutation tests and no citation-reference validation metric in fixture mode. |
| A14 | MEDIUM | Deterministic | Dates extracted but not normalized to comparable values (string-set comparison); time normalization exists for durations only. |
| A15 | MEDIUM | Deterministic | Negation scope is clause-split heuristic; embedded scopes ("not unlikely", "failed to deny") misparse. Must return UNCERTAIN when scope parse is ambiguous rather than guessing. |
| A16 | HIGH | Testing | No paired mutation testing (both directions) and no metamorphic tests (paraphrase invariance / contradiction sensitivity). |
| A17 | MEDIUM | Dataset schema | Cases lack scenario_family, mutation_type and per-case label_provenance fields. |
| A18 | LOW | Performance | One judge call per case; batching possible but free-tier pacing makes it a tradeoff, not a bug. Dense search O(N·d) pure Python — documented scale limit. |
| A19 | LOW | Legacy | V1 context_precision may use reranker grades (circular); V2 path independent. Legacy behavior preserved intentionally; flag in docs. |
| A20 | LOW | Reports | reports/v2 contains pre-fix intermediates; FINAL_V2_REPORT.md supersedes them. Reviewer guide must name authoritative files explicitly. |

## 3. Strengths to preserve

Fail-closed explicit states; support-aware deterministic checks (B16 fix);
injection screening with untrusted-data framing; per-claim JSON audit trails;
disk response cache (quota-free replays); pacing + transport retries + timeouts;
empty-response detection; separate hallucination/fabrication populations;
independent V2 precision judge; honest incident documentation; 98 passing tests
at audit time (123 at V2.1 hardening release).

## 4. Remediation map (V2.1 sections)

- A1, A17 → §4: data/{original,adversarial,development,heldout,regression};
  scenario-family disjoint splits; +200 independently constructed fixtures;
  leakage checker (family disjointness + near-duplicate Jaccard gate).
- A2, A3 → §5: ragpipe/evalstats.py — denominators, raw TP/FP/TN/FN, Wilson CI,
  macro/micro, abstention-aware accuracy, error taxonomy; uncertainty language
  in README/docs.
- A4, A14, A15 → §2-3: extended claim schema (agent/patient/tense/aspect/
  attribution/coreference), evidence-event tuples from the semantic stage,
  deterministic tuple comparison (role/attribution/temporal), date normalization,
  negation-scope ambiguity → UNCERTAIN.
- A5, A6, A7 → §7: PROMPT_VERSION + hash in manifests; optional secondary judge
  adapter; three-way disagreement; confidence stays ordinal (no calibration claim).
- A8, A9, A10 → §9-10: manifest module; resumable runner with per-item status
  incl. BLOCKED_BY_QUOTA; per-stage timers + tracemalloc peak.
- A11 → §11: ragpipe.api.RAGEvaluator + adapter protocols + example.
- A12 → §12: offline CI workflow + regression gate + optional live workflow.
- A13, A16 → §6: red-team mutation operators, paired both-direction tests,
  metamorphic invariance/sensitivity tests, citation-manipulation cases.
- A18, A19, A20 → docs/LIMITATIONS.md + docs/REVIEWER_GUIDE.md.

## 5. Audit verdict

V2 is honest and fail-closed but not yet independently verifiable: its benchmark
is a single self-authored set, its proportions lack uncertainty bounds, and its
runs lack provenance manifests. V2.1 must add held-out data, statistical
hygiene, provenance and CI before any claim of reviewer-grade robustness.

## 6. Addendum — defects found by the V2.1 gates themselves

- G1: judge output quirks (`coreference: {}`, `temporal_order: []`, `null`
  string fields) failed strict Pydantic validation → every semantic verdict
  became EVALUATION_ERROR. Fixed with boundary-normalizing field validators
  (unknown shapes still fail closed); regression-tested.
- G2: `numerical_support` initially affirmed claims whose extra causal /
  temporal / scope material was ignored by a min-denominator overlap, and
  stopword filtering dropped blocking words like "from". The held-out leakage/
  FAR gate caught 6 false acceptances; fixed with full-core subset coverage
  without stopword filtering. Held-out and development FAR returned to 0.000;
  regression tests added.
- G3: V1 report renderer assumed V1 verdict keys (`supported`, `claim`) and
  crashed on V2 records; fixed with status-aware rendering + regression test.

These are exactly the failures the V2.1 gate infrastructure was built to
surface; each fix is pinned by a test and the gates run in CI.