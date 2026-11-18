import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # google-genai falls back to the httpx2 fork on some hosts
    import httpx2 as httpx
from google import genai
from google.genai import errors, types

from .config import settings


class EmptyResponseError(RuntimeError):
    """Model returned no text (e.g. safety block). Never treated as a valid answer."""


class GeminiClient:
    """Gemini wrapper with pacing, retries, timeouts, usage accounting and a
    disk response cache. Cache hits make benchmark re-runs quota-free."""

    def __init__(self, api_key: str | None = None, rpm: int | None = None,
                 cache_dir: Path | None = None, use_cache: bool | None = None,
                 model: str | None = None):
        key = api_key or settings.api_key
        if not key or key == "your_api_key_here":
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
                "(free key at https://aistudio.google.com/apikey)."
            )
        self.model = model or settings.llm_model
        self._client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(api_version="v1beta", timeout=120_000),
        )
        self._min_interval = 60.0 / (rpm or settings.requests_per_minute)
        self._embed_interval = 60.0 / settings.embed_rpm
        self._last_call = 0.0
        self._last_embed = 0.0
        self.use_cache = settings.llm_cache if use_cache is None else use_cache
        self.cache_dir = cache_dir or settings.index_dir / "llm_cache"
        self.stats = {
            "generate_requests": 0, "embed_requests": 0, "cache_hits": 0,
            "prompt_tokens": 0, "output_tokens": 0, "latency_s": 0.0,
            "retries": 0, "errors": 0,
        }

    def _pace(self, embed: bool = False) -> None:
        interval = self._embed_interval if embed else self._min_interval
        last = self._last_embed if embed else self._last_call
        wait = interval - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        if embed:
            self._last_embed = time.monotonic()
        else:
            self._last_call = time.monotonic()

    def _cache_path(self, prompt: str, system: str | None, json_mode: bool,
                    temperature: float) -> Path:
        key = hashlib.sha256(json.dumps({
            "model": self.model, "prompt": prompt, "system": system,
            "json": json_mode, "temp": temperature,
        }, ensure_ascii=False).encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False,
                 temperature: float = 0.0, max_retries: int = 5) -> str:
        cache_path = self._cache_path(prompt, system, json_mode, temperature)
        if self.use_cache and cache_path.exists():
            self.stats["cache_hits"] += 1
            return json.loads(cache_path.read_text(encoding="utf-8"))["text"]

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        for attempt in range(max_retries):
            self._pace()
            started = time.monotonic()
            try:
                resp = self._client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
            except errors.APIError as e:
                self.stats["errors"] += 1
                if e.code not in (429, 500, 503) or attempt == max_retries - 1:
                    raise
                self.stats["retries"] += 1
                time.sleep(min(2 ** attempt * 5, 60))
                continue
            except (httpx.TimeoutException, httpx.TransportError):
                self.stats["errors"] += 1
                if attempt == max_retries - 1:
                    raise
                self.stats["retries"] += 1
                time.sleep(min(2 ** attempt * 5, 60))
                continue

            self.stats["generate_requests"] += 1
            self.stats["latency_s"] += time.monotonic() - started
            usage = getattr(resp, "usage_metadata", None)
            if usage is not None:
                self.stats["prompt_tokens"] += getattr(usage, "prompt_token_count", 0) or 0
                self.stats["output_tokens"] += getattr(usage, "candidates_token_count", 0) or 0
            text = resp.text
            if text is None or not text.strip():
                raise EmptyResponseError(
                    "Model returned empty text (possible safety block); "
                    "refusing to treat it as a valid response."
                )
            if self.use_cache:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps({"text": text}, ensure_ascii=False),
                                      encoding="utf-8")
            return text
        raise RuntimeError("unreachable")

    def generate_json(self, prompt: str, system: str | None = None,
                      temperature: float = 0.0) -> Any:
        text = self.generate(prompt, system=system, json_mode=True,
                             temperature=temperature)
        return parse_json(text)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), settings.embed_batch_size):
            batch = texts[i:i + settings.embed_batch_size]
            for attempt in range(5):
                self._pace(embed=True)
                try:
                    resp = self._client.models.embed_content(
                        model=settings.embed_model,
                        contents=batch,
                        config=types.EmbedContentConfig(
                            output_dimensionality=settings.embed_dim
                        ),
                    )
                except errors.APIError as e:
                    self.stats["errors"] += 1
                    if e.code not in (429, 500, 503) or attempt == 4:
                        raise
                    self.stats["retries"] += 1
                    time.sleep(min(2 ** attempt * 5, 60))
                    continue
                except (httpx.TimeoutException, httpx.TransportError):
                    self.stats["errors"] += 1
                    if attempt == 4:
                        raise
                    self.stats["retries"] += 1
                    time.sleep(min(2 ** attempt * 5, 60))
                    continue
                self.stats["embed_requests"] += 1
                values = [list(e.values) for e in resp.embeddings]
                for vec in values:
                    if len(vec) != settings.embed_dim:
                        raise ValueError(
                            f"Embedding dimension {len(vec)} != configured {settings.embed_dim}"
                        )
                vectors.extend(values)
                break
        return vectors


def parse_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if 0 <= start < end:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Model did not return valid JSON: {text[:200]!r}")