# Benchmark Methodology (V2.1)

## Splits and provenance

| Split | Path | n | Role |
|---|---|---|---|
| original | data/original/golden_dataset.json | 12 | V1 end-to-end benchmark (unchanged) |
| adversarial | data/adversarial/adversarial_golden_dataset.json | 104 | V2 fixture benchmark (unchanged) |
| development | data/development/dev_fixtures.json | 80 | tuning/iteration only (F01–F10 + hardening F21–F24) |
| heldout | data/heldout/heldout_fixtures.json | 140 | reporting benchmark, unseen during development |
| regression | data/regression/regression_cases.json | 14 pins | CI gate references (no duplicated content) |

All fixtures are **synthetic, authored and reviewed by the project owner**
(`provenance: synthetic-author-reviewed`). No independent human validation was
performed and none is claimed.

## Leakage control

- Splits are disjoint by **scenario family** (F01–F10 development, F11–F20
  held-out); families encode the underlying semantic scenario, not row ids.
- `scripts/check_leakage.py` gates: family disjointness, claim-token Jaccard
  < 0.85 across development↔heldout and heldout↔original-104, and required
  metadata (family, mutation_type, provenance) on every case.
- The gate caught and forced rewriting of 5 near-duplicate scenarios during
  construction (documented in commit history); it runs in CI on every push.
- Held-out results are reported separately; development numbers are never
  presented as held-out performance.

## Label conventions

- **Silence vs contradiction:** evidence attributing a property to entity A
  does not contradict the same property for entity B unless exclusivity is
  stated → NOT_SUPPORTED. CONTRADICTED requires an explicit opposite assertion
  (negation, role swap in the same event, different value for the same
  quantity, state reversal, reversed chain).
- **Functional relations:** owns / authored / maintains / stores / developed /
  funded are treated as single-holder by convention; a different holder for the
  same relation+target contradicts. Non-functional relations (locations,
  enforcement) and different-relation claims are silence.
- **Scope ambiguity:** "not only/merely/just", gapped negation…only, and modal
  stacks ("may not be unavailable") force UNCERTAIN in every execution mode.
- Disputable held-out labels are documented in docs/FAILURE_ANALYSIS.md and
  reserved for independent adjudication; held-out files are frozen.

## Execution modes (per record and per summary)

`fresh-live` (new API call), `cached-live` (replayed cached live response),
`deterministic` (no judge), `mocked` (scripted judge, tests only),
`quota-blocked` / `BLOCKED_BY_QUOTA` (run stopped, resumable),
`unlabeled-pre-hardening` (records produced before mode labeling existed).
Summaries carry an `execution_modes` count table; modes are never pooled into
a single benchmark number without the breakdown.

## Case schema

id, category (12), difficulty, context[], generated_answer, claims[],
expected_status, expected_reason, probe_question, scenario_family,
mutation_type, pair_id, provenance.

Mutation types cover the red-team taxonomy: negation removal/insertion,
double negation, scope ambiguity, agent-patient swap, entity substitution,
wrong ownership/attribution, number/unit/date manipulation, temporal reversal,
state reversal, modality escalation, paraphrase equivalence, multi-hop false,
injection true/false, citation manipulation, causal false.

## Execution modes

- **offline / deterministic**: zero judge calls; embeddings only for retrieval
  probes. Reproducible floor; unresolved → UNCERTAIN.
- **semantic (live)**: Gemini judge, one structured call per case; cached
  responses make replays quota-free; judge label recorded.
- **mocked**: scripted judges in tests only; never presented as benchmarks.
- **BLOCKED_BY_QUOTA**: daily free-tier cap (500 generate requests/day on
  gemini-3.5-flash-lite) stops a run; completed items persist in checkpoints;
  `evaluate-v2 --resume` continues without re-paying for completed work.

## Ablation grid

`grid-v21` runs bm25 / dense / hybrid / hybrid+rerank × {adversarial,
development, heldout}. Each variant retrieves top-4 evidence; the verifier
judges fixture claims against that retrieved evidence, so retrieval quality
propagates into detection / false-acceptance metrics. Mixed mode adds live
semantic verification for hybrid+rerank on development + heldout.

## Statistical reporting

Every proportion carries its denominator and a 95% Wilson interval; raw
TP/FP/TN/FN and confusion matrices are included; abstentions (UNCERTAIN) and
error states are separated from incorrect predictions; macro and micro
averages are reported per category with sample counts. A 0.000 false-acceptance
rate on n≈72 adversarial cases has a Wilson upper bound ≈0.05 — it is evidence
of fail-closed behavior on this sample, not proof of universal reliability.

## What was actually executed

See `reports/v2_1/EXECUTIVE_SUMMARY.md` for the executed-run inventory with
live/offline/blocked labels, and `docs/RED_TEAM_RESULTS.md` for metamorphic
results. Historical V1/V2 reports remain untouched in `reports/` and
`reports/v2/`.