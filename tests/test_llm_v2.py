"""LLM wrapper reliability tests: empty responses, retries, cache, stats, dims."""

import pytest

try:
    import httpx
except ImportError:
    import httpx2 as httpx

from ragpipe.llm import EmptyResponseError, GeminiClient, parse_json


class Resp:
    def __init__(self, text, tokens=(10, 5)):
        self.text = text
        self.usage_metadata = type("U", (), {
            "prompt_token_count": tokens[0], "candidates_token_count": tokens[1]})()


class EmbedResp:
    def __init__(self, vectors):
        self.embeddings = [type("E", (), {"values": v})() for v in vectors]


class StubModels:
    def __init__(self, behavior):
        self.behavior = behavior
        self.generate_calls = 0
        self.embed_calls = 0

    def generate_content(self, model, contents, config):
        self.generate_calls += 1
        return self.behavior(self.generate_calls)

    def embed_content(self, model, contents, config):
        self.embed_calls += 1
        return EmbedResp([[0.1] * 768 for _ in contents])


def make_client(tmp_path, behavior):
    client = GeminiClient(api_key="test-key", cache_dir=tmp_path / "cache")
    client._client = type("C", (), {})()
    client._client.models = StubModels(behavior)
    client._min_interval = 0.0
    client._embed_interval = 0.0
    return client


def test_empty_response_raises_not_silent(tmp_path):
    client = make_client(tmp_path, lambda n: Resp(None))
    with pytest.raises(EmptyResponseError):
        client.generate("q")


def test_whitespace_response_raises(tmp_path):
    client = make_client(tmp_path, lambda n: Resp("   "))
    with pytest.raises(EmptyResponseError):
        client.generate("q")


def test_transport_timeout_retried_then_succeeds(tmp_path):
    def behavior(n):
        if n == 1:
            raise httpx.TimeoutException("slow")
        return Resp("ok")

    client = make_client(tmp_path, behavior)
    assert client.generate("q") == "ok"
    assert client.stats["retries"] == 1
    assert client.stats["generate_requests"] == 1


def test_transport_failure_exhausts_retries(tmp_path):
    def behavior(n):
        raise httpx.ConnectError("down")

    client = make_client(tmp_path, behavior)
    with pytest.raises(httpx.ConnectError):
        client.generate("q", max_retries=2)
    assert client.stats["retries"] == 1


def test_cache_hit_avoids_second_request(tmp_path):
    client = make_client(tmp_path, lambda n: Resp("cached answer"))
    assert client.generate("same prompt") == "cached answer"
    assert client.generate("same prompt") == "cached answer"
    assert client.stats["generate_requests"] == 1
    assert client.stats["cache_hits"] == 1


def test_cache_disabled_always_requests(tmp_path):
    client = make_client(tmp_path, lambda n: Resp("answer"))
    client.use_cache = False
    client.generate("p")
    client.generate("p")
    assert client.stats["generate_requests"] == 2
    assert client.stats["cache_hits"] == 0


def test_usage_stats_accounted(tmp_path):
    client = make_client(tmp_path, lambda n: Resp("x", tokens=(100, 20)))
    client.generate("p")
    assert client.stats["prompt_tokens"] == 100
    assert client.stats["output_tokens"] == 20
    assert client.stats["latency_s"] >= 0


def test_embed_dimension_mismatch_raises(tmp_path):
    client = make_client(tmp_path, lambda n: Resp("x"))
    client._client.models.embed_content = lambda **kw: EmbedResp([[0.1, 0.2]])
    with pytest.raises(ValueError):
        client.embed(["text"])


def test_embed_ok_and_counted(tmp_path):
    client = make_client(tmp_path, lambda n: Resp("x"))
    vectors = client.embed(["a", "b"])
    assert len(vectors) == 2 and len(vectors[0]) == 768
    assert client.stats["embed_requests"] == 1


def test_parse_json_prefers_whole_then_braces():
    assert parse_json('prose {"a": 1} tail') == {"a": 1}
    assert parse_json('[1, 2]') == [1, 2]
    with pytest.raises(ValueError):
        parse_json("nothing here")