
import logging

import numpy as np

from app.memory.memory_manager import (
    MemoryManager,
    generate_embedding,
)

logger = logging.getLogger(__name__)


class MemoryRetriever:

    QUESTION_WEIGHT = 0.7
    CONTENT_WEIGHT = 0.3

    def __init__(self) -> None:
        self.memory_manager = MemoryManager()

    def retrieve_relevant_memories(
        self,
        agent_name: str,
        company_id: str,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.25,
    ) -> list[dict]:

        if not query.strip() or limit <= 0:
            return []

        query_vector = np.asarray(
            generate_embedding(query),
            dtype=np.float32,
        )

        cursor = self.memory_manager.collection.find({
            "agent_name": agent_name,
            "company_id": company_id,
        })

        scored_memories = []

        for memory in cursor:
            content = memory.get("content", "")

            if not isinstance(content, str) or not content.strip():
                continue

            metadata = memory.get("metadata") or {}
            original_question = metadata.get("question", "")

            if not isinstance(original_question, str):
                original_question = ""

            # Fall back to the stored content for older memories
            # that do not have an original question in metadata.
            question_text = original_question.strip() or content

            # Backfill older records with a content embedding.
            content_embedding = memory.get("embedding")

            if content_embedding is None:
                content_embedding = generate_embedding(content)

                self.memory_manager.collection.update_one(
                    {"_id": memory["_id"]},
                    {"$set": {"embedding": content_embedding}},
                )

            content_vector = np.asarray(
                content_embedding,
                dtype=np.float32,
            )

            if (
                content_vector.shape != query_vector.shape
                or not np.all(np.isfinite(content_vector))
            ):
                logger.warning(
                    "Skipping memory with invalid content embedding: %s",
                    memory.get("_id"),
                )
                continue

            content_similarity = float(
                np.dot(query_vector, content_vector)
            )

            # Generate an embedding for the original question.
            # Cache it in MongoDB to avoid repeating this work.
            question_embedding = memory.get("question_embedding")

            if question_embedding is None:
                question_embedding = generate_embedding(question_text)

                self.memory_manager.collection.update_one(
                    {"_id": memory["_id"]},
                    {"$set": {
                        "question_embedding": question_embedding,
                    }},
                )

            question_vector = np.asarray(
                question_embedding,
                dtype=np.float32,
            )

            if (
                question_vector.shape != query_vector.shape
                or not np.all(np.isfinite(question_vector))
            ):
                logger.warning(
                    "Skipping memory with invalid question embedding: %s",
                    memory.get("_id"),
                )
                continue

            question_similarity = float(
                np.dot(query_vector, question_vector)
            )

            combined_similarity = (
                self.QUESTION_WEIGHT * question_similarity
                + self.CONTENT_WEIGHT * content_similarity
            )

            if combined_similarity < min_similarity:
                continue

            memory["_id"] = str(memory["_id"])
            memory["similarity"] = combined_similarity
            memory["question_similarity"] = question_similarity
            memory["content_similarity"] = content_similarity

            scored_memories.append(memory)

        scored_memories.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        for rank, memory in enumerate(scored_memories[:limit], start=1):
            print(
                f"[MEMORY RANK {rank}] "
                f"agent={agent_name} | "
                f"combined={memory['similarity']:.3f} | "
                f"question={memory['question_similarity']:.3f} | "
                f"content={memory['content_similarity']:.3f} | "
                f"type={memory.get('memory_type')} | "
                f"question_text={memory.get('metadata', {}).get('question', '')!r} | "
                f"content={memory.get('content', '')[:160]!r}"
            )

        return scored_memories[:limit]
