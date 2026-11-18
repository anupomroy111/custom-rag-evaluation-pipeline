# Independent Validation Protocol (V2.1 hardening)

## Provenance levels

Every fixture carries `provenance`:

| Level | Meaning | Requirements |
|---|---|---|
| `synthetic-author-reviewed` | Authored and reviewed by the project owner only | default; no external review claimed |
| `independent-human-reviewed` | Labels adjudicated by an external reviewer | `reviewer_id` AND `review_date` mandatory; loader rejects the level without them |

**No independent human validation has occurred in this repository.** All 324
fixtures (104 adversarial + 80 development + 140 held-out) are
`synthetic-author-reviewed`. The `independent-human-reviewed` level exists so
external reviewers can contribute without mixing provenance, and the loader
enforces the metadata gate (`ragpipe/adversarial/dataset.py`).

## How an external reviewer contributes

1. Fork the repository; create a branch.
2. Add cases under `data/independent/<reviewer_id>/cases.json` using the standard
   case schema, with `provenance: independent-human-reviewed`, your
   `reviewer_id` (GitHub handle or ORCID) and `review_date` (ISO date).
3. Adjudicate disputed labels from `docs/FAILURE_ANALYSIS.md` (held-out label
   disputes are listed there; held-out files themselves stay frozen).
4. Run the offline gates: `pytest`, `scripts/check_leakage.py`,
   `scripts/regression_gate.py`, `python -m ragpipe.cli redteam`.
5. Open a PR. CI runs all offline gates; live benchmarks remain manual.
6. Reports must keep provenance separate: synthetic-only and
   independent-reviewed subsets are summarized independently; a combined
   number is never presented without a per-provenance breakdown.

## Reporting rules

- Benchmark summaries include `execution_modes` (fresh-live / cached-live /
  deterministic / mocked / quota-blocked / unlabeled-pre-hardening) and the
  prompt version + hash from the manifest.
- Synthetic author-reviewed results are NEVER described as independently
  validated, externally validated, or human-validated.
- Label disputes are documented, not silently relabeled: held-out and original
  datasets are frozen; adjudication happens in the independent split.

## Current status

`data/independent/` contains no cases yet (see its README). Until external
reviewers contribute, every published number in this repository is
synthetic-author-reviewed evidence, with Wilson intervals stating the
sample-size uncertainty.