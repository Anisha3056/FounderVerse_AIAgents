import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

sys.path.insert(0, str(BACKEND))

from app.database.mongodb import mongodb
from app.database.repositories.company_repository import CompanyRepository


def main():

    mongodb.connect()

    repository = CompanyRepository()

    company = {
        "company_name": "FounderVerse Demo",
        "industry": "Technology",
        "stage": "Pre-seed",

        "cash": 1000000,
        "revenue": 150000,
        "expenses": 100000,
        "profit": 50000,

        "customers": 1000,
        "churn_rate": 0.05,

        "monthly_growth_rate": 0.10,
        "runway_months": 10,

        "valuation": 5000000,

        "current_month": 1,
    }

    company_id = repository.create(company)

    print(f"Demo company created.")
    print(f"Company ID: {company_id}")

    mongodb.close()


if __name__ == "__main__":
    main()