"""Structured schemas for claim-level verification (V2).

Confidence values are ordinal judge outputs, NOT calibrated probabilities.
"""

from enum import Enum

from pydantic import BaseModel, Field


class VerdictStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    UNCERTAIN = "UNCERTAIN"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EVALUATION_ERROR = "EVALUATION_ERROR"


class AnswerState(str, Enum):
    OK = "OK"
    REFUSED = "REFUSED"
    NO_CLAIMS = "NO_CLAIMS"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EVALUATION_ERROR = "EVALUATION_ERROR"


RESOLVED_STATUSES = {
    VerdictStatus.SUPPORTED,
    VerdictStatus.CONTRADICTED,
    VerdictStatus.NOT_SUPPORTED,
}


class NumericalValue(BaseModel):
    raw: str
    value: float
    unit: str | None = None
    dimension: str | None = None


class ClaimAnalysis(BaseModel):
    claim_id: str
    original_claim: str
    normalized_claim: str = ""
    subject: str = ""
    predicate: str = ""
    object: str = ""
    negation: bool = False
    negation_cues: list[str] = Field(default_factory=list)
    modality: str = "assertive"
    entities: list[str] = Field(default_factory=list)
    numerical_values: list[NumericalValue] = Field(default_factory=list)
    temporal_references: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


class ClaimVerdict(BaseModel):
    claim_id: str
    status: VerdictStatus
    confidence: float = 0.0
    explanation: str = ""
    deterministic_flags: list[str] = Field(default_factory=list)
    semantic_status: VerdictStatus | None = None
    disagreement: bool = False
    citation_ids: list[str] = Field(default_factory=list)


class ExtractionModel(BaseModel):
    claims: list[str]


class AnalysisModel(BaseModel):
    claims: list[ClaimAnalysis]


class EntailmentItem(BaseModel):
    claim_id: str
    status: VerdictStatus
    confidence: float = 0.0
    explanation: str = ""


class EntailmentModel(BaseModel):
    verdicts: list[EntailmentItem]


class CombinedClaim(ClaimAnalysis):
    status: VerdictStatus
    confidence: float = 0.0
    explanation: str = ""


class CombinedModel(BaseModel):
    claims: list[CombinedClaim]


class VerificationResult(BaseModel):
    answer_state: AnswerState
    claims: list[ClaimAnalysis] = Field(default_factory=list)
    verdicts: list[ClaimVerdict] = Field(default_factory=list)
    faithfulness: float | None = None
    hallucination_rate: float | None = None
    errors: list[str] = Field(default_factory=list)

    @property
    def resolved_verdicts(self) -> list[ClaimVerdict]:
        return [v for v in self.verdicts if v.status in RESOLVED_STATUSES]