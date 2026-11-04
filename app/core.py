"""Pure functions (no Redis or Qdrant needed), so they are easy to test."""
import hashlib
import re


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
    """Split text by paragraph, then merge short paragraphs until max_chars is reached."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 1 > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def cache_key(question: str, top_k: int) -> str:
    """Redis key for a question. Case and extra whitespace do not change the key."""
    normalized = " ".join(question.lower().split())
    return "ask:" + hashlib.sha256(f"{normalized}|{top_k}".encode()).hexdigest()[:24]
