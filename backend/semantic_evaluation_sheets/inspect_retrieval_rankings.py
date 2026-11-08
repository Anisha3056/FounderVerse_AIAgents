
from time import perf_counter

import numpy as np

from app.database.mongodb import mongodb
from app.memory.memory_manager import generate_embedding


COMPANY_ID = "6ac27f9d8a6f61aa7c426a23"

TOP_K = 5
MIN_SIMILARITY = 0.25

CONFIGURATIONS = [
    ("Question only", 1.0, 0.0),
    ("Current 70/30", 0.7, 0.3),
    ("Balanced 50/50", 0.5, 0.5),
    ("Content only", 0.0, 1.0),
]

TEST_CASES = [
    {
        "topic": "acquisition",
        "query": (
            "How can we attract more paying users "
            "without depending entirely on word of mouth?"
        ),
    },
    {
        "topic": "reliability",
        "query": (
            "What should we prioritize so our product can "
            "handle a much larger user base without interruptions?"
        ),
    },
    {
        "topic": "expenses",
        "query": (
            "Where can we trim recurring costs while "
            "preserving our ability to grow?"
        ),
    },
    {
        "topic": "marketing_budget",
        "query": (
            "Would a modest increase in promotional spending "
            "be financially sensible for us?"
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


def get_valid_vector(value, expected_shape):
    if not isinstance(value, list) or not value:
        return None

    vector = np.asarray(value, dtype=np.float32)

    if vector.shape != expected_shape:
        return None

    if not np.all(np.isfinite(vector)):
        return None

    return vector


def retrieve(
    query_vector,
    memories,
    question_weight,
    content_weight,
):
    results = []

    for memory in memories:
        content_vector = get_valid_vector(
            memory.get("embedding"),
            query_vector.shape,
        )

        if content_vector is None:
            continue

        question_text = get_question(memory)
        question_embedding = memory.get("question_embedding")

        # Missing embeddings are calculated only in memory.
        # This script never writes to MongoDB.
        if not isinstance(question_embedding, list) or not question_embedding:
            question_embedding = generate_embedding(question_text)

        question_vector = get_valid_vector(
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
            results.append({
                "id": str(memory.get("_id", "unknown")),
                "question": question_text,
                "score": score,
                "question_similarity": question_similarity,
                "content_similarity": content_similarity,
            })

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:TOP_K]


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
        print("Warming up local embedding model...")

        generate_embedding("retrieval ranking inspection warm-up")

        # Prepare each query vector once for a fair comparison.
        query_vectors = {
            case["topic"]: np.asarray(
                generate_embedding(case["query"]),
                dtype=np.float32,
            )
            for case in TEST_CASES
        }

        total_comparisons = 0
        changed_rankings = 0
        different_top_results = 0

        print("\nREAD-ONLY RETRIEVAL RANKING INSPECTION")
        print("=" * 90)

        for case in TEST_CASES:
            query_vector = query_vectors[case["topic"]]

            print(f"\n\nTOPIC: {case['topic']}")
            print(f"QUERY: {case['query']}")
            print("=" * 90)

            for agent in AGENTS:
                agent_memories = [
                    memory for memory in memories
                    if memory.get("agent_name") == agent
                ]

                if not agent_memories:
                    print(f"\n{agent}: no memories found.")
                    continue

                print(f"\n--- {agent} ---")

                configuration_results = {}

                # Time each configuration's local scoring.
                for name, q_weight, c_weight in CONFIGURATIONS:
                    start = perf_counter()

                    results = retrieve(
                        query_vector=query_vector,
                        memories=agent_memories,
                        question_weight=q_weight,
                        content_weight=c_weight,
                    )

                    elapsed_ms = (
                        perf_counter() - start
                    ) * 1000

                    configuration_results[name] = results

                    print(
                        f"\n{name} "
                        f"(Q={q_weight:.1f}, C={c_weight:.1f}) "
                        f"[{elapsed_ms:.2f} ms]"
                    )

                    if not results:
                        print("  No results passed the threshold.")
                        continue

                    for rank, result in enumerate(results, start=1):
                        print(
                            f"  {rank}. score={result['score']:.4f} "
                            f"| Q={result['question_similarity']:.4f} "
                            f"| C={result['content_similarity']:.4f}"
                        )
                        print(f"     Memory ID: {result['id']}")
                        print(f"     Question: {result['question']}")

                # Compare the current configuration with each alternative.
                baseline = configuration_results["Current 70/30"]
                baseline_ids = [item["id"] for item in baseline]
                baseline_top = baseline_ids[0] if baseline_ids else None

                for name, _, _ in CONFIGURATIONS:
                    if name == "Current 70/30":
                        continue

                    alternative = configuration_results[name]
                    alternative_ids = [
                        item["id"] for item in alternative
                    ]
                    alternative_top = (
                        alternative_ids[0]
                        if alternative_ids
                        else None
                    )

                    total_comparisons += 1

                    if baseline_ids != alternative_ids:
                        changed_rankings += 1

                    if baseline_top != alternative_top:
                        different_top_results += 1

                    print(
                        f"\nComparison: Current 70/30 vs {name}"
                    )
                    print(
                        "  Same ordered top-five IDs: "
                        f"{baseline_ids == alternative_ids}"
                    )
                    print(
                        "  Same first result: "
                        f"{baseline_top == alternative_top}"
                    )

        print("\n\n" + "=" * 90)
        print("RANKING DIFFERENCE SUMMARY")
        print("=" * 90)
        print(f"Comparisons made: {total_comparisons}")
        print(f"Comparisons with changed top-five ordering: {changed_rankings}")
        print(f"Comparisons with a different first result: {different_top_results}")

        print("\nInterpretation:")
        print(
            "- Changed rankings show that weights affect ordering, "
            "not that the new ordering is necessarily better."
        )
        print(
            "- A different first result needs manual relevance review."
        )
        print(
            "- Memory IDs help distinguish repeated questions "
            "stored as separate records."
        )

        print("\nNo MongoDB documents were modified.")
        print("No Gemini API calls were made.")

    finally:
        mongodb.close()


if __name__ == "__main__":
    main()
