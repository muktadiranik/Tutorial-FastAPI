from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import sqlite3
import os
os.environ["TRANSFORMER_VERBOSITY"] = "ERROR"

CHROMA_DIRECTORY = "chroma_store"
COLLECTION = "tickets"
DATABASE_PATH = os.path.join("data", "tickets.db")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_ticket_documents(database_path: str) -> list[Document]:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT * FROM tickets WHERE status = 'resolved'").fetchall()
    connection.close()

    documents = []
    for row in rows:
        content = (
            f"issue: {row['issue_type']}\n"
            f"description: {row['description']}\n"
            f"resolution: {row['resolution']}"
        )
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": "ticket",
                    "ticket_id": row["ticket_id"],
                    "category": row["category"],
                    "status": row["status"]
                }
            )
        )
    return documents


def main():
    print("loading ticket documents from database...")
    documents = load_ticket_documents(DATABASE_PATH)
    print(f"tickets loaded: {len(documents)}")

    print(f"initialising embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print(f"embedding and storing data in chroma database...")
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=COLLECTION,
        persist_directory=CHROMA_DIRECTORY
    )

    print(f"vector stored: {vector_store._collection.count()}")


if __name__ == "__main__":
    main()
