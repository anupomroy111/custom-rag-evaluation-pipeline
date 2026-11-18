"""V2.1 ablation grid: 4 retrieval variants × {adversarial, development, heldout}.

For each case the variant retrieves top-4 evidence; the verification engine then
judges the fixture claims against THAT retrieved evidence — so retrieval quality
propagates into verification metrics (detection / false acceptance per variant).

offline mode: deterministic verification, zero judge calls (embeddings only).
mixed mode:   additionally semantic verification for hybrid+rerank on
              development + heldout (live judge, quota-bounded).
"""

import json
import time
from pathlib import Path

from ..adversarial.dataset import (
    ADVERSARIAL_PATH, DEVELOPMENT_PATH, HELDOUT_PATH, load_adversarial,
)
from ..adversarial.metrics import summarize_adversarial
from ..adversarial.probes import CachingEmbedClient, build_probe_index, probe_question
from ..config import settings
from ..llm import GeminiClient
from ..manifest import build_manifest
from ..verify.engine import VerificationEngine

VARIANTS = ["bm25", "dense", "hybrid", "hybrid+rerank"]


def run_grid(mode: str = "offline", client: GeminiClient | None = None) -> dict:
    if mode not in ("offline", "mixed"):
        raise ValueError(f"unknown grid mode {mode!r}")
    client = client or GeminiClient()
    engine = VerificationEngine(client if mode == "mixed" else None)
    datasets = {
        "adversarial": load_adversarial(ADVERSARIAL_PATH),
        "development": load_adversarial(DEVELOPMENT_PATH),
        "heldout": load_adversarial(HELDOUT_PATH),
    }
    report = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": mode,
              "datasets": {}}
    for ds, cases in datasets.items():
        print(f"\n=== grid dataset: {ds} ({len(cases)} cases) ===", flush=True)
        _, retriever = build_probe_index(cases, client,
                                         index_dir=settings.index_dir / f"probes_{ds}")
        caching = CachingEmbedClient(client)
        report["datasets"][ds] = {}
        for variant in VARIANTS:
            sem = mode == "mixed" and variant == "hybrid+rerank" and ds != "adversarial"
            records = []
            for i, case in enumerate(cases, 1):
                if i % 25 == 0:
                    print(f"  [{ds}/{variant}] {i}/{len(cases)}", flush=True)
                retrieved = retriever.search(
                    probe_question(case),
                    client=caching if variant != "bm25" else None,
                    mode=variant.removesuffix("+rerank"), top_k=4)
                contexts = [(c.chunk.id, c.chunk.text) for c in retrieved]
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
                        "retrieved_ids": [cid for cid, _ in contexts],
                    })
            report["datasets"][ds][variant] = {
                "judge": "live" if sem else "none",
                "summary": summarize_adversarial(records),
                "records": records,
            }
            s = report["datasets"][ds][variant]["summary"]
            print(f"  {variant:14s} detection={s['adversarial_detection_rate']} "
                  f"FAR={s['false_acceptance_rate']} exact={s['exact_status_accuracy']}",
                  flush=True)
    report["manifest"] = build_manifest(
        {"adversarial": ADVERSARIAL_PATH, "development": DEVELOPMENT_PATH,
         "heldout": HELDOUT_PATH},
        api_status="live-mixed" if mode == "mixed" else "offline-deterministic",
        extra={"grid_variants": VARIANTS},
    )
    report["api_stats"] = dict(client.stats)
    return report


def save_grid(report: dict, out_dir: Path | None = None) -> tuple[Path, Path]:
    out_dir = out_dir or settings.reports_dir / "v2_1"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    base = out_dir / f"grid_{report['mode']}_{stamp}"
    base.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# V2.1 Ablation Grid — retrieval variants × verification", "",
             f"- Generated: {report['timestamp']} · mode: {report['mode']}", "",
             "| Dataset | Variant | Judge | n | Detection | FAR | FRR | Exact | Uncertain |",
             "|---|---|---|---|---|---|---|---|---|"]
    for ds, variants in report["datasets"].items():
        for name, v in variants.items():
            s = v["summary"]
            lines.append(f"| {ds} | {name} | {v['judge']} | {s['n_cases']} | "
                         f"{s['adversarial_detection_rate']} | {s['false_acceptance_rate']} | "
                         f"{s['false_rejection_rate']} | {s['exact_status_accuracy']} | "
                         f"{s['uncertain_rate']} |")
    lines.append("")
    base.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return base.with_suffix(".json"), base.with_suffix(".md")