import json
import threading
from datetime import datetime, timezone
from typing import Any

import faiss
import numpy as np
from openai import OpenAI

from app.config import Settings
from app.models import ChatMessage, DocumentInfo


SYSTEM_PROMPT = """You are a concise document assistant. Answer only from the supplied document context.
If the context does not contain the answer, say: "I couldn't find that in the document."
Do not invent details or use outside knowledge. Use short paragraphs and bullets when useful."""


class RagService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.data_dir = settings.data_dir
        self.index_path = self.data_dir / "index.faiss"
        self.store_path = self.data_dir / "store.json"
        self._lock = threading.RLock()
        self._index: faiss.Index | None = None
        self._chunks: list[str] = []
        self._document: DocumentInfo | None = None
        self._client: OpenAI | None = None
        self._load()

    @property
    def client(self) -> OpenAI:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        if self._client is None:
            self._client = OpenAI(api_key=self.settings.openai_api_key)
        return self._client

    def _load(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists() or not self.store_path.exists():
            return
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
            self._index = faiss.read_index(str(self.index_path))
            self._chunks = payload["chunks"]
            self._document = DocumentInfo.model_validate(payload["document"])
            if self._index.ntotal != len(self._chunks):
                raise ValueError("Index and chunk metadata are out of sync")
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            self._index = None
            self._chunks = []
            self._document = None

    def get_document(self) -> DocumentInfo | None:
        return self._document

    def _embed(self, texts: list[str]) -> np.ndarray:
        response = self.client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=texts,
        )
        vectors = np.asarray([item.embedding for item in response.data], dtype="float32")
        faiss.normalize_L2(vectors)
        return vectors

    def replace_document(self, name: str, size: int, chunks: list[str]) -> DocumentInfo:
        vectors = self._embed(chunks)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        document = DocumentInfo(
            name=name,
            size=size,
            chunk_count=len(chunks),
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )

        with self._lock:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            temporary_index = self.data_dir / "index.faiss.tmp"
            temporary_store = self.data_dir / "store.json.tmp"
            faiss.write_index(index, str(temporary_index))
            temporary_store.write_text(
                json.dumps({"document": document.model_dump(), "chunks": chunks}),
                encoding="utf-8",
            )
            temporary_index.replace(self.index_path)
            temporary_store.replace(self.store_path)
            self._index = index
            self._chunks = chunks
            self._document = document
        return document

    def delete_document(self) -> None:
        with self._lock:
            self._index = None
            self._chunks = []
            self._document = None
            for path in (self.index_path, self.store_path):
                path.unlink(missing_ok=True)

    def retrieve(self, question: str) -> list[str]:
        if self._index is None or not self._chunks:
            raise LookupError("Upload a document before asking questions.")
        query = self._embed([question])
        count = min(self.settings.top_k, len(self._chunks))
        _, indices = self._index.search(query, count)
        return [self._chunks[index] for index in indices[0] if index >= 0]

    def answer(self, question: str, history: list[ChatMessage]) -> str:
        contexts = self.retrieve(question)
        context_text = "\n\n---\n\n".join(contexts)
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(
            {"role": message.role, "content": message.content}
            for message in history[-8:]
        )
        messages.append(
            {
                "role": "user",
                "content": f"Document context:\n{context_text}\n\nQuestion: {question}",
            }
        )
        response = self.client.chat.completions.create(
            model=self.settings.openai_chat_model,
            messages=messages,
            temperature=0.1,
        )
        return response.choices[0].message.content or "I couldn't find that in the document."

