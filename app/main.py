from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.document_processing import chunk_text, extract_text
from app.models import ChatRequest, ChatResponse, DocumentInfo
from app.rag_service import RagService


settings = get_settings()
rag = RagService(settings)
static_dir = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Lumen RAG",
    description="A simple single-document retrieval-augmented generation application.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {
        "ok": True,
        "openai_configured": bool(settings.openai_api_key),
        "document_ready": rag.get_document() is not None,
    }


@app.get("/api/document", response_model=DocumentInfo | None)
def get_document() -> DocumentInfo | None:
    return rag.get_document()


@app.post("/api/document", response_model=DocumentInfo, status_code=201)
async def upload_document(file: UploadFile = File(...)) -> DocumentInfo:
    filename = Path(file.filename or "document").name
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_mb} MB limit.")
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")

    try:
        text = extract_text(filename, content)
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise ValueError("The document did not produce any searchable text.")
        return rag.replace_document(filename, len(content), chunks)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Document processing failed: {exc}") from exc


@app.delete("/api/document", status_code=204)
def delete_document() -> None:
    rag.delete_document()


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return ChatResponse(answer=rag.answer(request.question.strip(), request.history))
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Answer generation failed: {exc}") from exc


app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")

