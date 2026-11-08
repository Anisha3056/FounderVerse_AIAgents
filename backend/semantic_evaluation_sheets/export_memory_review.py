
import csv
from pathlib import Path

from app.database.mongodb import mongodb

OUTPUT_FILE = Path("memory_review.csv")


def first_value(document, *keys, default=""):
    """Return the first non-empty value among possible field names."""
    for key in keys:
        value = document.get(key)
        if value is not None and value != "":
            return value
    return default


def main():
    exported = 0

    try:
        # Explicit connection is required for standalone scripts.
        mongodb.connect()
        collection = mongodb.get_database()["agent_memories"]

        fields = [
            "memory_id",
            "agent_name",
            "stored_question",
            "content_preview",
            "duplicate_group",
            "relevance_notes",
        ]

        with OUTPUT_FILE.open(
            "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()

            cursor = collection.find(
                {},
                {
                    "_id": 1,
                    "agent_name": 1,
                    "question": 1,
                    "content": 1,
                    "memory": 1,
                    "text": 1,
                    "created_at": 1,
                },
            ).sort("_id", 1)

            for doc in cursor:
                content = first_value(
                    doc, "content", "memory", "text"
                )

                writer.writerow({
                    "memory_id": str(doc.get("_id", "")),
                    "agent_name": first_value(
                        doc, "agent_name", "agent"
                    ),
                    "stored_question": first_value(
                        doc, "question", "query"
                    ),
                    # Export the complete content; do not truncate.
                    "content_preview": str(content),
                    "duplicate_group": "",
                    "relevance_notes": "",
                })
                exported += 1

        print(f"Export complete: {exported} memories")
        print(f"File: {OUTPUT_FILE.resolve()}")
        print("Full memory content exported.")
        print("MongoDB documents modified: 0")

    finally:
        mongodb.close()


if __name__ == "__main__":
    main()
