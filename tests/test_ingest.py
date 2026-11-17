from ragpipe.ingest import Chunk, chunk_documents, split_text


def test_short_text_single_chunk():
    assert split_text("hello world", 100, 20) == ["hello world"]


def test_empty_text():
    assert split_text("   ", 100, 20) == []


def test_chunks_respect_size():
    text = "\n\n".join(f"Paragraph number {i} with some words to give it length." for i in range(60))
    chunks = split_text(text, 300, 50)
    assert len(chunks) > 1
    assert all(len(c) <= 352 for c in chunks)


def test_long_sentence_hard_split():
    text = "x" * 1000
    chunks = split_text(text, 300, 50)
    assert len(chunks) >= 3
    # merged chunks may carry up to `overlap` chars of tail context
    assert all(len(c) <= 300 + 50 + 2 for c in chunks)


def test_chunk_ids_stable_and_unique():
    docs = {"a.md": "Some content here.\n\nAnother paragraph."}
    first = chunk_documents(docs)
    second = chunk_documents(docs)
    assert [c.id for c in first] == [c.id for c in second]
    assert len({c.id for c in first}) == len(first)


def test_chunk_ordinals_per_doc():
    docs = {"a.md": "para one\n\npara two\n\npara three"}
    chunks = chunk_documents(docs)
    assert all(isinstance(c, Chunk) for c in chunks)
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))