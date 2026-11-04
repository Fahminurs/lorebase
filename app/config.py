"""Central configuration. Every value can be overridden with an environment variable."""
import os
from pathlib import Path

COLLECTION = "lorebase"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # seconds
HF_HOME = os.getenv("HF_HOME") or None  # where the embedding model is cached

DATA_PATH = Path(
    os.getenv("KNOWLEDGE_PATH", Path(__file__).resolve().parent.parent / "data" / "knowledge.md")
)
