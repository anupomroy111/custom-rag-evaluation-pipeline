"""Dataset leakage checks (V2.1 §4).

Gates:
  1. Scenario families disjoint between development and held-out splits.
  2. No near-duplicate claims across splits (token Jaccard >= 0.85).
  3. Held-out claims not near-duplicates of the original 104 fixtures.
  4. Every case carries required provenance / family / mutation metadata.
Exit code 1 on any violation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragpipe.adversarial.dataset import (  # noqa: E402
    ADVERSARIAL_PATH, DEVELOPMENT_PATH, HELDOUT_PATH, load_adversarial,
)
from ragpipe.verify.checks import content_tokens  # noqa: E402


def jaccard(a: str, b: str) -> float:
    ta, tb = content_tokens(a), content_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def main() -> int:
    dev = load_adversarial(DEVELOPMENT_PATH)
    held = load_adversarial(HELDOUT_PATH)
    old = load_adversarial(ADVERSARIAL_PATH)
    problems = []

    fd = {c.scenario_family for c in dev}
    fh = {c.scenario_family for c in held}
    if fd & fh:
        problems.append(f"scenario family overlap: {sorted(fd & fh)}")

    for a in dev:
        for b in held:
            if jaccard(a.claims[0], b.claims[0]) >= 0.85:
                problems.append(f"near-duplicate dev/heldout: {a.id} ~ {b.id}")
    for a in held:
        for b in old:
            if jaccard(a.claims[0], b.claims[0]) >= 0.85:
                problems.append(f"near-duplicate heldout/original104: {a.id} ~ {b.id}")

    for case in dev + held:
        if not (case.scenario_family and case.mutation_type and case.provenance):
            problems.append(f"missing metadata: {case.id}")
        if case.provenance != "synthetic-author-reviewed":
            problems.append(f"unexpected provenance claim: {case.id}")

    if problems:
        print("LEAKAGE CHECK FAILED:")
        for p in problems[:20]:
            print(" -", p)
        return 1
    print(f"leakage check OK: dev={len(dev)} heldout={len(held)} original={len(old)}; "
          f"families disjoint, no near-duplicates >= 0.85 Jaccard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())