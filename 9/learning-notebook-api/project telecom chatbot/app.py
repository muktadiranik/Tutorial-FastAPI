"""Streamlit chat interface for the existing telecom RAG chain."""

import os
from collections.abc import Iterator
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import APIConnectionError, AuthenticationError, RateLimitError
from langchain_core.runnables import Runnable

APP_DIR = Path(__file__).resolve().parent
INDEX_DIR = APP_DIR / "chroma_store"
WELCOME = "How can I help with your mobile service? Ask about signal, mobile data, roaming, or billing."

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
load_dotenv(APP_DIR / ".env")
load_dotenv(APP_DIR.parent / ".env")


@st.cache_resource(show_spinner=False)
def get_chain() -> Runnable:
    """Load the existing chain once, using this project's index from any working directory."""
    import retriever
    from rag import build_rag_chain

    setattr(retriever, "CHROMA_DIRECTORY", str(INDEX_DIR))
    return build_rag_chain()


def clear_chat() -> None:
    """Start a fresh conversation in the current browser session."""
    st.session_state.messages = [{"role": "assistant", "content": WELCOME}]


def friendly_error(error: Exception) -> str:
    """Explain failures without displaying credentials or raw provider responses."""
    if isinstance(error, AuthenticationError):
        return "Groq rejected GROQ_API_KEY. Check the environment variable or your .env file."
    if isinstance(error, RateLimitError):
        return "Groq's rate limit was reached. Wait a moment and send your question again."
    if isinstance(error, APIConnectionError):
        return "Could not reach Groq. Check your connection and send your question again."
    return (
        "Could not finish the answer. Check the knowledge base and the Groq model configured in rag.py, "
        "then send your question again."
    )


st.set_page_config(page_title="Telecom support", page_icon=":material/support_agent:")
if "messages" not in st.session_state:
    clear_chat()

st.title(":material/support_agent: Telecom support")
st.caption("Get help from the telecom FAQs, resolved support cases, and PDF guide.")

with st.sidebar:
    st.header("Support chat")
    st.button("New conversation", key="new_conversation", on_click=clear_chat, width="stretch")
    st.subheader("Try asking")
    st.caption('"Why is my mobile data slow?"')
    st.caption('"How do I enable international roaming?"')
    st.caption('"My phone has no signal. What should I do?"')
    st.divider()
    st.caption("Each question searches the existing knowledge base. Include the details of your issue in your question.")
    st.caption("Your question and relevant reference passages are sent to Groq to generate an answer.")

configured = bool(os.getenv("GROQ_API_KEY", "").strip())
index_ready = (INDEX_DIR / "chroma.sqlite3").is_file()
if not configured:
    st.warning("Set GROQ_API_KEY in your environment or the project's .env file to start chatting.")
if not index_ready:
    st.info("Run faq.py, tickets.py, and pdf.py from this project folder to prepare the knowledge base, then refresh.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["content"]:
            st.markdown(message["content"])
        if message.get("error"):
            st.error(message["error"])

prompt = (st.chat_input(
    "Describe your telecom issue...",
    key="support_question",
    disabled=not configured or not index_ready,
    submit_mode="disable",
) or "").strip()

if prompt and configured and index_ready:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        parts: list[str] = []

        def stream_answer() -> Iterator[str]:
            """Retain streamed text so an interrupted reply remains visible in history."""
            for chunk in get_chain().stream(prompt):
                if isinstance(chunk, str):
                    parts.append(chunk)
                    yield chunk

        try:
            with st.spinner("Searching support knowledge... The first response may take longer to load."):
                st.write_stream(stream_answer())
            answer = "".join(parts)
            if not answer.strip():
                raise ValueError("No answer returned")
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as error:
            error_text = friendly_error(error)
            st.error(error_text)
            st.session_state.messages.append({
                "role": "assistant", "content": "".join(parts), "error": error_text,
            })
