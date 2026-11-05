import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.database.repositories.company_repository import CompanyRepository
from app.orchestration.single_llm_baseline import SingleLLMBaseline


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/experiments",
    tags=["Research Experiments"],
)

company_repository = CompanyRepository()
baseline = SingleLLMBaseline()


class SingleLLMBaselineRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )


@router.post("/{company_id}/single-llm")
async def run_single_llm_baseline(
    company_id: str,
    request: SingleLLMBaselineRequest,
    current_user=Depends(get_current_user),
):
    """
    Run Condition A: the single-LLM research baseline.

    This endpoint:
    - Requires authentication.
    - Verifies company ownership.
    - Calls the baseline service, not the boardroom orchestrator.
    - Does not save a founder decision.
    - Does not consume the existing boardroom trial allowance.

    Research runs should be logged separately from normal
    FounderVerse consultations.
    """

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    company = company_repository.get_by_id(company_id)

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found.",
        )

    if company.get("owner_user_id") != str(current_user["_id"]):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this company.",
        )

    try:
        result = await baseline.generate(
            founder_question=question,
            company=company,
            company_id=company_id,
        )

        return {
            "company_id": company_id,
            "question": question,
            **result,
        }

    except Exception as exc:
        logger.exception(
            "Single-LLM baseline failed for company %s",
            company_id,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "The single-LLM baseline could not generate "
                "a valid recommendation. Check the backend logs."
            ),
        ) from exc