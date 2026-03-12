from fastapi import APIRouter, HTTPException
from app.api.schemas import IngestRequest, IngestResponse
from app.ingestion.pipeline import ingest_startup
from app.retrieval.vector_store import VectorStore

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("", response_model=IngestResponse)
def ingest(req: IngestRequest):
    """Ingest all documents for a startup from its data directory."""
    try:
        summary = ingest_startup(
            startup_id=req.startup_id,
            startup_name=req.startup_name,
            startup_dir=req.data_dir,
            description=req.description,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    return IngestResponse(**summary)


@router.delete("/{startup_id}")
def delete_startup(startup_id: str):
    """Remove all ingested data for a startup (useful for re-ingestion)."""
    from app.storage.metadata_store import metadata_store

    metadata_store.delete_startup_data(startup_id)
    vs = VectorStore(startup_id)
    vs.reset()
    return {"status": "deleted", "startup_id": startup_id}
