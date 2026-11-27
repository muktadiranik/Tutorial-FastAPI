from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"


CHROMA_DIRECTORY = "chroma_store"
COLLECTION = "pdf"
PDF_PATH = os.path.join("data", "telecom_guide.pdf")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def main():
    print("loading PDF...")
    loader = PyPDFLoader(PDF_PATH)
    pages = loader.load()
    print(f"loaded {len(pages)} pages")

    print("splitting pages into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(pages)
    print(f"split into {len(chunks)} chunks")

    print("initialising embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print(f"embedding and storing data in chroma database...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION,
        persist_directory=CHROMA_DIRECTORY
    )

    print(
        f"vector stored: {vector_store._collection.count()} in collection: {COLLECTION}")


if __name__ == "__main__":
    main()
