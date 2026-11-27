"""Test the agent's database tools against an isolated SQLite database."""

import importlib
import json
import unittest
from unittest.mock import patch

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import reviews
from database import Base, Order, Product, Review


class ToolCallingModel(FakeMessagesListChatModel):
    """A deterministic model supporting the agent's tool-binding interface."""

    def bind_tools(self, tools, **kwargs):
        """Use the configured tool-call messages without contacting a provider."""
        return self


class AgentDatabaseTests(unittest.TestCase):
    """Exercise real ORM queries without calling an LLM or touching store.db."""

    @classmethod
    def setUpClass(cls) -> None:
        """Import the tool definitions without loading credentials or an agent."""
        with (
            patch("dotenv.load_dotenv"),
            patch("langchain_groq.ChatGroq"),
            patch("langchain.agents.create_agent"),
        ):
            cls.agent = importlib.import_module("agent")

    def setUp(self) -> None:
        """Provide each test with a fresh database using the actual schema."""
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        engine_patch = patch.object(self.agent, "engine", self.engine)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)
        reviews_patch = patch.object(reviews, "engine", self.engine)
        reviews_patch.start()
        self.addCleanup(reviews_patch.stop)
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session, session.begin():
            session.add_all(
                [
                    Product(
                        id=1, name="Organic Honey", category="honey", price=14.99,
                        description="Unfiltered and cold-pressed", is_organic=1,
                    ),
                    Product(
                        id=2, name="Wildflower Honey", category="honey", price=8.99,
                        description="Natural honey", is_organic=0,
                    ),
                    Product(
                        id=3, name="Almond Oil", category="oil", price=9.99,
                        description="Organic cooking oil", is_organic=1,
                    ),
                    Product(
                        id=4, name="Free Sample", category="grains", price=0.0,
                        description="Complimentary oats", is_organic=0,
                    ),
                    Product(id=5, name="Unpriced Product", price=None, is_organic=0),
                ]
            )
            session.add_all([Review(product_id=1, rating=5.0), Review(product_id=1, rating=4.0)])

    def search(self, query: str = "", **filters) -> list[dict]:
        """Call the registered search tool and decode its public JSON response."""
        return json.loads(self.agent.search_products.invoke({"query": query, **filters}))

    def order_count(self) -> int:
        """Count committed orders using a separate session."""
        with Session(self.engine) as session:
            return session.scalar(select(func.count()).select_from(Order)) or 0

    def test_unfiltered_search_preserves_fields_and_nulls(self) -> None:
        products = self.search()
        self.assertEqual(len(products), 5)
        honey = next(product for product in products if product["id"] == 1)
        self.assertEqual(
            honey,
            {
                "id": 1, "name": "Organic Honey", "category": "honey", "price": 14.99,
                "description": "Unfiltered and cold-pressed", "is_organic": 1,
            },
        )
        self.assertIsNone(next(product for product in products if product["id"] == 5)["price"])
        self.assertEqual(self.order_count(), 0)

    def test_keyword_matches_name_description_or_category(self) -> None:
        for query, expected in [("WILDFLOWER", [2]), ("cold-pressed", [1]), ("grains", [4])]:
            with self.subTest(query=query):
                self.assertEqual([product["id"] for product in self.search(query)], expected)

    def test_combined_filters(self) -> None:
        products = self.search("honey", max_price=15.0, is_organic=True)
        self.assertEqual([product["id"] for product in products], [1])
        self.assertEqual(self.search("honey", max_price=10.0, is_organic=True), [])

    def test_zero_price_and_false_organic_filters(self) -> None:
        products = self.search(max_price=0.0, is_organic=False)
        self.assertEqual([product["id"] for product in products], [4])

    def test_sql_like_input_is_bound_as_data(self) -> None:
        self.assertEqual(self.search("' OR 1=1 --"), [])
        self.assertEqual(len(self.search()), 5)

    def test_rating_lookup_does_not_place_order(self) -> None:
        rating = json.loads(self.agent.get_rating.invoke({"product_id": "1"}))
        self.assertEqual(rating, {"product_id": 1, "average_rating": 4.5, "review_count": 2})
        self.assertEqual(self.order_count(), 0)

    def test_checkout_commits_product_snapshot(self) -> None:
        confirmation = self.agent.checkout.invoke({"product_id": "1"})
        with Session(self.engine) as session:
            order = session.scalars(select(Order)).one()
            self.assertEqual((order.product_id, order.product_name, order.price), (1, "Organic Honey", 14.99))
            self.assertIsNotNone(order.ordered_at)
            self.assertIn(f"order #{order.id} confirmed!", confirmation)
        self.assertIn("Organic Honey", confirmation)
        self.assertIn("$14.99", confirmation)

    def test_missing_product_creates_no_order(self) -> None:
        response = self.agent.checkout.invoke({"product_id": "999"})
        self.assertEqual(json.loads(response), {"error": "Product not found"})
        self.assertEqual(self.order_count(), 0)

    def test_failed_order_rolls_back_and_releases_session(self) -> None:
        with self.assertRaises(IntegrityError):
            self.agent.checkout.invoke({"product_id": "5"})
        self.assertEqual(self.order_count(), 0)
        self.agent.checkout.invoke({"product_id": "1"})
        self.assertEqual(self.order_count(), 1)

    def test_checkout_waits_for_confirmation(self) -> None:
        model = ToolCallingModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "checkout", "args": {"product_id": "1"}, "id": "buy-1"}]),
            AIMessage(content="Your order is confirmed."),
        ])
        graph = create_agent(
            model=model, tools=[self.agent.checkout], checkpointer=InMemorySaver(),
            middleware=[HumanInTheLoopMiddleware(
                interrupt_on={"checkout": {"allowed_decisions": ["approve", "reject"]}},
                interrupt_mode="batched",
            )],
        )
        config: RunnableConfig = {"configurable": {"thread_id": "approval-test"}}
        result = graph.invoke({"messages": [{"role": "user", "content": "Order the honey."}]}, config)
        self.assertTrue(result["__interrupt__"])
        self.assertEqual(self.order_count(), 0)
        interrupt_id = result["__interrupt__"][0].id
        graph.invoke(Command(resume={interrupt_id: {"decisions": [{"type": "approve"}]}}), config)
        self.assertEqual(self.order_count(), 1)

    def test_rejected_checkout_creates_no_order(self) -> None:
        model = ToolCallingModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "checkout", "args": {"product_id": "1"}, "id": "buy-1"}]),
            AIMessage(content="The order was cancelled."),
        ])
        graph = create_agent(
            model=model, tools=[self.agent.checkout], checkpointer=InMemorySaver(),
            middleware=[HumanInTheLoopMiddleware(
                interrupt_on={"checkout": {"allowed_decisions": ["approve", "reject"]}},
                interrupt_mode="batched",
            )],
        )
        config: RunnableConfig = {"configurable": {"thread_id": "rejection-test"}}
        result = graph.invoke({"messages": [{"role": "user", "content": "Order the honey."}]}, config)
        interrupt_id = result["__interrupt__"][0].id
        graph.invoke(Command(resume={interrupt_id: {"decisions": [{"type": "reject"}]}}), config)
        self.assertEqual(self.order_count(), 0)


if __name__ == "__main__":
    unittest.main()
