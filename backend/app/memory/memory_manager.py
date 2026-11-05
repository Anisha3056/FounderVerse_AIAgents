
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from sentence_transformers import SentenceTransformer

from app.database.mongodb import mongodb


EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model once per process."""
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def generate_embedding(text: str) -> list[float]:
    """Generate a normalized, 384-dimensional embedding."""
    model = get_embedding_model()

    vector = model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return vector.tolist()


class MemoryManager:

    @property
    def collection(self):
        db = mongodb.get_database()
        return db["agent_memories"]

    def save_memory(
        self,
        agent_name: str,
        company_id: str,
        memory_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:

        document = {
            "agent_name": agent_name,
            "company_id": company_id,
            "memory_type": memory_type,
            "content": content,
            "metadata": metadata or {},
            "embedding": generate_embedding(content),
            "created_at": datetime.now(timezone.utc),
        }

        result = self.collection.insert_one(document)

        return str(result.inserted_id)

    def get_recent_memories(
        self,
        agent_name: str,
        company_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:

        cursor = (
            self.collection
            .find({
                "agent_name": agent_name,
                "company_id": company_id,
            })
            .sort("created_at", -1)
            .limit(limit)
        )

        memories = []

        for memory in cursor:
            memory["_id"] = str(memory["_id"])
            memories.append(memory)

        return memories
