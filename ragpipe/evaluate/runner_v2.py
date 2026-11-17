"""V2 end-to-end evaluation runner: engine-based verification + independent
relevance judge for context precision (fixes audit M1 circularity)."""

import json
import time
from pathlib import Path

from ..config import settings
from ..llm import GeminiClient
from ..pipeline import RAGPipeline
from ..verify import VerificationEngine
from . import metrics
from .report import write_markdown_report
from .runner import Variant, _mean, load_golden, print_summary


class EvalRunnerV2:
    def __init__(self, pipeline: RAGPipeline, client: GeminiClient | None = None):
        self.pipeline = pipeline
        self.client = client or pipeline.client
        self.engine = VerificationEngine(self.client)

    def evaluate_item(self, item: dict, variant: Variant) -> dict:
        result = self.pipeline.run(item["question"], mode=variant.mode, rerank=variant.rerank)
        answer = result.answer
        contexts = [(c.chunk.id, c.chunk.text) for c in result.contexts]
        context_texts = [t for _, t in contexts]
        answerable = item["answerable"]

        record = {
            "id": item.get("id", item["question"][:40]),
            "question": item["question"],
            "answerable": answerable,
            "answer": answer.text,
            "refused": answer.refused,
            "cited_ids": answer.cited_ids,
            "invalid_citations": answer.invalid_citations,
            "context_ids": [cid for cid, _ in contexts],
            "context_docs": [c.chunk.doc for c in result.contexts],
            "retrieved_ids": [c.chunk.id for c in result.retrieved],
        }

        verification = self.engine.verify_answer(
            answer.text, contexts, refused=answer.refused, mode="semantic"
        )
        record["answer_state"] = verification.answer_state.value
        record["faithfulness"] = verification.faithfulness
        record["hallucination_rate"] = verification.hallucination_rate
        record["claim_verdicts"] = [v.model_dump() for v in verification.verdicts]
        record["claim_analyses"] = [c.model_dump() for c in verification.claims]
        record["verification_errors"] = verification.errors
        if not answerable:
            record["fabricated"] = not answer.refused

        if answerable and not answer.refused:
            recall = metrics.context_recall(item["ground_truth"], context_texts, self.client)
            record["context_recall"] = recall["score"]
            record["recall_verdicts"] = recall["verdicts"]
        elif answerable:
            record["over_refusal"] = True
            record["context_recall"] = 0.0
        else:
            record["context_recall"] = None

        if answerable:
            # independent judge, never the reranker's own grades (audit M1)
            precision = metrics.context_precision(item["question"], context_texts, self.client)
            record["context_precision"] = precision["score"]
            record["context_relevant_flags"] = precision["relevant"]
            record["precision_judge"] = "independent"

        relevancy = metrics.answer_relevancy(item["question"], answer.text, self.client)
        record["answer_relevancy"] = relevancy["score"]
        record["relevancy_reason"] = relevancy["reason"]
        return record

    def run(self, items: list[dict], variants: list[Variant]) -> dict:
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "v2",
            "llm_model": settings.llm_model,
            "embed_model": settings.embed_model,
            "num_questions": len(items),
            "variants": {},
        }
        for variant in variants:
            print(f"\n=== V2 variant: {variant.name} ===", flush=True)
            records = []
            for i, item in enumerate(items, 1):
                print(f"[{i}/{len(items)}] {item['question'][:70]}", flush=True)
                records.append(self.evaluate_item(item, variant))
                report["variants"][variant.name] = {
                    "summary": summarize_v2(records),
                    "results": records,
                }
                self._checkpoint(report)
            print_summary(variant.name, report["variants"][variant.name]["summary"])
        report["api_stats"] = dict(self.client.stats)
        return report

    def _checkpoint(self, report: dict) -> None:
        out = settings.reports_dir / "v2"
        out.mkdir(parents=True, exist_ok=True)
        (out / "checkpoint_v2.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def save(self, report: dict, out_dir: Path | None = None) -> tuple[Path, Path]:
        out_dir = out_dir or settings.reports_dir / "v2"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        json_path = out_dir / f"eval_v2_{stamp}.json"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path = out_dir / f"eval_v2_{stamp}.md"
        md_path.write_text(render_v2_markdown(report), encoding="utf-8")
        return json_path, md_path


def summarize_v2(records: list[dict]) -> dict:
    answerable = [r for r in records if r["answerable"]]
    unanswerable = [r for r in records if not r["answerable"]]
    answered = [r for r in answerable if not r["refused"]]
    attempts = sum(len(r["cited_ids"]) + len(r["invalid_citations"]) for r in answered)
    invalid = sum(len(r["invalid_citations"]) for r in answered)
    states = [r.get("answer_state") for r in answered]
    return {
        "faithfulness": _mean([r.get("faithfulness") for r in answerable]),
        "hallucination_rate_answerable": _mean(
            [r.get("hallucination_rate") for r in answerable]),
        "fabrication_rate_unanswerable": (
            round(sum(1 for r in unanswerable if r.get("fabricated")) / len(unanswerable), 4)
            if unanswerable else None
        ),
        "answer_relevancy": _mean([r.get("answer_relevancy") for r in records]),
        "context_precision": _mean([r.get("context_precision") for r in answerable]),
        "context_recall": _mean([r.get("context_recall") for r in answerable]),
        "refusal_accuracy": (
            round(sum(1 for r in unanswerable if r["refused"]) / len(unanswerable), 4)
            if unanswerable else None
        ),
        "over_refusal_rate": (
            round(sum(1 for r in answerable if r["refused"]) / len(answerable), 4)
            if answerable else None
        ),
        "citation_coverage": (
            round(sum(1 for r in answered if r["cited_ids"]) / len(answered), 4)
            if answered else None
        ),
        "citation_validity_rate": round(1 - invalid / attempts, 4) if attempts else None,
        "claim_extraction_success_rate": (
            round(sum(1 for s in states if s == "OK") / len(states), 4) if states else None
        ),
        "evaluation_error_rate": (
            round(sum(1 for s in states if s == "EVALUATION_ERROR") / len(states), 4)
            if states else None
        ),
    }


def render_v2_markdown(report: dict) -> str:
    md = write_markdown_report(report)
    lines = ["", "## V2 verification health", "",
             "| Variant | Citation validity | Extraction success | Evaluation errors |",
             "|---|---|---|---|"]
    for name, v in report["variants"].items():
        s = v["summary"]
        lines.append(f"| {name} | {s['citation_validity_rate']} | "
                     f"{s['claim_extraction_success_rate']} | {s['evaluation_error_rate']} |")
    stats = report.get("api_stats", {})
    if stats:
        lines += ["", "## API usage (this run)", "",
                  f"- generate requests: {stats.get('generate_requests')} "
                  f"(cache hits: {stats.get('cache_hits')})",
                  f"- embed requests: {stats.get('embed_requests')}",
                  f"- tokens: prompt {stats.get('prompt_tokens')} / "
                  f"output {stats.get('output_tokens')}",
                  f"- latency: {stats.get('latency_s', 0):.1f}s · "
                  f"retries: {stats.get('retries')} · errors: {stats.get('errors')}"]
    return md + "\n".join(lines) + "\n"