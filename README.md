# Lumen RAG

A focused, single-document Retrieval-Augmented Generation web application built with FastAPI, OpenAI, and a local FAISS index.

## Features

- Upload one PDF, DOCX, or TXT document (20 MB maximum)
- Extract and chunk text with configurable overlap
- Generate OpenAI embeddings and store them in local FAISS
- Retrieve relevant passages with cosine similarity
- Ask conversational questions grounded in the uploaded document
- View or delete the active document and its index
- Responsive, dependency-free browser interface
- Docker baseline ready for later CI/CD and DevSecOps work

Uploading a new document replaces the current document. This intentionally keeps the first version within the single-document scope.

## Run locally

Requires Python 3.11+ and an OpenAI API key.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` in `.env`, then start the app:

```powershell
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Interactive API documentation is available at http://127.0.0.1:8000/docs.

## Run with Docker

Create `.env` from `.env.example`, add the API key, then run:

```powershell
docker compose up --build
```

The FAISS index is persisted in the `rag-data` Docker volume.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | required | OpenAI API authentication |
| `OPENAI_CHAT_MODEL` | `gpt-4.1-mini` | Answer generation model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `CHUNK_SIZE` | `1000` | Approximate chunk size in characters |
| `CHUNK_OVERLAP` | `200` | Character overlap between chunks |
| `TOP_K` | `4` | Retrieved chunks per question |
| `MAX_UPLOAD_MB` | `20` | Maximum upload size |

Changing embedding models after indexing requires uploading the document again.

## Test

```powershell
pip install -r requirements-dev.txt
pytest
ruff check app tests
```

## Project structure

```text
app/
  main.py                 FastAPI routes and static UI hosting
  document_processing.py Text extraction and chunking
  rag_service.py          OpenAI, FAISS, retrieval, and generation
  static/                 Browser interface
data/                     Local FAISS index and metadata (gitignored)
tests/                    Unit and API smoke tests
```

## Current boundaries

This baseline intentionally omits authentication, multi-document collections, source citations, advanced retrieval, evaluation, monitoring, and deployment automation. Those can be introduced as later DevSecOps increments without rewriting the core service boundaries.
