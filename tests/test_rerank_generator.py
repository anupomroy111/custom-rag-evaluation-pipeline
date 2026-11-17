from ragpipe.generator import generate_answer
from ragpipe.ingest import Chunk
from ragpipe.rerank import llm_rerank
from ragpipe.retrieval import RetrievedChunk


def make_candidates():
    return [
        RetrievedChunk(Chunk(id="aaa", doc="a.md", text="gateway info", ordinal=0), score=0.03, rank=1),
        RetrievedChunk(Chunk(id="bbb", doc="b.md", text="vault secrets", ordinal=0), score=0.02, rank=2),
        RetrievedChunk(Chunk(id="ccc", doc="c.md", text="unrelated filler", ordinal=0), score=0.01, rank=3),
    ]


class RerankFakeClient:
    def generate_json(self, prompt, system=None, temperature=0.0):
        return [
            {"id": "aaa", "relevance": 1},
            {"id": "bbb", "relevance": 3},
            {"id": "ccc", "relevance": 0},
        ]


def test_rerank_reorders_by_relevance():
    kept, grades = llm_rerank("where are secrets?", make_candidates(), RerankFakeClient(), top_k=2)
    assert [c.chunk.id for c in kept] == ["bbb", "aaa"]
    assert grades == {"aaa": 1, "bbb": 3, "ccc": 0}
    assert kept[0].rank == 1


def test_rerank_clamps_grades():
    class BadGrades:
        def generate_json(self, prompt, system=None, temperature=0.0):
            return [{"id": "aaa", "relevance": 99}, {"id": "bbb", "relevance": -5}]

    kept, grades = llm_rerank("q", make_candidates(), BadGrades(), top_k=3)
    assert grades["aaa"] == 3
    assert grades["bbb"] == 0


def test_rerank_empty_candidates():
    kept, grades = llm_rerank("q", [], RerankFakeClient())
    assert kept == [] and grades == {}


class AnswerFakeClient:
    def __init__(self, text):
        self.text = text

    def generate(self, prompt, system=None, json_mode=False, temperature=0.0, max_retries=5):
        return self.text


def test_answer_citations_filtered_to_valid_ids():
    text = "Secrets live in vault [id:bbb]. Also see [id:zzz] and [id: aaa]."
    answer = generate_answer("q", make_candidates(), AnswerFakeClient(text))
    assert answer.cited_ids == ["bbb", "aaa"]
    assert not answer.refused


def test_citation_formats_multi_and_bare():
    from ragpipe.generator import extract_citations

    valid = {"aaa", "bbb"}
    text = ("Fact one [id: aaa, id: bbb]. Fact two [aaa]. "
            "Fact three [bbb, aaa]. Ignored [zzz] and [id: ccc].")
    assert extract_citations(text, valid) == ["aaa", "bbb"]


def test_refusal_detected():
    text = "I cannot answer this from the provided documents."
    answer = generate_answer("q", make_candidates(), AnswerFakeClient(text))
    assert answer.refused
    assert answer.cited_ids == []