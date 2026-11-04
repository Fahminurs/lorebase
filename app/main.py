"""Lorebase API: question -> embedding -> Qdrant search -> Redis cache."""
import json
import logging
import time
from contextlib import asynccontextmanager
from functools import lru_cache

import redis
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from app import config
from app.core import cache_key
from app.ingest import ingest

log = logging.getLogger("lorebase")


@lru_cache
def get_embedder():
    from fastembed import TextEmbedding  # imported lazily: heavy, and not needed by the tests

    return TextEmbedding(config.MODEL, cache_dir=config.HF_HOME)


@lru_cache
def get_qdrant() -> QdrantClient:
    return QdrantClient(url=config.QDRANT_URL)


@lru_cache
def get_cache() -> redis.Redis:
    return redis.Redis.from_url(config.REDIS_URL, decode_responses=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the index on first start, so `docker compose up` works without extra steps."""
    client = get_qdrant()
    for _ in range(30):
        try:
            if not client.collection_exists(config.COLLECTION):
                log.info("Indexing %s chunks", ingest(client, get_embedder()))
            break
        except Exception as exc:  # Qdrant may still be starting
            log.warning("Waiting for Qdrant: %s", exc)
            time.sleep(2)
    yield


app = FastAPI(title="Lorebase", description="Semantic search over a knowledge base (the retrieval step of RAG).", lifespan=lifespan)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)


class Hit(BaseModel):
    text: str
    score: float


class Answer(BaseModel):
    results: list[Hit]
    cached: bool
    elapsed_ms: float


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


@app.get("/health")
def health(cache=Depends(get_cache), qdrant=Depends(get_qdrant)):
    status = {"redis": False, "qdrant": False}
    try:
        status["redis"] = bool(cache.ping())
    except redis.RedisError:
        pass
    try:
        status["qdrant"] = bool(qdrant.collection_exists(config.COLLECTION))
    except Exception:
        pass
    if not status["qdrant"]:
        raise HTTPException(status_code=503, detail=status)
    return status  # Redis being down only disables caching, so it does not fail the check


@app.post("/ask", response_model=Answer)
def ask(body: Question, cache=Depends(get_cache), qdrant=Depends(get_qdrant), embedder=Depends(get_embedder)):
    started = time.perf_counter()
    key = cache_key(body.question, body.top_k)

    try:
        hit = cache.get(key)
    except redis.RedisError:
        hit = None  # cache is optional: fall through to Qdrant
    if hit:
        return Answer(results=json.loads(hit), cached=True, elapsed_ms=_elapsed_ms(started))

    vector = next(iter(embedder.embed([body.question]))).tolist()
    try:
        points = qdrant.query_points(config.COLLECTION, query=vector, limit=body.top_k).points
    except Exception as exc:
        log.error("Qdrant query failed: %s", exc)
        raise HTTPException(status_code=503, detail="vector store unavailable")

    results = [{"text": p.payload["text"], "score": round(p.score, 3)} for p in points]
    try:
        cache.setex(key, config.CACHE_TTL, json.dumps(results))
    except redis.RedisError:
        pass
    return Answer(results=results, cached=False, elapsed_ms=_elapsed_ms(started))
