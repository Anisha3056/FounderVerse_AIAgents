
from typing import Any

from app.database.repositories.company_repository import CompanyRepository
from app.database.repositories.simulation_repository import SimulationRepository


class SimulationEngine:
    """
    Data-informed monthly SaaS simulation.

    Calibration references from the FounderVerse dataset:
    - Mean new subscriptions: approximately 151.9/month.
    - Mean established-customer monthly churn: approximately 1.276%.

    These observations describe the dataset, not every startup.
    Acquisition is scaled to the simulated company's customer base.
    Channel-specific causal effects are not inferred from this data.

    Expense growth and valuation multiples remain explicit modelling
    assumptions, not parameters learned from a trained ML model.
    """

    # Approximate mean active customer base at the start of months
    # in the Jan 2024-Sep 2025 calibration window.
    # This is a rounded reference value from the monthly audit.
    REFERENCE_CUSTOMER_BASE = 2800

    CALIBRATED_NEW_SUBSCRIPTIONS_PER_MONTH = 151.9
    CALIBRATED_MONTHLY_CHURN_RATE = 0.01276

    # Explicit provisional assumption; not estimated from this dataset.
    MONTHLY_EXPENSE_GROWTH_RATE = 0.01

    # Indicative ARR-multiple assumptions, not formal valuations.
    VALUATION_MULTIPLIERS = {
        "idea": 1.0,
        "early": 2.0,
        "growth": 4.0,
        "scale": 5.0,
    }

    def __init__(self) -> None:
        self.company_repository = CompanyRepository()
        self.simulation_repository = SimulationRepository()

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            result = float(value)
            if result != result or result in (float("inf"), float("-inf")):
                return default
            return result
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_current_state(self, company_id: str) -> dict:
        company = self.company_repository.get_by_id(company_id)

        if not company:
            raise ValueError("Company not found.")

        company["_id"] = str(company["_id"])
        return company

    def advance_month(self, company_id: str) -> dict:
        company = self.company_repository.get_by_id(company_id)

        if not company:
            raise ValueError("Company not found.")

        # 1. Read founder-provided starting state.
        current_month = max(
            1, self._safe_int(company.get("current_month"), 1)
        )
        customers = max(
            0, self._safe_int(company.get("customers"), 0)
        )
        revenue = max(0.0, self._safe_float(company.get("revenue")))
        revenue_status = company.get("monthly_revenue_status", "known")
        revenue_is_known = revenue_status == "known"
        expenses = max(0.0, self._safe_float(company.get("expenses")))
        cash = self._safe_float(company.get("cash"))

        stage = str(company.get("stage", "early")).lower().strip()
        if stage not in self.VALUATION_MULTIPLIERS:
            stage = "early"

        # 2. Calculate calibrated acquisition and churn.
        #
        # Scale the observed acquisition count relative to the
        # reference customer base. This is a proportional baseline,
        # not a claim that startup acquisition always scales linearly.
        acquisition_rate = (
            self.CALIBRATED_NEW_SUBSCRIPTIONS_PER_MONTH
            / self.REFERENCE_CUSTOMER_BASE
        )

        founder_new_customers = company.get("expected_new_customers")
        if founder_new_customers is not None:
            try:
                new_customers = max(0, int(founder_new_customers))
            except (TypeError, ValueError):
                new_customers = round(customers * acquisition_rate)
        else:
            # Round expected counts deterministically for reproducibility.
            new_customers = round(customers * acquisition_rate)

        founder_churn_percent = company.get("known_monthly_churn_percent")
        if founder_churn_percent is not None:
            try:
                churn_rate = min(
                    max(float(founder_churn_percent) / 100, 0.0), 1.0
                )
            except (TypeError, ValueError):
                churn_rate = self.CALIBRATED_MONTHLY_CHURN_RATE
        else:
            churn_rate = self.CALIBRATED_MONTHLY_CHURN_RATE

        churned_customers = min(
            customers, round(customers * churn_rate)
        )

        next_customers = max(
            0, customers + new_customers - churned_customers
        )

        
        # 3. Project revenue.
        # Unknown revenue uses zero only as a provisional
        # calculation assumption; it is not actual revenue.
        if not revenue_is_known:
            next_revenue = 0.0

        elif customers > 0:
            revenue_per_customer = revenue / customers
            next_revenue = next_customers * revenue_per_customer

        else:
            # Preserve known revenue when the customer count is zero.
            next_revenue = revenue


        # 4. Project operating expenses.
        founder_expense_growth_percent = company.get(
            "expected_monthly_expense_growth_percent"
        )
        if founder_expense_growth_percent is not None:
            try:
                expense_change_rate = min(
                    max(float(founder_expense_growth_percent) / 100, 0.0),
                    1.0,
                )
            except (TypeError, ValueError):
                expense_change_rate = self.MONTHLY_EXPENSE_GROWTH_RATE
        else:
            expense_change_rate = self.MONTHLY_EXPENSE_GROWTH_RATE

        next_expenses = expenses * (1 + expense_change_rate)

        # 5. Profit and cash.
        next_profit = next_revenue - next_expenses
        next_cash = cash + next_profit

        # 6. Cash runway based on projected monthly operating burn.
        monthly_burn = next_expenses - next_revenue
        if monthly_burn > 0:
            next_runway = max(0.0, next_cash / monthly_burn)
        else:
            # Zero means no positive operating burn in this simplified
            # model; it does not mean the company has no cash available.
            next_runway = 0.0

        # 7. Indicative valuation proxy based on projected ARR.
        valuation_multiplier = self.VALUATION_MULTIPLIERS[stage]
        next_valuation = next_revenue * 12 * valuation_multiplier

        # 8. Save the next state.
        updated_state = {
            "current_month": current_month + 1,
            "customers": next_customers,
            "new_customers": new_customers,
            "churned_customers": churned_customers,
            "revenue": round(next_revenue, 2),
            "monthly_revenue_status": revenue_status,
            "monthly_revenue": (round(next_revenue, 2) 
                                if revenue_is_known
                                else None),
            "expenses": round(next_expenses, 2),
            "profit": round(next_profit, 2),
            "cash": round(next_cash, 2),
            "churn_rate": churn_rate,
            "monthly_growth_rate": acquisition_rate,
            "runway_months": round(next_runway, 2),
            "valuation": round(next_valuation, 2),
        }

        self.company_repository.update(company_id, updated_state)
        current_state = self.get_current_state(company_id)

        self.simulation_repository.save_snapshot(
            company_id=company_id,
            state=current_state,
        )

        return current_state
