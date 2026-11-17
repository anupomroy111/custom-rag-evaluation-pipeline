"""Custom Ragas-style metrics: LLM-as-judge + deterministic checks.

Every judge returns structured JSON so each score has an auditable trail
(claim verdicts, per-chunk relevance, per-sentence recall attribution).
"""

from dataclasses import dataclass, field

from ..llm import GeminiClient

CLAIM_EXTRACT_SYSTEM = (
    "Extract the atomic factual claims made in the answer. A claim is a single "
    "statement that can be verified independently (a number, name, behavior, version). "
    "Ignore citations like [id:xxx], opinions and filler. "
    "Return ONLY JSON: {\"claims\": [string, ...]}. If the answer makes no factual "
    "claims (e.g. a refusal), return {\"claims\": []}."
)

CLAIM_VERIFY_SYSTEM = (
    "You verify claims against reference context. For each claim decide whether it "
    "is directly supported by the context. A claim is NOT supported if the context "
    "is silent about it or contradicts it, even if the claim might be true in general. "
    "Return ONLY JSON: {\"verdicts\": [{\"claim\": string, \"supported\": bool, "
    "\"reason\": string}]} with one verdict per claim, in order."
)

RELEVANCY_SYSTEM = (
    "Rate how well the answer addresses the question, ignoring style. "
    "1.0 = complete and on-topic, 0.5 = partial or vague, 0.0 = off-topic or empty. "
    "A correct refusal when the question is unanswerable from the documents counts "
    "as fully relevant (1.0). "
    "Return ONLY JSON: {\"score\": number between 0 and 1, \"reason\": string}."
)

CONTEXT_RELEVANCE_SYSTEM = (
    "For each numbered passage, judge whether it is useful for answering the question. "
    "Return ONLY JSON: {\"verdicts\": [{\"index\": int, \"relevant\": bool}]} "
    "with one verdict per passage."
)

RECALL_SYSTEM = (
    "You are given a reference answer and retrieved context passages. For each "
    "sentence of the reference answer, decide whether that sentence can be "
    "attributed to (is supported by) any of the passages. "
    "Return ONLY JSON: {\"verdicts\": [{\"sentence\": string, \"attributed\": bool}]} "
    "with one verdict per reference sentence, in order."
)


@dataclass
class FaithfulnessResult:
    score: float
    claims: list[str] = field(default_factory=list)
    verdicts: list[dict] = field(default_factory=list)

    @property
    def hallucination_rate(self) -> float:
        return 1.0 - self.score


def extract_claims(answer_text: str, client: GeminiClient) -> list[str]:
    data = client.generate_json(f"Answer:\n{answer_text}", system=CLAIM_EXTRACT_SYSTEM)
    claims = data.get("claims", []) if isinstance(data, dict) else []
    return [str(c) for c in claims if str(c).strip()]


def faithfulness(answer_text: str, context_texts: list[str],
                 client: GeminiClient) -> FaithfulnessResult:
    claims = extract_claims(answer_text, client)
    if not claims:
        return FaithfulnessResult(score=1.0)
    context = "\n\n---\n\n".join(context_texts)
    prompt = f"Context:\n{context}\n\nClaims:\n" + "\n".join(
        f"{i + 1}. {c}" for i, c in enumerate(claims)
    )
    data = client.generate_json(prompt, system=CLAIM_VERIFY_SYSTEM)
    raw = data.get("verdicts", []) if isinstance(data, dict) else []
    verdicts = []
    for i, claim in enumerate(claims):
        v = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
        verdicts.append({
            "claim": claim,
            "supported": bool(v.get("supported", False)),
            "reason": str(v.get("reason", "")),
        })
    supported = sum(1 for v in verdicts if v["supported"])
    return FaithfulnessResult(score=supported / len(verdicts), claims=claims, verdicts=verdicts)


def answer_relevancy(question: str, answer_text: str, client: GeminiClient) -> dict:
    prompt = f"Question: {question}\n\nAnswer:\n{answer_text}"
    data = client.generate_json(prompt, system=RELEVANCY_SYSTEM)
    score = float(data.get("score", 0.0)) if isinstance(data, dict) else 0.0
    return {"score": max(0.0, min(1.0, score)),
            "reason": str(data.get("reason", "")) if isinstance(data, dict) else ""}


def context_precision(question: str, context_texts: list[str],
                      client: GeminiClient,
                      grades: dict[str, int] | None = None,
                      context_ids: list[str] | None = None) -> dict:
    """Rank-weighted precision (average-precision style) over retrieved passages.

    Uses reranker relevance grades when available (>=2 counts as relevant),
    otherwise falls back to a binary LLM judgment per passage.
    """
    if not context_texts:
        return {"score": 0.0, "relevant": []}

    if grades and context_ids:
        relevant = [grades.get(cid, 0) >= 2 for cid in context_ids]
    else:
        passages = "\n\n".join(f"Passage {i + 1}:\n{t[:1200]}"
                               for i, t in enumerate(context_texts))
        data = client.generate_json(f"Question: {question}\n\n{passages}",
                                    system=CONTEXT_RELEVANCE_SYSTEM)
        raw = data.get("verdicts", []) if isinstance(data, dict) else []
        relevant = [False] * len(context_texts)
        for v in raw:
            if isinstance(v, dict):
                idx = int(v.get("index", 0)) - 1
                if 0 <= idx < len(relevant):
                    relevant[idx] = bool(v.get("relevant", False))

    hits, ap_sum = 0, 0.0
    for k, rel in enumerate(relevant, start=1):
        if rel:
            hits += 1
            ap_sum += hits / k
    score = ap_sum / hits if hits else 0.0
    return {"score": score, "relevant": relevant}


def context_recall(ground_truth: str, context_texts: list[str],
                   client: GeminiClient) -> dict:
    if not ground_truth.strip():
        return {"score": 1.0, "verdicts": []}
    context = "\n\n---\n\n".join(context_texts)
    prompt = f"Retrieved passages:\n{context}\n\nReference answer:\n{ground_truth}"
    data = client.generate_json(prompt, system=RECALL_SYSTEM)
    raw = data.get("verdicts", []) if isinstance(data, dict) else []
    verdicts = [{"sentence": str(v.get("sentence", "")),
                 "attributed": bool(v.get("attributed", False))}
                for v in raw if isinstance(v, dict)]
    if not verdicts:
        return {"score": 0.0, "verdicts": []}
    score = sum(1 for v in verdicts if v["attributed"]) / len(verdicts)
    return {"score": score, "verdicts": verdicts}