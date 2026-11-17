import pytest

from ragpipe.ingest import Chunk
from ragpipe.retrieval import BM25, HybridRetriever, tokenize


class FakeClient:
    def __init__(self, query_vec):
        self.query_vec = query_vec

    def embed(self, texts):
        return [self.query_vec for _ in texts]


def make_chunks():
    return [
        Chunk(id="aaa", doc="a.md", text="the gateway retries requests on server errors", ordinal=0),
        Chunk(id="bbb", doc="b.md", text="secrets are stored in vault and encrypted at rest", ordinal=0),
        Chunk(id="ccc", doc="c.md", text="build timeout default is fifteen minutes", ordinal=0),
    ]


def make_matrix():
    # aaa close to query direction, bbb orthogonal, ccc opposite
    return [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]]


def test_tokenize_lowercases():
    assert tokenize("Hello WORLD foo_bar") == ["hello", "world", "foo_bar"]


def test_bm25_prefers_matching_doc():
    bm25 = BM25([tokenize(c.text) for c in make_chunks()])
    scores = bm25.get_scores(tokenize("vault secrets"))
    assert scores[1] > scores[0] and scores[1] > scores[2]


def test_bm25_unknown_term_zero():
    bm25 = BM25([tokenize(c.text) for c in make_chunks()])
    assert bm25.get_scores(["zzzznotaword"]) == [0.0, 0.0, 0.0]


def test_bm25_search_finds_keyword_match():
    r = HybridRetriever(make_chunks(), make_matrix())
    hits = r.search("vault secrets", mode="bm25", top_k=2)
    assert hits[0].chunk.id == "bbb"


def test_dense_finds_nearest_vector():
    r = HybridRetriever(make_chunks(), make_matrix())
    hits = r.search("anything", client=FakeClient([1.0, 0.0]), mode="dense", top_k=3)
    assert [h.chunk.id for h in hits] == ["aaa", "bbb", "ccc"]


def test_hybrid_rrf_boosts_consensus():
    r = HybridRetriever(make_chunks(), make_matrix())
    hits = r.search("gateway retries", client=FakeClient([1.0, 0.0]), mode="hybrid", top_k=3)
    assert hits[0].chunk.id == "aaa"
    assert hits[0].rank == 1
    assert hits[0].score > hits[1].score


def test_rrf_score_formula():
    r = HybridRetriever(make_chunks(), make_matrix(), rrf_k=60)
    hits = r.search("gateway retries", client=FakeClient([1.0, 0.0]), mode="hybrid", top_k=1)
    # rank 1 in both lists: 1/61 + 1/61
    assert hits[0].score == pytest.approx(2 / 61)


def test_dense_without_client_raises():
    r = HybridRetriever(make_chunks(), make_matrix())
    with pytest.raises(ValueError):
        r.search("q", mode="dense")


def test_unknown_mode_raises():
    r = HybridRetriever(make_chunks(), make_matrix())
    with pytest.raises(ValueError):
        r.search("q", mode="magic")