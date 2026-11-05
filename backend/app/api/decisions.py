
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.database.models.decision import DecisionCreate
from app.database.repositories.company_repository import CompanyRepository
from app.database.repositories.decision_repository import DecisionRepository
from app.orchestration.agent_impact import AgentImpactClassifier


router = APIRouter(
    prefix="/api/decisions",
    tags=["Decisions"],
)

company_repository = CompanyRepository()
decision_repository = DecisionRepository()
agent_impact_classifier = AgentImpactClassifier()


def verify_company_access(company_id: str, current_user: dict):
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


# ---------------------------------------------------------
# RECORD A FOUNDER DECISION
# POST /api/decisions/{company_id}
# ---------------------------------------------------------

@router.post("/{company_id}")
async def create_decision(
    company_id: str,
    decision: DecisionCreate,
    current_user=Depends(get_current_user),
):
    company = verify_company_access(
        company_id,
        current_user,
    )

    if decision.company_id != company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID does not match the request.",
        )

    if decision.decision not in {"proceed", "hold_off"}:
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'proceed' or 'hold_off'.",
        )

    if not decision.explanation.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide an explanation.",
        )

    affected_agents, affected_agents_warning = (
        await agent_impact_classifier.identify_affected_agents(
            question=decision.question,
            boardroom_responses=decision.boardroom_responses,
        )
    )

    decision_data = decision.model_dump()
    decision_data["affected_agents"] = affected_agents

    decision_data["simulation_month"] = company.get(
        "current_month",
        1,
    )

    decision_id = decision_repository.create(
        decision_data
    )

    return {
        "decision_id": str(decision_id),
        "message": "Decision recorded successfully.",
        "company_id": company_id,
        "question": decision.question,
        "decision": decision.decision,
        "explanation": decision.explanation,
        "affected_agents": affected_agents,
        "affected_agents_warning": affected_agents_warning,
        "simulation_month": decision_data["simulation_month"],
    }


# ---------------------------------------------------------
# RETRIEVE DECISION HISTORY
# GET /api/decisions/{company_id}
# ---------------------------------------------------------

@router.get("/{company_id}")
async def get_decision_history(
    company_id: str,
    current_user=Depends(get_current_user),
):
    verify_company_access(
        company_id,
        current_user,
    )

    decisions = decision_repository.get_by_company(
        company_id
    )

    return {
        "company_id": company_id,
        "count": len(decisions),
        "decisions": decisions,
    }
