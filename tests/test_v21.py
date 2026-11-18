"""V2.1 tests: statistical hygiene, semantic tuples, red-team, public API, manifest."""

import json

import pytest

from ragpipe import evalstats
from ragpipe.api import RAGEvaluator
from ragpipe.manifest import build_manifest
from ragpipe.redteam import run_redteam
from ragpipe.verify import checks
from ragpipe.verify.engine import VerificationEngine
from ragpipe.verify.schemas import Attribution, ClaimAnalysis, EventTuple


def test_wilson_bounds_and_zero_denominator():
    lo, hi = evalstats.wilson(0, 72)
    assert lo == 0.0 and 0.0 < hi < 0.1
    assert evalstats.wilson(0, 0) is None
    lo, hi = evalstats.wilson(72, 72)
    assert hi == 1.0 and lo > 0.9


def test_binary_counts_include_tn():
    records = [
        {"expected": "CONTRADICTED", "predicted": "CONTRADICTED"},
        {"expected": "SUPPORTED", "predicted": "SUPPORTED"},
        {"expected": "SUPPORTED", "predicted": "CONTRADICTED"},
        {"expected": "CONTRADICTED", "predicted": "SUPPORTED"},
    ]
    c = evalstats.binary_counts(records, "CONTRADICTED")
    assert (c["tp"], c["fp"], fn := c["fn"], c["tn"]) == (1, 1, 1, 1)


def test_macro_micro_and_abstentions():
    records = [
        {"category": "a", "expected": "CONTRADICTED", "predicted": "CONTRADICTED"},
        {"category": "a", "expected": "SUPPORTED", "predicted": "UNCERTAIN"},
        {"category": "b", "expected": "CONTRADICTED", "predicted": "EVALUATION_ERROR"},
    ]
    mm = evalstats.macro_micro({"a": records[:2], "b": records[2:]}, "CONTRADICTED")
    assert mm["micro"]["tp"] == 1
    ab = evalstats.abstentions(records)
    assert ab["uncertain"] == 1 and ab["errors"] == 1
    assert ab["accuracy_resolved_only"] == 1.0
    assert ab["accuracy_all"] == pytest.approx(1 / 3, abs=1e-3)


def test_numerical_support_requires_same_quantity():
    assert checks.numerical_support(
        "The default build timeout is 900 seconds.",
        "The default build timeout is 15 minutes.")
    assert not checks.numerical_support(
        "The maximum image size is 10 MB.",
        "Maximum request body size at the Gateway: 10 MB.")


def test_negation_parity_double_negation():
    # NOT(acquire) == did not acquire: parity matches the negated context
    assert checks.negation_flip_flags(
        "It is not true that Company A acquired Company B.",
        "Company A did not acquire Company B.") == []


def test_negation_scope_ambiguous_returns_uncertain():
    engine = VerificationEngine()
    result = engine.verify_claims(
        ["Company A did not merely talk about acquiring Company B."],
        [("p0", "Company A did not acquire Company B.")], mode="deterministic")
    assert result.verdicts[0].status.value == "UNCERTAIN"


def _claim(agent, patient, predicate="acquire", negation=False, attributions=None):
    return ClaimAnalysis(claim_id="c1", original_claim=f"{agent} {predicate} {patient}",
                         agent=agent, patient=patient, predicate=predicate,
                         negation=negation, entities=[agent, patient],
                         attributions=attributions or [])


def test_role_consistency_detects_swap():
    claim = _claim("Company B", "Company A")
    events = [EventTuple(event_id="e1", agent="Company A", predicate="acquire",
                         patient="Company B", entities=["Company A", "Company B"])]
    assert checks.role_consistency(claim, events)


def test_role_consistency_accepts_paraphrase_order():
    claim = _claim("Company A", "Company B")
    events = [EventTuple(event_id="e1", agent="Company A", predicate="acquired",
                         patient="Company B", entities=["Company A", "Company B"])]
    assert checks.role_consistency(claim, events) == []


