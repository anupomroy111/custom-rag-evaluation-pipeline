"""Statistical hygiene for evaluation proportions (V2.1 §5).

Every proportion reports its denominator and a Wilson score interval.
Abstentions (UNCERTAIN) and error states are separated from incorrect
predictions; zero denominators yield None, never 0.0 or 1.0.
"""

import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson score interval for k successes out of n trials."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)


def rate(k: int, n: int) -> float | None:
    return round(k / n, 4) if n else None


def binary_counts(records: list[dict], positive: str) -> dict:
    tp = sum(1 for r in records if r["expected"] == positive and r["predicted"] == positive)
    fp = sum(1 for r in records if r["expected"] != positive and r["predicted"] == positive)
    fn = sum(1 for r in records if r["expected"] == positive and r["predicted"] != positive)
    tn = sum(1 for r in records if r["expected"] != positive and r["predicted"] != positive)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def prf(counts: dict) -> dict:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = rate(tp, tp + fp)
    recall = rate(tp, tp + fn)
    f1 = (round(2 * precision * recall / (precision + recall), 4)
          if precision and recall else None)
    return {**counts, "precision": precision, "recall": recall, "f1": f1,
            "precision_ci": wilson(tp, tp + fp), "recall_ci": wilson(tp, tp + fn)}


def macro_micro(per_category: dict[str, list[dict]], positive: str) -> dict:
    pooled = [r for records in per_category.values() for r in records]
    micro = prf(binary_counts(pooled, positive))
    macros: dict[str, list[float]] = {"precision": [], "recall": [], "f1": []}
    for records in per_category.values():
        c = prf(binary_counts(records, positive))
        for key in macros:
            if c[key] is not None:
                macros[key].append(c[key])
    macro = {k: (round(sum(v) / len(v), 4) if v else None) for k, v in macros.items()}
    return {"micro": micro, "macro": macro,
            "macro_categories": {k: len(v) for k, v in macros.items()}}


def abstentions(records: list[dict]) -> dict:
    n = len(records)
    uncertain = sum(1 for r in records if r["predicted"] == "UNCERTAIN")
    errors = sum(1 for r in records if r["predicted"] in
                 ("EVALUATION_ERROR", "EXTRACTION_FAILED"))
    resolved = [r for r in records if r["predicted"] not in
                ("UNCERTAIN", "EVALUATION_ERROR", "EXTRACTION_FAILED")]
    correct = sum(1 for r in resolved if r["expected"] == r["predicted"])
    return {
        "n": n,
        "uncertain": uncertain,
        "errors": errors,
        "coverage": rate(len(resolved), n),
        "accuracy_all": rate(correct, n),
        "accuracy_resolved_only": rate(correct, len(resolved)),
        "accuracy_resolved_only_ci": wilson(correct, len(resolved)),
    }