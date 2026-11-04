"""API tests with fake Redis, Qdrant and embedder, so no services or model download are needed."""
import json
from types import SimpleNamespace

import pytest
import redis
from fastapi.testclient import TestClient

from app.main import app, get_cache, get_embedder, get_qdrant


class FakeVector(list):
    def tolist(self):
        return list(self)


class FakeEmbedder:
    def embed(self, texts):
        return (FakeVector([float(len(t))]) for t in texts)


class FakeQdrant:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def query_points(self, collection, query, limit):
        self.calls += 1
        if self.fail:
            raise RuntimeError("down")
        points = [SimpleNamespace(payload={"text": f"passage {i}"}, score=1 / (i + 1)) for i in range(limit)]
        return SimpleNamespace(points=points)

    def collection_exists(self, name):
        return not self.fail


class FakeCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value

    def ping(self):
        return True


class BrokenCache:
    def get(self, key):
        raise redis.ConnectionError("redis is down")

    def setex(self, key, ttl, value):
        raise redis.ConnectionError("redis is down")

    def ping(self):
        raise redis.ConnectionError("redis is down")


@pytest.fixture
def setup():
    def _make(cache=None, qdrant=None):
        app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
        app.dependency_overrides[get_cache] = lambda: cache
        app.dependency_overrides[get_qdrant] = lambda: qdrant
        return TestClient(app)  # not used as a context manager, so the startup indexing is skipped

    yield _make
    app.dependency_overrides.clear()


def test_ask_returns_top_k_results(setup):
    client = setup(FakeCache(), FakeQdrant())
    res = client.post("/ask", json={"question": "What is Qdrant?", "top_k": 2})
    assert res.status_code == 200
    body = res.json()
    assert [r["text"] for r in body["results"]] == ["passage 0", "passage 1"]
    assert body["cached"] is False


def test_second_identical_question_is_served_from_cache(setup):
    qdrant = FakeQdrant()
    client = setup(FakeCache(), qdrant)
    client.post("/ask", json={"question": "What is Redis?"})
    res = client.post("/ask", json={"question": "  what is REDIS? "})
    assert res.json()["cached"] is True
    assert qdrant.calls == 1


def test_works_without_redis(setup):
    client = setup(BrokenCache(), FakeQdrant())
    res = client.post("/ask", json={"question": "hello"})
    assert res.status_code == 200
    assert res.json()["cached"] is False


def test_rejects_empty_question_and_bad_top_k(setup):
    client = setup(FakeCache(), FakeQdrant())
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.post("/ask", json={"question": "hi", "top_k": 99}).status_code == 422


def test_qdrant_failure_returns_503(setup):
    client = setup(FakeCache(), FakeQdrant(fail=True))
    assert client.post("/ask", json={"question": "hi"}).status_code == 503


def test_health_ok_and_fails_when_store_is_down(setup):
    assert setup(FakeCache(), FakeQdrant()).get("/health").json() == {"redis": True, "qdrant": True}
    assert setup(FakeCache(), FakeQdrant(fail=True)).get("/health").status_code == 503


def test_cached_payload_is_plain_json(setup):
    cache = FakeCache()
    setup(cache, FakeQdrant()).post("/ask", json={"question": "hello"})
    stored = json.loads(next(iter(cache.data.values())))
    assert set(stored[0]) == {"text", "score"}
