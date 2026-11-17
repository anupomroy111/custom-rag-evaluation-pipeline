# Adversarial Benchmark (V2)

## Purpose

V1's perfect scores on a lexically-aligned corpus proved nothing about
robustness. V2 benchmarks the *verifier* against evidence designed to fool it:
negation flips, role reversals, misattribution, numerical/temporal/modality
contradictions, multi-hop fallacies and prompt injection.

## Dataset

`data/adversarial_golden_dataset.json` — 104 cases, 13 per category across
8 categories: `negation_flip`, `role_reversal`, `entity_attribution`,
`numerical`, `temporal`, `modality`, `multi_hop`, `context_injection`.

Each case: `id`, `category`, `difficulty`, `context[]` (evidence passages),
`generated_answer`, `claims[]`, `expected_status`, `expected_reason`,
`probe_question`, `provenance`.

**Provenance honesty:** all fixtures are SYNTHETIC, authored and reviewed by the
project owner (`provenance: synthetic-author-reviewed`). They have NOT undergone
independent human validation. The dataset includes positive controls,
paraphrase controls, unit-conversion controls, symmetric-predicate edges and
known-limitation edges (e.g. ROLE-010, INJ-012) whose expected labels document
where conservative disagreement handling or injection regexes fall short.

## Benchmark modes

| Mode | LLM calls | What it measures |
|---|---|---|
| `deterministic` | 0 | Reproducible floor: what lexical/numeric/temporal/modality checks alone can resolve. Unresolved → UNCERTAIN, never guessed. |
| `semantic` (live) | 1 per case | Full engine with Gemini judge; labeled `judge: live`. |
| `semantic` (mocked) | 0 (scripted) | Pipeline regression tests; labeled `judge: mocked`. |

Commands:

```bash
python -m ragpipe.cli adversarial --mode deterministic
python -m ragpipe.cli adversarial --mode semantic            # live API
python -m ragpipe.cli adversarial --mode semantic --category negation_flip
python -m ragpipe.cli probes-v2                              # retrieval variants
```

## Measured results — deterministic mode (104 cases, executed)

| Metric | Value |
|---|---|
| Adversarial detection rate | 0.528 |
| False acceptance rate | **0.000** |
| False rejection rate | **0.000** |
| Exact status accuracy | 0.279 |
| Uncertain rate | 0.635 |
| Evaluation error rate | 0.000 |
| Injection cases flagged | 13/13 |

Interpretation: the deterministic battery is **fail-closed** — it never accepts
an adversarial claim and never rejects a true one, but it can only resolve ~28%
of cases exactly; role reversal, entity attribution and multi-hop composition
require semantic SPO analysis (hence UNCERTAIN, not a guess). This is the honest
floor, not a headline score.

Per-category exact accuracy (deterministic): negation 0.462, numerical 0.538,
modality 0.615, temporal 0.231, multi_hop 0.154, injection 0.154,
role_reversal 0.077, entity_attribution 0.000.

Live semantic results are reported separately in
`reports/v2/adversarial_semantic_live_*.md` (never merged with deterministic or
mocked runs).

## Measured results — semantic mode, live judge (104 cases, executed)

| Metric | Value |
|---|---|
| Adversarial detection rate | 0.986 |
| False acceptance rate | **0.000** |
| False rejection rate | 0.062 |
| Exact status accuracy | 0.903 |
| Uncertain rate | 0.048 |
| Evaluation error rate | 0.010 (1 case fail-closed, no score manufactured) |
| Contradiction precision / recall / F1 | 0.944 / 0.981 / 0.962 |
| Deterministic↔semantic disagreements | 5 (flagged for review) |
| Injection cases flagged | 13/13 |

Per-category exact accuracy: negation 1.000, modality 1.000, injection 1.000,
numerical 1.000 (n=12 resolved), entity 0.846, multi_hop 0.846,
role_reversal 0.769, temporal 0.769. Unresolved hard edges stay UNCERTAIN
rather than being guessed SUPPORTED.

Consolidated cross-benchmark summary: `reports/v2/FINAL_V2_REPORT.md`.

## Retrieval probes (`probes-v2`)

Each case's evidence passages become a synthetic document in a probe index
(original corpus + 104 adversarial docs). For each retrieval variant
(bm25 / dense / hybrid) we measure, with NO LLM judge: evidence hit@10, MRR of
first gold passage, evidence recall@4. Query embeddings are memoized across
variants. Probes isolate retrieval; the reranking stage is benchmarked
end-to-end by `evaluate-v2` (labeling a retrieval-only probe "+rerank" would
overstate what was measured). Results: `reports/v2/probes_*.md`.

## Known limitations

- Deterministic role/entity checks need SPO; without the semantic stage they
  stay UNCERTAIN by design.
- Negation/modality checks are cue+overlap heuristics; scope-sensitive cases
  (NEG-012) and symmetric predicates (ROLE-010) are documented edges.
- Injection regexes false-positive on benign documentation imperatives
  (INJ-012); flags are security signals, not verdicts.
- 104 synthetic cases give indicative rates, not statistical guarantees;
  sample counts are reported with every rate.