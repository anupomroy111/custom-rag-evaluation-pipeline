# RAG Evaluation Report

- **Generated:** 2026-11-17 20:08:04
- **LLM:** `gemini-3.5-flash-lite`  |  **Embeddings:** `gemini-embedding-001`
- **Questions:** 12

## Variant comparison

| Metric | bm25 | dense | hybrid | hybrid+rerank |
|---|---|---|---|---|
| Faithfulness | 1.000 | 1.000 | 1.000 | 1.000 |
| Hallucination rate | 0.000 | 0.000 | 0.000 | 0.000 |
| Answer relevancy | 1.000 | 1.000 | 1.000 | 1.000 |
| Context precision | 1.000 | 0.908 | 1.000 | 1.000 |
| Context recall | 1.000 | 1.000 | 1.000 | 1.000 |
| Refusal accuracy (unanswerable) | 1.000 | 1.000 | 1.000 | 1.000 |
| Over-refusal rate | 0.000 | 0.000 | 0.000 | 0.000 |
| Citation coverage | 1.000 | 1.000 | 1.000 | 1.000 |

## Details: `bm25`

| # | Question | Faithful | Halluc. | Relevancy | Ctx Prec | Ctx Recall | Refused |
|---|---|---|---|---|---|---|---|
| 1 | What is the default build timeout in Nimbus, and what is the... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 2 | How much RAM does a free tier service instance get, and what... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 3 | Which role is allowed to deploy to prod and manage secrets? | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 4 | How does the Gateway handle retries on 5xx responses? | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 5 | What command rolls back a prod service to a specific revisio... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 6 | How long are audit logs retained, and where can they be expo... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 7 | What changed in release v2.4.0 regarding build nodes and can... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 8 | My service returns 502 after deploy and my build times out. ... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 9 | How much does the Pro tier cost and how many builds per mont... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 10 | Where are application secrets stored, and what must happen f... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 11 | Who is the CEO of Nimbus Deploy and what is their background... | n/a | 0.000 | 1.000 | n/a | n/a | yes |
| 12 | Does Nimbus offer GPU instances for machine learning workloa... | n/a | 0.000 | 1.000 | n/a | n/a | yes |

## Details: `dense`

| # | Question | Faithful | Halluc. | Relevancy | Ctx Prec | Ctx Recall | Refused |
|---|---|---|---|---|---|---|---|
| 1 | What is the default build timeout in Nimbus, and what is the... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 2 | How much RAM does a free tier service instance get, and what... | 1.000 | 0.000 | 1.000 | 0.917 | 1.000 | no |
| 3 | Which role is allowed to deploy to prod and manage secrets? | 1.000 | 0.000 | 1.000 | 0.500 | 1.000 | no |
| 4 | How does the Gateway handle retries on 5xx responses? | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 5 | What command rolls back a prod service to a specific revisio... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 6 | How long are audit logs retained, and where can they be expo... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 7 | What changed in release v2.4.0 regarding build nodes and can... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 8 | My service returns 502 after deploy and my build times out. ... | 1.000 | 0.000 | 1.000 | 0.833 | 1.000 | no |
| 9 | How much does the Pro tier cost and how many builds per mont... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 10 | Where are application secrets stored, and what must happen f... | 1.000 | 0.000 | 1.000 | 0.833 | 1.000 | no |
| 11 | Who is the CEO of Nimbus Deploy and what is their background... | n/a | 0.000 | 1.000 | n/a | n/a | yes |
| 12 | Does Nimbus offer GPU instances for machine learning workloa... | n/a | 0.000 | 1.000 | n/a | n/a | yes |

## Details: `hybrid`

| # | Question | Faithful | Halluc. | Relevancy | Ctx Prec | Ctx Recall | Refused |
|---|---|---|---|---|---|---|---|
| 1 | What is the default build timeout in Nimbus, and what is the... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 2 | How much RAM does a free tier service instance get, and what... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 3 | Which role is allowed to deploy to prod and manage secrets? | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 4 | How does the Gateway handle retries on 5xx responses? | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 5 | What command rolls back a prod service to a specific revisio... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 6 | How long are audit logs retained, and where can they be expo... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 7 | What changed in release v2.4.0 regarding build nodes and can... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 8 | My service returns 502 after deploy and my build times out. ... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 9 | How much does the Pro tier cost and how many builds per mont... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 10 | Where are application secrets stored, and what must happen f... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 11 | Who is the CEO of Nimbus Deploy and what is their background... | n/a | 0.000 | 1.000 | n/a | n/a | yes |
| 12 | Does Nimbus offer GPU instances for machine learning workloa... | n/a | 0.000 | 1.000 | n/a | n/a | yes |

## Details: `hybrid+rerank`

| # | Question | Faithful | Halluc. | Relevancy | Ctx Prec | Ctx Recall | Refused |
|---|---|---|---|---|---|---|---|
| 1 | What is the default build timeout in Nimbus, and what is the... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 2 | How much RAM does a free tier service instance get, and what... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 3 | Which role is allowed to deploy to prod and manage secrets? | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 4 | How does the Gateway handle retries on 5xx responses? | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 5 | What command rolls back a prod service to a specific revisio... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 6 | How long are audit logs retained, and where can they be expo... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 7 | What changed in release v2.4.0 regarding build nodes and can... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 8 | My service returns 502 after deploy and my build times out. ... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 9 | How much does the Pro tier cost and how many builds per mont... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 10 | Where are application secrets stored, and what must happen f... | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | no |
| 11 | Who is the CEO of Nimbus Deploy and what is their background... | n/a | 0.000 | 1.000 | n/a | n/a | yes |
| 12 | Does Nimbus offer GPU instances for machine learning workloa... | n/a | 0.000 | 1.000 | n/a | n/a | yes |

## Metric definitions

- **Faithfulness** — fraction of atomic answer claims supported by retrieved context (claim extraction + per-claim LLM verification).
- **Hallucination rate** — `1 - faithfulness` for answerable questions; for unanswerable questions, 1 if the model fabricated an answer instead of refusing.
- **Answer relevancy** — LLM-judged alignment of the answer with the question (0–1).
- **Context precision** — rank-weighted (average-precision style) relevance of retrieved passages; uses reranker grades when available.
- **Context recall** — fraction of reference-answer sentences attributable to retrieved context.
- **Refusal accuracy** — correct refusals on unanswerable questions; **Over-refusal** — wrong refusals on answerable ones.

## Findings

- All four variants achieve faithfulness 1.0 and zero hallucinations on this corpus; both unanswerable questions are correctly refused everywhere.
- **dense** is the weakest retriever here (context precision 0.908): its top-4 admits less-relevant passages than BM25 on keyword-heavy questions.
- **hybrid (RRF)** recovers precision to 1.0 by letting BM25 consensus outrank dense-only hits.
- **hybrid+rerank** matches hybrid on every metric; the reranker adds no measurable gain on this small, lexically-aligned corpus — its value shows on larger or paraphrased corpora.
- The sample corpus is intentionally small (13 chunks); differences between strategies are expected to widen with corpus size and question paraphrasing.
