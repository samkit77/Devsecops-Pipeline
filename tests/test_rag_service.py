import numpy as np

from app.config import Settings
from app.rag_service import RagService


def test_faiss_index_persists_retrieves_and_deletes(tmp_path, monkeypatch) -> None:
    service = RagService(Settings(data_dir=tmp_path))
    vectors = {
        "security controls": [1.0, 0.0, 0.0],
        "release checklist": [0.0, 1.0, 0.0],
        "security question": [0.9, 0.1, 0.0],
    }

    def fake_embed(texts: list[str]) -> np.ndarray:
        result = np.asarray([vectors[text] for text in texts], dtype="float32")
        norms = np.linalg.norm(result, axis=1, keepdims=True)
        return result / norms

    monkeypatch.setattr(service, "_embed", fake_embed)
    document = service.replace_document(
        "guide.txt",
        128,
        ["security controls", "release checklist"],
    )

    assert document.chunk_count == 2
    assert service.retrieve("security question")[0] == "security controls"

    reloaded = RagService(Settings(data_dir=tmp_path))
    assert reloaded.get_document() is not None
    assert reloaded.get_document().name == "guide.txt"

    reloaded.delete_document()
    assert reloaded.get_document() is None
    assert not (tmp_path / "index.faiss").exists()
    assert not (tmp_path / "store.json").exists()
