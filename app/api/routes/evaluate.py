from fastapi import APIRouter, HTTPException
from app.api.schemas import EvaluateRequest, EvaluateResponse
from app.evaluation.evaluator import run_evaluation

router = APIRouter(tags=["evaluation"])


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest):
    """Run the evaluation suite against a startup's ingested data."""
    try:
        result = run_evaluation(
            startup_id=req.startup_id,
            question_set=req.question_set,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}")

    return EvaluateResponse(**result)
