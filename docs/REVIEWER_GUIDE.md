# Reviewer Guide (V2.1)

A skeptical reviewer can verify every claim in this repository offline, then
optionally reproduce live results. Estimated offline time: < 2 minutes.

## 1. Install

```bash
git clone https://github.com/anupomroy111/custom-rag-evaluation-pipeline
cd custom-rag-evaluation-pipeline
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # or POSIX equivalent
```

## 2. Run offline tests (no API key needed)

```bash
python -m pytest tests/ -q
```

Expect 114 passing tests: V1 regression, V2 fail-closed states, V2.1 statistical
hygiene, semantic tuple checks, red-team metamorphic pairs, mocked-judge
integration, public API, manifest provenance.

## 3. Reproduce deterministic benchmark results

```bash
python scripts/check_leakage.py        # split integrity + near-duplicate gate
python scripts/regression_gate.py      # 14 pins + FAR/detection floors
python -m ragpipe.cli redteam          # 22/22 metamorphic pairs
python -m ragpipe.cli adversarial --mode deterministic
```

Compare against `reports/v2_1/` and `docs/RED_TEAM_RESULTS.md`. These runs make
zero judge calls; results are pure functions of the committed code and data.

## 4. Configure Gemini (optional, for live reproduction)

```bash
cp .env.example .env    # paste GEMINI_API_KEY (free: aistudio.google.com/apikey)
python -m ragpipe.cli ingest
```

Note the free-tier cap: 500 generate requests/day. Long runs stop with
`BLOCKED_BY_QUOTA` and resume via `evaluate-v2 --resume`.

## 5. Execute live evaluation

```bash
python -m ragpipe.cli evaluate-v2 --variants bm25,dense,hybrid,hybrid+rerank
python -m ragpipe.cli grid-v21 --mode mixed
python -m ragpipe.cli adversarial --mode semantic
```

Cached judge responses make re-runs quota-free; `api_stats.cache_hits` shows
how many calls were replayed.

## 6. Inspect claim-level JSON traces

Open any `reports/v2_1/grid_*.json` or `reports/v2/eval_v2_*.json`:
each record chains question → `retrieved_ids` → answer → `claim_analyses`
(agent/patient/predicate/negation/modality/numbers) → `evidence_events` and
mapped `citation_ids` → verdicts (status, flags, semantic/secondary status,
disagreement, explanation) → summary metrics with denominators + Wilson CIs
→ `manifest` (git commit, dataset/prompt hashes, dependency versions, API
status).

## 7. Understand metric calculations

`docs/METRIC_DEFINITIONS.md` gives numerator/denominator for every metric,
abstention/error separation, macro/micro rules and Wilson intervals.
`ragpipe/evalstats.py` is the single implementation; tests pin its math.

## 8. Identify known limitations

`docs/LIMITATIONS.md` lists 15 concrete limitations, including synthetic
single-author labels, small-sample uncertainty bounds, judge fallibility,
quota-blocked stages and environment constraints. Anything not executed is
labeled `not-run` / `BLOCKED_BY_QUOTA` — never silently mocked.

## 9. Check the gates yourself

CI (`.github/workflows/ci.yml`) runs on every push: syntax, lint, scoped type
check, tests, dataset schema, leakage gate, regression gate, red-team gate and
a tracked-file secret scan. Live and full-benchmark workflows are manual and
require an explicit API-key secret.