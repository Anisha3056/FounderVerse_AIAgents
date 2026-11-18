from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from app.database.mongodb import mongodb


FREE_MONTHLY_QUESTION_LIMIT = 15


class UserRepository:
    @property
    def collection(self):
        db = mongodb.get_database()
        return db["users"]

    def create(self, email: str, password_hash: str) -> str:
        now = datetime.now(timezone.utc)
        result = self.collection.insert_one({
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "email_verified": False,
            "email_verification_token_hash": None,
            "email_verification_expires_at": None,
            "verification_last_sent_at": None,
            "company_id": None,
            "created_at": now,
            "updated_at": now,
        })
        return str(result.inserted_id)

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        return self.collection.find_one({"email": email.lower().strip()})

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(user_id)
        except Exception:
            return None
        return self.collection.find_one({"_id": object_id})

    def set_email_verification(
        self,
        email: str,
        token_hash: str,
        expires_at: datetime,
        sent_at: datetime,
        cooldown_seconds: int = 60,
    ) -> bool:
        """Store a hashed, expiring token and enforce a resend cooldown."""
        cooldown_cutoff = sent_at - timedelta(seconds=cooldown_seconds)

        result = self.collection.update_one(
            {
                "email": email.lower().strip(),
                "email_verified": {"$ne": True},
                "$or": [
                    {"verification_last_sent_at": {"$exists": False}},
                    {"verification_last_sent_at": None},
                    {"verification_last_sent_at": {"$lte": cooldown_cutoff}},
                ],
            },
            {
                "$set": {
                    "email_verification_token_hash": token_hash,
                    "email_verification_expires_at": expires_at,
                    "verification_last_sent_at": sent_at,
                    "updated_at": sent_at,
                }
            },
        )
        return result.modified_count == 1

    def verify_email_token(
        self,
        token_hash: str,
        verified_at: datetime,
    ) -> dict[str, Any] | None:
        """Atomically verify an account and consume its one-time token."""
        return self.collection.find_one_and_update(
            {
                "email_verification_token_hash": token_hash,
                "email_verification_expires_at": {"$gt": verified_at},
                "email_verified": {"$ne": True},
            },
            {
                "$set": {
                    "email_verified": True,
                    "email_verified_at": verified_at,
                    "updated_at": verified_at,
                },
                "$unset": {
                    "email_verification_token_hash": "",
                    "email_verification_expires_at": "",
                },
            },
            return_document=ReturnDocument.AFTER,
        )

    def attach_company(self, user_id: str, company_id: str) -> bool:
        try:
            object_id = ObjectId(user_id)
        except Exception:
            return False
        result = self.collection.update_one(
            {"_id": object_id},
            {"$set": {"company_id": company_id, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0 or result.matched_count > 0

    @staticmethod
    def _current_month_key() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def get_monthly_usage(self, user_id: str, limit: int = FREE_MONTHLY_QUESTION_LIMIT) -> dict[str, Any]:
        """Return this user's allowance for the current UTC calendar month."""
        try:
            object_id = ObjectId(user_id)
        except Exception:
            raise ValueError("Invalid user ID")

        month_key = self._current_month_key()
        user = self.collection.find_one({"_id": object_id}, {
            "monthly_question_month": 1,
            "monthly_questions_used": 1,
        })
        if user is None:
            raise ValueError("User not found")

        used = int(user.get("monthly_questions_used", 0) or 0)
        if user.get("monthly_question_month") != month_key:
            used = 0
        used = max(0, min(used, limit))
        return {
            "plan": "free",
            "month": month_key,
            "limit": limit,
            "used": used,
            "remaining": max(0, limit - used),
            "upgrade_available": True,
        }

    def reserve_monthly_question(self, user_id: str, limit: int = FREE_MONTHLY_QUESTION_LIMIT) -> dict[str, Any] | None:
        """Atomically reserve one new consultation; return None if the trial is exhausted."""
        try:
            object_id = ObjectId(user_id)
        except Exception:
            raise ValueError("Invalid user ID")

        month_key = self._current_month_key()
        eligible_filter = {
            "_id": object_id,
            "$or": [
                {"monthly_question_month": {"$ne": month_key}},
                {"monthly_questions_used": {"$lt": limit}},
            ],
        }
        updated_user = self.collection.find_one_and_update(
            eligible_filter,
            [{"$set": {
                "monthly_questions_used": {
                    "$cond": [
                        {"$eq": ["$monthly_question_month", month_key]},
                        {"$add": [{"$ifNull": ["$monthly_questions_used", 0]}, 1]},
                        1,
                    ]
                },
                "monthly_question_month": month_key,
                "updated_at": datetime.now(timezone.utc),
            }}],
            return_document=ReturnDocument.AFTER,
            projection={"monthly_question_month": 1, "monthly_questions_used": 1},
        )

        if updated_user is None:
            user = self.collection.find_one({"_id": object_id}, {
                "monthly_question_month": 1,
                "monthly_questions_used": 1,
            })
            if user is None:
                raise ValueError("User not found")
            used = int(user.get("monthly_questions_used", 0) or 0)
            if user.get("monthly_question_month") != month_key:
                used = 0
            return None if used >= limit else None

        used = int(updated_user.get("monthly_questions_used", 0) or 0)
        return {
            "plan": "free",
            "month": month_key,
            "limit": limit,
            "used": used,
            "remaining": max(0, limit - used),
            "upgrade_available": True,
        }