def test_attribution_consistency():
    claim = _claim("Company B", "the model", predicate="develop",
                   attributions=[Attribution(relation="developed", holder="Company B",
                                             target="the model")])
    events = [EventTuple(event_id="e1", agent="Company A", predicate="develop",
                         patient="the model",
                         attributions=[Attribution(relation="developed",
                                                   holder="Company A", target="the model")])]
    assert checks.attribution_consistency(claim, events)


def test_temporal_state_reversal():
    claim = ClaimAnalysis(claim_id="c1", original_claim="ARM nodes are available in all regions.")
    events = [EventTuple(event_id="e1", agent="platform", predicate="available",
                         patient="ARM nodes", state="planned")]
    flags = checks.temporal_consistency(claim, events)
    assert any("planned" in f for f in flags)


def test_redteam_deterministic_all_pairs_pass():
    report = run_redteam(VerificationEngine(), mode="deterministic")
    assert report["n_pairs"] >= 20
    assert report["passed"] == report["n_pairs"]


def test_redteam_metamorphic_relations():
    report = run_redteam(VerificationEngine(), mode="deterministic")
    for rec in report["records"]:
        if rec["relation"] == "equivalent":
            assert rec["mutated_status"] == rec["base_status"]
        else:
            assert rec["mutated_status"] != "SUPPORTED"


class ScriptedJudge:
    def generate_json(self, prompt, system=None, temperature=0.0):
        if "atomic factual claims" in system:
            return {"claims": ["The timeout is 15 minutes."]}
        return {"claims": [{"claim_id": "c1", "original_claim": "The timeout is 15 minutes.",
                            "status": "SUPPORTED", "confidence": 0.9,
                            "explanation": "scripted"}], "evidence_events": []}

    def generate(self, prompt, system=None, json_mode=False, temperature=0.0):
        return "The timeout is 15 minutes [id:p0] [id:deadbeefdead]."

    def embed(self, texts):
        return [[0.0] * 8 for _ in texts]


def test_public_api_offline_with_invalid_citation_tracking():
    evaluator = RAGEvaluator(llm=ScriptedJudge())
    result = evaluator.evaluate(
        question="What is the timeout?",
        context=[("p0", "The timeout is 15 minutes.")])
    assert result["metrics"]["faithfulness"] == 1.0
    assert result["metrics"]["invalid_citations"] == ["deadbeefdead"]
    assert result["verification"]["verdicts"][0]["status"] == "SUPPORTED"


def test_public_api_custom_metric_and_extractor():
    evaluator = RAGEvaluator(
        llm=ScriptedJudge(),
        extractor=type("E", (), {"extract": lambda self, text: ["The timeout is 15 minutes."]})(),
        metrics={"answer_len": lambda r: len(r["answer"])})
    result = evaluator.evaluate(question="q", context=["The timeout is 15 minutes."],
                                answer="The timeout is 15 minutes.")
    assert result["metrics"]["answer_len"] == len("The timeout is 15 minutes.")


def test_manifest_has_provenance_and_no_secrets():
    from ragpipe.adversarial.dataset import ADVERSARIAL_PATH
    m = build_manifest({"adversarial": ADVERSARIAL_PATH}, api_status="offline-deterministic")
    blob = json.dumps(m)
    assert m["git_commit"] and m["prompt_hash"] and m["dataset_hashes"]["adversarial"]
    assert m["python_version"] and m["dependency_versions"]["pydantic"]
    assert "api_key" not in blob and "GEMINI_API_KEY" not in blob
    assert m["random_seed"] is None


def test_numerical_support_rejects_extra_unsupported_content():
    ctx = "Untagged images are deleted after 30 days."
    assert not checks.numerical_support(
        "Images are untagged because they are deleted after 30 days.", ctx)
    assert not checks.numerical_support(
        "Untagged images are deleted after 30 days from 2026-01-01.", ctx)
    assert not checks.numerical_support(
        "Untagged images will definitely be deleted after 30 days in every region.", ctx)
    assert checks.numerical_support("Untagged images are deleted after 30 days.", ctx)


