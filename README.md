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
- GitHub Actions tests the app and publishes verified Docker images to Amazon ECR

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
docker build -t lumen-rag:local .
docker run -d --name lumen-rag -p 127.0.0.1:8000:8000 --env-file .env --mount type=volume,src=rag-data,dst=/app/data lumen-rag:local
```

Open http://127.0.0.1:8000 and check readiness with `Invoke-RestMethod http://127.0.0.1:8000/api/health`. The FAISS index and chunk metadata persist in the `rag-data` Docker volume. Use `docker stop lumen-rag` and `docker start lumen-rag` for subsequent sessions.

## Publish to Amazon ECR

Pull requests targeting `main` run pytest, Gitleaks, OWASP Dependency-Check, build the Docker image, and scan it with Trivy. Pushes to `main` also publish the image to private ECR with the full commit SHA as its tag. A failed test, detected secret, or high or critical vulnerability stops publication.

Configure once before the first push to `main`:

1. In Amazon ECR, create a private repository in your chosen region (for example, `lumen-rag`).
2. Create an AWS IAM access key with permission to push images to that ECR repository.
3. In GitHub, open **Settings → Secrets and variables → Actions**.

Add these repository secrets:

| Secret | Value |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | IAM access key ID |
| `AWS_SECRET_ACCESS_KEY` | IAM secret access key |

Add these repository variables:

| Variable | Value |
| --- | --- |
| `AWS_REGION` | Region containing your ECR repository |
| `ECR_REPOSITORY` | ECR repository name, including any path prefix |

Gitleaks requires a `GITLEAKS_LICENSE` secret only when the repository belongs to a GitHub organization.

After pushing to `main`, open the **Actions** run summary for the published image URI.

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
