from fastapi.testclient import TestClient

from app.main import app, rag


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_home_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Lumen RAG" in response.text


def test_upload_rejects_unsupported_file() -> None:
    response = client.post("/api/document", files={"file": ("photo.jpg", b"fake", "image/jpeg")})
    assert response.status_code == 400


def test_chat_requires_document(monkeypatch) -> None:
    monkeypatch.setattr(rag, "_index", None)
    monkeypatch.setattr(rag, "_chunks", [])
    response = client.post("/api/chat", json={"question": "What is this?"})
    assert response.status_code == 409

