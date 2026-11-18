"""Minimal external usage example — runs fully offline with a scripted judge.

    python examples/external_usage.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragpipe import RAGEvaluator


class ScriptedJudge:
    """Stands in for the Gemini judge so the example needs no API key."""

    def generate_json(self, prompt, system=None, temperature=0.0):
        if "atomic factual claims" in system:
            return {"claims": ["The default build timeout is 15 minutes."]}
        return {"claims": [{"claim_id": "c1",
                            "original_claim": "The default build timeout is 15 minutes.",
                            "status": "SUPPORTED", "confidence": 0.9,
                            "explanation": "scripted for offline example"}],
                "evidence_events": []}

    def generate(self, prompt, system=None, json_mode=False, temperature=0.0):
        return "The default build timeout is 15 minutes [id:p0]."

    def embed(self, texts):
        return [[0.0] * 8 for _ in texts]


evaluator = RAGEvaluator(llm=ScriptedJudge())
result = evaluator.evaluate(
    question="What is the default build timeout?",
    context=[("p0", "The default build timeout is 15 minutes.")],
)
print("answer state:", result["metrics"]["answer_state"])
print("faithfulness:", result["metrics"]["faithfulness"])
print("verdicts:", [(v["claim_id"], v["status"])
                   for v in result["verification"]["verdicts"]])