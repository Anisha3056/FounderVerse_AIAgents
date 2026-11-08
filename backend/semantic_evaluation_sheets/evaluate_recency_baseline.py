from typing import Any

from app.memory.memory_manager import MemoryManager


def retrieve_recent_memories(
    agent_name: str,
    company_id: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Stage 1: Recency-only retrieval baseline.

    Evaluation-only implementation.
    Does not modify MongoDB documents.
    Does not generate embeddings or call an LLM.
    """
    if limit <= 0:
        return []

    manager = MemoryManager()

    cursor = (
        manager.collection
        .find(
            {
                "agent_name": agent_name,
                "company_id": company_id,
            }
        )
        .sort("created_at", -1)
        .limit(limit)
    )

    memories = []

    for memory in cursor:
        memory["_id"] = str(memory["_id"])
        memories.append(memory)

    return memories