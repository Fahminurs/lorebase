"""Load the knowledge base into Qdrant: split -> embed -> store."""
from pathlib import Path

from qdrant_client.models import Distance, PointStruct, VectorParams

from app import config
from app.core import chunk_text


def ingest(client, embedder, path: Path = config.DATA_PATH) -> int:
    """(Re)build the collection from a text file and return how many chunks were stored."""
    chunks = chunk_text(Path(path).read_text(encoding="utf-8"))
    if not chunks:
        raise ValueError(f"{path} has no text to index")
    vectors = [v.tolist() for v in embedder.embed(chunks)]
    if client.collection_exists(config.COLLECTION):
        client.delete_collection(config.COLLECTION)
    client.create_collection(
        config.COLLECTION,
        vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
    )
    client.upsert(
        config.COLLECTION,
        [PointStruct(id=i, vector=v, payload={"text": t}) for i, (t, v) in enumerate(zip(chunks, vectors))],
    )
    return len(chunks)


def main() -> None:
    from app.main import get_embedder, get_qdrant

    print(f"{ingest(get_qdrant(), get_embedder())} chunks stored in Qdrant")


if __name__ == "__main__":
    main()
