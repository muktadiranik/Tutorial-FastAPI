"""Run with: streamlit run \"project shopping agent/app.py\"."""

import os
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
from groq import APIConnectionError, AuthenticationError, RateLimitError
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from PIL import Image, UnidentifiedImageError
from sqlalchemy import URL, create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from streamlit.typing import UploadedFile

from database import DB_PATH, Order, Product, Review

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")
load_dotenv(APP_DIR.parent / ".env")


@st.cache_resource
def store_engine(database_path: str) -> Engine:
    """Reuse a database engine, keeping sessions local to each operation."""
    return create_engine(URL.create("sqlite", database=database_path))


def new_conversation() -> None:
    """Release uploaded files and reset this browser session's conversation."""
    uploads = st.session_state.get("uploads")
    if uploads is not None:
        uploads.cleanup()
    st.session_state.update(
        history=[], shopping_agent=None, thread_id=uuid4().hex, pending={},
        order_confirmations={}, uploads=None, conversation_failed=False, last_error=None,
    )


def shopping_agent() -> Any:
    """Build a private conversation with checkout paused for a UI decision."""
    if st.session_state.shopping_agent is None:
        from agent import SHOPPING_TOOLS, llm, system_prompt

        st.session_state.shopping_agent = create_agent(
            model=llm,
            tools=SHOPPING_TOOLS,
            system_prompt=(system_prompt + "\nIn this app, checkout pauses for a Confirm order button. "
                           "No order is placed until that button is selected. Do not show local file paths in replies."),
            middleware=[HumanInTheLoopMiddleware(
                interrupt_on={"checkout": {"allowed_decisions": ["approve", "reject"]}},
                interrupt_mode="batched",
            )],
            checkpointer=InMemorySaver(),
        )
    return st.session_state.shopping_agent


def message_text(message: AIMessage | ToolMessage) -> str:
    """Return visible text without exposing tool arguments or reasoning blocks."""
    return message.text


def record_orders(messages: list) -> None:
    """Keep actual checkout results even if a later model response fails."""
    for message in messages:
        if isinstance(message, ToolMessage) and message.name == "checkout":
            text = message_text(message)
            if text.startswith("order #"):
                st.session_state.order_confirmations[message.tool_call_id] = text


def run_agent(agent_input: dict | Command) -> None:
    """Advance the conversation once and retain any pending order requests."""
    graph = None
    config = {"configurable": {"thread_id": st.session_state.thread_id}, "recursion_limit": 30}
    st.session_state.pending = {}
    try:
        graph = shopping_agent()
        with st.spinner("Your shopping assistant is working..."):
            result = graph.invoke(agent_input, config=config)
        record_orders(result.get("messages", []))
        interrupts = result.get("__interrupt__", [])
        if interrupts:
            st.session_state.pending = {item.id: item.value["action_requests"] for item in interrupts}
        else:
            message = result["messages"][-1]
            if not isinstance(message, AIMessage) or message.tool_calls or not message_text(message).strip():
                raise ValueError("No final assistant response")
            st.session_state.history.append({"role": "assistant", "content": message_text(message)})
        st.session_state.last_error = None
    except Exception as exc:
        # The graph may have committed an order before a later model call failed.
        try:
            if graph is not None:
                record_orders(graph.get_state(config).values.get("messages", []))
        except Exception:
            pass
        if isinstance(exc, AuthenticationError):
            error = "Groq rejected GROQ_API_KEY. Check the environment variable or .env file."
        elif isinstance(exc, RateLimitError):
            error = "Groq's rate limit was reached. Wait a moment before starting a new conversation."
        elif isinstance(exc, APIConnectionError):
            error = "Could not reach Groq. Check your connection."
        elif isinstance(exc, SQLAlchemyError):
            error = "The store database could not complete the request. Check its setup and try again."
        else:
            error = "The assistant could not complete this turn. Check your Groq model configuration."
        st.session_state.last_error = error
        st.session_state.conversation_failed = True
        st.session_state.pending = {}


def save_image(uploaded: UploadedFile) -> tuple[str, bytes]:
    """Validate an uploaded image and retain it only for this conversation."""
    image_bytes = uploaded.getvalue()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise ValueError("Please choose an image smaller than 10 MB.")
    with Image.open(BytesIO(image_bytes)) as image:
        suffix = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(image.format or "")
        image.verify()
    if suffix is None:
        raise ValueError("Please upload a JPEG, PNG, or WebP image.")
    if st.session_state.uploads is None:
        st.session_state.uploads = TemporaryDirectory(prefix="shopping-chat-")
    path = Path(st.session_state.uploads.name) / f"{uuid4().hex}{suffix}"
    path.write_bytes(image_bytes)
    return str(path), image_bytes


