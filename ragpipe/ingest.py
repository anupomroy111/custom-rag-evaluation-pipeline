import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import settings

SUPPORTED_SUFFIXES = {".md", ".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".rst"}


@dataclass
class Chunk:
    id: str
    doc: str
    text: str
    ordinal: int


def load_documents(docs_dir: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for path in sorted(docs_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            rel = path.relative_to(docs_dir).as_posix()
            docs[rel] = path.read_text(encoding="utf-8", errors="replace")
    if not docs:
        raise FileNotFoundError(f"No supported documents found in {docs_dir}")
    return docs


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Recursive-style splitting: prefer paragraph, then sentence, then hard cuts."""
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    pieces: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= chunk_size:
            pieces.append(para)
        else:
            sentences = re.split(r"(?<=[.!?।])\s+", para)
            buf = ""
            for sent in sentences:
                if len(sent) > chunk_size:
                    if buf:
                        pieces.append(buf)
                        buf = ""
                    for i in range(0, len(sent), chunk_size - overlap):
                        pieces.append(sent[i:i + chunk_size])
                elif len(buf) + len(sent) + 1 <= chunk_size:
                    buf = f"{buf} {sent}".strip()
                else:
                    if buf:
                        pieces.append(buf)
                    buf = sent
            if buf:
                pieces.append(buf)

    chunks: list[str] = []
    buf = ""
    for piece in pieces:
        if buf and len(buf) + len(piece) + 2 > chunk_size:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap else ""
            buf = (tail + "\n\n" + piece).strip() if tail else piece
        else:
            buf = f"{buf}\n\n{piece}".strip()
    if buf:
        chunks.append(buf)
    return chunks


def chunk_documents(docs: dict[str, str]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc_name, text in docs.items():
        for i, piece in enumerate(split_text(text, settings.chunk_size, settings.chunk_overlap)):
            digest = hashlib.sha1(f"{doc_name}:{i}:{piece}".encode()).hexdigest()[:12]
            chunks.append(Chunk(id=digest, doc=doc_name, text=piece, ordinal=i))
    return chunks


def save_chunks(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(c) for c in chunks], ensure_ascii=False, indent=2),
                    encoding="utf-8")


def load_chunks(path: Path) -> list[Chunk]:
    return [Chunk(**item) for item in json.loads(path.read_text(encoding="utf-8"))]