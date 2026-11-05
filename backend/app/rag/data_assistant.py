from typing import Any

from app.database.repositories.company_repository import CompanyRepository


class AgentDataAssistant:

    def __init__(self) -> None:
        self.company_repository = CompanyRepository()

    def get_company_data(
        self,
        company_id: str,
    ) -> dict[str, Any]:

        company = self.company_repository.get_by_id(company_id)

        if not company:
            raise ValueError("Company not found.")

        company["_id"] = str(company["_id"])

        return company

    def calculate_profit(
        self,
        company_id: str,
    ) -> float:

        company = self.get_company_data(company_id)

        revenue = float(company.get("revenue", 0))
        expenses = float(company.get("expenses", 0))

        return revenue - expenses

    def calculate_runway(
        self,
        company_id: str,
    ) -> float:

        company = self.get_company_data(company_id)

        cash = float(company.get("cash", 0))
        monthly_expenses = float(company.get("expenses", 0))

        if monthly_expenses <= 0:
            return 0.0

        return cash / monthly_expenses