st.set_page_config(page_title="Shopping assistant", page_icon=":material/shopping_bag:")
if "history" not in st.session_state:
    new_conversation()

st.title(":material/shopping_bag: Shopping assistant")
st.caption("Find products, compare reviews, and shop by photo.")

with st.sidebar:
    st.header("Your shopping session")
    st.button("New conversation", key="new_conversation", on_click=new_conversation, width="stretch")
    st.subheader("Try asking")
    st.caption('"Find organic honey under $20 with at least 4.5 stars."')
    st.caption('"Show me affordable cooking oils."')
    st.caption("Attach a product photo using the paperclip in the message box.")
    st.divider()
    st.caption("Orders are recorded in the local demo store after you select Confirm order.")

configured = bool(os.getenv("GROQ_API_KEY", "").strip())
if not configured:
    st.warning("Set GROQ_API_KEY in your environment or the project's .env file to start chatting.")

database_ready = False
if Path(DB_PATH).is_file():
    try:
        inspector = inspect(store_engine(DB_PATH))
        database_ready = all(inspector.has_table(model.__tablename__) for model in (Product, Review, Order))
    except SQLAlchemyError:
        pass
if not database_ready:
    st.error("The store database is not ready. Run database.py from this project folder to initialize it.")

if not st.session_state.history:
    with st.chat_message("assistant"):
        st.markdown("What are you shopping for? Tell me your budget, preferred rating, or organic preference.")

for entry in st.session_state.history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
        if entry.get("image"):
            st.image(entry["image"], width=280, alt="Product photo uploaded for matching")

if st.session_state.last_error:
    st.error(st.session_state.last_error)
    st.info("Start a new conversation to continue. Review any confirmed orders below before ordering again.")

if st.session_state.order_confirmations:
    with st.expander("Confirmed orders", expanded=True):
        for confirmation in st.session_state.order_confirmations.values():
            st.text(confirmation)

pending = st.session_state.pending
if pending:
    with st.container(border=True):
        st.subheader("Review your order")
        valid = database_ready and configured
        total = 0.0
        if database_ready:
            with Session(store_engine(DB_PATH)) as session:
                for actions in pending.values():
                    for action in actions:
                        try:
                            product_id = int(action["args"]["product_id"])
                            product = session.get(Product, product_id) if action["name"] == "checkout" else None
                        except (KeyError, TypeError, ValueError):
                            product = None
                        if product is None or product.price is None:
                            st.error("A requested product is unavailable. Cancel this order and choose another product.")
                            valid = False
                        else:
                            st.markdown(f"**{product.name}** · ID {product.id} · ${product.price:.2f}")
                            total += product.price
        st.markdown(f"**Total: ${total:.2f}**")
        decision = None
        with st.container(horizontal=True):
            if st.button("Confirm order", key="approve_order", type="primary", disabled=not valid):
                decision = "approve"
            if st.button("Cancel order", key="reject_order", disabled=not configured):
                decision = "reject"
        if decision:
            responses = {
                interrupt_id: {"decisions": [{"type": decision} for _ in actions]}
                for interrupt_id, actions in pending.items()
            }
            run_agent(Command(resume=responses))
            st.rerun()

submission = st.chat_input(
    "Ask about products or attach a photo...",
    key="shopping_chat", accept_file=True, file_type=["jpg", "jpeg", "png", "webp"],
    max_upload_size=10, submit_mode="disable",
    disabled=not configured or not database_ready or bool(pending) or st.session_state.conversation_failed,
)
if submission and configured and database_ready and not pending and not st.session_state.conversation_failed:
    text = submission.text.strip()
    if text or submission.files:
        entry: dict[str, Any] = {"role": "user", "content": text or "Find products like this photo."}
        agent_text = entry["content"]
        if submission.files:
            try:
                image_path, image_bytes = save_image(submission.files[0])
            except (ValueError, OSError, UnidentifiedImageError):
                st.error("Please attach a valid JPEG, PNG, or WebP image smaller than 10 MB.")
                st.stop()
            entry["image"] = image_bytes
            agent_text += f"\nThe uploaded product image is at this local path: {image_path}"
        st.session_state.history.append(entry)
        run_agent({"messages": [HumanMessage(content=agent_text)]})
        st.rerun()
