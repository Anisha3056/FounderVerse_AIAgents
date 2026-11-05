
from typing import Literal
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.database.repositories.company_repository import CompanyRepository
from app.database.repositories.user_repository import (
    UserRepository,
    FREE_MONTHLY_QUESTION_LIMIT,
)
from app.orchestration.boardroom import BoardroomOrchestrator


router = APIRouter(
    prefix="/api/boardroom",
    tags=["Boardroom"],
)

company_repository = CompanyRepository()
user_repository = UserRepository()
orchestrator = BoardroomOrchestrator()


# =====================================================
# REQUEST MODELS
# =====================================================

class BoardroomQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    mode: Literal[
        "individual",
        "collaborative",
        "both",
    ] = "individual"


class ContinueBoardroomRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    responses: list[dict] = Field(min_length=1)


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def _get_owned_company(company_id: str, current_user):
    """
    Retrieve a company and verify that the authenticated
    user owns it.
    """

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

    return company


def _user_id(current_user) -> str:
    """
    Get the authenticated user's ID from the server-side
    authentication dependency.
    """

    return str(current_user.get("_id", ""))


# =====================================================
# MONTHLY FREE-TRIAL USAGE
# =====================================================

@router.get("/usage")
async def get_boardroom_usage(
    current_user=Depends(get_current_user),
):
    """
    Return the authenticated user's monthly question usage.

    Usage is tied to the user, not to a particular company
    or boardroom mode.
    """

    try:
        return user_repository.get_monthly_usage(
            _user_id(current_user)
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc


# =====================================================
# ASK THE AI BOARDROOM
# =====================================================

@router.post("/{company_id}/ask")
async def ask_boardroom(
    company_id: str,
    request: BoardroomQuestion,
    current_user=Depends(get_current_user),
):
    """
    Start a new boardroom consultation.

    Records backend latency for the consultation workflow.
    Every new consultation consumes one free question,
    regardless of the selected mode.
    """

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    # Verify company ownership before reserving usage.
    company = _get_owned_company(
        company_id,
        current_user,
    )

    # Reserve one monthly question.
    try:
        usage = user_repository.reserve_monthly_question(
            _user_id(current_user)
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc

    # A None result means the monthly limit has been reached.
    if usage is None:
        usage = user_repository.get_monthly_usage(
            _user_id(current_user)
        )

        raise HTTPException(
            status_code=429,
            detail={
                "code": "TRIAL_LIMIT_REACHED",
                "message": (
                    "You've used all 15 free consultations "
                    "for this calendar month."
                ),
                "usage": usage,
            },
        )

    # Measure the consultation workflow using a monotonic clock.
    started_at = time.perf_counter()

    try:
        result = await orchestrator.consult(
            founder_question=question,
            company=company,
            mode=request.mode,
        )
    except Exception:
        # Keep the existing error behavior while ensuring
        # the exception is not silently swallowed.
        raise

    elapsed_ms = round(
        (time.perf_counter() - started_at) * 1000,
        2,
    )

    # Add research performance metadata without replacing
    # the existing recommendation or agent responses.
    result["performance"] = {
        "mode": request.mode,
        "backend_consultation_latency_ms": elapsed_ms,
        "measurement": (
            "Wall-clock time spent awaiting the "
            "BoardroomOrchestrator consultation."
        ),
    }

    # Return updated usage alongside the consultation result.
    result["usage"] = usage

    return result
# =====================================================
# CONTINUE AN EXISTING COLLABORATION
# =====================================================

@router.post("/{company_id}/continue")
async def continue_boardroom(
    company_id: str,
    request: ContinueBoardroomRequest,
    current_user=Depends(get_current_user),
):
    """
    Continue an existing consultation using the responses
    already generated.

    This is not a new consultation and therefore does not
    reserve or consume another monthly question.
    """

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    company = _get_owned_company(
        company_id,
        current_user,
    )

    return await orchestrator.continue_collaboration(
        founder_question=question,
        company=company,
        responses=request.responses,
    )
