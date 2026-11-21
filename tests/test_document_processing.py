from app.document_processing import chunk_text, extract_text


def test_extract_text_normalizes_txt() -> None:
    result = extract_text("notes.txt", b"First   line\n\n\nSecond line")
    assert result == "First line\n\nSecond line"


def test_extract_text_rejects_unsupported_type() -> None:
    try:
        extract_text("image.png", b"data")
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("Expected unsupported file type to fail")


def test_chunk_text_overlaps_and_preserves_content() -> None:
    text = " ".join(f"word{i}" for i in range(200))
    chunks = chunk_text(text, chunk_size=220, overlap=40)
    assert len(chunks) > 1
    assert all(len(chunk) <= 220 for chunk in chunks)
    assert chunks[0][-20:] in chunks[1]

