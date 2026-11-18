"""Public Python API for external developers (V2.1 §11).

    from ragpipe import RAGEvaluator
    evaluator = RAGEvaluator(config={"llm_model": "gemini-3.5-flash-lite"})
    result = evaluator.evaluate(question="...", context=["..."], answer="...")

Adapters (all optional, duck-typed protocols):
  llm        — generate / generate_json / embed
  retrieval  — search(question, top_k) -> list of (id, text)
  extractor  — extract(answer_text) -> list[str]
  verifier   — verify_claims(claims, contexts, mode) -> VerificationResult
  metrics    — dict[str, callable(record) -> float|None]
"""

import json
from pathlib import Path
from typing import Any, Protocol

from .config import settings
from .generator import Answer, extract_citations, citation_attempts
from .llm import GeminiClient
from .verify.engine import VerificationEngine
from .verify.schemas import VerificationResult


class LLMAdapter(Protocol):
    def generate(self, prompt: str, system: str | None = None,
                 json_mode: bool = False, temperature: float = 0.0) -> str: ...
    def generate_json(self, prompt: str, system: str | None = None,
                      temperature: float = 0.0) -> Any: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class RetrievalAdapter(Protocol):
    def search(self, question: str, top_k: int = 4) -> list[tuple[str, str]]: ...


class ClaimExtractor(Protocol):
    def extract(self, answer_text: str) -> list[str]: ...


class VerificationStrategy(Protocol):
    def verify_claims(self, claims: list[str], contexts: list[tuple[str, str]],
                      mode: str = "semantic") -> VerificationResult: ...
    def verify_answer(self, answer_text: str, contexts: list[tuple[str, str]],
                      refused: bool = False, mode: str = "semantic") -> VerificationResult: ...


def _load_config(config) -> dict:
    if config is None:
        return {}
    if isinstance(config, dict):
        return dict(config)
    path = Path(config)
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise RuntimeError(
                "YAML config requires pyyaml (pip install pyyaml); "
                "JSON config and dict config work without it."
            ) from e
        return yaml.safe_load(text) or {}
    return json.loads(text)


class RAGEvaluator:
    def __init__(self, config=None, llm: LLMAdapter | None = None,
                 retrieval: RetrievalAdapter | None = None,
                 extractor: ClaimExtractor | None = None,
                 verifier: VerificationStrategy | None = None,
                 metrics: dict | None = None):
        self.config = _load_config(config)
        self.llm = llm or GeminiClient(model=self.config.get("llm_model"))
        self.retrieval = retrieval
        self.extractor = extractor
        self.verifier = verifier or VerificationEngine(self.llm)
        self.metrics = metrics or {}

    def evaluate(self, question: str, context: list, answer: str | None = None,
                 refused: bool = False, mode: str = "semantic") -> dict:
        contexts = [(c[0], c[1]) if isinstance(c, (tuple, list)) else (f"p{i}", c)
                    for i, c in enumerate(context)]
        if answer is None:
            if self.retrieval is not None:
                contexts = self.retrieval.search(question, top_k=4)
            from .generator import generate_answer
            from .retrieval import RetrievedChunk
            from .ingest import Chunk
            chunks = [RetrievedChunk(Chunk(id=cid, doc="external", text=text, ordinal=i),
                                     score=1.0, rank=i + 1)
                      for i, (cid, text) in enumerate(contexts)]
            ans = generate_answer(question, chunks, self.llm)
            answer, refused = ans.text, ans.refused
            cited, invalid = ans.cited_ids, ans.invalid_citations
        else:
            valid = {cid for cid, _ in contexts}
            cited = extract_citations(answer, valid)
            invalid = [t for t in citation_attempts(answer) if t not in valid]

        if self.extractor is not None and not refused:
            claims = self.extractor.extract(answer)
            result = self.verifier.verify_claims(claims, contexts, mode=mode)
        else:
            result = self.verifier.verify_answer(answer, contexts, refused=refused,
                                                 mode=mode)
        record = {
            "question": question, "answer": answer, "refused": refused,
            "cited_ids": cited, "invalid_citations": invalid,
            "faithfulness": result.faithfulness,
            "hallucination_rate": result.hallucination_rate,
            "answer_state": result.answer_state.value,
        }
        for name, fn in self.metrics.items():
            record[name] = fn(record)
        return {"verification": result.model_dump(), "metrics": record}

    def evaluate_dataset(self, cases, mode: str = "deterministic") -> dict:
        from .adversarial.benchmark import AdversarialBenchmark
        bench = AdversarialBenchmark(client=self.llm if mode == "semantic" else None,
                                     mode=mode)
        return bench.run(cases)