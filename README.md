# Custom RAG & Evaluation Pipeline

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini_API-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Gemini API" />
  <img src="https://img.shields.io/badge/Faithfulness-1.000-34d399?style=for-the-badge" alt="Faithfulness 1.000" />
  <img src="https://img.shields.io/badge/Hallucination-0.000-22d3ee?style=for-the-badge" alt="Hallucination 0.000" />
  <img src="https://img.shields.io/badge/License-MIT-f5b83d?style=for-the-badge" alt="MIT License" />
</p>


A document-grounded RAG system that **evaluates its own answers**. Hybrid retrieval
(BM25 + dense embeddings, fused with Reciprocal Rank Fusion), LLM re-ranking,
citation-grounded generation, and an automated evaluation pipeline measuring
**Faithfulness, Hallucination rate, Answer Relevancy, Context Precision/Recall** —
with a per-claim audit trail for debugging.

**V2 — Adversarial & Semantic Faithfulness Testing:** a fail-closed claim
verification engine (explicit SUPPORTED / CONTRADICTED / NOT_SUPPORTED /
UNCERTAIN / EXTRACTION_FAILED / EVALUATION_ERROR states), deterministic evidence
checks (negation, roles, entities, numbers, temporal, modality), prompt-injection
resistance, and a 104-case adversarial benchmark with confusion matrices and
detection / false-acceptance / false-rejection rates. See
[docs/V2_AUDIT_REPORT.md](docs/V2_AUDIT_REPORT.md),
[docs/ARCHITECTURE_V2.md](docs/ARCHITECTURE_V2.md),
[docs/ADVERSARIAL_BENCHMARK.md](docs/ADVERSARIAL_BENCHMARK.md),
[docs/EVALUATION_METHODOLOGY.md](docs/EVALUATION_METHODOLOGY.md) and
[docs/MIGRATION_V2.md](docs/MIGRATION_V2.md).

**V2.1 — Independent Validation & Research-Grade Evaluation:** scenario-family
disjoint development/held-out splits (+200 fixtures, leakage-gated), Wilson
confidence intervals and raw TP/FP/TN/FN for every proportion, abstention-aware
accuracy, paired mutation + metamorphic red-team testing, normalized semantic
event tuples (agent/patient/tense/aspect/attribution), optional secondary judge,
run manifests (git commit, dataset/prompt hashes, dependency versions),
resumable quota-blocked execution, a public `RAGEvaluator` API with adapters,
and offline CI with benchmark regression gates. Start here:
[docs/REVIEWER_GUIDE.md](docs/REVIEWER_GUIDE.md),
[docs/V21_ENGINEERING_AUDIT.md](docs/V21_ENGINEERING_AUDIT.md),
[docs/BENCHMARK_METHODOLOGY.md](docs/BENCHMARK_METHODOLOGY.md),
[docs/METRIC_DEFINITIONS.md](docs/METRIC_DEFINITIONS.md),
[docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md),
[docs/RED_TEAM_RESULTS.md](docs/RED_TEAM_RESULTS.md),
[docs/OPEN_SOURCE_USAGE.md](docs/OPEN_SOURCE_USAGE.md),
[docs/LIMITATIONS.md](docs/LIMITATIONS.md).

Built with pure-Python retrieval (no native dependencies) and the Gemini API for
embeddings, generation, and LLM-as-judge evaluation.

## V1 results (live run, 12-question golden dataset)

| Metric | bm25 | dense | hybrid | hybrid+rerank |
|---|---|---|---|---|
| Faithfulness | 1.000 | 1.000 | 1.000 | 1.000 |
| Hallucination rate | 0.000 | 0.000 | 0.000 | 0.000 |
| Answer relevancy | 1.000 | 1.000 | 1.000 | 1.000 |
| Context precision | 1.000 | **0.908** | 1.000 | 1.000 |
| Context recall | 1.000 | 1.000 | 1.000 | 1.000 |
| Refusal accuracy (unanswerable) | 1.000 | 1.000 | 1.000 | 1.000 |
| Citation coverage | 1.000 | 1.000 | 1.000 | 1.000 |

