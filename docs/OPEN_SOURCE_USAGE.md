# Open-Source Usage (V2.1)

## Install

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # POSIX
cp .env.example .env   # add GEMINI_API_KEY for live modes
```

Python ≥ 3.10. No native dependencies (pure-Python retrieval); YAML config
additionally needs `pyyaml` (optional; JSON/dict config work without it).

## Public Python API

```python
from ragpipe import RAGEvaluator

evaluator = RAGEvaluator(config={"llm_model": "gemini-3.5-flash-lite"})
result = evaluator.evaluate(
    question="What is the default build timeout?",
    context=[("p0", "The default build timeout is 15 minutes.")],
    answer="The default build timeout is 15 minutes [id:p0].",
)
print(result["metrics"]["faithfulness"])          # 1.0
print(result["verification"]["verdicts"])         # per-claim audit trail
```

Omit `answer` to let the pipeline generate one (optionally via a custom
retrieval adapter). `evaluate_dataset(cases, mode=...)` runs the fixture
benchmark with the same engine.

## Adapters

All optional; duck-typed protocols in `ragpipe/api.py`:

- `llm`: `generate`, `generate_json`, `embed` — swap Gemini for any provider
  or a scripted judge (see `examples/external_usage.py`, runs offline).
- `retrieval`: `search(question, top_k) -> [(id, text)]` — plug your own index.
- `extractor`: `extract(answer_text) -> [claims]`.
- `verifier`: `verify_claims` / `verify_answer` — custom verification strategy.
- `metrics`: `dict[str, callable(record)]` — add your own metrics.

Config accepts a dict, a JSON file, or a YAML file (with pyyaml installed).

## CLI

```bash
python -m ragpipe.cli ingest                 # build index
python -m ragpipe.cli ask "..."              # grounded answer + citations
python -m ragpipe.cli evaluate               # V1 benchmark
python -m ragpipe.cli evaluate-v2 [--resume] # V2 end-to-end, resumable
python -m ragpipe.cli adversarial --mode deterministic|semantic
python -m ragpipe.cli grid-v21 --mode offline|mixed
python -m ragpipe.cli probes-v2
python -m ragpipe.cli redteam [--mode semantic]
```

## Custom datasets

Any JSON with the case schema (see docs/BENCHMARK_METHODOLOGY.md) can be passed
to `load_adversarial(path)` / `RAGEvaluator.evaluate_dataset`. Keep provenance
honest: label synthetic vs human-reviewed data explicitly.

## CI for your fork

`.github/workflows/ci.yml` runs fully offline (tests, schema, leakage,
regression and red-team gates, secret scan). Live evaluation is a separate
manual workflow requiring a `GEMINI_API_KEY` secret — never mandatory for PRs.