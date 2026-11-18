"""Retrieval-side adversarial probes (V2 ablation, retrieval variants).

Each adversarial case contributes its evidence passages as a synthetic document.
For every retrieval variant we measure, deterministically (no LLM judge):
  evidence_hit_rate@10 — gold evidence present in top-10
  mrr                — reciprocal rank of first gold evidence passage
  evidence_recall@4  — gold evidence coverage in the final top-4 window

Probes isolate RETRIEVAL only (bm25/dense/hybrid). The reranking stage is
benchmarked end-to-end by `evaluate-v2`, where it actually runs; labeling a
retrieval-only probe as "+rerank" would overstate what was measured.
"""

import json
import time
from pathlib import Path

from ..config import settings
from ..embeddings import EmbeddingStore
from ..ingest import chunk_documents, load_documents, save_chunks
from ..llm import GeminiClient
from ..retrieval import HybridRetriever
from .dataset import AdversarialCase, load_adversarial

VARIANTS = ["bm25", "dense", "hybrid"]


class CachingEmbedClient:
    """Delegates embeddings but memoizes query vectors across variants and
    across processes (disk cache) so replays never repay embed quota."""

    def __init__(self, inner: GeminiClient, cache_path: Path | None = None):
        self.inner = inner
        self.cache_path = cache_path or settings.index_dir / "query_cache.json"
        self._cache: dict[str, list[float]] = {}
        if self.cache_path.exists():
            self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))

    def embed(self, texts: list[str]) -> list[list[float]]:
        missing = [t for t in texts if t not in self._cache]
        if missing:
            for t, vec in zip(missing, self.inner.embed(missing)):
                self._cache[t] = vec
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._cache), encoding="utf-8")
        return [self._cache[t] for t in texts]


def build_probe_index(cases: list[AdversarialCase], client: GeminiClient,
                      index_dir: Path | None = None):
    index_dir = index_dir or settings.index_dir / "probes"
    docs = load_documents(settings.docs_dir)
    for case in cases:
        docs[f"adv/{case.id}.md"] = "\n\n".join(case.context)
    chunks = chunk_documents(docs)
    save_chunks(chunks, index_dir / "chunks.json")
    matrix = EmbeddingStore(index_dir).build(chunks, client)
    return chunks, HybridRetriever(chunks, matrix)


def probe_question(case: AdversarialCase) -> str:
    return case.probe_question or case.claims[0]


def run_probes(cases: list[AdversarialCase], client: GeminiClient,
               index_dir: Path | None = None) -> dict:
    chunks, retriever = build_probe_index(cases, client, index_dir)
    caching = CachingEmbedClient(client)
    gold_by_case = {
        case.id: {c.id for c in chunks if c.doc == f"adv/{case.id}.md"} for case in cases
    }

    variants: dict[str, dict] = {}
    for variant in VARIANTS:
        mode = variant.removesuffix("+rerank")
        hits, rr, recalls = 0, 0.0, []
        per_case = []
        for case in cases:
            gold = gold_by_case[case.id]
            results = retriever.search(
                probe_question(case), client=caching if mode != "bm25" else None,
                mode=mode, top_k=10,
            )
            ids = [r.chunk.id for r in results]
            hit = bool(gold & set(ids))
            hits += int(hit)
            first = next((i + 1 for i, cid in enumerate(ids) if cid in gold), None)
            rr += 1.0 / first if first else 0.0
            recall4 = len(gold & set(ids[:4])) / len(gold) if gold else 0.0
            recalls.append(recall4)
            per_case.append({"id": case.id, "category": case.category,
                             "hit": hit, "first_gold_rank": first,
                             "evidence_recall_at_4": round(recall4, 4)})
        n = len(cases)
        variants[variant] = {
            "n": n,
            "evidence_hit_rate_at_10": round(hits / n, 4) if n else None,
            "mrr": round(rr / n, 4) if n else None,
            "evidence_recall_at_4": round(sum(recalls) / n, 4) if n else None,
            "per_case": per_case,
        }
        print(f"probe variant {variant}: hit@10={variants[variant]['evidence_hit_rate_at_10']} "
              f"mrr={variants[variant]['mrr']}", flush=True)

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": "retrieval-probes",
        "judge": "deterministic (no LLM relevance judge)",
        "n_cases": len(cases),
        "variants": variants,
    }


def save_probes(report: dict, out_dir: Path | None = None) -> tuple[Path, Path]:
    out_dir = out_dir or settings.reports_dir / "v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    base = out_dir / f"probes_{stamp}"
    base.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Retrieval Probes on Adversarial Evidence (V2)", "",
             f"- **Generated:** {report['timestamp']}",
             f"- **Judge:** {report['judge']}",
             f"- **Cases:** {report['n_cases']}", "",
             "| Variant | n | Evidence hit@10 | MRR | Evidence recall@4 |",
             "|---|---|---|---|---|"]
    for name, v in report["variants"].items():
        lines.append(f"| {name} | {v['n']} | {v['evidence_hit_rate_at_10']} | "
                     f"{v['mrr']} | {v['evidence_recall_at_4']} |")
    lines.append("")
    base.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return base.with_suffix(".json"), base.with_suffix(".md")