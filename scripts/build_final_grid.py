"""Assemble the final V2.1 grid report by deterministic replay.

Retrieval results (retrieved_ids) are taken from the executed live grid run's
report; verification is recomputed with the FINAL code: deterministic checks
offline, semantic judgments replayed from the disk response cache. Zero API
calls. Provenance of the retrieval source is recorded in the manifest.

Run: python scripts/build_final_grid.py
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ragpipe.adversarial.dataset import (  # noqa: E402
    ADVERSARIAL_PATH, DEVELOPMENT_PATH, HELDOUT_PATH, load_adversarial,
)
from ragpipe.adversarial.metrics import summarize_adversarial  # noqa: E402
from ragpipe.config import settings  # noqa: E402
from ragpipe.evaluate.ablation_v21 import VARIANTS, save_grid  # noqa: E402
from ragpipe.llm import GeminiClient  # noqa: E402
from ragpipe.manifest import build_manifest  # noqa: E402
from ragpipe.verify.engine import VerificationEngine  # noqa: E402

SPLITS = {"adversarial": ADVERSARIAL_PATH, "development": DEVELOPMENT_PATH,
          "heldout": HELDOUT_PATH}


def main() -> int:
    sources = sorted(glob.glob(str(ROOT / "reports" / "v2_1" / "grid_mixed_*.json")))
    if not sources:
        print("no executed mixed grid report found")
        return 1
    source = json.loads(Path(sources[-1]).read_text(encoding="utf-8"))
    # client object required for semantic mode; all judgments replay from cache
    engine = VerificationEngine(GeminiClient())
    report = {"timestamp": source["timestamp"], "mode": "mixed-replay",
              "datasets": {}}
    for ds, path in SPLITS.items():
        cases = load_adversarial(path)
        chunks = {c["id"]: c["text"] for c in json.loads(
            (settings.index_dir / f"probes_{ds}" / "chunks.json").read_text(encoding="utf-8"))}
        report["datasets"][ds] = {}
        for variant in VARIANTS:
            src_records = {r["id"]: r for r in
                           source["datasets"][ds][variant]["records"]
                           if r["claim_index"] == 0}
            sem = variant == "hybrid+rerank" and ds != "adversarial"
            records = []
            for case in cases:
                retrieved_ids = src_records[case.id]["retrieved_ids"]
                contexts = [(cid, chunks[cid]) for cid in retrieved_ids]
                result = engine.verify_claims(
                    case.claims, contexts, mode="semantic" if sem else "deterministic")
                for j, verdict in enumerate(result.verdicts):
                    records.append({
                        "id": case.id, "claim_index": j, "category": case.category,
                        "difficulty": case.difficulty, "claim": case.claims[j],
                        "expected": case.expected_for(j),
                        "predicted": verdict.status.value,
                        "match": case.expected_for(j) == verdict.status.value,
                        "deterministic_flags": verdict.deterministic_flags,
                        "disagreement": verdict.disagreement,
                        "explanation": verdict.explanation,
                        "injection_detected": any(f.startswith("injection:")
                                                  for f in verdict.deterministic_flags),
                        "errors": result.errors,
                        "retrieved_ids": retrieved_ids,
                    })
            report["datasets"][ds][variant] = {
                "judge": "cached-live" if sem else "none",
                "summary": summarize_adversarial(records),
                "records": records,
            }
            s = report["datasets"][ds][variant]["summary"]
            print(f"{ds:12s} {variant:14s} detection={s['adversarial_detection_rate']} "
                  f"FAR={s['false_acceptance_rate']} exact={s['exact_status_accuracy']}")
    report["manifest"] = build_manifest(
        SPLITS, api_status="replay-cached",
        extra={"retrieval_source": Path(sources[-1]).name,
               "verification": "recomputed with final code; semantic judgments "
                               "replayed from disk response cache",
               "grid_variants": VARIANTS})
    report["api_stats"] = {"generate_requests": 0, "embed_requests": 0,
                           "cache_hits": "all semantic judgments replayed"}
    j, m = save_grid(report)
    print("saved:", j.name, m.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())