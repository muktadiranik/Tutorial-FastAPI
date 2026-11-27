from rag import build_rag_chain
from dotenv import load_dotenv
import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"


load_dotenv()


def main():
    chain = build_rag_chain()

    while True:
        question = input("user: ").strip()
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            break

        print("\nassistant: ", end="", flush=True)
        for chunk in chain.stream(question):
            print(chunk, end="", flush=True)
        print("\n")


if __name__ == "__main__":
    main()
