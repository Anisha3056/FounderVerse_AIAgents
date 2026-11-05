from pydantic import BaseModel


class SimulationState(BaseModel):
    company_id: str

    month: int

    cash: float
    revenue: float
    expenses: float
    profit: float

    customers: int
    churn_rate: float

    runway_months: float
    valuation: float