
from time import perf_counter

import numpy as np

from app.database.mongodb import mongodb
from app.memory.memory_manager import generate_embedding


COMPANY_ID = "6ac27f9d8a6f61aa7c426a23"

TOP_K = 5
MIN_SIMILARITY = 0.25

CONFIGURATIONS = [
    ("Question only", 1.0, 0.0),
    ("Current baseline", 0.7, 0.3),
    ("Balanced", 0.5, 0.5),
    ("Content only", 0.0, 1.0),
]

TEST_CASES = [
    {
        "topic": "acquisition",
        "query": (
            "How can we attract more paying users "
            "without depending entirely on word of mouth?"
        ),
        "label_terms": (
            "customer acquisition",
            "customer incoming count",
            "increase the number of new customers",
            "increase our customer in number",
        ),
    },
    {
        "topic": "reliability",
        "query": (
            "What should we prioritize so our product "
            "can handle a much larger user base without service interruptions?"
        ),
        "label_terms": (
            "platform reliability",
            "scalability",
        ),
    },
    {
        "topic": "expenses",
        "query": (
            "Where can we trim recurring costs "
            "while preserving our ability to grow?"
        ),
        "label_terms": (
            "reduce operating expenses",
            "reducing operating expenses",
        ),
    },
    {
        "topic": "marketing_budget",
        "query": (
            "Would a modest increase in promotional "
            "spending be financially sensible for us?"
        ),
        "label_terms": (
            "budget for marketing",
            "marketing budget",
        ),
    },
]

AGENTS = [
    "CTO Agent",
    "Finance Agent",
    "Sales Agent",
    "Marketing Agent",
    "Legal Agent",
]


def get_question(memory):
    metadata = memory.get("metadata") or {}
    question = metadata.get("question", "")

    if isinstance(question, str) and question.strip():
        return question.strip()

    return memory.get("content", "")


def is_relevant(memory, test_case):
    question = get_question(memory).lower()

    return any(
        term in question
        for term in test_case["label_terms"]
    )


def valid_vector(value, expected_shape):
    if not isinstance(value, list) or not value:
        return None

    vector = np.asarray(value, dtype=np.float32)

    if vector.shape != expected_shape:
        return None

    if not np.all(np.isfinite(vector)):
        return None

    return vector


def rank_memories(
    query_vector,
    memories,
    test_case,
    question_weight,
    content_weight,
):
    ranked = []

    for memory in memories:
        content_embedding = memory.get("embedding")

        content_vector = valid_vector(
            content_embedding,
            query_vector.shape,
        )

        if content_vector is None:
            continue

        question_text = get_question(memory)
        question_embedding = memory.get("question_embedding")

        # Read-only fallback: calculate missing embeddings in memory.
        if not isinstance(question_embedding, list) or not question_embedding:
            question_embedding = generate_embedding(question_text)

        question_vector = valid_vector(
            question_embedding,
            query_vector.shape,
        )

        if question_vector is None:
            continue

        question_similarity = float(
            np.dot(query_vector, question_vector)
        )

        content_similarity = float(
            np.dot(query_vector, content_vector)
        )

        score = (
            question_weight * question_similarity
            + content_weight * content_similarity
        )

        if score >= MIN_SIMILARITY:
            ranked.append({
                "score": score,
                "question": question_text,
                "relevant": is_relevant(memory, test_case),
            })

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return ranked[:TOP_K]


def main():
    try:
        mongodb.connect()

        collection = mongodb.get_database()["agent_memories"]

        memories = list(
            collection.find({"company_id": COMPANY_ID})
        )

        if not memories:
            print("No memories found for the configured company ID.")
            return

        print(f"Loaded {len(memories)} memories.")
        print("Warming up the local embedding model...")

        generate_embedding("retrieval comparison warm-up query")

        # Precompute query embeddings once for a fairer comparison.
        query_vectors = {}

        for case in TEST_CASES:
            query_vectors[case["topic"]] = np.asarray(
                generate_embedding(case["query"]),
                dtype=np.float32,
            )

        print("\nREAD-ONLY RETRIEVAL WEIGHT COMPARISON")
        print("=" * 78)

        summaries = []

        for name, q_weight, c_weight in CONFIGURATIONS:
            total_precision = 0.0
            total_recall = 0.0
            total_rr = 0.0
            total_latency = 0.0
            evaluated = 0
            skipped = 0

            print(
                f"\n{name}: question={q_weight:.1f}, "
                f"content={c_weight:.1f}"
            )
            print("-" * 78)

            for case in TEST_CASES:
                query_vector = query_vectors[case["topic"]]

                for agent in AGENTS:
                    agent_memories = [
                        memory
                        for memory in memories
                        if memory.get("agent_name") == agent
                    ]

                    relevant_total = sum(
                        is_relevant(memory, case)
                        for memory in agent_memories
                    )

                    if relevant_total == 0:
                        skipped += 1
                        continue

                    start = perf_counter()

                    results = rank_memories(
                        query_vector=query_vector,
                        memories=agent_memories,
                        test_case=case,
                        question_weight=q_weight,
                        content_weight=c_weight,
                    )

                    latency_ms = (
                        perf_counter() - start
                    ) * 1000

                    relevant_retrieved = sum(
                        result["relevant"]
                        for result in results
                    )

                    # Empty top-k slots count as non-relevant.
                    precision = relevant_retrieved / TOP_K

                    recall = (
                        relevant_retrieved / relevant_total
                    )

                    reciprocal_rank = 0.0

                    for rank, result in enumerate(
                        results, start=1
                    ):
                        if result["relevant"]:
                            reciprocal_rank = 1.0 / rank
                            break

                    evaluated += 1
                    total_precision += precision
                    total_recall += recall
                    total_rr += reciprocal_rank
                    total_latency += latency_ms

            if evaluated == 0:
                print("No eligible evaluations.")
                continue

            mean_precision = total_precision / evaluated
            mean_recall = total_recall / evaluated
            mean_rr = total_rr / evaluated
            mean_latency = total_latency / evaluated

            summary = {
                "name": name,
                "question_weight": q_weight,
                "content_weight": c_weight,
                "evaluated": evaluated,
                "skipped": skipped,
                "precision": mean_precision,
                "recall": mean_recall,
                "mrr": mean_rr,
                "latency_ms": mean_latency,
            }

            summaries.append(summary)

            print(f"Evaluations: {evaluated}")
            print(f"Skipped: {skipped}")
            print(f"Mean Precision@{TOP_K}: {mean_precision:.3f}")
            print(f"Mean Recall@{TOP_K}: {mean_recall:.3f}")
            print(f"Mean Reciprocal Rank: {mean_rr:.3f}")
            print(f"Mean local latency: {mean_latency:.2f} ms")

        print("\n" + "=" * 100)
        print("COMPARISON SUMMARY")
        print("=" * 100)

        print(
            f"{'Configuration':<20}"
            f"{'Precision@5':>14}"
            f"{'Recall@5':>12}"
            f"{'MRR':>10}"
            f"{'Latency(ms)':>15}"
        )

        for result in summaries:
            print(
                f"{result['name']:<20}"
                f"{result['precision']:>14.3f}"
                f"{result['recall']:>12.3f}"
                f"{result['mrr']:>10.3f}"
                f"{result['latency_ms']:>15.2f}"
            )

        print("\nNo MongoDB documents were modified.")
        print("No Gemini API calls were made.")

    finally:
        mongodb.close()


if __name__ == "__main__":
    main()