Key findings: dense-only retrieval admits less-relevant passages on keyword-heavy
questions (precision 0.908); RRF fusion recovers it to 1.0. All variants refuse
both unanswerable questions correctly — zero fabricated answers. Full audit trail:
[reports/eval_ablation_comparison.md](reports/eval_ablation_comparison.md).

## V2 results (adversarial & semantic faithfulness)

104 synthetic adversarial fixtures (8 categories), live Gemini judge:
**adversarial detection 0.986, false acceptance 0.000**, contradiction F1 0.962,
injection flags 13/13; deterministic LLM-free floor: detection 0.583 with
false acceptance/rejection 0.000 (fail-closed). Consolidated report incl.
retrieval probes, end-to-end ablation status and two documented incidents
(quota cap, verifier bug B16): [reports/v2/FINAL_V2_REPORT.md](reports/v2/FINAL_V2_REPORT.md).

## Architecture

```
Documents (.md/.txt/code)
   │  ingest: recursive chunking (900 chars, 150 overlap)
   ▼
Chunks ──► Gemini embeddings (gemini-embedding-001, 768-d) ──► JSON vector cache
   │
   ▼  query
┌─────────────────────────────────────────────┐
│ Hybrid retrieval                            │
│   BM25 (Okapi, pure Python)  ─┐             │
│                               ├─ RRF fusion │
│   Dense cosine similarity    ─┘             │
└─────────────────────────────────────────────┘
   │  top-10 candidates
   ▼
LLM re-ranker (listwise relevance grades 0–3) ──► top-4 passages
   │
   ▼
Grounded generation (cite [id:xxx], refuse if unsupported)
   │
   ▼
V2 verification engine (fail-closed, ragpipe/verify/)
   ├─ deterministic analysis: negation, modality, entities, numbers, dates
   ├─ semantic stage: SPO + entailment (one structured judge call)
   ├─ support-aware evidence checks + injection screening (untrusted data)
   └─ explicit states: SUPPORTED / CONTRADICTED / NOT_SUPPORTED /
      UNCERTAIN / EXTRACTION_FAILED / EVALUATION_ERROR
   │
   ▼
Evaluation pipeline (LLM-as-judge + deterministic checks)
   ├─ Faithfulness: supported / resolved claim verdicts (None on failure)
   ├─ Hallucination rate (answerable) / fabrication rate (unanswerable), separate
   ├─ Answer relevancy: judge score 0–1
   ├─ Context precision: AP-style; V2 uses an independent judge (not reranker grades)
   ├─ Context recall: reference sentences attributable to context
   └─ Refusal accuracy / over-refusal / citation coverage + validity
   ▼
reports/ (V1) and reports/v2/ (V2 benchmarks, probes, FINAL_V2_REPORT)
```

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
cp .env.example .env    # then add your GEMINI_API_KEY
```

Free API key: https://aistudio.google.com/apikey

## Usage

```bash
# 1. Build the index (chunks + embeddings, cached on disk)
python -m ragpipe.cli ingest

# 2. Ask questions
python -m ragpipe.cli ask "What is the default build timeout?"
python -m ragpipe.cli ask "..." --mode bm25 --no-rerank   # retrieval ablation

# 3. Evaluate against the golden dataset (12 questions, incl. 2 unanswerable)
python -m ragpipe.cli evaluate

# 4. Ablation study: compare retrieval strategies in one report
python -m ragpipe.cli evaluate --variants bm25,dense,hybrid,hybrid+rerank

# Quick smoke run (first 3 questions only)
python -m ragpipe.cli evaluate --limit 3

# V2: adversarial verification benchmark (deterministic = zero API calls)
python -m ragpipe.cli adversarial --mode deterministic
python -m ragpipe.cli adversarial --mode semantic          # live LLM judge

