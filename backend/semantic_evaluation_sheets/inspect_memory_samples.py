from app.database.mongodb import mongodb

COMPANY_ID = "6ac27f9d8a6f61aa7c426a23"

def main():
    try:
        mongodb.connect()
        collection = mongodb.get_database()["agent_memories"]

        memories = list(
            collection.find({"company_id": COMPANY_ID}).sort(
                [("created_at", 1), ("agent_name", 1)]
            )
        )

        print(f"\nFound {len(memories)} memories for the selected company.\n")

        for index, memory in enumerate(memories, start=1):
            metadata = memory.get("metadata") or {}
            question = metadata.get("question") or "(no original question)"
            content = memory.get("content") or ""
            month = metadata.get("simulation_month", "unknown")

            print("=" * 90)
            print(f"MEMORY #{index}")
            print(f"Agent: {memory.get('agent_name', 'unknown')}")
            print(f"Month: {month}")
            print(f"Original question: {question}")
            print(f"Content: {content[:350]}")
            if len(content) > 350:
                print("...")
        print("\nInspection complete. No documents were modified.")

    finally:
        mongodb.close()

if __name__ == "__main__":
    main()
