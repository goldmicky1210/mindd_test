from fastapi import APIRouter, HTTPException
from app.api.schemas import AskRequest, AskResponse, StartupListResponse
from app.reasoning.qa_chain import answer_question
from app.storage.metadata_store import metadata_store

router = APIRouter(tags=["query"])


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """Answer an investor question about a specific startup."""
    startup = metadata_store.get_startup(req.startup_id)
    if not startup:
        raise HTTPException(
            status_code=404,
            detail=f"Startup '{req.startup_id}' not found. Please ingest documents first.",
        )

    try:
        result = answer_question(
            startup_id=req.startup_id,
            question=req.question,
            top_k=req.top_k,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}")

    return AskResponse(
        startup_id=result["startup_id"],
        question=req.question,
        answer=result["answer"],
        evidence=result["evidence"],
        sources=result["sources"],
        metrics=result["metrics"],
    )


@router.get("/startups", response_model=StartupListResponse)
def list_startups():
    """List all ingested startups."""
    return StartupListResponse(startups=metadata_store.list_startups())


@router.get("/startups/{startup_id}/metrics")
def get_metrics(startup_id: str):
    """Retrieve all structured financial metrics for a startup."""
    startup = metadata_store.get_startup(startup_id)
    if not startup:
        raise HTTPException(status_code=404, detail=f"Startup '{startup_id}' not found.")
    metrics = metadata_store.get_financial_metrics(startup_id)
    return {"startup_id": startup_id, "metrics": metrics}
