import math
import re
from collections import Counter
from dataclasses import dataclass

from .config import settings
from .embeddings import normalize
from .ingest import Chunk
from .llm import GeminiClient

TOKEN_RE = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class BM25:
    """Okapi BM25 (k1=1.5, b=0.75), pure Python — no native dependencies."""

    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.doc_len = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0
        self.tf = [Counter(doc) for doc in corpus]
        df: Counter = Counter()
        for counts in self.tf:
            df.update(counts.keys())
        n = len(corpus)
        self.idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores = [0.0] * len(self.tf)
        for term in query_tokens:
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, counts in enumerate(self.tf):
                freq = counts.get(term, 0)
                if not freq:
                    continue
                denom = freq + self.k1 * (
                    1 - self.b + self.b * self.doc_len[i] / (self.avgdl or 1.0)
                )
                scores[i] += idf * freq * (self.k1 + 1) / denom
        return scores


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float
    rank: int


def _top_indices(scores: list[float], top_k: int) -> list[int]:
    return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]


class HybridRetriever:
    """BM25 + dense cosine search, fused with Reciprocal Rank Fusion (RRF)."""

    def __init__(self, chunks: list[Chunk], matrix: list[list[float]], rrf_k: int = 60):
        self.chunks = chunks
        self.rrf_k = rrf_k
        self.bm25 = BM25([tokenize(c.text) for c in chunks])
        self.unit_matrix = normalize(matrix)

    def bm25_search(self, query: str, top_k: int) -> list[int]:
        return _top_indices(self.bm25.get_scores(tokenize(query)), top_k)

    def dense_search(self, query_vec: list[float], top_k: int) -> list[int]:
        norm = math.sqrt(sum(v * v for v in query_vec)) or 1.0
        q = [v / norm for v in query_vec]
        scores = [sum(a * b for a, b in zip(row, q)) for row in self.unit_matrix]
        return _top_indices(scores, top_k)

    def search(self, query: str, client: GeminiClient | None = None,
               mode: str = "hybrid", top_k: int | None = None) -> list[RetrievedChunk]:
        top_k = top_k or settings.top_k_retrieval
        rankings: list[list[int]] = []

        if mode in ("bm25", "hybrid"):
            rankings.append(self.bm25_search(query, top_k))
        if mode in ("dense", "hybrid"):
            if client is None:
                raise ValueError("dense/hybrid search needs a GeminiClient for query embedding")
            query_vec = client.embed([query])[0]
            rankings.append(self.dense_search(query_vec, top_k))
        if not rankings:
            raise ValueError(f"Unknown retrieval mode: {mode!r}")

        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, idx in enumerate(ranking):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (self.rrf_k + rank + 1)

        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        return [RetrievedChunk(chunk=self.chunks[i], score=s, rank=r + 1)
                for r, (i, s) in enumerate(ordered)]