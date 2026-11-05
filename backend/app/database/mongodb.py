from pymongo import MongoClient
from pymongo.database import Database

from app.config.settings import get_settings


class MongoDB:
    def __init__(self) -> None:
        self.client: MongoClient | None = None
        self.database: Database | None = None

    def connect(self) -> None:
        settings = get_settings()

        self.client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=10000,
        )

        self.database = self.client[settings.mongodb_database]

        # Force a connection check.
        self.client.admin.command("ping")

        print("MongoDB connected successfully.")

    def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None
            self.database = None

    def get_database(self) -> Database:
        if self.database is None:
            raise RuntimeError("MongoDB is not connected.")

        return self.database


mongodb = MongoDB()