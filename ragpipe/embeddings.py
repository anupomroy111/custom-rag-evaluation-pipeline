import json
import math
from pathlib import Path

from .config import settings
from .ingest import Chunk
from .llm import GeminiClient


def normalize(matrix: list[list[float]]) -> list[list[float]]:
    unit = []
    for row in matrix:
        norm = math.sqrt(sum(v * v for v in row)) or 1.0
        unit.append([v / norm for v in row])
    return unit


class EmbeddingStore:
    """Dense vectors with an on-disk JSON cache keyed by chunk id + model + dimension."""

    def __init__(self, index_dir: Path | None = None):
        self.index_dir = index_dir or settings.index_dir
        self.cache_path = self.index_dir / "embeddings.json"

    def _cache_key(self) -> dict:
        return {"model": settings.embed_model, "dim": settings.embed_dim}

    def _load_cache(self) -> tuple[dict[str, int], list[list[float]] | None]:
        if not self.cache_path.exists():
            return {}, None
        data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        if data.get("key") != self._cache_key():
            return {}, None
        return data["rows"], data["vectors"]

    def build(self, chunks: list[Chunk], client: GeminiClient) -> list[list[float]]:
        rows, cached = self._load_cache()
        matrix: list[list[float]] = [[0.0] * settings.embed_dim for _ in chunks]

        missing: list[int] = []
        for i, chunk in enumerate(chunks):
            row = rows.get(chunk.id)
            if row is not None and cached is not None and row < len(cached):
                matrix[i] = cached[row]
            else:
                missing.append(i)

        if missing:
            texts = [chunks[i].text for i in missing]
            print(f"Embedding {len(missing)} chunks ({len(chunks) - len(missing)} cached)...")
            vectors = client.embed(texts)
            for i, vec in zip(missing, vectors):
                matrix[i] = list(vec)

        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps({
            "key": self._cache_key(),
            "rows": {chunk.id: i for i, chunk in enumerate(chunks)},
            "vectors": matrix,
        }), encoding="utf-8")
        return matrix

    def load(self, chunks: list[Chunk]) -> list[list[float]]:
        rows, cached = self._load_cache()
        if cached is None:
            raise FileNotFoundError("Embedding index missing. Run `ingest` first.")
        matrix: list[list[float]] = []
        for chunk in chunks:
            row = rows.get(chunk.id)
            if row is None:
                raise KeyError(f"Chunk {chunk.id} ({chunk.doc}) not in embedding index. Re-run `ingest`.")
            matrix.append(cached[row])
        return matrix