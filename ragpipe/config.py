import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class Settings:
    api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.environ.get("RAG_LLM_MODEL", "gemini-3.5-flash-lite"))
    embed_model: str = field(default_factory=lambda: os.environ.get("RAG_EMBED_MODEL", "gemini-embedding-001"))
    embed_dim: int = field(default_factory=lambda: int(os.environ.get("RAG_EMBED_DIM", "768")))
    requests_per_minute: int = field(default_factory=lambda: int(os.environ.get("RAG_RPM", "10")))
    embed_rpm: int = field(default_factory=lambda: int(os.environ.get("RAG_EMBED_RPM", "100")))
    llm_cache: bool = field(default_factory=lambda: os.environ.get("RAG_LLM_CACHE", "1") != "0")

    docs_dir: Path = PROJECT_ROOT / "data" / "docs"
    index_dir: Path = PROJECT_ROOT / "index"
    golden_path: Path = PROJECT_ROOT / "data" / "original" / "golden_dataset.json"
    reports_dir: Path = PROJECT_ROOT / "reports"

    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k_retrieval: int = 10
    top_k_final: int = 4
    embed_batch_size: int = 32


settings = Settings()