# V2: retrieval-variant probes on adversarial evidence (no LLM judge)
python -m ragpipe.cli probes-v2

# V2: end-to-end ablation with engine verification + independent precision judge
python -m ragpipe.cli evaluate-v2 --variants bm25,dense,hybrid,hybrid+rerank
python -m ragpipe.cli evaluate-v2 --resume          # continue after quota block

# V2.1: leakage-gated splits, red-team, ablation grid, public API
python scripts/check_leakage.py
python scripts/regression_gate.py
python -m ragpipe.cli redteam
python -m ragpipe.cli grid-v21 --mode offline       # deterministic, judge-free
python -m ragpipe.cli grid-v21 --mode mixed         # + live semantic on heldout
```

```python
from ragpipe import RAGEvaluator
evaluator = RAGEvaluator()
result = evaluator.evaluate(question="...", context=["..."], answer="...")
```

Reports land in `reports/` as JSON (full audit trail) and Markdown (comparison
tables + unsupported-claim listing). A real 4-variant run is included:
[reports/eval_ablation_comparison.md](reports/eval_ablation_comparison.md).

## Metrics

| Metric | How it is computed |
|---|---|
| Faithfulness | Atomic claims verified against context; V2 score = SUPPORTED / resolved verdicts (CONTRADICTED + NOT_SUPPORTED count against). `None` on extraction/evaluation failure — never a manufactured 1.0. |
| Hallucination rate (answerable) | `1 − faithfulness` over answerable questions only. |
| Fabrication rate (unanswerable) | Fraction of unanswerable questions answered instead of refused. Reported separately, never averaged with the above. |
| Answer relevancy | LLM judge, 0–1 rubric; correct refusals count as relevant. |
| Context precision | Average-precision-style rank weighting; V1 may use reranker grades, V2 always an independent relevance judge. |
| Context recall | Fraction of reference-answer sentences attributable to retrieved context. |
| Refusal accuracy / over-refusal | Correct refusals on unanswerable / wrong refusals on answerable questions. |
| Citation coverage / validity | Answers carrying ≥1 valid citation; 1 − invalid attempts / all attempts. |
| Claim extraction success / evaluation error rate | Fraction of answered items in OK / EVALUATION_ERROR state (fail-closed health). |

V2 adversarial metrics (fixture benchmark): confusion matrix over the four
verdict states, adversarial detection rate, false acceptance / false rejection
rates, contradiction precision/recall/F1 with TP/FP/FN counts, per-category
exact-match accuracy with sample counts, and injection-flag coverage.
Retrieval probes add evidence hit@10, MRR and evidence recall@4 with no LLM judge.

Every judge returns structured JSON, so each score is auditable down to the
individual claim verdict — the Markdown report lists every unsupported claim
with the judge's reason.

## Sample corpus & golden dataset

`data/docs/` contains documentation for a fictional platform ("Nimbus Deploy")
with concrete, checkable facts (timeouts, prices, versions, limits).
`data/golden_dataset.json` has 12 questions: 10 answerable (single- and
multi-document) and 2 unanswerable ones that test hallucination resistance.

To use your own corpus, drop files into `data/docs/` (`.md`, `.txt`, `.py`,
`.js`, `.ts`, `.json`, `.yaml`, `.rst`), re-run `ingest`, and extend the golden
dataset.

## Design notes

- **Pure-Python BM25 + cosine** — zero native dependencies; the corpus is small
  enough that NumPy/FAISS add no measurable speed, and the implementation stays
  fully inspectable.
- **RRF fusion** (`1/(60+rank)`) — rank-based, so BM25 and cosine scores never
  need calibration against each other.
- **Embedding cache** keyed by chunk id + model + dimension — re-ingesting only
  embeds new/changed chunks.
- **Rate limiting & retries** — client-side pacing (`RAG_RPM`, separate
  `RAG_EMBED_RPM`) plus exponential backoff on 429/5xx and transport failures;
  explicit 120 s timeouts; empty/blocked completions raise instead of scoring.
- **Response cache** — judge responses cached on disk keyed by model+prompt;
  benchmark replays are quota-free and reproducible (`RAG_LLM_CACHE=0` disables).
- **Fail-closed evaluation** — every failure mode yields an explicit state and
  `None`, never a silent perfect score; incompatible metric populations are
  reported separately.
- **Support-aware deterministic checks** — a contradiction flag requires a
  conflict AND no supporting sentence (multi-fact contexts don't self-contradict);
  negation is clause-scoped; injection sentences are excluded from evidence.
- **Model choice** — defaults to `gemini-3.5-flash-lite`: older `gemini-2.5-flash`
  free tier allows only 20 requests/day and is closed to new API keys. The
  flash-lite free tier caps at 500 generate requests/day; long ablations may
  need a second day (documented in FINAL_V2_REPORT.md). Override with
  `RAG_LLM_MODEL` if you have a paid quota.
- **Ablation-first evaluation** — the same runner scores `bm25`, `dense`,
  `hybrid`, and `+rerank` variants, making retrieval regressions visible.

## Tests

```bash
python -m pytest tests/ -q    # 114 tests, no API calls needed
```

Covers chunking, BM25, RRF fusion math, reranker grade handling, citation
filtering, refusal detection, metric math, report rendering, deterministic
adversarial checks, engine fail-closed states, schema validation, API
failure/retry/cache behavior, and mocked-judge integration paths.

## Project layout

```
ragpipe/
  config.py        # settings + .env loading
  llm.py           # Gemini client: pacing, retries, JSON mode
  ingest.py        # document loading + recursive chunking
  embeddings.py    # embedding cache (JSON, pure Python)
  retrieval.py     # BM25 + dense + RRF hybrid search
  rerank.py        # listwise LLM re-ranking
  generator.py     # grounded answers with citations
  pipeline.py      # end-to-end orchestration
  evaluate/
    metrics.py     # faithfulness, relevancy, precision, recall judges (fail-closed)
    runner.py      # V1 dataset runner, variants, aggregation
    runner_v2.py   # V2 runner: engine verification + independent precision judge
    report.py      # Markdown report with claim audit
  verify/
    schemas.py     # Pydantic claim/event/verdict models + explicit states
    checks.py      # deterministic evidence checks (LLM-free, support-aware)
    engine.py      # multi-stage fail-closed verification engine (prompt v2.1)
  adversarial/
    dataset.py     # split loaders + schema validation (12 categories)
    benchmark.py   # deterministic / semantic / mocked benchmark modes
    metrics.py     # confusion matrices, detection/FAR/FRR, PRF, Wilson CIs
    probes.py      # retrieval-variant evidence probes
  evaluate/
    ablation_v21.py # 4 variants x {adversarial, development, heldout} grid
  evalstats.py     # Wilson intervals, TP/FP/TN/FN, macro/micro, abstentions
  redteam.py       # paired mutation + metamorphic testing
  manifest.py      # run provenance (commit, hashes, deps, API status)
  api.py           # public RAGEvaluator + adapter protocols
  cli.py           # ingest / ask / evaluate / evaluate-v2 / adversarial /
                   # probes-v2 / grid-v21 / redteam
data/original/     # V1 12-question golden set (unchanged)
data/adversarial/  # V2 104 fixtures (unchanged)
data/development/  # 60 tuning fixtures (families F01-F10)
data/heldout/      # 140 unseen fixtures (families F11-F20)
data/regression/   # CI gate pins
docs/              # V2 + V2.1 audits, methodology, metrics, reviewer guide
examples/          # offline external-usage example
scripts/           # leakage gate, regression gate, dataset/report builders
tests/             # 114 tests
reports/           # V1 evaluation reports (immutable history)
reports/v2/        # V2 benchmark reports
reports/v2_1/      # V2.1 grids, red-team, executive summary
```

## License

MIT — see [LICENSE](LICENSE).