import json
import time
from dataclasses import dataclass
from pathlib import Path

from ..config import settings
from ..llm import GeminiClient
from ..pipeline import RAGPipeline
from . import metrics
from .report import write_markdown_report


@dataclass
class Variant:
    mode: str
    rerank: bool

    @property
    def name(self) -> str:
        return f"{self.mode}+rerank" if self.rerank else self.mode

    @classmethod
    def parse(cls, spec: str) -> "Variant":
        spec = spec.strip().lower()
        rerank = spec.endswith("+rerank")
        mode = spec.removesuffix("+rerank")
        if mode not in ("bm25", "dense", "hybrid"):
            raise ValueError(f"Invalid variant {spec!r}; use bm25|dense|hybrid[+rerank]")
        return cls(mode=mode, rerank=rerank)


def load_golden(path: Path | None = None) -> list[dict]:
    path = path or settings.golden_path
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    for item in items:
        item.setdefault("answerable", True)
        item.setdefault("ground_truth", "")
    return items


class EvalRunner:
    def __init__(self, pipeline: RAGPipeline, client: GeminiClient | None = None):
        self.pipeline = pipeline
        self.client = client or pipeline.client

    def evaluate_item(self, item: dict, variant: Variant) -> dict:
        result = self.pipeline.run(item["question"], mode=variant.mode, rerank=variant.rerank)
        answer = result.answer
        context_texts = [c.chunk.text for c in result.contexts]
        context_ids = [c.chunk.id for c in result.contexts]
        answerable = item["answerable"]

        record = {
            "id": item.get("id", item["question"][:40]),
            "question": item["question"],
            "answerable": answerable,
            "answer": answer.text,
            "refused": answer.refused,
            "cited_ids": answer.cited_ids,
            "context_ids": context_ids,
            "context_docs": [c.chunk.doc for c in result.contexts],
            "retrieved_ids": [c.chunk.id for c in result.retrieved],
        }

        if answerable and not answer.refused:
            faith = metrics.faithfulness(answer.text, context_texts, self.client)
            record["faithfulness"] = faith.score
            record["faithfulness_status"] = faith.status
            record["hallucination_rate"] = faith.hallucination_rate
            record["claim_verdicts"] = faith.verdicts
            recall = metrics.context_recall(item["ground_truth"], context_texts, self.client)
            record["context_recall"] = recall["score"]
            record["recall_verdicts"] = recall["verdicts"]
        elif answerable and answer.refused:
            # Over-refusal: answer exists in docs but model declined.
            record["faithfulness"] = None
            record["faithfulness_status"] = "OVER_REFUSAL"
            record["hallucination_rate"] = None
            record["over_refusal"] = True
            record["context_recall"] = 0.0
            record["claim_verdicts"] = []
        else:
            # Unanswerable question: fabricating anything is a hallucination.
            record["faithfulness"] = None
            record["hallucination_rate"] = None
            record["fabricated"] = not answer.refused
            record["context_recall"] = None
            record["claim_verdicts"] = []

        if answerable:
            precision = metrics.context_precision(
                item["question"], context_texts, self.client,
                grades=result.relevance_grades or None, context_ids=context_ids,
            )
            record["context_precision"] = precision["score"]
            record["context_relevant_flags"] = precision["relevant"]

        relevancy = metrics.answer_relevancy(item["question"], answer.text, self.client)
        record["answer_relevancy"] = relevancy["score"]
        record["relevancy_reason"] = relevancy["reason"]
        return record

    def run(self, items: list[dict], variants: list[Variant]) -> dict:
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "llm_model": settings.llm_model,
            "embed_model": settings.embed_model,
            "num_questions": len(items),
            "variants": {},
        }
        for variant in variants:
            print(f"\n=== Variant: {variant.name} ===")
            records = []
            for i, item in enumerate(items, 1):
                print(f"[{i}/{len(items)}] {item['question'][:70]}", flush=True)
                records.append(self.evaluate_item(item, variant))
                report["variants"][variant.name] = {
                    "summary": summarize(records),
                    "results": records,
                }
                self._checkpoint(report)
            print_summary(variant.name, report["variants"][variant.name]["summary"])
        return report

    def _checkpoint(self, report: dict) -> None:
        settings.reports_dir.mkdir(parents=True, exist_ok=True)
        (settings.reports_dir / "checkpoint.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def save(self, report: dict, out_dir: Path | None = None) -> tuple[Path, Path]:
        out_dir = out_dir or settings.reports_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        json_path = out_dir / f"eval_{stamp}.json"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path = out_dir / f"eval_{stamp}.md"
        md_path.write_text(write_markdown_report(report), encoding="utf-8")
        return json_path, md_path


def _mean(values: list) -> float | None:
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else None


def summarize(records: list[dict]) -> dict:
    answerable = [r for r in records if r["answerable"]]
    unanswerable = [r for r in records if not r["answerable"]]
    return {
        "faithfulness": _mean([r.get("faithfulness") for r in answerable]),
        # Incompatible populations are reported separately, never averaged together.
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
            round(sum(1 for r in answerable if r["cited_ids"]) / len(answerable), 4)
            if answerable else None
        ),
    }


def print_summary(name: str, summary: dict) -> None:
    print(f"--- {name} ---")
    for key, value in summary.items():
        print(f"  {key:22s}: {value if value is not None else 'n/a'}")