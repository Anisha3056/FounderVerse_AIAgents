from datetime import datetime, timezone
from typing import Any
from app.database.mongodb import mongodb


class DecisionRepository:
    @property
    def collection(self):
        return mongodb.get_database()["decisions"]

    def create(self, decision_data: dict[str, Any]) -> str:
        decision_data["created_at"] = datetime.now(timezone.utc)
        result = self.collection.insert_one(decision_data)
        return str(result.inserted_id)

    def get_by_company(self, company_id: str) -> list[dict[str, Any]]:
        decisions = list(self.collection.find({"company_id": company_id}).sort("created_at", -1))
        for decision in decisions:
            decision["_id"] = str(decision["_id"])
        return decisions
