"""Adversarial dataset, benchmark and metrics tests (deterministic + mocked)."""

from collections import Counter

from ragpipe.adversarial import (
    AdversarialBenchmark,
    load_adversarial,
    summarize_adversarial,
)
from ragpipe.adversarial.dataset import CATEGORIES
from ragpipe.adversarial.metrics import binary_prf, confusion_matrix


def test_dataset_size_and_category_coverage():
    cases = load_adversarial()
    assert len(cases) >= 100
    counts = Counter(c.category for c in cases)
    for cat in CATEGORIES:
        assert counts[cat] >= 10, cat


def test_dataset_provenance_and_labels():
    cases = load_adversarial()
    assert all(c.provenance == "synthetic-author-reviewed" for c in cases)
    assert all(c.expected_status in
               ("SUPPORTED", "CONTRADICTED", "NOT_SUPPORTED", "UNCERTAIN") for c in cases)
    assert all(c.expected_reason for c in cases)


def test_dataset_has_positives_paraphrases_and_hard_cases():
    cases = load_adversarial()
    assert sum(1 for c in cases if c.expected_status == "SUPPORTED") >= 20
    assert sum(1 for c in cases if c.difficulty == "hard") >= 20
    assert any("paraphrase" in c.expected_reason for c in cases)


def test_deterministic_benchmark_never_false_accepts():
    """Regression: fail-closed property of the deterministic check battery."""
    report = AdversarialBenchmark(mode="deterministic").run(load_adversarial())
    s = report["summary"]
    assert s["false_acceptance_rate"] == 0.0
    assert s["evaluation_error_rate"] == 0.0
    assert s["injection_flagged"] == s["injection_cases"]


def test_deterministic_benchmark_detects_negation_and_numbers():
    cases = [c for c in load_adversarial()
             if c.id in ("NEG-001", "NEG-002", "NUM-001", "NUM-006")]
    report = AdversarialBenchmark(mode="deterministic").run(cases)
    assert all(r["predicted"] == "CONTRADICTED" for r in report["records"])


def test_mocked_semantic_benchmark_labeled_mocked():
    class MockJudge:
        def generate_json(self, prompt, system=None, temperature=0.0):
            return {"claims": [{"claim_id": "c1", "original_claim": "x",
                                "status": "CONTRADICTED", "confidence": 0.9,
                                "explanation": "mocked"}]}

    cases = load_adversarial()[:2]
    bench = AdversarialBenchmark(client=MockJudge(), mode="semantic",
                                 judge_label="mocked")
    report = bench.run(cases)
    assert report["judge"] == "mocked"
    assert all(r["predicted"] == "CONTRADICTED" for r in report["records"])


def test_confusion_matrix_counts_and_exclusions():
    records = [
        {"expected": "CONTRADICTED", "predicted": "CONTRADICTED"},
        {"expected": "CONTRADICTED", "predicted": "SUPPORTED"},
        {"expected": "SUPPORTED", "predicted": "SUPPORTED"},
        {"expected": "SUPPORTED", "predicted": "EVALUATION_ERROR"},
    ]
    cm = confusion_matrix(records)
    assert cm["matrix"]["CONTRADICTED"]["CONTRADICTED"] == 1
    assert cm["matrix"]["CONTRADICTED"]["SUPPORTED"] == 1
    assert cm["excluded_error_states"] == 1


def test_binary_prf_math():
    records = [
        {"expected": "CONTRADICTED", "predicted": "CONTRADICTED"},
        {"expected": "CONTRADICTED", "predicted": "CONTRADICTED"},
        {"expected": "CONTRADICTED", "predicted": "NOT_SUPPORTED"},
        {"expected": "SUPPORTED", "predicted": "CONTRADICTED"},
    ]
    prf = binary_prf(records, "CONTRADICTED")
    assert (prf["tp"], prf["fp"], prf["fn"]) == (2, 1, 1)
    assert prf["precision"] == round(2 / 3, 4)
    assert prf["recall"] == round(2 / 3, 4)


def test_summarize_separates_populations():
    records = [
        {"category": "negation_flip", "expected": "CONTRADICTED",
         "predicted": "CONTRADICTED", "disagreement": False},
        {"category": "negation_flip", "expected": "CONTRADICTED",
         "predicted": "SUPPORTED", "disagreement": False},
        {"category": "negation_flip", "expected": "SUPPORTED",
         "predicted": "CONTRADICTED", "disagreement": False},
        {"category": "negation_flip", "expected": "SUPPORTED",
         "predicted": "EVALUATION_ERROR", "disagreement": False},
    ]
    s = summarize_adversarial(records)
    assert s["n_cases"] == 4
    assert s["evaluation_error_rate"] == 0.25
    assert s["adversarial_detection_rate"] == 0.5
    assert s["false_acceptance_rate"] == 0.5
    assert s["false_rejection_rate"] == 1.0
    assert s["per_category"]["negation_flip"]["n"] == 3