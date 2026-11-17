"""Verification engine tests with mocked LLM (labeled mocked, no API calls)."""

import pytest
from pydantic import ValidationError

from ragpipe.llm import EmptyResponseError
from ragpipe.verify.engine import VerificationEngine
from ragpipe.verify.schemas import AnswerState, VerdictStatus


class ScriptedClient:
    """Mock judge: scripted responses keyed by prompt marker."""

    def __init__(self, extract=None, verify=None, fail_verify=False):
        self.extract = extract
        self.verify = verify
        self.fail_verify = fail_verify
        self.calls = []

    def generate_json(self, prompt, system=None, temperature=0.0):
        self.calls.append(system)
        if "atomic factual claims" in system:
            if self.extract is None:
                raise ValueError("no extraction script")
            return self.extract
        if self.fail_verify:
            raise EmptyResponseError("blocked")
        if self.verify is None:
            raise ValueError("no verify script")
        return self.verify


def combined(claim_id, status, **kw):
    base = {"claim_id": claim_id, "original_claim": kw.get("claim", ""),
            "normalized_claim": kw.get("claim", ""), "subject": kw.get("subject", ""),
            "predicate": kw.get("predicate", ""), "object": kw.get("object", ""),
            "negation": False, "modality": "assertive", "entities": [],
            "status": status, "confidence": 0.9, "explanation": "mocked"}
    base.update(kw)
    return base


CTX = [("p1", "Company A did not acquire Company B.")]


def test_deterministic_negation_contradicted():
    engine = VerificationEngine()
    result = engine.verify_claims(["Company A acquired Company B."], CTX,
                                  mode="deterministic")
    assert result.verdicts[0].status == VerdictStatus.CONTRADICTED
    assert result.faithfulness == 0.0


def test_deterministic_role_uncertain_without_spo():
    engine = VerificationEngine()
    result = engine.verify_claims(["Bob approved Alice's request."],
                                  [("p1", "Alice approved Bob's request.")],
                                  mode="deterministic")
    assert result.verdicts[0].status == VerdictStatus.UNCERTAIN
    assert result.faithfulness is None


def test_deterministic_mode_rejects_verify_answer():
    with pytest.raises(ValueError):
        VerificationEngine().verify_answer("some answer", CTX, mode="deterministic")


def test_semantic_mocked_supported():
    client = ScriptedClient(verify={"claims": [combined("c1", "SUPPORTED")]})
    result = VerificationEngine(client).verify_claims(
        ["Company A did not acquire Company B."], CTX, mode="semantic")
    assert result.verdicts[0].status == VerdictStatus.SUPPORTED
    assert result.faithfulness == 1.0
    assert result.answer_state == AnswerState.OK


def test_numerical_disagreement_overrides_to_contradicted():
    client = ScriptedClient(verify={"claims": [combined("c1", "SUPPORTED")]})
    result = VerificationEngine(client).verify_claims(
        ["The model achieved 82% accuracy."],
        [("p1", "The model achieved 92% accuracy.")], mode="semantic")
    v = result.verdicts[0]
    assert v.status == VerdictStatus.CONTRADICTED
    assert v.disagreement is True
    assert v.semantic_status == VerdictStatus.SUPPORTED


def test_non_numerical_disagreement_becomes_uncertain():
    client = ScriptedClient(verify={"claims": [combined("c1", "SUPPORTED")]})
    result = VerificationEngine(client).verify_claims(
        ["Company A acquired Company B."], CTX, mode="semantic")
    v = result.verdicts[0]
    assert v.status == VerdictStatus.UNCERTAIN
    assert v.disagreement is True


def test_missing_semantic_verdict_is_uncertain():
    client = ScriptedClient(verify={"claims": []})
    result = VerificationEngine(client).verify_claims(["Anything at all."], CTX,
                                                      mode="semantic")
    assert result.verdicts[0].status == VerdictStatus.UNCERTAIN
    assert result.faithfulness is None


def test_api_failure_is_evaluation_error_not_score():
    client = ScriptedClient(fail_verify=True)
    result = VerificationEngine(client).verify_claims(["Anything."], CTX, mode="semantic")
    assert result.answer_state == AnswerState.EVALUATION_ERROR
    assert result.verdicts[0].status == VerdictStatus.EVALUATION_ERROR
    assert result.faithfulness is None
    assert result.errors


def test_invalid_status_schema_is_evaluation_error():
    client = ScriptedClient(verify={"claims": [combined("c1", "MAYBE")]})
    result = VerificationEngine(client).verify_claims(["Anything."], CTX, mode="semantic")
    assert result.answer_state == AnswerState.EVALUATION_ERROR
    assert result.faithfulness is None


def test_refusal_short_circuits_without_llm():
    client = ScriptedClient()
    result = VerificationEngine(client).verify_answer(
        "I cannot answer this from the provided documents.", CTX, refused=True)
    assert result.answer_state == AnswerState.REFUSED
    assert client.calls == []


def test_empty_answer_is_no_claims():
    result = VerificationEngine(ScriptedClient()).verify_answer("   ", CTX)
    assert result.answer_state == AnswerState.NO_CLAIMS
    assert result.faithfulness is None


def test_extraction_failure_after_retry_is_explicit():
    client = ScriptedClient(extract={"wrong": "shape"})
    result = VerificationEngine(client).verify_answer("Some factual answer.", CTX)
    assert result.answer_state == AnswerState.EXTRACTION_FAILED
    assert result.faithfulness is None
    assert len(client.calls) == 2  # one retry attempted


def test_extraction_empty_claims_is_no_claims_not_success():
    client = ScriptedClient(extract={"claims": []})
    result = VerificationEngine(client).verify_answer("Opinion only, no facts.", CTX)
    assert result.answer_state == AnswerState.NO_CLAIMS
    assert result.faithfulness is None


def test_score_excludes_uncertain():
    client = ScriptedClient(verify={"claims": [
        combined("c1", "SUPPORTED"), combined("c2", "UNCERTAIN")]})
    result = VerificationEngine(client).verify_claims(
        ["Fact one.", "Fact two."], CTX, mode="semantic")
    assert result.faithfulness == 1.0
    assert len(result.resolved_verdicts) == 1


def test_schema_rejects_unknown_status():
    from ragpipe.verify.schemas import ClaimVerdict
    with pytest.raises(ValidationError):
        ClaimVerdict(claim_id="c1", status="SUPPORTEDISH")