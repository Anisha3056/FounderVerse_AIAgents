from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.database.mongodb import mongodb


class CompanyRepository:

    @property
    def collection(self):
        db = mongodb.get_database()
        return db["companies"]

    def create(self, company_data: dict[str, Any]) -> str:
        company_data["created_at"] = datetime.now(timezone.utc)
        company_data["updated_at"] = datetime.now(timezone.utc)

        result = self.collection.insert_one(company_data)

        return str(result.inserted_id)

    def get_by_id(self, company_id: str) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(company_id)
        except Exception:
            return None

        return self.collection.find_one({"_id": object_id})

    def update(
        self,
        company_id: str,
        updates: dict[str, Any],
    ) -> bool:

        try:
            object_id = ObjectId(company_id)
        except Exception:
            return False

        updates["updated_at"] = datetime.now(timezone.utc)

        result = self.collection.update_one(
            {"_id": object_id},
            {"$set": updates},
        )

        return result.modified_count > 0

    def list_companies(self) -> list[dict[str, Any]]:
        return list(self.collection.find())