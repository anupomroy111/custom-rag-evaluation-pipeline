import json
import re
import time
from typing import Any

from google import genai
from google.genai import errors, types

from .config import settings


class GeminiClient:
    """Thin wrapper over google-genai with pacing, retries and JSON helpers."""

    def __init__(self, api_key: str | None = None, rpm: int | None = None):
        key = api_key or settings.api_key
        if not key or key == "your_api_key_here":
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
                "(free key at https://aistudio.google.com/apikey)."
            )
        self._client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(api_version="v1beta"),
        )
        self._min_interval = 60.0 / (rpm or settings.requests_per_minute)
        self._last_call = 0.0

    def _pace(self) -> None:
        wait = self._min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False,
                 temperature: float = 0.0, max_retries: int = 5) -> str:
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        for attempt in range(max_retries):
            self._pace()
            try:
                resp = self._client.models.generate_content(
                    model=settings.llm_model, contents=prompt, config=config
                )
                return resp.text or ""
            except errors.APIError as e:
                retryable = e.code in (429, 500, 503)
                if not retryable or attempt == max_retries - 1:
                    raise
                time.sleep(min(2 ** attempt * 5, 60))
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
                self._pace()
                try:
                    resp = self._client.models.embed_content(
                        model=settings.embed_model,
                        contents=batch,
                        config=types.EmbedContentConfig(
                            output_dimensionality=settings.embed_dim
                        ),
                    )
                    vectors.extend([e.values for e in resp.embeddings])
                    break
                except errors.APIError as e:
                    if e.code not in (429, 500, 503) or attempt == 4:
                        raise
                    time.sleep(min(2 ** attempt * 5, 60))
        return vectors


def parse_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Model did not return valid JSON: {text[:200]!r}")