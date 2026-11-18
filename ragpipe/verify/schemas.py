"""Structured schemas for claim-level verification (V2).

Confidence values are ordinal judge outputs, NOT calibrated probabilities.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


def _as_str_list(value):
    """Normalize judge output quirks at the boundary: dict/str/None → list[str].
    Unknown shapes still raise (fail-closed)."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        return [f"{k}: {v}" for k, v in value.items()]
    if isinstance(value, str):
        return [value] if value.strip() else []
    raise ValueError(f"cannot normalize to list[str]: {type(value)}")


def _as_int_or_none(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return value[0] if value and isinstance(value[0], int) else None
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    raise ValueError(f"cannot normalize to int|None: {type(value)}")


def _none_to_empty(value):
    return "" if value is None else value


def _none_to_zero(value):
    return 0.0 if value is None else value


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


class Attribution(BaseModel):
    relation: str = ""
    holder: str = ""
    target: str = ""


class ClaimAnalysis(BaseModel):
    claim_id: str
    original_claim: str
    normalized_claim: str = ""
    subject: str = ""
    predicate: str = ""
    object: str = ""
    agent: str = ""
    patient: str = ""
    negation: bool = False
    negation_cues: list[str] = Field(default_factory=list)
    modality: str = "assertive"
    tense: str = "unknown"
    aspect: str = "unknown"
    voice: str = "active"
    entities: list[str] = Field(default_factory=list)
    coreference: list[str] = Field(default_factory=list)
    attributions: list[Attribution] = Field(default_factory=list)
    numerical_values: list[NumericalValue] = Field(default_factory=list)
    temporal_references: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)

    _norm_coref = field_validator("coreference", mode="before")(_as_str_list)
    _norm_entities = field_validator("entities", mode="before")(_as_str_list)
    _norm_temporal_refs = field_validator("temporal_references", mode="before")(_as_str_list)
    _norm_strs = field_validator(
        "normalized_claim", "subject", "predicate", "object", "agent", "patient",
        "tense", "aspect", "voice", "modality", mode="before")(_none_to_empty)


class EventTuple(BaseModel):
    """Semantic event extracted from evidence, roles normalized (agent = doer
    regardless of surface voice)."""
    event_id: str = ""
    agent: str = ""
    predicate: str = ""
    patient: str = ""
    negation: bool = False
    tense: str = "unknown"
    aspect: str = "unknown"
    modality: str = "assertive"
    state: str = "unknown"
    entities: list[str] = Field(default_factory=list)
    attributions: list[Attribution] = Field(default_factory=list)
    temporal_order: int | None = None
    temporal_cues: list[str] = Field(default_factory=list)

    _norm_order = field_validator("temporal_order", mode="before")(_as_int_or_none)
    _norm_entities = field_validator("entities", mode="before")(_as_str_list)
    _norm_cues = field_validator("temporal_cues", mode="before")(_as_str_list)
    _norm_strs = field_validator(
        "agent", "predicate", "patient", "tense", "aspect", "modality", "state",
        mode="before")(_none_to_empty)


class ClaimVerdict(BaseModel):
    claim_id: str
    status: VerdictStatus
    confidence: float = 0.0
    explanation: str = ""
    deterministic_flags: list[str] = Field(default_factory=list)
    semantic_status: VerdictStatus | None = None
    secondary_status: VerdictStatus | None = None
    disagreement: bool = False
    three_way_disagreement: bool = False
    citation_ids: list[str] = Field(default_factory=list)
    execution_mode: str = "deterministic"


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

    _norm_conf = field_validator("confidence", mode="before")(_none_to_zero)
    _norm_expl = field_validator("explanation", mode="before")(_none_to_empty)


class CombinedModel(BaseModel):
    claims: list[CombinedClaim]
    evidence_events: list[EventTuple] = Field(default_factory=list)


class VerificationResult(BaseModel):
    answer_state: AnswerState
    claims: list[ClaimAnalysis] = Field(default_factory=list)
    verdicts: list[ClaimVerdict] = Field(default_factory=list)
    evidence_events: list[EventTuple] = Field(default_factory=list)
    faithfulness: float | None = None
    hallucination_rate: float | None = None
    errors: list[str] = Field(default_factory=list)

    @property
    def resolved_verdicts(self) -> list[ClaimVerdict]:
        return [v for v in self.verdicts if v.status in RESOLVED_STATUSES]