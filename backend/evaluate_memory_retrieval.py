
from time import perf_counter

import numpy as np

from app.database.mongodb import mongodb
from app.memory.memory_manager import generate_embedding

COMPANY_ID = "6ac27f9d8a6f61aa7c426a23"

QUESTION_WEIGHT = 0.7
CONTENT_WEIGHT = 0.3
TOP_K = 5
MIN_SIMILARITY = 0.25

# These are deliberately paraphrased rather than copied from stored questions.
TEST_CASES = [
    {
        "topic": "acquisition",
        "query": (
            "How can we attract more paying users without depending "
            "entirely on word of mouth?"
        ),
        "label_terms": (
            "customer acquisition",
            "customer incoming count",
            "increase the number of new customers",
            "increase our customer in number",
            "customer acquisition",
        ),
    },
    {
        "topic": "reliability",
        "query": (
            "What should we prioritize so our product can handle a "
            "much larger user base without service interruptions?"
        ),
        "label_terms": ("platform reliability", "scalability"),
    },
    {
        "topic": "expenses",
        "query": (
            "Where can we trim recurring costs while preserving "
            "our ability to grow?"
        ),
        "label_terms": (
            "reduce operating expenses",
            "reducing operating expenses",
        ),
    },
    {
        "topic": "marketing_budget",
        "query": (
            "Would a modest increase in promotional spending be "
            "financially sensible for us?"
        ),
        "label_terms": ("budget for marketing", "marketing budget"),
    },
]

AGENTS = [
    "CTO Agent",
    "Finance Agent",
    "Sales Agent",
    "Marketing Agent",
    "Legal Agent",
]


def question_for(memory):
    metadata = memory.get("metadata") or {}
    question = metadata.get("question", "")
    return question.strip() if isinstance(question, str) else ""


def is_relevant(memory, test_case):
    """Initial human-defined topic labels based on stored questions."""
    question = question_for(memory).lower()
    return any(term in question for term in test_case["label_terms"])


def evaluate_one(query_vector, memories, test_case):
    ranked = []

    for memory in memories:
        content = memory.get("content", "")
        if not isinstance(content, str) or not content.strip():
            continue

        content_embedding = memory.get("embedding")
        if not isinstance(content_embedding, list) or not content_embedding:
            continue

        content_vector = np.asarray(content_embedding, dtype=np.float32)
        if content_vector.shape != query_vector.shape:
            continue
        if not np.all(np.isfinite(content_vector)):
            continue

        question_text = question_for(memory) or content
        question_embedding = memory.get("question_embedding")

        # Read-only fallback: calculate missing question embeddings in memory.
        if not isinstance(question_embedding, list) or not question_embedding:
            question_embedding = generate_embedding(question_text)

        question_vector = np.asarray(question_embedding, dtype=np.float32)
        if question_vector.shape != query_vector.shape:
            continue
        if not np.all(np.isfinite(question_vector)):
            continue

        content_similarity = float(np.dot(query_vector, content_vector))
        question_similarity = float(np.dot(query_vector, question_vector))
        score = (
            QUESTION_WEIGHT * question_similarity
            + CONTENT_WEIGHT * content_similarity
        )

        if score >= MIN_SIMILARITY:
            ranked.append({
                "score": score,
                "question": question_text,
                "relevant": is_relevant(memory, test_case),
            })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:TOP_K]


def main():
    try:
        mongodb.connect()
        collection = mongodb.get_database()["agent_memories"]

        memories = list(collection.find({"company_id": COMPANY_ID}))
        if not memories:
            print("No memories found for the configured company ID.")
            return

        print(f"Loaded {len(memories)} memories.")
        print("Loading/warming up the local embedding model...")

        # Warm up so initial model loading doesn't dominate retrieval latency.
        generate_embedding("warm-up query for retrieval evaluation")

        total_precision = 0.0
        total_recall = 0.0
        total_mrr = 0.0
        total_latency_ms = 0.0
        evaluated = 0
        skipped = 0

        print("\n" + "=" * 90)
        print("READ-ONLY SEMANTIC MEMORY RETRIEVAL EVALUATION")
        print("=" * 90)

        for test_case in TEST_CASES:
            for agent in AGENTS:
                agent_memories = [
                    m for m in memories
                    if m.get("agent_name") == agent
                ]

                relevant_total = sum(
                    is_relevant(m, test_case) for m in agent_memories
                )

                # Recall cannot be meaningfully computed without any
                # known relevant memories for this agent/topic.
                if relevant_total == 0:
                    skipped += 1
                    print(
                        f"\n[{test_case['topic']}] {agent}: "
                        "SKIPPED — no labelled relevant memories."
                    )
                    continue

                start = perf_counter()
                query_vector = np.asarray(
                    generate_embedding(test_case["query"]),
                    dtype=np.float32,
                )
                results = evaluate_one(
                    query_vector, agent_memories, test_case
                )
                elapsed_ms = (perf_counter() - start) * 1000

                relevant_retrieved = sum(
                    result["relevant"] for result in results
                )
                precision = relevant_retrieved / TOP_K
                recall = relevant_retrieved / relevant_total

                reciprocal_rank = 0.0
                for rank, result in enumerate(results, start=1):
                    if result["relevant"]:
                        reciprocal_rank = 1.0 / rank
                        break

                evaluated += 1
                total_precision += precision
                total_recall += recall
                total_mrr += reciprocal_rank
                total_latency_ms += elapsed_ms

                print(
                    f"\n[{test_case['topic']}] {agent}\n"
                    f"Query: {test_case['query']}\n"
                    f"Relevant memories available: {relevant_total}\n"
                    f"Relevant in top {TOP_K}: {relevant_retrieved}\n"
                    f"Precision@{TOP_K}: {precision:.3f} | "
                    f"Recall@{TOP_K}: {recall:.3f} | "
                    f"RR: {reciprocal_rank:.3f} | "
                    f"Latency: {elapsed_ms:.2f} ms"
                )

                for rank, result in enumerate(results, start=1):
                    marker = "RELEVANT" if result["relevant"] else "other"
                    print(
                        f"  {rank}. [{marker}] "
                        f"score={result['score']:.3f} | "
                        f"{result['question']}"
                    )

        print("\n" + "=" * 90)
        print("AGGREGATE RESULTS")
        print("=" * 90)

        if evaluated:
            print(f"Evaluations completed: {evaluated}")
            print(f"Evaluations skipped: {skipped}")
            print(f"Mean Precision@{TOP_K}: {total_precision / evaluated:.3f}")
            print(f"Mean Recall@{TOP_K}: {total_recall / evaluated:.3f}")
            print(f"Mean Reciprocal Rank: {total_mrr / evaluated:.3f}")
            print(
                "Mean warm retrieval latency: "
                f"{total_latency_ms / evaluated:.2f} ms"
            )
        else:
            print("No eligible evaluations; inspect the topic labels.")

        print("\nNo MongoDB documents were modified.")

    finally:
        mongodb.close()


if __name__ == "__main__":
    main()
