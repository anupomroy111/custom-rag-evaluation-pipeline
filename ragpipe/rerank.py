from .config import settings
from .llm import GeminiClient
from .retrieval import RetrievedChunk

RERANK_SYSTEM = (
    "You are a search relevance judge. Given a question and candidate passages, "
    "rate each passage's relevance to answering the question. "
    "Return ONLY JSON: a list of objects {\"id\": string, \"relevance\": integer 0-3}. "
    "3 = directly answers the question, 2 = strongly related, 1 = tangential, 0 = irrelevant. "
    "Judge every candidate id exactly once."
)


def llm_rerank(query: str, candidates: list[RetrievedChunk], client: GeminiClient,
               top_k: int | None = None) -> tuple[list[RetrievedChunk], dict[str, int]]:
    """Listwise LLM re-ranking. Returns reordered chunks and per-id relevance grades."""
    top_k = top_k or settings.top_k_final
    if not candidates:
        return [], {}

    passages = "\n\n".join(
        f"[id: {c.chunk.id}]\n{c.chunk.text[:1200]}" for c in candidates
    )
    prompt = f"Question: {query}\n\nCandidate passages:\n{passages}"
    judgments = client.generate_json(prompt, system=RERANK_SYSTEM)

    grades: dict[str, int] = {}
    if isinstance(judgments, list):
        for item in judgments:
            if isinstance(item, dict) and "id" in item:
                try:
                    grades[str(item["id"])] = max(0, min(3, int(item.get("relevance", 0))))
                except (TypeError, ValueError):
                    continue

    by_id = {c.chunk.id: c for c in candidates}
    ordered = sorted(candidates, key=lambda c: grades.get(c.chunk.id, 0), reverse=True)
    kept = [RetrievedChunk(chunk=c.chunk, score=float(grades.get(c.chunk.id, 0)), rank=r + 1)
            for r, c in enumerate(ordered[:top_k])]
    return kept, {cid: g for cid, g in grades.items() if cid in by_id}