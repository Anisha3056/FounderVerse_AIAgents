"""
Human-validated memory retrieval evaluation: recency baseline plus semantic configurations.

Run from the backend directory:
    python evaluate_human_ground_truth_with_recency.py

Safety:
- Reads MongoDB only (collection.find; no insert/update/delete).
- Does not call Gemini.
- Uses the existing local generate_embedding function.
- Does not change production retrieval settings.
- Writes evaluation CSV/JSON reports locally only.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path
from time import perf_counter

import numpy as np

from app.database.mongodb import mongodb
from app.memory.memory_manager import generate_embedding

COMPANY_ID = "6ac27f9d8a6f61aa7c426a23"
TOP_K = 5
MIN_SIMILARITY = 0.25

CONFIGURATIONS = [
    ("Stage 1 - Recency only", 0.0, 0.0, "recency", None),
    ("Question only", 1.0, 0.0, "semantic", None),
    ("Current baseline 70/30", 0.7, 0.3, "semantic", None),
    ("Balanced 50/50", 0.5, 0.5, "semantic", None),
    ("Content only", 0.0, 1.0, "semantic", None),
    ("Stage 3 - MMR lambda 0.8", 0.7, 0.3, "mmr", 0.8),
    ("Stage 3 - MMR lambda 0.6", 0.7, 0.3, "mmr", 0.6),
    ("Stage 3 - MMR lambda 0.4", 0.7, 0.3, "mmr", 0.4),
]

AGENTS = [
    "CTO Agent",
    "Finance Agent",
    "Sales Agent",
    "Marketing Agent",
    "Legal Agent",
]

HERE = Path(__file__).resolve().parent
GROUND_TRUTH_PATH = HERE / "human_ground_truth_labels_complete.json"
OUT_DIR = HERE / "human_retrieval_evaluation_stage3_mmr_positive_cosine"
OUT_DIR.mkdir(exist_ok=True)


def valid_vector(value, expected_shape):
    if not isinstance(value, (list, tuple)) or len(value) == 0:
        return None
    try:
        vector = np.asarray(value, dtype=np.float32)
    except (TypeError, ValueError):
        return None
    if vector.shape != expected_shape or not np.all(np.isfinite(vector)):
        return None
    return vector


def memory_question(memory):
    metadata = memory.get("metadata") or {}
    question = metadata.get("question", "")
    if isinstance(question, str) and question.strip():
        return question.strip()
    content = memory.get("content", "")
    return content.strip() if isinstance(content, str) else ""


def load_ground_truth():
    rows = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    labels = {}
    queries = {}
    coverage = defaultdict(lambda: {"labeled": 0, "relevant": 0, "not_relevant": 0, "borderline": 0, "unknown": 0})
    for row in rows:
        qid = row["query_id"]
        queries[qid] = row["query_text"]
        key = (qid, row["memory_id"], row["agent_name"])
        labels[key] = row["label"]
        coverage[qid]["labeled"] += 1
        bucket = row["label"] if row["label"] in {"relevant", "borderline", "unknown", "not_relevant"} else "unknown"
        coverage[qid][bucket] += 1
    metadata = {}
    for row in rows:
        key = (row["query_id"], row["memory_id"], row["agent_name"])
        metadata[key] = {
            "redundancy_group": row.get("redundancy_group"),
            "redundancy_assessed": bool(row.get("redundancy_assessed", False)),
            "raw_label": row.get("raw_label", row["label"]),
            "is_redundant_label": bool(row.get("is_redundant_label", False)),
        }
    return queries, labels, coverage, metadata


def retrieve(query_vector, memories, q_weight, c_weight):
    ranked = []
    for memory in memories:
        content_vector = valid_vector(memory.get("embedding"), query_vector.shape)
        if content_vector is None:
            continue

        question_text = memory_question(memory)
        question_embedding = memory.get("question_embedding")
        if not isinstance(question_embedding, list) or not question_embedding:
            # In-memory fallback only; no MongoDB write.
            question_embedding = generate_embedding(question_text)

        question_vector = valid_vector(question_embedding, query_vector.shape)
        if question_vector is None:
            continue

        q_sim = float(np.dot(query_vector, question_vector))
        c_sim = float(np.dot(query_vector, content_vector))
        score = q_weight * q_sim + c_weight * c_sim

        if score >= MIN_SIMILARITY:
            ranked.append({
                "memory_id": str(memory.get("_id", "")),
                "agent_name": str(memory.get("agent_name", "")),
                "stored_question": question_text,
                "score": score,
                "question_similarity": q_sim,
                "content_similarity": c_sim,
            })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:TOP_K]



def retrieve_recent(agent_memories, limit=TOP_K):
    """
    Stage 1: rank memories by created_at, newest first.
    Evaluation-only: no embedding generation and no database writes.
    Missing timestamps sort after dated memories; _id provides a stable tie-break.
    """
    if limit <= 0:
        return []

    def recency_key(memory):
        created_at = memory.get("created_at")
        if hasattr(created_at, "timestamp"):
            try:
                timestamp = created_at.timestamp()
            except (OverflowError, OSError, ValueError):
                timestamp = float("-inf")
        else:
            timestamp = float("-inf")
        # The ID tie-breaker makes equal/missing timestamps deterministic.
        return (timestamp, str(memory.get("_id", "")))

    ordered = sorted(agent_memories, key=recency_key, reverse=True)
    ranked = []
    for memory in ordered[:limit]:
        ranked.append({
            "memory_id": str(memory.get("_id", "")),
            "agent_name": str(memory.get("agent_name", "")),
            "stored_question": memory_question(memory),
            "score": None,
            "question_similarity": None,
            "content_similarity": None,
        })
    return ranked


def retrieve_mmr(query_vector, memories, q_weight, c_weight, lambda_value, candidate_pool=15):
    """
    Stage 3: retrieve a larger semantic candidate pool, then rerank with MMR.
    Relevance score remains the existing weighted question/content score.
    Redundancy penalty uses only positive cosine similarity between stored content embeddings; negative similarity is clamped to zero.
    Evaluation-only: no database writes and no ground-truth labels used for ranking.
    """
    candidates = []
    for memory in memories:
        content_vector = valid_vector(memory.get("embedding"), query_vector.shape)
        if content_vector is None:
            continue

        question_text = memory_question(memory)
        question_embedding = memory.get("question_embedding")
        if not isinstance(question_embedding, list) or not question_embedding:
            # In-memory fallback only; no MongoDB write.
            question_embedding = generate_embedding(question_text)

        question_vector = valid_vector(question_embedding, query_vector.shape)
        if question_vector is None:
            continue

        q_sim = float(np.dot(query_vector, question_vector))
        c_sim = float(np.dot(query_vector, content_vector))
        relevance = q_weight * q_sim + c_weight * c_sim
        if relevance >= MIN_SIMILARITY:
            candidates.append({
                "memory_id": str(memory.get("_id", "")),
                "agent_name": str(memory.get("agent_name", "")),
                "stored_question": question_text,
                "score": relevance,
                "question_similarity": q_sim,
                "content_similarity": c_sim,
                "_content_vector": content_vector,
            })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    candidates = candidates[:max(TOP_K, candidate_pool)]

    selected = []
    remaining = candidates.copy()
    while remaining and len(selected) < TOP_K:
        best_item = None
        best_mmr_score = float("-inf")
        for candidate in remaining:
            if not selected:
                max_redundancy = 0.0
            else:
                # Penalize only positive cosine similarity. Negative cosine values
                # are treated as zero redundancy, never as a bonus to the candidate.
                max_redundancy = max(
                    0.0,
                    max(
                        float(np.dot(candidate["_content_vector"], chosen["_content_vector"]))
                        for chosen in selected
                    )
                )
            mmr_score = (
                lambda_value * candidate["score"]
                - (1.0 - lambda_value) * max_redundancy
            )
            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                best_item = candidate
        selected.append(best_item)
        remaining.remove(best_item)

    for item in selected:
        item.pop("_content_vector", None)
    return selected


def label_is_relevant(label, include_borderline=False):
    return label == "relevant" or (include_borderline and label == "borderline")


def main():
    queries, labels, coverage, label_metadata = load_ground_truth()
    all_rank_rows = []
    metric_rows = []

    try:
        mongodb.connect()
        collection = mongodb.get_database()["agent_memories"]
        memories = list(collection.find({"company_id": COMPANY_ID}))
        if not memories:
            raise RuntimeError("No memories found for configured COMPANY_ID.")

        print(f"Loaded {len(memories)} memories (read-only).")
        print("Warming local embedding model...")
        generate_embedding("human-ground-truth evaluation warm-up")

        query_vectors = {
            qid: np.asarray(generate_embedding(query), dtype=np.float32)
            for qid, query in queries.items()
        }

        # Use human-reviewed labels only. No keyword-derived labels are used.
        for config_name, q_weight, c_weight, strategy, lambda_value in CONFIGURATIONS:
            for qid, query in queries.items():
                query_vector = query_vectors[qid]
                for agent in AGENTS:
                    agent_memories = [m for m in memories if m.get("agent_name") == agent]
                    start = perf_counter()
                    if strategy == "recency":
                        ranked = retrieve_recent(agent_memories, TOP_K)
                    elif strategy == "mmr":
                        ranked = retrieve_mmr(
                            query_vector, agent_memories, q_weight, c_weight,
                            lambda_value=lambda_value, candidate_pool=15
                        )
                    else:
                        ranked = retrieve(query_vector, agent_memories, q_weight, c_weight)
                    elapsed_ms = (perf_counter() - start) * 1000

                    relevant_total = sum(
                        1 for (label_qid, _mid, label_agent), label in labels.items()
                        if label_qid == qid and label_agent == agent and label == "relevant"
                    )
                    relevant_groups = {
                        label_metadata.get((label_qid, mid, label_agent), {}).get("redundancy_group") or mid
                        for (label_qid, mid, label_agent), label in labels.items()
                        if label_qid == qid and label_agent == agent and label == "relevant"
                    }
                    redundancy_assessed = all(
                        label_metadata.get((qid, mid, agent), {}).get("redundancy_assessed", False)
                        for (label_qid, mid, label_agent) in labels
                        if label_qid == qid and label_agent == agent
                    )
                    borderline_total = sum(
                        1 for (label_qid, _mid, label_agent), label in labels.items()
                        if label_qid == qid and label_agent == agent and label == "borderline"
                    )

                    judged = []
                    for rank, result in enumerate(ranked, start=1):
                        key = (qid, result["memory_id"], agent)
                        label = labels.get(key, "unknown")
                        meta = label_metadata.get(key, {})
                        row = {
                            "configuration": config_name,
                            "question_weight": q_weight,
                            "content_weight": c_weight,
                            "retrieval_strategy": strategy,
                            "mmr_lambda": lambda_value,
                            "query_id": qid,
                            "query_text": query,
                            "agent_name": agent,
                            "rank": rank,
                            **result,
                            "human_label": label,
                            "raw_human_label": meta.get("raw_label", label),
                            "redundancy_group": meta.get("redundancy_group") or result["memory_id"],
                            "redundancy_assessed": meta.get("redundancy_assessed", False),
                            "is_human_relevant": label == "relevant",
                            "is_borderline": label == "borderline",
                            "latency_ms_for_query_agent": round(elapsed_ms, 3),
                        }
                        all_rank_rows.append(row)
                        if label != "unknown":
                            judged.append((rank, label))

                    # Redundancy metrics are only reported for queries whose ground truth explicitly assessed redundancy (Q1/Q2).
                    retrieved_groups = [
                        label_metadata.get((qid, result["memory_id"], agent), {}).get("redundancy_group") or result["memory_id"]
                        for result in ranked
                    ]
                    duplicate_results = len(retrieved_groups) - len(set(retrieved_groups))
                    relevant_retrieved_groups = {
                        label_metadata.get((qid, result["memory_id"], agent), {}).get("redundancy_group") or result["memory_id"]
                        for result in ranked
                        if labels.get((qid, result["memory_id"], agent), "unknown") == "relevant"
                    }
                    unique_relevant_count = len(relevant_retrieved_groups)
                    unique_coverage = (
                        unique_relevant_count / len(relevant_groups) if relevant_groups else None
                    ) if redundancy_assessed else None
                    redundancy_rate = (duplicate_results / TOP_K) if redundancy_assessed else None

                    judged_relevant_retrieved = sum(label == "relevant" for _, label in judged)
                    borderline_retrieved = sum(label == "borderline" for _, label in judged)
                    judged_count = len(judged)
                    # Judged precision excludes unreviewed memories from its denominator.
                    judged_precision = (
                        judged_relevant_retrieved / judged_count if judged_count else None
                    )
                    # Conservative precision uses five slots; unknowns do not receive credit.
                    conservative_precision = judged_relevant_retrieved / TOP_K
                    pooled_recall = (
                        judged_relevant_retrieved / relevant_total if relevant_total else None
                    )
                    rr = 0.0
                    for rank, label in judged:
                        if label == "relevant":
                            rr = 1.0 / rank
                            break

                    # Sensitivity: borderline counts as relevant.
                    relevant_plus_borderline = judged_relevant_retrieved + borderline_retrieved
                    judged_precision_plus_borderline = (
                        relevant_plus_borderline / judged_count if judged_count else None
                    )
                    recall_plus_borderline = (
                        relevant_plus_borderline / (relevant_total + borderline_total)
                        if (relevant_total + borderline_total) else None
                    )

                    metric_rows.append({
                        "configuration": config_name,
                        "question_weight": q_weight,
                        "content_weight": c_weight,
                        "retrieval_strategy": strategy,
                        "mmr_lambda": lambda_value,
                        "query_id": qid,
                        "query_text": query,
                        "agent_name": agent,
                        "retrieved_count": len(ranked),
                        "judged_in_top_k": judged_count,
                        "unknown_in_top_k": len(ranked) - judged_count,
                        "relevant_total_judged_for_agent": relevant_total,
                        "borderline_total_for_agent": borderline_total,
                        "relevant_retrieved": judged_relevant_retrieved,
                        "borderline_retrieved": borderline_retrieved,
                        "unique_relevant_coverage_at_5_count": unique_relevant_count if redundancy_assessed else None,
                        "normalized_unique_relevant_coverage_at_5": unique_coverage,
                        "redundancy_rate_at_5": redundancy_rate,
                        "redundancy_assessed": redundancy_assessed,
                        "judged_precision_at_5": judged_precision,
                        "conservative_precision_at_5": conservative_precision,
                        "pooled_recall_at_5": pooled_recall,
                        "reciprocal_rank": rr,
                        "judged_precision_at_5_including_borderline": judged_precision_plus_borderline,
                        "recall_at_5_including_borderline": recall_plus_borderline,
                        "local_scoring_latency_ms": round(elapsed_ms, 3),
                    })

        # Write raw ranked results and per-query/agent metrics.
        rank_path = OUT_DIR / "ranked_results.csv"
        metric_path = OUT_DIR / "metrics_by_query_agent.csv"
        summary_path = OUT_DIR / "aggregate_summary.csv"

        def write_csv(path, rows):
            if not rows:
                return
            with path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

        write_csv(rank_path, all_rank_rows)
        write_csv(metric_path, metric_rows)

        # Aggregate means by configuration. Report pooled recall only over judged relevant labels.
        agg = []
        for config_name, q_weight, c_weight, strategy, lambda_value in CONFIGURATIONS:
            subset = [r for r in metric_rows if r["configuration"] == config_name]
            def mean_non_null(field):
                vals = [r[field] for r in subset if r[field] is not None]
                return sum(vals) / len(vals) if vals else None
            agg.append({
                "configuration": config_name,
                "question_weight": q_weight,
                "content_weight": c_weight,
                "retrieval_strategy": strategy,
                "mmr_lambda": lambda_value,
                "query_agent_cases": len(subset),
                "mean_judged_precision_at_5": mean_non_null("judged_precision_at_5"),
                "mean_conservative_precision_at_5": mean_non_null("conservative_precision_at_5"),
                "mean_pooled_recall_at_5": mean_non_null("pooled_recall_at_5"),
                "mean_mrr": mean_non_null("reciprocal_rank"),
                "mean_borderline_inclusive_precision": mean_non_null("judged_precision_at_5_including_borderline"),
                "mean_borderline_inclusive_recall": mean_non_null("recall_at_5_including_borderline"),
                "mean_local_scoring_latency_ms": mean_non_null("local_scoring_latency_ms"),
                "mean_normalized_unique_relevant_coverage_at_5": mean_non_null("normalized_unique_relevant_coverage_at_5"),
                "mean_redundancy_rate_at_5": mean_non_null("redundancy_rate_at_5"),
                "warning": "Stage 1 is reconstructed, not confirmed historical production behavior. Stage 3 MMR uses semantic relevance plus cosine redundancy penalty on content embeddings; ground-truth labels are not used by ranking. Q1/Q2 redundancy metrics only; Q3/Q4 redundancy was not separately labeled."
            })
        write_csv(summary_path, agg)

        print("\nAGGREGATE HUMAN-LABEL RESULTS")
        print("=" * 100)
        for row in agg:
            print(
                f"{row['configuration']:<24} "
                f"Judged-P@5={row['mean_judged_precision_at_5']:.3f} "
                f"Conservative-P@5={row['mean_conservative_precision_at_5']:.3f} "
                f"Pooled-R@5={row['mean_pooled_recall_at_5']:.3f} "
                f"MRR={row['mean_mrr']:.3f} "
                f"Latency={row['mean_local_scoring_latency_ms']:.2f}ms"
            )
        print("\nReports written to:", OUT_DIR)
        print("MongoDB documents modified: 0")
        print("Gemini API calls made: 0")
        print("\nMetric notes:")
        print("- Judged Precision@5 excludes unreviewed results from its denominator.")
        print("- Conservative Precision@5 divides relevant hits by 5; unknown hits get no credit.")
        print("- Pooled Recall@5 uses relevant labels currently available for that query+agent.")
        print("- Q1/Q2 have 58/58 human labels each. Q3/Q4 label coverage is also loaded from the existing ground truth.")
        print("- Unique relevant coverage and redundancy rate are reported only for Q1/Q2, where redundancy links were reviewed.")
        print("- Redundant-but-relevant labels count as relevant for precision/recall; raw human labels are preserved separately.")
        print("- Borderline-inclusive metrics are reported separately.")
        print("- Latency is local retrieval/scoring time, not end-to-end API latency.")
        print("- Stage 1 is reconstructed from get_recent_memories semantics; it is not evidence that production previously used this strategy.")
        print("- Stage 1 score and similarity fields are blank/None by design; ranking is based only on created_at.")
        print("- Stage 3 MMR uses a top-15 semantic candidate pool and positive-only content-embedding cosine similarity to penalize redundancy.")
        print("- MMR lambda values 0.8, 0.6, 0.4 are offline experiments; production retrieval is unchanged.")
    finally:
        mongodb.close()


if __name__ == "__main__":
    main()