def test_schema_normalizes_judge_output_quirks():
    from ragpipe.verify.schemas import ClaimAnalysis, EventTuple
    a = ClaimAnalysis.model_validate({
        "claim_id": "c1", "original_claim": "x", "coreference": {"it": "the cache"},
        "entities": {"A": "Company A"}, "temporal_references": None})
    assert a.coreference == ["it: the cache"]
    assert a.entities == ["A: Company A"]
    e = EventTuple.model_validate({"event_id": "e1", "temporal_order": [],
                                   "temporal_cues": "before"})
    assert e.temporal_order is None
    assert e.temporal_cues == ["before"]
    with pytest.raises(ValueError):
        ClaimAnalysis.model_validate({"claim_id": "c1", "original_claim": "x",
                                      "coreference": 42})


def test_scope_ambiguity_forces_uncertain_in_semantic_mode():
    class YesJudge:
        def generate_json(self, prompt, system=None, temperature=0.0):
            return {"claims": [{"claim_id": "c1", "original_claim": "x",
                                "status": "SUPPORTED", "confidence": 0.9,
                                "explanation": "judge says yes"}],
                    "evidence_events": []}

    engine = VerificationEngine(YesJudge())
    result = engine.verify_claims(
        ["The gateway does not retry only on 5xx responses."],
        [("p0", "The gateway retries up to 2 times on 5xx responses.")],
        mode="semantic")
    assert result.verdicts[0].status.value == "UNCERTAIN"


def test_dummy_pronouns_not_entities():
    assert checks.clean_entities(["It", "The Scheduler", "There"]) == ["The Scheduler"]


def test_transitive_chain_support_and_reversal():
    events = [EventTuple(event_id="e1", agent="Service A", predicate="depends on",
                         patient="Service B"),
              EventTuple(event_id="e2", agent="Service B", predicate="depends on",
                         patient="Service C")]
    fwd = ClaimAnalysis(claim_id="c1", original_claim="Service A depends on service C.",
                        agent="Service A", patient="Service C", predicate="depends on")
    rev = ClaimAnalysis(claim_id="c2", original_claim="Service C depends on service A.",
                        agent="Service C", patient="Service A", predicate="depends on")
    assert any(f.startswith("multihop-support:")
               for f in checks.transitive_chain_flags(fwd, events))
    assert any(f.startswith("multihop:")
               for f in checks.transitive_chain_flags(rev, events))


def test_attribution_non_functional_relation_is_silence():
    claim = ClaimAnalysis(
        claim_id="c1", original_claim="TLS 1.3 is enforced at the scheduler.",
        attributions=[Attribution(relation="enforced at", holder="scheduler",
                                  target="gateway")])
    events = [EventTuple(event_id="e1", attributions=[
        Attribution(relation="enforced at", holder="gateway", target="gateway")])]
    assert checks.attribution_consistency(claim, events) == []


def test_provenance_gate_rejects_independent_without_reviewer(tmp_path):
    from ragpipe.adversarial.dataset import load_adversarial
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"cases": [{
        "id": "X-01", "category": "negation_flip", "context": ["c"],
        "claims": ["c"], "expected_status": "SUPPORTED",
        "provenance": "independent-human-reviewed"}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_adversarial(p)


def test_execution_mode_labels():
    det = VerificationEngine().verify_claims(
        ["Company A acquired Company B."],
        [("p0", "Company A did not acquire Company B.")], mode="deterministic")
    assert det.verdicts[0].execution_mode == "deterministic"

    class YesJudge:
        def generate_json(self, prompt, system=None, temperature=0.0):
            return {"claims": [{"claim_id": "c1", "original_claim": "x",
                                "status": "SUPPORTED", "confidence": 0.9,
                                "explanation": "mock"}], "evidence_events": []}

    mocked = VerificationEngine(YesJudge()).verify_claims(
        ["anything"], [("p0", "evidence")], mode="semantic")
    assert mocked.verdicts[0].execution_mode == "mocked"


def test_splits_family_disjoint():
    from ragpipe.adversarial.dataset import DEVELOPMENT_PATH, HELDOUT_PATH, load_adversarial
    dev = load_adversarial(DEVELOPMENT_PATH)
    held = load_adversarial(HELDOUT_PATH)
    assert {c.scenario_family for c in dev}.isdisjoint({c.scenario_family for c in held})
    assert len(dev) + len(held) >= 200