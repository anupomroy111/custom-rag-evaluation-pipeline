"""V2 runner integration tests with mocked pipeline + judge (no API calls)."""

from types import SimpleNamespace

from ragpipe.evaluate.runner import Variant, summarize
from ragpipe.evaluate.runner_v2 import EvalRunnerV2, summarize_v2
from ragpipe.generator import Answer
from ragpipe.ingest import Chunk
from ragpipe.retrieval import RetrievedChunk


class MockJudge:
    def generate_json(self, prompt, system=None, temperature=0.0):
        if "atomic factual claims" in system:
            return {"claims": ["The default build timeout is 15 minutes."]}
        if "analyze and verify" in system:
            return {"claims": [{"claim_id": "c1",
                                "original_claim": "The default build timeout is 15 minutes.",
                                "status": "SUPPORTED", "confidence": 0.9,
                                "explanation": "mocked"}]}
        if "reference answer" in system:
            return {"verdicts": [{"sentence": "The timeout is 15 minutes.",
                                  "attributed": True}]}
        if "numbered passage" in system:
            return {"verdicts": [{"index": 1, "relevant": True}]}
        if "Rate how well" in system:
            return {"score": 1.0, "reason": "mocked"}
        raise ValueError(f"unexpected system prompt: {system}")


def make_pipeline(refused=False):
    chunk = RetrievedChunk(Chunk(id="p1", doc="a.md", text="The default build timeout is 15 minutes.",
                                 ordinal=0), score=1.0, rank=1)
    answer = Answer(text="I cannot answer this from the provided documents." if refused
                    else "The default build timeout is 15 minutes [id:p1].",
                    cited_ids=[] if refused else ["p1"],
                    refused=refused,
                    invalid_citations=[] if refused else ["ffffffffffff"])
    return SimpleNamespace(run=lambda q, mode, rerank, top_k=None: SimpleNamespace(
        answer=answer, contexts=[chunk], retrieved=[chunk], relevance_grades={"p1": 3}))


ITEM = {"id": "q01", "question": "What is the default build timeout?",
        "ground_truth": "The default build timeout is 15 minutes.", "answerable": True}
UNANSWERABLE = {"id": "q11", "question": "Who is the CEO?", "ground_truth": "",
                "answerable": False}


def test_v2_item_uses_engine_and_independent_precision():
    runner = EvalRunnerV2(make_pipeline(), client=MockJudge())
    record = runner.evaluate_item(ITEM, Variant(mode="hybrid", rerank=True))
    assert record["faithfulness"] == 1.0
    assert record["answer_state"] == "OK"
    assert record["precision_judge"] == "independent"
    assert record["context_precision"] == 1.0
    assert record["invalid_citations"] == ["ffffffffffff"]
    assert record["claim_verdicts"][0]["status"] == "SUPPORTED"


def test_v2_refusal_on_unanswerable_not_fabrication():
    runner = EvalRunnerV2(make_pipeline(refused=True), client=MockJudge())
    record = runner.evaluate_item(UNANSWERABLE, Variant(mode="hybrid", rerank=True))
    assert record["fabricated"] is False
    assert record["answer_state"] == "REFUSED"
    assert record["faithfulness"] is None


def test_v2_summary_citation_validity_and_populations():
    runner = EvalRunnerV2(make_pipeline(), client=MockJudge())
    refusal_runner = EvalRunnerV2(make_pipeline(refused=True), client=MockJudge())
    records = [runner.evaluate_item(ITEM, Variant(mode="hybrid", rerank=True)),
               refusal_runner.evaluate_item(UNANSWERABLE, Variant(mode="hybrid", rerank=True))]
    s = summarize_v2(records)
    assert s["citation_validity_rate"] == 0.5
    assert s["claim_extraction_success_rate"] == 1.0
    assert s["evaluation_error_rate"] == 0.0
    assert s["fabrication_rate_unanswerable"] == 0.0
    assert s["hallucination_rate_answerable"] == 0.0


def test_report_renderer_handles_v2_verdict_dicts():
    """Regression: V2 verdicts carry 'status', not V1's 'supported' key."""
    from ragpipe.evaluate.report import write_markdown_report
    report = {
        "timestamp": "t", "llm_model": "m", "embed_model": "e", "num_questions": 1,
        "variants": {"hybrid+rerank": {"summary": {"faithfulness": 1.0}, "results": [{
            "id": "q01", "question": "What?", "answerable": True, "refused": False,
            "faithfulness": 1.0, "hallucination_rate": 0.0, "answer_relevancy": 1.0,
            "context_precision": 1.0, "context_recall": 1.0,
            "claim_verdicts": [{"claim_id": "c1", "status": "CONTRADICTED",
                                "explanation": "x"}],
        }]}},
    }
    md = write_markdown_report(report)
    assert "CONTRADICTED" in md or "unsupported" in md.lower()


def test_v1_summary_no_longer_mixes_populations():
    records = [
        {"answerable": True, "refused": False, "faithfulness": 1.0,
         "hallucination_rate": 0.0, "answer_relevancy": 1.0,
         "context_precision": 1.0, "context_recall": 1.0, "cited_ids": ["a"]},
        {"answerable": False, "refused": False, "fabricated": True,
         "faithfulness": None, "hallucination_rate": None,
         "answer_relevancy": 0.0, "cited_ids": []},
    ]
    s = summarize(records)
    assert "hallucination_rate" not in s
    assert s["hallucination_rate_answerable"] == 0.0
    assert s["fabrication_rate_unanswerable"] == 1.0