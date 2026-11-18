# Reproducibility (V2.1)

## Run manifests

Every V2.1 report embeds a manifest (`ragpipe/manifest.py`):

- run_id, timestamp
- git commit hash (12 chars) of the producing code
- Python version and dependency versions (google-genai, pydantic,
  python-dotenv, pytest)
- SHA-256 (16-char) hashes of every dataset used
- prompt version (`v2.1`) and SHA-256 hash of the judge/extractor prompts
- model identifier + configuration (temperature 0, embed dim, JSON mime)
- random seed: `null` — the pipeline uses no sampling RNG; determinism comes
  from temperature 0 and cached responses
- retrieval configuration (chunk size/overlap, top-k, RRF k)
- evaluation configuration (cache flag, RPM budgets)
- API execution status: `live`, `offline-deterministic`, `live-mixed`,
  `BLOCKED_BY_QUOTA`, `not-run`

Secrets are never written to manifests or reports (CI secret-scans tracked
files for key-shaped strings).

## Deterministic replay

- Non-LLM components (chunking, BM25, RRF, deterministic checks, metrics) are
  pure functions of inputs → identical across runs and machines.
- LLM judge responses are cached on disk keyed by
  (model, system prompt, user prompt, temperature, json_mode). Re-running a
  benchmark replays cached judgments with zero API quota; cache hits are
  counted in `api_stats`.
- `RAG_LLM_CACHE=0` disables caching for fresh-judge experiments.
- Embedding vectors cached per chunk id + model + dimension.

## Resumable execution

`evaluate-v2 --resume` reuses completed (variant, question) records from
`reports/v2/checkpoint_v2.json`. On daily-quota 429 the runner records
`api_status: BLOCKED_BY_QUOTA`, lists pending item ids per variant, saves the
partial report, and exits cleanly; resuming continues where it stopped.

## Reproduce everything offline

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
python -m pytest tests/ -q                     # 114 tests, no API
python scripts/check_leakage.py                # dataset integrity gate
python scripts/regression_gate.py              # pins + FAR/detection gates
python -m ragpipe.cli redteam                  # metamorphic pairs, no API
python -m ragpipe.cli adversarial --mode deterministic
python -m ragpipe.cli grid-v21 --mode offline  # needs key for embeddings only
```

## Reproduce live (quota-bounded)

```bash
cp .env.example .env   # add GEMINI_API_KEY
python -m ragpipe.cli ingest
python -m ragpipe.cli evaluate-v2 --variants bm25,dense,hybrid,hybrid+rerank
python -m ragpipe.cli grid-v21 --mode mixed
python -m ragpipe.cli adversarial --mode semantic
```

## Reviewer trace

Each grid/benchmark record carries: question/probe → `retrieved_ids` →
generated answer (end-to-end records) → `claim_analyses` (tuples) →
`evidence_events` + mapped `citation_ids` → per-claim verdict (status,
confidence, flags, semantic/secondary status, disagreement, explanation) →
summary metrics with denominators and Wilson intervals → manifest.