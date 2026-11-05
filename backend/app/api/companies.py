
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.database.models.company import CompanyCreate
from app.database.repositories.company_repository import CompanyRepository
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.simulation_repository import SimulationRepository


router = APIRouter(
    prefix="/api/companies",
    tags=["Companies"],
)

repository = CompanyRepository()
user_repository = UserRepository()
simulation_repository = SimulationRepository()


@router.post("/")
async def create_company(
    company: CompanyCreate,
    current_user=Depends(get_current_user),
):
    # Pydantic validates the incoming request before this point.
    company_data = company.model_dump()

    # -------------------------------------------------
    # 1. INITIAL COMPANY STATE
    # -------------------------------------------------

    initial_capital = company.initial_capital
    initial_customers = company.initial_customers
    monthly_expenses = company.monthly_expenses

    # Preserve whether revenue is known or unknown.
    revenue_is_known = company.monthly_revenue_status == "known"

    monthly_revenue = (
        company.monthly_revenue
        if revenue_is_known and company.monthly_revenue is not None
        else 0.0
    )


    company_data.update({
        "cash": initial_capital,
        "revenue": monthly_revenue,
        "monthly_revenue": (monthly_revenue if revenue_is_known else None),
        "monthly_revenue_status": ("known" if revenue_is_known else "unknown"),
        "expenses": monthly_expenses,
        "profit": monthly_revenue - monthly_expenses,
        "customers": initial_customers,
        "monthly_growth_rate": 0.0,
        "churn_rate": 0.0,
        "current_month": 1,
        "valuation": 0.0,
    })

    # -------------------------------------------------
    # 2. PRESERVE FOUNDER-PROVIDED ASSUMPTIONS
    # -------------------------------------------------

    # These may be None if the founder left them blank.
    # The simulation engine will apply documented defaults
    # when it advances the simulation.
    company_data["expected_new_customers"] = (
        company.expected_new_customers
    )
    company_data["known_monthly_churn_percent"] = (
        company.known_monthly_churn_percent
    )
    company_data["expected_monthly_expense_growth_percent"] = (
        company.expected_monthly_expense_growth_percent
    )

    # -------------------------------------------------
    # 3. INITIAL RUNWAY
    # -------------------------------------------------

    monthly_burn = monthly_expenses - monthly_revenue

    if monthly_burn > 0:
        company_data["runway_months"] = round(
            initial_capital / monthly_burn, 2
        )
    else:
        # Preserve the existing convention for initial state.
        company_data["runway_months"] = 0.0

    # -------------------------------------------------
    # 4. OWNER
    # -------------------------------------------------

    company_data["owner_user_id"] = str(current_user["_id"])

    # -------------------------------------------------
    # 5. SAVE COMPANY AND INITIAL SNAPSHOT
    # -------------------------------------------------

    company_id = repository.create(company_data)

    simulation_repository.save_snapshot(
        company_id=company_id,
        state=company_data,
    )

    user_repository.attach_company(
        user_id=str(current_user["_id"]),
        company_id=company_id,
    )

    return {
        "company_id": company_id,
        "message": "Company created successfully.",
    }


@router.get("/{company_id}")
async def get_company(
    company_id: str,
    current_user=Depends(get_current_user),
):
    result = repository.get_by_id(company_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Company not found.",
        )

    owner_user_id = result.get("owner_user_id")

    if owner_user_id != str(current_user["_id"]):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this company.",
        )

    result["_id"] = str(result["_id"])

    return result
