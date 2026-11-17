from dataclasses import dataclass, field
from pathlib import Path

from .config import settings
from .embeddings import EmbeddingStore
from .generator import Answer, generate_answer
from .ingest import Chunk, chunk_documents, load_chunks, load_documents, save_chunks
from .llm import GeminiClient
from .rerank import llm_rerank
from .retrieval import HybridRetriever, RetrievedChunk


@dataclass
class PipelineResult:
    question: str
    answer: Answer
    retrieved: list[RetrievedChunk]
    contexts: list[RetrievedChunk]
    relevance_grades: dict[str, int] = field(default_factory=dict)
    mode: str = "hybrid"
    reranked: bool = True


def build_index(client: GeminiClient, docs_dir: Path | None = None) -> list[Chunk]:
    docs_dir = docs_dir or settings.docs_dir
    docs = load_documents(docs_dir)
    chunks = chunk_documents(docs)
    save_chunks(chunks, settings.index_dir / "chunks.json")
    EmbeddingStore().build(chunks, client)
    print(f"Indexed {len(chunks)} chunks from {len(docs)} documents.")
    return chunks


class RAGPipeline:
    def __init__(self, client: GeminiClient | None = None,
                 index_dir: Path | None = None):
        self.client = client or GeminiClient()
        chunks_path = (index_dir or settings.index_dir) / "chunks.json"
        self.chunks = load_chunks(chunks_path)
        matrix = EmbeddingStore(index_dir).load(self.chunks)
        self.retriever = HybridRetriever(self.chunks, matrix)

    def run(self, question: str, mode: str = "hybrid", rerank: bool = True,
            top_k: int | None = None) -> PipelineResult:
        retrieved = self.retriever.search(
            question, client=self.client if mode != "bm25" else None, mode=mode
        )
        grades: dict[str, int] = {}
        if rerank:
            contexts, grades = llm_rerank(question, retrieved, self.client, top_k=top_k)
        else:
            contexts = retrieved[:(top_k or settings.top_k_final)]
        answer = generate_answer(question, contexts, self.client)
        return PipelineResult(
            question=question, answer=answer, retrieved=retrieved,
            contexts=contexts, relevance_grades=grades, mode=mode, reranked=rerank,
        )