"""
MinDD Startup Intelligence System – FastAPI entry point.

Run with:
    uvicorn main:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ask, compare, evaluate, ingest
from app.api.schemas import HealthResponse
from config import settings

# Ensure storage directories exist on startup
Path(settings.storage_dir).mkdir(exist_ok=True)
settings.indexes_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="MinDD Startup Intelligence System",
    description=(
        "Multi-tenant RAG system for startup due-diligence. "
        "Ingests pitch decks, financial models, and investor updates. "
        "Answers investor questions with grounded evidence."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(ask.router)
app.include_router(compare.router)
app.include_router(evaluate.router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health():
    return HealthResponse(
        status="ok",
        llm_available=settings.llm_available,
        embedding_model=settings.embedding_model,
    )


@app.get("/", tags=["system"])
def root():
    return {
        "message": "MinDD Startup Intelligence API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "POST /ingest": "Ingest startup documents",
            "POST /ask": "Ask a question about a startup",
            "POST /compare": "Compare multiple startups",
            "POST /evaluate": "Run evaluation suite",
            "GET /startups": "List all ingested startups",
        },
    }
