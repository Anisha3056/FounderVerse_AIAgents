from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.database.repositories.company_repository import CompanyRepository
from app.simulation.engine import SimulationEngine
from app.database.repositories.simulation_repository import SimulationRepository


router = APIRouter(
    prefix="/api/simulation",
    tags=["Simulation"],
)


company_repository = CompanyRepository()
simulation_engine = SimulationEngine()
simulation_repository = SimulationRepository()


@router.get("/{company_id}/state")
async def get_simulation_state(
    company_id: str,
    current_user=Depends(get_current_user),
):

    company = company_repository.get_by_id(
        company_id
    )

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found.",
        )

    if company.get("owner_user_id") != str(
        current_user["_id"]
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this company.",
        )

    current_state = (
        simulation_engine.get_current_state(
            company_id
        )
    )

    timeline = simulation_repository.get_all(
        company_id
    )

    previous_state = (
        timeline[-2]
        if len(timeline) >= 2
        else None
    )

    if previous_state:
        previous_state["_id"] = str(
            previous_state["_id"]
        )

    for snapshot in timeline:
        snapshot["_id"] = str(
            snapshot["_id"]
        )

    return {
        **current_state,

        "previous_state": previous_state,

        "timeline": timeline,
    }


@router.post("/{company_id}/advance")
async def advance_simulation(
    company_id: str,
    current_user=Depends(get_current_user),
):

    company = company_repository.get_by_id(
        company_id
    )

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found.",
        )


    if company.get("owner_user_id") != str(
        current_user["_id"]
    ):

        raise HTTPException(
            status_code=403,
            detail="You do not have access to this company.",
        )


    try:

        updated_state = (
            simulation_engine.advance_month(
                company_id
            )
        )

        return {
            "message":
                "Simulation advanced successfully.",

            "state":
                updated_state,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )