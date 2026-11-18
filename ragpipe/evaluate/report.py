METRIC_LABELS = [
    ("faithfulness", "Faithfulness"),
    ("hallucination_rate_answerable", "Hallucination rate (answerable)"),
    ("fabrication_rate_unanswerable", "Fabrication rate (unanswerable)"),
    ("answer_relevancy", "Answer relevancy"),
    ("context_precision", "Context precision"),
    ("context_recall", "Context recall"),
    ("refusal_accuracy", "Refusal accuracy (unanswerable)"),
    ("over_refusal_rate", "Over-refusal rate"),
    ("citation_coverage", "Citation coverage"),
]


def _fmt(value) -> str:
    return f"{value:.3f}" if isinstance(value, (int, float)) else "n/a"


def write_markdown_report(report: dict) -> str:
    lines = [
        "# RAG Evaluation Report",
        "",
        f"- **Generated:** {report['timestamp']}",
        f"- **LLM:** `{report['llm_model']}`  |  **Embeddings:** `{report['embed_model']}`",
        f"- **Questions:** {report['num_questions']}",
        "",
        "## Variant comparison",
        "",
        "| Metric | " + " | ".join(report["variants"]) + " |",
        "|---" * (len(report["variants"]) + 1) + "|",
    ]
    summaries = {name: v["summary"] for name, v in report["variants"].items()}
    for key, label in METRIC_LABELS:
        row = " | ".join(_fmt(s.get(key)) for s in summaries.values())
        lines.append(f"| {label} | {row} |")

    for name, variant in report["variants"].items():
        lines += ["", f"## Details: `{name}`", "",
                  "| # | Question | Faithful | Halluc./Fabr. | Relevancy | Ctx Prec | Ctx Recall | Refused |",
                  "|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(variant["results"], 1):
            q = r["question"][:60] + ("..." if len(r["question"]) > 60 else "")
            halluc = (r.get("hallucination_rate") if r["answerable"]
                      else (1.0 if r.get("fabricated") else 0.0))
            lines.append(
                f"| {i} | {q} | {_fmt(r.get('faithfulness'))} | "
                f"{_fmt(halluc)} | {_fmt(r.get('answer_relevancy'))} | "
                f"{_fmt(r.get('context_precision'))} | {_fmt(r.get('context_recall'))} | "
                f"{'yes' if r['refused'] else 'no'} |"
            )

        unsupported = [
            (r["id"], v)
            for r in variant["results"]
            for v in r.get("claim_verdicts", [])
            if not (v.get("supported") if "supported" in v
                    else v.get("status") == "SUPPORTED")
        ]
        if unsupported:
            lines += ["", "### Unsupported claims (hallucination audit)", ""]
            for qid, v in unsupported:
                label = v.get("claim") or v.get("claim_id", "?")
                lines.append(f"- **{qid}**: \"{label}\"")
                reason = v.get("reason") or v.get("explanation")
                if reason:
                    lines.append(f"  - Judge: {reason}")

    lines += [
        "", "## Metric definitions", "",
        "- **Faithfulness** — fraction of atomic answer claims supported by retrieved context (claim extraction + per-claim LLM verification).",
        "- **Hallucination rate (answerable)** — `1 - faithfulness` over resolved claim verdicts; None when extraction/verification failed (fail-closed).",
        "- **Fabrication rate (unanswerable)** — fraction of unanswerable questions where the model fabricated an answer instead of refusing. Reported separately from the answerable population.",
        "- **Answer relevancy** — LLM-judged alignment of the answer with the question (0–1).",
        "- **Context precision** — rank-weighted (average-precision style) relevance of retrieved passages; uses reranker grades when available.",
        "- **Context recall** — fraction of reference-answer sentences attributable to retrieved context.",
        "- **Refusal accuracy** — correct refusals on unanswerable questions; **Over-refusal** — wrong refusals on answerable ones.",
        "",
    ]
    return "\n".join(lines)