"""Fixture-mode adversarial benchmark over the verification engine.

Modes:
  deterministic — LLM-free checks only; unresolved cases stay UNCERTAIN.
  semantic      — full engine with a live GeminiClient (judge_label="live").
  semantic with an injected fake client is labeled judge_label="mocked".
"""

import json
import time
from pathlib import Path

from ..config import settings
from ..llm import GeminiClient
from ..verify import checks
from ..verify.engine import JudgeClient, VerificationEngine
from .dataset import AdversarialCase, load_adversarial
from .metrics import summarize_adversarial


class AdversarialBenchmark:
    def __init__(self, client: JudgeClient | None = None, mode: str = "deterministic",
                 judge_label: str | None = None):
        if mode not in ("deterministic", "semantic"):
            raise ValueError(f"unknown benchmark mode {mode!r}")
        self.mode = mode
        self.engine = VerificationEngine(client)
        self.judge_label = judge_label or ("none" if mode == "deterministic" else "live")

    def run_case(self, case: AdversarialCase) -> list[dict]:
        contexts = [(f"{case.id}-p{i}", text) for i, text in enumerate(case.context)]
        result = self.engine.verify_claims(case.claims, contexts, mode=self.mode)
        records = []
        for i, verdict in enumerate(result.verdicts):
            records.append({
                "id": case.id,
                "claim_index": i,
                "category": case.category,
                "difficulty": case.difficulty,
                "claim": case.claims[i],
                "expected": case.expected_for(i),
                "predicted": verdict.status.value,
                "match": case.expected_for(i) == verdict.status.value,
                "deterministic_flags": verdict.deterministic_flags,
                "disagreement": verdict.disagreement,
                "explanation": verdict.explanation,
                "injection_detected": any(f.startswith("injection:")
                                          for f in verdict.deterministic_flags),
                "errors": result.errors,
            })
        return records

    def run(self, cases: list[AdversarialCase]) -> dict:
        records: list[dict] = []
        for i, case in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] {case.id} ({case.category})", flush=True)
            records.extend(self.run_case(case))
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": self.mode,
            "judge": self.judge_label,
            "llm_model": settings.llm_model if self.mode == "semantic" else None,
            "provenance": "synthetic-author-reviewed fixtures; no independent human validation",
            "n_cases": len(cases),
            "summary": summarize_adversarial(records),
            "records": records,
        }

    def save(self, report: dict, out_dir: Path | None = None) -> tuple[Path, Path]:
        out_dir = out_dir or settings.reports_dir / "v2"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        base = out_dir / f"adversarial_{self.mode}_{self.judge_label}_{stamp}"
        json_path = base.with_suffix(".json")
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path = base.with_suffix(".md")
        md_path.write_text(render_markdown(report), encoding="utf-8")
        return json_path, md_path


def _fmt(v) -> str:
    return f"{v:.3f}" if isinstance(v, (int, float)) else "n/a"


def render_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# Adversarial Benchmark Report (V2)",
        "",
        f"- **Generated:** {report['timestamp']}",
        f"- **Mode:** {report['mode']}  |  **Judge:** {report['judge']}",
        f"- **Cases:** {report['n_cases']}  |  **Claim records:** {len(report['records'])}",
        f"- **Provenance:** {report['provenance']}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Adversarial detection rate | {_fmt(s['adversarial_detection_rate'])} |",
        f"| False acceptance rate | {_fmt(s['false_acceptance_rate'])} |",
        f"| False rejection rate | {_fmt(s['false_rejection_rate'])} |",
        f"| Exact status accuracy | {_fmt(s['exact_status_accuracy'])} |",
        f"| Uncertain rate | {_fmt(s['uncertain_rate'])} |",
        f"| Evaluation error rate | {_fmt(s['evaluation_error_rate'])} |",
        f"| Deterministic/semantic disagreements | {s['deterministic_semantic_disagreements']} |",
        f"| Injection cases flagged | {s['injection_flagged']}/{s['injection_cases']} |",
        "",
        "## Contradiction detection (binary)",
        "",
        f"TP={s['contradiction_detection']['tp']} FP={s['contradiction_detection']['fp']} "
        f"FN={s['contradiction_detection']['fn']} · "
        f"precision={_fmt(s['contradiction_detection']['precision'])} "
        f"recall={_fmt(s['contradiction_detection']['recall'])} "
        f"F1={_fmt(s['contradiction_detection']['f1'])}",
        "",
        "## Per-category accuracy (exact status match)",
        "",
        "| Category | n | Accuracy | Uncertain |",
        "|---|---|---|---|",
    ]
    for cat, c in s["per_category"].items():
        lines.append(f"| {cat} | {c['n']} | {_fmt(c['exact_match_accuracy'])} | {c['uncertain']} |")

    lines += ["", "## Confusion matrix (expected rows × predicted columns)", "",
              "| expected \\ predicted | SUPPORTED | CONTRADICTED | NOT_SUPPORTED | UNCERTAIN |",
              "|---|---|---|---|---|"]
    for e, row in s["confusion"]["matrix"].items():
        lines.append(f"| {e} | " + " | ".join(str(row[p]) for p in
                     ["SUPPORTED", "CONTRADICTED", "NOT_SUPPORTED", "UNCERTAIN"]) + " |")
    lines.append(f"\nExcluded error-state records: {s['confusion']['excluded_error_states']}")

    misses = [r for r in report["records"] if not r["match"]]
    if misses:
        lines += ["", "## Misclassified / unresolved claims", ""]
        for r in misses:
            lines.append(f"- **{r['id']}** [{r['category']}] expected {r['expected']}, "
                         f"got {r['predicted']}: \"{r['claim']}\"")
            if r["deterministic_flags"]:
                lines.append(f"  - flags: {'; '.join(r['deterministic_flags'])}")
    lines.append("")
    return "\n".join(lines)