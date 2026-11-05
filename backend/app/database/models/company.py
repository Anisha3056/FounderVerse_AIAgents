
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, model_validator


class CompanyState(BaseModel):
    company_name: str
    industry: str | None = None
    stage: str | None = None

    cash: float = 0.0
    revenue: float = 0.0
    expenses: float = 0.0
    profit: float = 0.0

    team_size: int = 1

    initial_capital: float = 0.0
    initial_customers: int = 0

    monthly_revenue: float | None = 0.0
    monthly_revenue_status: str = "known"
    monthly_expenses: float = 0.0

    region: str | None = None
    segment: str | None = None
    target_market: str | None = None
    acquisition_channel: str | None = None

    # Founder-provided simulation assumptions.
    expected_new_customers: int | None = None
    known_monthly_churn_percent: float | None = None
    expected_monthly_expense_growth_percent: float | None = None

    customers: int = 0
    churn_rate: float = 0.0
    monthly_growth_rate: float = 0.0
    runway_months: float = 0.0
    valuation: float = 0.0
    current_month: int = 1

    metadata: dict[str, Any] = Field(default_factory=dict)

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CompanyCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    company_name: str = Field(min_length=1, max_length=120)

    industry: str = "SaaS"
    stage: str = "idea"

    region: str | None = None
    segment: str | None = None
    acquisition_channel: str | None = None
    target_market: str | None = None

    initial_capital: float = Field(default=0.0, ge=0)
    team_size: int = Field(default=1, ge=1)

    initial_customers: int = Field(default=0, ge=0)
    monthly_revenue: float | None = Field(default=0.0, ge=0)
    monthly_revenue_status: str = Field(
        default="known",
        pattern="^(known|unknown)$",
    )
    monthly_expenses: float = Field(default=0.0, ge=0)

    expected_new_customers: int | None = Field(default=None, ge=0)
    known_monthly_churn_percent: float | None = Field(
        default=None, ge=0, le=100
    )
    expected_monthly_expense_growth_percent: float | None = Field(
        default=None, ge=0, le=100
    )

    @model_validator(mode="after")
    def validate_revenue_status(self):
        if (
            self.monthly_revenue_status == "unknown"
            and self.monthly_revenue is not None
        ):
            self.monthly_revenue = None

        return self