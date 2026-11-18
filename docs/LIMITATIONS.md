# Limitations (V2.1) — read before trusting any number

## Data and labels

1. All fixtures (104 + 60 + 140) are synthetic and author-reviewed by one
   person. No independent human validation occurred; label bias is possible.
   Controls, paraphrase pairs and documented edge cases mitigate but do not
   eliminate this.
2. Sample sizes are small. FAR 0.000 on ~72 adversarial-expected cases has a
   95% Wilson upper bound ≈ 0.05. "Zero observed" ≠ "zero possible".
3. The held-out split is unseen by the tuning loop but shares the same author
   and generation process; it tests generalization across scenario families,
   not across labelers or domains.

## Verification

4. The deterministic layer is a heuristic floor: it abstains (UNCERTAIN) on
   anything it cannot decide (roles, entities, multi-hop, embedded negation
   scopes). High UNCERTAIN rates in deterministic mode are by design.
   On held-out positives it also over-flags some paraphrases (FRR ≈ 0.20 in
   deterministic mode): surface heuristics cannot prove equivalence, and the
   fail-closed rule prefers abstention/contradiction flags over approval.
   Semantic mode resolves these; read deterministic FRR as a floor artifact,
   not as semantic performance.
5. The semantic judge is an LLM and can be wrong. Disagreement flags bound but
   do not remove judge error; a secondary judge (optional) is NOT assumed
   statistically independent of the primary.
6. Judge confidence is ordinal self-report, NOT a calibrated probability. No
   calibration (Brier/ECE) is claimed because none was evaluated.
7. Role/temporal exact accuracy measured 0.769 in V2 live runs; V2.1 tuple
   checks target these, but re-measured held-out numbers must be read from
   reports/v2_1/ — improvement is not assumed.
8. Injection screening is regex-based; benign documentation imperatives can
   false-positive (documented case INJ-012). Flags are security signals, not
   verdicts.

## Execution and quota

9. Gemini free tier caps at 500 generate requests/day per project. Runs that
   hit the cap stop with `BLOCKED_BY_QUOTA` and remain resumable; some V2.1
   live stages may be partial or not-run in a given release — every report
   labels its execution status. No mocked results are presented as benchmarks.
10. One judge call per case (batching traded against free-tier pacing);
    latency is dominated by client-side RPM pacing, not model speed.

## Engineering

11. Pure-Python dense search is O(N·d) per query — fine at hundreds of chunks,
    a bottleneck beyond ~10k; no FAISS/NumPy because host Application Control
    blocks native DLLs (documented environment constraint).
12. `mypy` cannot run on the development host (Application Control blocks its
    compiled DLL); type checking runs in CI (ubuntu) and locally via pyright.
13. V1 `context_precision` may use reranker grades (circular); preserved for
    historical comparability. V2/V2.1 paths use an independent judge.
14. reports/v2/ contains pre-fix intermediate runs; FINAL_V2_REPORT.md names
    the authoritative files. Historical reports are never overwritten.

## Scope

15. This framework evaluates document-grounded QA on a small fictional corpus
    plus synthetic adversarial fixtures. It is not evidence of production
    robustness on open-domain or multilingual workloads.