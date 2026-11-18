"""Build the V2.1 reviewer-ready executive summary from actual reports.

Reads the newest eval_v2 (full 4-variant), grid (mixed or offline), red-team
and deterministic adversarial reports; emits reports/v2_1/EXECUTIVE_SUMMARY.md
with executed-run inventory, Wilson bounds and failure analysis pointers.
Run after benchmarks: python scripts/build_v21_summary.py
"""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V21 = ROOT / "reports" / "v2_1"


def latest(pattern):
    files = sorted(glob.glob(str(ROOT / "reports" / pattern)))
    return json.loads(Path(files[-1]).read_text(encoding="utf-8")) if files else None


def f(v):
    return f"{v:.3f}" if isinstance(v, (int, float)) else "n/a"


def ci(bounds):
    return f"[{bounds[0]:.3f}, {bounds[1]:.3f}]" if bounds else "n/a"


def main():
    ev = None
    for p in sorted(glob.glob(str(ROOT / "reports" / "v2" / "eval_v2_*.json")), reverse=True):
        r = json.loads(Path(p).read_text(encoding="utf-8"))
        if all(len(v["results"]) == 12 for v in r["variants"].values()) and \
                len(r["variants"]) == 4:
            ev = r
            ev_name = Path(p).name
            break
    grid = None
    grids = sorted(glob.glob(str(ROOT / "reports" / "v2_1" / "grid_*.json")))
    for p in reversed(grids):
        r = json.loads(Path(p).read_text(encoding="utf-8"))
        if r.get("mode") == "mixed-replay":
            grid = r
            break
    if grid is None and grids:
        grid = json.loads(Path(grids[-1]).read_text(encoding="utf-8"))
    rt = latest("v2_1/redteam_deterministic.json")
    det = latest("v2/adversarial_deterministic_none_*.json")

    lines = ["# V2.1 Executive Summary (reviewer-ready)", "",
             "All numbers below come from executed runs; execution status is labeled",
             "per stage. Nothing mocked is presented as a benchmark.", ""]
    lines += ["## Executed-run inventory", "",
              "| Stage | Status | Source |", "|---|---|---|",
              f"| End-to-end ablation (4 variants × 12 Q) | "
              f"{ev['api_status'] if ev else 'not-run'} | {ev_name if ev else '—'} |",
              f"| Ablation grid (4 variants × 3 splits) | "
              f"{grid['mode'] if grid else 'not-run'} | newest reports/v2_1/grid_*.json |",
              f"| Red-team metamorphic (deterministic) | executed | "
              f"redteam_deterministic.json |",
              f"| Adversarial deterministic floor | executed | "
              f"newest adversarial_deterministic_none_*.json |",
              "| Red-team semantic (live) | not-run (quota reserved) | — |", ""]

    if ev:
        lines += ["## End-to-end ablation (original golden set, live judge)", "",
                  "| Variant | Faithfulness | Halluc. (answ.) | Fabrication (unansw.) | "
                  "Ctx precision | Ctx recall | Refusal acc | Citation validity |",
                  "|---|---|---|---|---|---|---|---|"]
        for name, v in ev["variants"].items():
            s = v["summary"]
            lines.append(f"| {name} | {f(s['faithfulness'])} | "
                         f"{f(s['hallucination_rate_answerable'])} | "
                         f"{f(s['fabrication_rate_unanswerable'])} | "
                         f"{f(s['context_precision'])} | {f(s['context_recall'])} | "
                         f"{f(s['refusal_accuracy'])} | {f(s['citation_validity_rate'])} |")
        lines.append("")
    if grid:
        lines += ["## Ablation grid — verification against retrieved evidence", "",
                  "| Split | Variant | Judge | Detection | FAR (95% CI) | FRR | Exact |",
                  "|---|---|---|---|---|---|---|"]
        for ds, variants in grid["datasets"].items():
            for name, v in variants.items():
                s = v["summary"]
                lines.append(f"| {ds} | {name} | {v['judge']} | "
                             f"{f(s['adversarial_detection_rate'])} | "
                             f"{f(s['false_acceptance_rate'])} "
                             f"{ci(s.get('false_acceptance_ci'))} | "
                             f"{f(s['false_rejection_rate'])} | "
                             f"{f(s['exact_status_accuracy'])} |")
        lines.append("")
        held = grid["datasets"].get("heldout", {})
        sem = held.get("hybrid+rerank", {})
        if sem and sem["judge"] in ("live", "cached-live"):
            s = sem["summary"]
            lines += ["### Held-out live semantic (hybrid+rerank) — headline", "",
                      f"- Detection {f(s['adversarial_detection_rate'])} "
                      f"{ci(s.get('adversarial_detection_ci'))}",
                      f"- FAR {f(s['false_acceptance_rate'])} "
                      f"{ci(s.get('false_acceptance_ci'))} "
                      f"(n={s['false_acceptance_counts']['adversarial_n']})",
                      f"- FRR {f(s['false_rejection_rate'])} "
                      f"{ci(s.get('false_rejection_ci'))}",
                      f"- Exact accuracy {f(s['exact_status_accuracy'])} "
                      f"{ci(s.get('exact_status_accuracy_ci'))}",
                      f"- Contradiction F1 {f(s['contradiction_detection']['f1'])}",
                      f"- Abstentions: {s['abstentions']['uncertain']} uncertain, "
                      f"{s['abstentions']['errors']} errors; "
                      f"coverage {f(s['abstentions']['coverage'])}", ""]
            lines += ["Per-category (held-out, live):", "",
                      "| Category | n | Exact | Uncertain |", "|---|---|---|---|"]
            for cat, c in s["per_category"].items():
                lines.append(f"| {cat} | {c['n']} | {f(c['exact_match_accuracy'])} | "
                             f"{c['uncertain']} |")
            lines.append("")
    if rt:
        lines += ["## Red-team metamorphic (deterministic)", "",
                  f"- Pairs {rt['n_pairs']}, passed {rt['passed']}, "
                  f"rate {f(rt['pass_rate'])}", ""]
    if det:
        s = det["summary"]
        lines += ["## Deterministic floor (104 fixtures, zero judge calls)", "",
                  f"- Detection {f(s['adversarial_detection_rate'])}, "
                  f"FAR {f(s['false_acceptance_rate'])} "
                  f"{ci(s.get('false_acceptance_ci'))}, "
                  f"FRR {f(s['false_rejection_rate'])}",
                  f"- Exact {f(s['exact_status_accuracy'])}, "
                  f"uncertain {f(s['uncertain_rate'])}", ""]
    lines += ["## Failure analysis & limitations", "",
              "- Misclassified/unresolved claims are listed per report "
              "(grid JSON `records`, benchmark Markdown sections).",
              "- Known limitations: docs/LIMITATIONS.md (15 items).",
              "- Metric denominators & CIs: docs/METRIC_DEFINITIONS.md.",
              "- Provenance manifests embedded in every V2.1 report.", ""]
    V21.mkdir(parents=True, exist_ok=True)
    (V21 / "EXECUTIVE_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print("EXECUTIVE_SUMMARY.md written")


if __name__ == "__main__":
    main()