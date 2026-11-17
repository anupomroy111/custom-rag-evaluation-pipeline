import pytest

from ragpipe.evaluate.metrics import context_precision, faithfulness
from ragpipe.evaluate.report import write_markdown_report
from ragpipe.evaluate.runner import Variant, summarize
from ragpipe.llm import parse_json


def test_parse_json_plain():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_fenced():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_with_prose():
    assert parse_json('Here you go: {"a": 1} hope that helps') == {"a": 1}


def test_parse_json_invalid_raises():
    with pytest.raises(ValueError):
        parse_json("no json at all")


class FaithFakeClient:
    def generate_json(self, prompt, system=None, temperature=0.0):
        if "atomic factual claims" in system:
            return {"claims": ["timeout is 15 minutes", "max is 90 minutes"]}
        return {"verdicts": [
            {"claim": "timeout is 15 minutes", "supported": True, "reason": "stated"},
            {"claim": "max is 90 minutes", "supported": False, "reason": "docs say 60"},
        ]}


def test_faithfulness_half_supported():
    result = faithfulness("answer", ["context"], FaithFakeClient())
    assert result.score == 0.5
    assert result.hallucination_rate == 0.5
    assert len(result.verdicts) == 2


def test_faithfulness_no_claims():
    class NoClaims:
        def generate_json(self, prompt, system=None, temperature=0.0):
            return {"claims": []}

    result = faithfulness("I cannot answer.", ["ctx"], NoClaims())
    assert result.score == 1.0


def test_context_precision_from_grades():
    # relevant flags [True, False, True] -> AP = (1/1 + 2/3) / 2
    result = context_precision(
        "q", ["t1", "t2", "t3"], client=None,
        grades={"a": 3, "b": 0, "c": 2}, context_ids=["a", "b", "c"],
    )
    assert result["relevant"] == [True, False, True]
    assert result["score"] == pytest.approx((1 + 2 / 3) / 2)


def test_context_precision_empty():
    assert context_precision("q", [], client=None)["score"] == 0.0


def test_variant_parse():
    assert Variant.parse("hybrid+rerank") == Variant(mode="hybrid", rerank=True)
    assert Variant.parse("bm25") == Variant(mode="bm25", rerank=False)
    assert Variant.parse("dense").name == "dense"
    with pytest.raises(ValueError):
        Variant.parse("magic")


def test_summarize_means_and_refusals():
    records = [
        {"answerable": True, "refused": False, "faithfulness": 1.0, "hallucination_rate": 0.0,
         "answer_relevancy": 1.0, "context_precision": 1.0, "context_recall": 0.5, "cited_ids": ["a"]},
        {"answerable": True, "refused": True, "faithfulness": None, "hallucination_rate": 0.0,
         "answer_relevancy": 0.5, "context_precision": 0.0, "context_recall": 0.0, "cited_ids": []},
        {"answerable": False, "refused": True, "faithfulness": None, "hallucination_rate": 0.0,
         "answer_relevancy": 1.0, "cited_ids": []},
    ]
    s = summarize(records)
    assert s["faithfulness"] == 1.0
    assert s["context_recall"] == 0.25
    assert s["refusal_accuracy"] == 1.0
    assert s["over_refusal_rate"] == 0.5
    assert s["citation_coverage"] == 0.5


def test_markdown_report_contains_sections():
    report = {
        "timestamp": "2026-11-17 00:00:00",
        "llm_model": "test-model",
        "embed_model": "test-embed",
        "num_questions": 1,
        "variants": {
            "hybrid+rerank": {
                "summary": {"faithfulness": 0.9},
                "results": [{
                    "id": "q01", "question": "What?", "answerable": True, "refused": False,
                    "faithfulness": 0.9, "hallucination_rate": 0.1, "answer_relevancy": 1.0,
                    "context_precision": 1.0, "context_recall": 1.0,
                    "claim_verdicts": [{"claim": "bad claim", "supported": False, "reason": "not in docs"}],
                }],
            }
        },
    }
    md = write_markdown_report(report)
    assert "Variant comparison" in md
    assert "bad claim" in md
    assert "hybrid+rerank" in md