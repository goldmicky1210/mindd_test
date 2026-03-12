from fastapi import APIRouter, HTTPException
from app.api.schemas import CompareRequest, CompareResponse
from app.reasoning.comparison import compare_startups
from app.storage.metadata_store import metadata_store

router = APIRouter(tags=["comparison"])


@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest):
    """Compare two or more startups on a given question."""
    for sid in req.startup_ids:
        if not metadata_store.get_startup(sid):
            raise HTTPException(
                status_code=404,
                detail=f"Startup '{sid}' not found. Please ingest documents first.",
            )

    try:
        result = compare_startups(
            startup_ids=req.startup_ids,
            question=req.question,
            top_k=req.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {exc}")

    return CompareResponse(
        startup_ids=req.startup_ids,
        question=req.question,
        answer=result["answer"],
        startup_evidence=result["startup_evidence"],
        sources=result["sources"],
    )
