# Custom RAG & Evaluation Pipeline

A document-grounded RAG system that **evaluates its own answers**. Hybrid retrieval
(BM25 + dense embeddings, fused with Reciprocal Rank Fusion), LLM re-ranking,
citation-grounded generation, and an automated evaluation pipeline measuring
**Faithfulness, Hallucination rate, Answer Relevancy, Context Precision/Recall** —
with a per-claim audit trail for debugging.

Built with pure-Python retrieval (no native dependencies) and the Gemini API for
embeddings, generation, and LLM-as-judge evaluation.

## Results (live run, 12-question golden dataset)

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
Evaluation pipeline (LLM-as-judge + deterministic checks)
   ├─ Faithfulness: claim extraction → per-claim verification vs context
   ├─ Hallucination rate: 1 − faithfulness; fabrication on unanswerable questions
   ├─ Answer relevancy: judge score 0–1
   ├─ Context precision: rank-weighted (AP-style) passage relevance
   ├─ Context recall: reference sentences attributable to context
   └─ Refusal accuracy / over-refusal / citation coverage
   ▼
reports/eval_<timestamp>.json + .md  (variant comparison + claim audit)
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
```

Reports land in `reports/` as JSON (full audit trail) and Markdown (comparison
tables + unsupported-claim listing). A real 4-variant run is included:
[reports/eval_ablation_comparison.md](reports/eval_ablation_comparison.md).

## Metrics

| Metric | How it is computed |
|---|---|
| Faithfulness | Extract atomic claims from the answer, verify each against retrieved context (2-step LLM judge). Score = supported / total. |
| Hallucination rate | `1 − faithfulness`; for unanswerable questions, 1 if the model fabricated instead of refusing. |
| Answer relevancy | LLM judge, 0–1 rubric; correct refusals count as relevant. |
| Context precision | Average-precision-style rank weighting over relevant passages; uses reranker grades (≥2) when available. |
| Context recall | Fraction of reference-answer sentences attributable to retrieved context. |
| Refusal accuracy | Correct refusals on unanswerable questions (hallucination resistance). |
| Over-refusal rate | Wrong refusals on answerable questions. |
| Citation coverage | Fraction of answers carrying valid passage citations. |

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
- **Rate limiting & retries** — client-side pacing (`RAG_RPM`) plus exponential
  backoff on 429/5xx, so evaluation runs survive free-tier quotas.
- **Model choice** — defaults to `gemini-3.5-flash-lite`: older `gemini-2.5-flash`
  free tier allows only 20 requests/day (an eval run needs ~80) and is closed to
  new API keys. Override with `RAG_LLM_MODEL` if you have a paid quota.
- **Ablation-first evaluation** — the same runner scores `bm25`, `dense`,
  `hybrid`, and `+rerank` variants, making retrieval regressions visible.

## Tests

```bash
python -m pytest tests/ -q    # 31 tests, no API calls needed
```

Covers chunking, BM25, RRF fusion math, reranker grade handling, citation
filtering, refusal detection, metric math, and report rendering.

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
    metrics.py     # faithfulness, relevancy, precision, recall judges
    runner.py      # dataset runner, variants, aggregation
    report.py      # Markdown report with claim audit
  cli.py           # ingest / ask / evaluate
data/docs/         # sample corpus
data/golden_dataset.json
tests/
reports/           # generated evaluation reports
```