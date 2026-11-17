"""Adversarial golden dataset loading and validation."""

import json
from pathlib import Path

from pydantic import BaseModel, Field

from ..config import settings

CATEGORIES = [
    "negation_flip",
    "role_reversal",
    "entity_attribution",
    "numerical",
    "temporal",
    "modality",
    "multi_hop",
    "context_injection",
]

ADVERSARIAL_PATH = settings.golden_path.parent / "adversarial_golden_dataset.json"


class AdversarialCase(BaseModel):
    id: str
    category: str
    difficulty: str = "medium"
    context: list[str]
    generated_answer: str = ""
    claims: list[str]
    expected_status: str
    expected_reason: str = ""
    expected_statuses: list[str] = Field(default_factory=list)
    probe_question: str = ""
    provenance: str = "synthetic-author-reviewed"

    def expected_for(self, index: int) -> str:
        if self.expected_statuses:
            return self.expected_statuses[index]
        return self.expected_status


def load_adversarial(path: Path | None = None) -> list[AdversarialCase]:
    path = path or ADVERSARIAL_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["cases"] if isinstance(data, dict) else data
    cases = [AdversarialCase.model_validate(item) for item in items]
    for case in cases:
        if case.category not in CATEGORIES:
            raise ValueError(f"{case.id}: unknown category {case.category!r}")
        if not case.claims:
            raise ValueError(f"{case.id}: no claims")
        if not case.context:
            raise ValueError(f"{case.id}: empty context")
    return cases