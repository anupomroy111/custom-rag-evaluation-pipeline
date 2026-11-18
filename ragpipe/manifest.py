"""Run manifests for reproducibility (V2.1 §9).

Every benchmark report carries a manifest tying results to code, data, prompts
and configuration. Secrets are never included.
"""

import hashlib
import importlib.metadata
import platform
import subprocess
import time
import uuid
from pathlib import Path

from .config import settings
from .verify.engine import EXTRACT_SYSTEM, PROMPT_VERSION, VERIFY_SYSTEM

DEPS = ["google-genai", "pydantic", "python-dotenv", "pytest"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10, cwd=settings.index_dir.parent)
        return out.stdout.strip()[:12] if out.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def prompt_hash() -> str:
    blob = "\n".join([PROMPT_VERSION, EXTRACT_SYSTEM, VERIFY_SYSTEM])
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def build_manifest(datasets: dict[str, Path], api_status: str = "not-run",
                   extra: dict | None = None) -> dict:
    manifest = {
        "run_id": uuid.uuid4().hex[:12],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "dependency_versions": {
            d: (importlib.metadata.version(d)
                if _installed(d) else "missing") for d in DEPS
        },
        "dataset_hashes": {name: _sha(p) for name, p in datasets.items() if p.exists()},
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": prompt_hash(),
        "model": settings.llm_model,
        "embed_model": settings.embed_model,
        "model_config": {"temperature": 0.0, "embed_dim": settings.embed_dim,
                         "response_mime": "application/json"},
        "random_seed": None,  # pipeline is deterministic; no sampling RNG in use
        "retrieval_config": {"chunk_size": settings.chunk_size,
                             "chunk_overlap": settings.chunk_overlap,
                             "top_k_retrieval": settings.top_k_retrieval,
                             "top_k_final": settings.top_k_final, "rrf_k": 60},
        "evaluation_config": {"llm_cache": settings.llm_cache,
                              "rpm": settings.requests_per_minute,
                              "embed_rpm": settings.embed_rpm},
        "api_status": api_status,
    }
    if extra:
        manifest.update(extra)
    return manifest


def _installed(dep: str) -> bool:
    try:
        importlib.metadata.version(dep)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False