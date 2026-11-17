import re
from dataclasses import dataclass, field

from .llm import GeminiClient
from .retrieval import RetrievedChunk

ANSWER_SYSTEM = (
    "You are a precise documentation assistant. Answer the question using ONLY the "
    "provided context passages.\n"
    "Rules:\n"
    "1. Cite the passage ids you use inline like [id:abc123] immediately after the "
    "claim they support.\n"
    "2. If the context does not contain the answer, reply exactly: "
    "\"I cannot answer this from the provided documents.\" and nothing else.\n"
    "3. Never use outside knowledge, never guess numbers, names or versions.\n"
    "4. Be concise and factual."
)


@dataclass
class Answer:
    text: str
    cited_ids: list[str] = field(default_factory=list)
    refused: bool = False
    invalid_citations: list[str] = field(default_factory=list)


REFUSAL_MARKER = "cannot answer this from the provided documents"


def extract_citations(text: str, valid_ids: set[str]) -> list[str]:
    """Accept [id:xxx], [id:xxx, id:yyy] and bare [xxx] / [xxx, yyy] formats."""
    cited: list[str] = []
    for bracket in re.findall(r"\[([^\]]*)\]", text):
        for token in re.split(r"[,\s]+", bracket):
            token = token.strip().removeprefix("id:")
            if token in valid_ids:
                cited.append(token)
    return list(dict.fromkeys(cited))


def citation_attempts(text: str) -> list[str]:
    """All citation-like tokens, including invalid ones (for validity metrics)."""
    attempts: list[str] = []
    for bracket in re.findall(r"\[([^\]]*)\]", text):
        for token in re.split(r"[,\s]+", bracket):
            token = token.strip().removeprefix("id:")
            if re.fullmatch(r"[a-f0-9]{6,}", token):
                attempts.append(token)
    return list(dict.fromkeys(attempts))


def generate_answer(query: str, contexts: list[RetrievedChunk], client: GeminiClient) -> Answer:
    passages = "\n\n".join(
        f"[id: {c.chunk.id}] (source: {c.chunk.doc})\n{c.chunk.text}" for c in contexts
    )
    prompt = f"Context passages:\n{passages}\n\nQuestion: {query}"
    text = client.generate(prompt, system=ANSWER_SYSTEM, temperature=0.0).strip()

    valid_ids = {c.chunk.id for c in contexts}
    cited = extract_citations(text, valid_ids)
    attempts = citation_attempts(text)
    invalid = [t for t in attempts if t not in valid_ids]
    refused = REFUSAL_MARKER in text.lower()
    return Answer(text=text, cited_ids=cited, refused=refused, invalid_citations=invalid)