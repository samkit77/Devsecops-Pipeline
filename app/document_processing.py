import io
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Upload a PDF, DOCX, or TXT file.")

    if extension == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif extension == ".docx":
        document = Document(io.BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8-sig")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise ValueError("No readable text was found in this document.")
    return text


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text at natural boundaries while preserving a character overlap."""
    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        target_end = min(start + chunk_size, text_length)
        end = target_end

        if target_end < text_length:
            search_from = start + max(chunk_size // 2, 1)
            candidates = [
                text.rfind("\n\n", search_from, target_end),
                text.rfind(". ", search_from, target_end),
                text.rfind(" ", search_from, target_end),
            ]
            boundary = max(candidates)
            if boundary > start:
                end = boundary + (1 if text[boundary] == " " else 0)

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = max(end - overlap, start + 1)

    return chunks

