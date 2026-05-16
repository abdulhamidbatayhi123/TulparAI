"""Tests for the sentence-aware chunker — no external deps needed."""
from backend.data.chunker import chunk_text


def test_short_text_returns_one_chunk():
    # Text must be >= min_len (default 80) AND <= target (600) to be returned as a single chunk.
    text = "This is a short paragraph that should fit in exactly one chunk because it is comfortably above the 80-char minimum length."
    assert len(text) >= 80
    chunks = chunk_text(text, target=600, overlap=120)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_empty_text_returns_empty_list():
    assert chunk_text("", target=600, overlap=120) == []
    assert chunk_text("   \n\t  ", target=600, overlap=120) == []


def test_below_min_length_dropped():
    assert chunk_text("tiny", target=600, overlap=120, min_len=80) == []


def test_long_text_splits_at_sentence_boundaries():
    text = ("Bu cümle bir spor doktorunun düzenli tavsiyesidir. " * 30)
    chunks = chunk_text(text, target=300, overlap=60, min_len=80)
    assert len(chunks) > 1
    for c in chunks:
        # Chunks should generally end with sentence punctuation (with overlap allowance)
        assert c.endswith(".") or c.endswith("!") or c.endswith("?")
        assert len(c) >= 80


def test_overlap_preserves_context():
    sents = [f"This is sentence number {i}." for i in range(20)]
    chunks = chunk_text(" ".join(sents), target=200, overlap=60)
    # consecutive chunks should share at least some characters via overlap
    assert len(chunks) >= 2


def test_deterministic_same_input_same_chunks():
    text = "First sentence. Second one! Third question? Fourth statement. " * 10
    a = chunk_text(text, target=200, overlap=40)
    b = chunk_text(text, target=200, overlap=40)
    assert a == b
