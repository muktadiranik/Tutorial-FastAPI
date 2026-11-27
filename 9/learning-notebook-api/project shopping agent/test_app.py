"""Verify the shopping interface with isolated data and mocked model responses."""

import os
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command, Interrupt
from PIL import Image
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session
from streamlit.testing.v1 import AppTest

from database import Base, Product

APP_FILE = Path(__file__).with_name("app.py")


class ShoppingAppTests(unittest.TestCase):
    """Exercise chat, image input, confirmation, and failure recovery."""

    def setUp(self) -> None:
        """Use a disposable store and prevent external model calls."""
        self.addCleanup(patch.stopall)
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database_path = str(Path(self.directory.name) / "store.db")
        self.engine = create_engine(URL.create("sqlite", database=database_path))
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session, session.begin():
            session.add(Product(id=1, name="Organic Honey", price=14.99, is_organic=1))
        patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}).start()
        patch("dotenv.load_dotenv").start()
        patch("database.DB_PATH", database_path).start()
        patch("sqlalchemy.create_engine", return_value=self.engine).start()
        patch("langchain_groq.ChatGroq").start()
        self.graph = MagicMock()
        self.graph.invoke.return_value = {"messages": [AIMessage(content="Here is some honey.")]}
        patch("langchain.agents.create_agent", return_value=self.graph).start()
        self.app = AppTest.from_file(str(APP_FILE), default_timeout=30).run()
        self.addCleanup(self.cleanup_uploads)

    def cleanup_uploads(self) -> None:
        """Remove any temporary image files created by the UI."""
        uploads = self.app.session_state.get("uploads")
        if uploads is not None:
            uploads.cleanup()

    def send(self, text: str = "Find organic honey") -> None:
        """Submit one chat turn."""
        self.app.chat_input(key="shopping_chat").set_value(text).run()

    def queue_order(self) -> None:
        """Return a genuine interrupt-shaped result to the interface."""
        self.graph.invoke.return_value = {
            "messages": [],
            "__interrupt__": [Interrupt(id="order-approval", value={
                "action_requests": [{"name": "checkout", "args": {"product_id": "1"}}],
            })],
        }
        self.send("Order the honey")

    def test_page_requires_environment_key(self) -> None:
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.text_input), 0)
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            self.app.run()
        self.assertTrue(self.app.chat_input[0].disabled)
        self.assertIn("GROQ_API_KEY", self.app.warning[0].value)
        self.graph.invoke.assert_not_called()

    def test_missing_database_disables_chat(self) -> None:
        with patch("database.DB_PATH", str(Path(self.directory.name) / "missing.db")):
            self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.chat_input[0].disabled)
        self.assertTrue(self.app.error)
        self.graph.invoke.assert_not_called()

    def test_chat_history_and_reruns(self) -> None:
        self.send()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.session_state.history), 2)
        first_thread = self.graph.invoke.call_args.kwargs["config"]["configurable"]["thread_id"]
        self.app.run()
        self.assertEqual(self.graph.invoke.call_count, 1)
        self.send("Which one is cheaper?")
        self.assertEqual(self.graph.invoke.call_count, 2)
        self.assertEqual(self.graph.invoke.call_args.kwargs["config"]["configurable"]["thread_id"], first_thread)
        self.app.button(key="new_conversation").click().run()
        self.assertFalse(self.app.session_state.history)
        self.assertNotEqual(self.app.session_state.thread_id, first_thread)

    def test_image_upload_and_cleanup(self) -> None:
        buffer = BytesIO()
        Image.new("RGB", (2, 2), color="green").save(buffer, format="PNG")
        self.app.chat_input[0].upload("product.png", buffer.getvalue()).set_value("Find this").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state.history[0]["image"], buffer.getvalue())
        self.assertNotIn("local path", self.app.session_state.history[0]["content"])
        self.assertIn("local path", self.graph.invoke.call_args.args[0]["messages"][0].content)
        upload_directory = Path(self.app.session_state.uploads.name)
        self.assertEqual(len(list(upload_directory.iterdir())), 1)
        self.app.button(key="new_conversation").click().run()
        self.assertFalse(upload_directory.exists())

    def test_invalid_image_does_not_call_agent(self) -> None:
        self.app.chat_input[0].upload("broken.png", b"not an image").set_value("Find this").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.error)
        self.graph.invoke.assert_not_called()

    def test_confirmation_resumes_only_after_click(self) -> None:
        self.queue_order()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.chat_input[0].disabled)
        self.assertEqual(self.graph.invoke.call_count, 1)
        self.assertTrue(any("$14.99" in element.value for element in self.app.markdown))
        self.graph.invoke.return_value = {"messages": [
            ToolMessage(content="order #1 confirmed! Organic Honey", tool_call_id="buy-1", name="checkout"),
            AIMessage(content="Your order is confirmed."),
        ]}
        self.app.button(key="approve_order").click().run()
        self.assertFalse(self.app.exception)
        command = self.graph.invoke.call_args.args[0]
        self.assertIsInstance(command, Command)
        self.assertEqual(command.resume, {"order-approval": {"decisions": [{"type": "approve"}]}})
        self.assertFalse(self.app.session_state.pending)
        self.assertEqual(len(self.app.session_state.order_confirmations), 1)
        self.app.run()
        self.assertEqual(self.graph.invoke.call_count, 2)

    def test_cancel_rejects_order(self) -> None:
        self.queue_order()
        self.graph.invoke.return_value = {"messages": [AIMessage(content="Order cancelled.")]}
        self.app.button(key="reject_order").click().run()
        self.assertFalse(self.app.exception)
        command = self.graph.invoke.call_args.args[0]
        self.assertEqual(command.resume, {"order-approval": {"decisions": [{"type": "reject"}]}})
        self.assertFalse(self.app.session_state.order_confirmations)

    def test_failure_preserves_confirmed_order_without_retry(self) -> None:
        self.graph.invoke.side_effect = RuntimeError("private provider details")
        self.graph.get_state.return_value = SimpleNamespace(values={"messages": [
            ToolMessage(content="order #1 confirmed! Organic Honey", tool_call_id="buy-1", name="checkout"),
        ]})
        self.send()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.session_state.conversation_failed)
        self.assertEqual(len(self.app.session_state.order_confirmations), 1)
        self.assertNotIn("private provider details", self.app.error[0].value)
        self.assertTrue(self.app.chat_input[0].disabled)
        self.app.run()
        self.assertEqual(self.graph.invoke.call_count, 1)


if __name__ == "__main__":
    unittest.main()
