"""V2 adversarial metrics: confusion matrices and standard detection rates.

Incompatible populations are never merged into a single composite score.
Small-sample counts are always reported alongside rates.
"""

from collections import Counter

from ..verify.schemas import VerdictStatus

MATRIX_STATUSES = ["SUPPORTED", "CONTRADICTED", "NOT_SUPPORTED", "UNCERTAIN"]
ADVERSARIAL_EXPECTED = {"CONTRADICTED", "NOT_SUPPORTED"}


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def confusion_matrix(records: list[dict]) -> dict:
    matrix = {e: {p: 0 for p in MATRIX_STATUSES} for e in MATRIX_STATUSES}
    excluded = 0
    for r in records:
        e, p = r["expected"], r["predicted"]
        if e in matrix and p in matrix[e]:
            matrix[e][p] += 1
        else:
            excluded += 1
    return {"matrix": matrix, "excluded_error_states": excluded}


def binary_prf(records: list[dict], positive: str) -> dict:
    tp = sum(1 for r in records if r["expected"] == positive and r["predicted"] == positive)
    fp = sum(1 for r in records if r["expected"] != positive and r["predicted"] == positive)
    fn = sum(1 for r in records if r["expected"] == positive and r["predicted"] != positive)
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    f1 = (round(2 * precision * recall / (precision + recall), 4)
          if precision and recall else None)
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1}


def summarize_adversarial(records: list[dict]) -> dict:
    total = len(records)
    errors = [r for r in records if r["predicted"] in
              ("EVALUATION_ERROR", "EXTRACTION_FAILED")]
    resolved = [r for r in records if r not in errors]
    adversarial = [r for r in resolved if r["expected"] in ADVERSARIAL_EXPECTED]
    positives = [r for r in resolved if r["expected"] == "SUPPORTED"]

    detected = sum(1 for r in adversarial if r["predicted"] in ADVERSARIAL_EXPECTED)
    accepted = sum(1 for r in adversarial if r["predicted"] == "SUPPORTED")
    rejected = sum(1 for r in positives if r["predicted"] in ADVERSARIAL_EXPECTED)
    exact = sum(1 for r in resolved if r["expected"] == r["predicted"])
    uncertain = sum(1 for r in resolved if r["predicted"] == "UNCERTAIN")
    disagreements = sum(1 for r in resolved if r.get("disagreement"))

    per_category = {}
    for cat in sorted({r["category"] for r in records}):
        cat_records = [r for r in resolved if r["category"] == cat]
        cat_exact = sum(1 for r in cat_records if r["expected"] == r["predicted"])
        per_category[cat] = {
            "n": len(cat_records),
            "exact_match_accuracy": _rate(cat_exact, len(cat_records)),
            "uncertain": sum(1 for r in cat_records if r["predicted"] == "UNCERTAIN"),
        }

    return {
        "n_cases": total,
        "n_resolved": len(resolved),
        "evaluation_error_rate": _rate(len(errors), total),
        "adversarial_detection_rate": _rate(detected, len(adversarial)),
        "false_acceptance_rate": _rate(accepted, len(adversarial)),
        "false_rejection_rate": _rate(rejected, len(positives)),
        "exact_status_accuracy": _rate(exact, len(resolved)),
        "uncertain_rate": _rate(uncertain, len(resolved)),
        "deterministic_semantic_disagreements": disagreements,
        "contradiction_detection": binary_prf(resolved, "CONTRADICTED"),
        "confusion": confusion_matrix(resolved),
        "per_category": per_category,
        "injection_flagged": sum(1 for r in records if r.get("injection_detected")),
        "injection_cases": sum(1 for r in records if r["category"] == "context_injection"),
    }