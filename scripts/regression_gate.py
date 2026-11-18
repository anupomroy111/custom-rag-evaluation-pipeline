"""Offline benchmark regression gate (V2.1 §12).

Fails if any regression pin flips, or if the deterministic adversarial
benchmark shows false acceptance / detection below the recorded floor.
No API calls.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ragpipe.adversarial.dataset import (  # noqa: E402
    ADVERSARIAL_PATH, DEVELOPMENT_PATH, HELDOUT_PATH, REGRESSION_PATH, load_adversarial,
)
from ragpipe.adversarial.benchmark import AdversarialBenchmark  # noqa: E402
from ragpipe.verify.engine import VerificationEngine  # noqa: E402

SOURCES = {"adversarial": ADVERSARIAL_PATH, "development": DEVELOPMENT_PATH,
           "heldout": HELDOUT_PATH}


def main() -> int:
    spec = json.loads(REGRESSION_PATH.read_text(encoding="utf-8"))
    engine = VerificationEngine()
    pools = {name: {c.id: c for c in load_adversarial(path)}
             for name, path in SOURCES.items()}
    failures = []
    for pin in spec["pins"]:
        if pin["kind"] != "verdict":
            continue  # golden pins require live API; checked in live workflow
        case = pools[pin["source"]].get(pin["ref_id"])
        if case is None:
            failures.append(f"missing pin reference {pin['source']}/{pin['ref_id']}")
            continue
        contexts = [(f"{case.id}-p{i}", t) for i, t in enumerate(case.context)]
        result = engine.verify_claims(case.claims, contexts, mode="deterministic")
        got = result.verdicts[0].status.value
        if got != pin["expected_status"]:
            failures.append(f"pin flip {pin['ref_id']}: expected "
                            f"{pin['expected_status']}, got {got}")

    report = AdversarialBenchmark(mode="deterministic").run(load_adversarial())
    s = report["summary"]
    gates = spec["gates"]
    if (s["false_acceptance_rate"] or 0) > gates["adversarial_subset_false_acceptance"]:
        failures.append(f"false acceptance gate: {s['false_acceptance_rate']}")
    if (s["adversarial_detection_rate"] or 0) < gates["adversarial_subset_detection_floor"]:
        failures.append(f"detection floor gate: {s['adversarial_detection_rate']}")

    if failures:
        print("REGRESSION GATE FAILED:")
        for f in failures:
            print(" -", f)
        return 1
    print(f"regression gate OK: {len(spec['pins'])} pins, "
          f"FAR={s['false_acceptance_rate']}, detection={s['adversarial_detection_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())