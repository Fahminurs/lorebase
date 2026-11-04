# Lorebase sample knowledge base

FastAPI is a modern Python web framework for building APIs. It uses type hints and Pydantic to validate every request, supports async code, and generates interactive API documentation automatically at the /docs page.

Qdrant is a vector database. It stores embeddings, which are lists of numbers that represent the meaning of a text, and finds the stored vectors closest to a query vector using a similarity measure such as cosine similarity. It is used for semantic search instead of exact keyword matching.

Redis is an in-memory key-value store. It is commonly used as a cache: a result that was already computed is saved under a key with a time-to-live (TTL), so the next identical request is answered much faster without repeating the work.

Docker packages an application together with its dependencies into a container, so it runs the same way on every machine. Docker Compose describes several containers, such as an API, a Redis cache and a Qdrant database, in one file and starts them with a single command.

Retrieval-Augmented Generation (RAG) first retrieves the passages most relevant to a question and then gives them to a large language model, so the answer is grounded in your own documents. Lorebase implements the retrieval step: it returns the best matching passages together with a similarity score.

Embeddings come from a multilingual sentence-transformer model that runs locally through fastembed, so no paid API is needed. Because the model is multilingual, Lorebase can also answer questions written in Indonesian, for example "Apa fungsi Redis?".

Quality is checked with pytest, and GitHub Actions runs the test suite automatically on every push and pull request.
