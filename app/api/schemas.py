"""Pydantic request / response schemas for all API endpoints."""

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    startup_id: str = Field(..., description="Unique identifier for the startup (e.g. 'alpha')")
    startup_name: str = Field(..., description="Human-readable name of the startup")
    description: str = Field(default="", description="Optional one-line description")
    data_dir: str | None = Field(
        default=None,
        description="Path to directory containing startup documents. Defaults to data/startups/<startup_id>",
    )


class IngestResponse(BaseModel):
    startup_id: str
    documents_ingested: list[dict[str, Any]]
    total_chunks: int
    metrics_extracted: int
    status: str = "success"


# ---------------------------------------------------------------------------
# Ask
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    startup_id: str = Field(..., description="Target startup ID")
    question: str = Field(..., description="Investor question")
    top_k: int = Field(default=5, ge=1, le=20)


class EvidenceItem(BaseModel):
    text: str
    source: str
    score: float
    doc_type: str


class AskResponse(BaseModel):
    startup_id: str
    question: str
    answer: str
    evidence: list[EvidenceItem]
    sources: list[str]
    metrics: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

class CompareRequest(BaseModel):
    startup_ids: list[str] = Field(..., min_length=2, description="List of startup IDs to compare")
    question: str = Field(..., description="Comparative question")
    top_k: int = Field(default=5, ge=1, le=20)


class CompareResponse(BaseModel):
    startup_ids: list[str]
    question: str
    answer: str
    startup_evidence: dict[str, Any]
    sources: dict[str, list[str]]


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

class EvaluateRequest(BaseModel):
    startup_id: str = Field(..., description="Startup to evaluate against")
    question_set: str = Field(default="default", description="Named question set to run")


class EvaluationResult(BaseModel):
    question: str
    answer: str
    retrieved_sources: list[str]
    metrics_used: list[str]
    has_evidence: bool
    grounding_score: float = Field(description="Fraction of answer words found in context (0-1)")
    hallucination_flag: bool = Field(description="True if answer contains facts not in context")
    retrieval_relevant: bool


class EvaluateResponse(BaseModel):
    startup_id: str
    total_questions: int
    avg_grounding_score: float
    retrieval_relevance_rate: float
    hallucination_rate: float
    results: list[EvaluationResult]


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

class StartupListResponse(BaseModel):
    startups: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    llm_available: bool
    embedding_model: str
