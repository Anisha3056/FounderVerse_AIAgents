from app.database.mongodb import mongodb

def main():
    try:
        # Initialize the same MongoDB connection used by FastAPI.
        mongodb.connect()
        collection = mongodb.get_database()["agent_memories"]

        total = collection.count_documents({})
        print(f"\nTotal stored memories: {total}")

        print("\nMemories grouped by company and agent:")
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "company_id": "$company_id",
                        "agent_name": "$agent_name",
                    },
                    "count": {"$sum": 1},
                    "missing_embedding": {
                        "$sum": {
                            "$cond": [
                                {"$in": [{"$type": "$embedding"}, ["missing", "null"]]},
                                1,
                                0,
                            ]
                        }
                    },
                    "missing_question_embedding": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$in": [
                                        {"$type": "$question_embedding"},
                                        ["missing", "null"],
                                    ]
                                },
                                1,
                                0,
                            ]
                        }
                    },
                }
            },
            {"$sort": {"_id.company_id": 1, "_id.agent_name": 1}},
        ]

        for item in collection.aggregate(pipeline):
            key = item["_id"]
            print(
                f"Company: {key.get('company_id')} | "
                f"Agent: {key.get('agent_name')} | "
                f"Memories: {item['count']} | "
                f"Missing content embeddings: {item['missing_embedding']} | "
                f"Missing question embeddings: {item['missing_question_embedding']}"
            )

        print("\nInspection completed. No documents were modified.")

    finally:
        mongodb.close()

if __name__ == "__main__":
    main()
