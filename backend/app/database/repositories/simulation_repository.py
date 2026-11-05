
from datetime import datetime, timezone
from typing import Any

from app.database.mongodb import mongodb


class SimulationRepository:

    @property
    def collection(self):
        return mongodb.get_database()["simulation_states"]

    def save_snapshot(
        self,
        company_id: str,
        state: dict[str, Any],
    ) -> str:
        # Preserve the distinction between unknown revenue and known ₹0.
        revenue_status = state.get("monthly_revenue_status", "known")
        revenue_value = state.get("revenue")

        # Numeric revenue remains available for provisional calculations.
        # The status field tells the UI whether that number is actual/known.
        numeric_revenue = (
            0.0 if revenue_value is None else float(revenue_value)
        )

        monthly_revenue = state.get("monthly_revenue")
        if monthly_revenue is not None:
            monthly_revenue = float(monthly_revenue)

        snapshot = {
            "company_id": company_id,
            "month": int(state.get("current_month", 1)),
            "cash": float(state.get("cash", 0.0)),
            "revenue": numeric_revenue,
            "monthly_revenue": monthly_revenue,
            "monthly_revenue_status": revenue_status,
            "expenses": float(state.get("expenses", 0.0)),
            "profit": float(state.get("profit", 0.0)),
            "customers": int(state.get("customers", 0)),
            "churn_rate": float(state.get("churn_rate", 0.0)),
            "monthly_growth_rate": float(
                state.get("monthly_growth_rate", 0.0)
            ),
            "runway_months": float(
                state.get("runway_months", 0.0)
            ),
            "valuation": float(state.get("valuation", 0.0)),
            "team_size": int(state.get("team_size", 0)),
            "simulation_events": state.get("simulation_events", []),
            "historical_profile": state.get("historical_profile", {}),
            "created_at": datetime.now(timezone.utc),
        }

        result = self.collection.insert_one(snapshot)
        return str(result.inserted_id)

    def get_latest(
        self,
        company_id: str,
    ) -> dict[str, Any] | None:
        return self.collection.find_one(
            {"company_id": company_id},
            sort=[("month", -1)],
        )

    def get_all(
        self,
        company_id: str,
    ) -> list[dict[str, Any]]:
        return list(
            self.collection.find(
                {"company_id": company_id}
            ).sort("month", 1)
        )
