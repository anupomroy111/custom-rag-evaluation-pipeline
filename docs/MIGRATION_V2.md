# Migration Guide: V1 → V2

## What changed for users

| V1 | V2 | Notes |
|---|---|---|
| `evaluate` | `evaluate` (unchanged) + `evaluate-v2` | V1 command and reports preserved |
| faithfulness 1.0 on empty extraction | explicit `NO_CLAIMS` / `EXTRACTION_FAILED`, score `None` | audit B1 fix; **breaking for consumers assuming float** |
| single `hallucination_rate` | `hallucination_rate_answerable` + `fabrication_rate_unanswerable` | audit B7 fix; report labels updated |
| over-refusal hallucination 0.0 | `None` + `over_refusal` flag | audit B6 fix |
| precision from reranker grades | independent judge in V2 (`precision_judge: independent`) | audit M1 fix; V1 path unchanged |
| invalid citations silently dropped | tracked in `Answer.invalid_citations` + validity metric | audit M5 fix |
| no timeout / transport retry | 120 s timeout, transport retries, EmptyResponseError | audit B4/B5/S2 fixes |
| no cache | disk response cache (`RAG_LLM_CACHE=0` to disable) | re-runs quota-free |
| — | `adversarial`, `probes-v2` commands | new benchmark surfaces |

## Backward compatibility

- `ragpipe.cli ingest / ask / evaluate` behave as before (except the documented
  bug fixes above, which change *incorrect* V1 outputs).
- `FaithfulnessResult.score` is now `float | None`; `.hallucination_rate`
  returns `None` when score is `None`. Callers must handle `None`.
- `metrics.context_recall` returns `score: None` + `status: EVALUATION_ERROR`
  on empty judge output instead of a silent 0.0.
- V1 report files in `reports/` are untouched; V2 writes to `reports/v2/`.
- Test expectation updated with documentation: `test_faithfulness_no_claims`
  now asserts the fail-closed state (audit B15).

## New configuration

```
RAG_EMBED_RPM=100     # separate pacing budget for embeddings
RAG_LLM_CACHE=1       # disk response cache (0 disables)
```

## New modules

```
ragpipe/verify/{schemas,checks,engine}.py
ragpipe/adversarial/{dataset,benchmark,metrics,probes}.py
ragpipe/evaluate/runner_v2.py
data/adversarial_golden_dataset.json
docs/{V2_AUDIT_REPORT,ARCHITECTURE_V2,ADVERSARIAL_BENCHMARK,EVALUATION_METHODOLOGY,MIGRATION_V2}.md
```

## Upgrade checklist

1. `python -m pip install -r requirements.txt` (pydantic arrives via google-genai).
2. `python -m pytest tests/ -q` — 95 tests, zero API calls.
3. `python -m ragpipe.cli adversarial --mode deterministic` — quota-free floor.
4. `python -m ragpipe.cli adversarial --mode semantic` — live judge benchmark.
5. `python -m ragpipe.cli probes-v2` — retrieval-variant evidence probes.
6. `python -m ragpipe.cli evaluate-v2 --variants bm25,dense,hybrid,hybrid+rerank`.
7. Read `reports/v2/*.md`; check disagreement lists and error rates before
   trusting any headline number.