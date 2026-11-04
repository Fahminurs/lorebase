from app.core import cache_key, chunk_text


def test_chunk_merges_short_paragraphs():
    text = "A one.\n\nB two.\n\nC three."
    assert chunk_text(text, max_chars=400) == ["A one.\nB two.\nC three."]


def test_chunk_splits_when_over_limit():
    text = ("x" * 30) + "\n\n" + ("y" * 30)
    assert chunk_text(text, max_chars=40) == ["x" * 30, "y" * 30]


def test_chunk_empty_text():
    assert chunk_text("  \n\n ") == []


def test_cache_key_ignores_case_and_spaces():
    assert cache_key("What  is Qdrant?", 3) == cache_key("what is qdrant?", 3)


def test_cache_key_differs_by_top_k():
    assert cache_key("hello", 3) != cache_key("hello", 5)
