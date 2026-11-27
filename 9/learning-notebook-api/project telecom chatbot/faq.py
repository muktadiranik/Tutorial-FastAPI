from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import pandas as pd
import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

CHROMA_DIRECTORY = "chroma_store"
COLLECTION = "faq"
CSV_PATH = os.path.join("data", "faq.csv")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_faq_documents(csv_path: str) -> list[Document]:
    df = pd.read_csv(csv_path)
    documents = []
    for _, row in df.iterrows():
        content = f"Question: {row['question']}\n\n Answer: {row['answer']}"
        documents.append(Document(
            page_content=content,
            metadata={
                "source": "faq",
                "category": row["category"],
                "faq_id": str(row["id"])
            }
        ))
    return documents


def main():
    print("loading faq documents...")
    documents = load_faq_documents(CSV_PATH)
    print(f"{len(documents)} documents loaded")

    print("initializing embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print("embedding and storing in chroma store...")
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=CHROMA_DIRECTORY,
        collection_name=COLLECTION
    )
    print(f"vector store {vector_store._collection_name} created")


if __name__ == "__main__":
    main()
