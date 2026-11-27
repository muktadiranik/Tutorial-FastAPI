import base64
import json
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from sqlalchemy import URL, create_engine, or_, select
from sqlalchemy.orm import Session

from database import DB_PATH, Order, Product
from reviews import get_product_rating

load_dotenv()

engine = create_engine(URL.create("sqlite", database=DB_PATH))

llm = ChatGroq(
    model="qwen/qwen3.8-27b",
    temperature=0.0,
)

vision_llm = ChatGroq(
    model="qwen/qwen3.8-27b",
    temperature=0.0,
)


@tool
def search_products(
    query: str,
    max_price: float | None = None,
    is_organic: bool | None = None,
) -> str:
    """
    Search the product database by keyword (matched against name, description, and category).
    Optionally filter by maximum price and/or organic status.
    Returns a JSON array of matching products, each with: id, name, category, price,
    description, is_organic.
    """

    statement = select(Product)

    if query:
        like = f"%{query}%"
        statement = statement.where(
            or_(Product.name.like(like), Product.description.like(like), Product.category.like(like))
        )

    if max_price is not None:
        statement = statement.where(Product.price <= max_price)

    if is_organic is not None:
        statement = statement.where(Product.is_organic == is_organic)

    with Session(engine) as session:
        products = [
            {
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "description": product.description,
                "is_organic": product.is_organic,
            }
            for product in session.scalars(statement)
        ]

    return json.dumps(products)


@tool
def get_rating(product_id: str) -> str:
    """
    Get the average customer rating and total review count for a product by its ID.
    Returns a JSON object with: product_id, average_rating, review_count.
    """

    try:
        parsed_id = int(product_id)
    except ValueError:
        return json.dumps({"error": "Invalid product ID"})
    return json.dumps(get_product_rating(parsed_id))


@tool
def checkout(product_id: str) -> str:
    """Place an order for a product only after the user confirms the purchase."""

    with Session(engine) as session, session.begin():
        product = session.get(Product, product_id)
        if product is None:
            return json.dumps({"error": "Product not found"})

        name, price = product.name, product.price
        order = Order(product_id=product.id, product_name=name, price=price)
        session.add(order)
        session.flush()
        order_id = order.id

    return (
        f"order #{order_id} confirmed! {name} has been successfully added to your cart ordered for ${price}."
        f" Your order will be ready in 24 hours. Thank you for your business!"
    )


@tool
def describe_product_image(image_path: str) -> str:
    """
    Analyze a product image and return its key attributes as a JSON object.
    Use this when the user uploads a photo of a product they are interested in.
    The returned attributes can be used directly with search_products.
    """

    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")

    extension = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = "image/jpeg" if extension == "jpg" else f"image/{extension}"

    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{image_data}",
                },
            },
            {
                "type": "text",
                "text": """Look at this product image and extract its key attributes. Return ONLY a JSON object with these fields:
                        - product_type: what kind of product it is (e.g. honey, olive oil, almonds)
                        - search_query: a short keyword to search for it (e.g. 'honey', 'olive oil')
                        - is_organic: true if the label says organic, false if not, null if unclear
                        - description: one sentence describing the product""",
            },
        ]
    )

    response = vision_llm.invoke([message])
    return response.text


system_prompt = """You are a helpful shopping assistant. Follow these rules strictly.

IMAGE SEARCH — when the user provides an image path:
1. Call describe_product_image with the path to identify the product.
2. Use the returned search_query and is_organic to call search_products.
3. Continue with the BROWSING flow from step 2 onwards.

BROWSING — when the user describes what they want to buy:
1. Call search_products to find matching items (apply any price/organic filters given).
2. For each candidate, call get_rating to retrieve its average rating.
3. Filter by the user's minimum rating if specified.
4. Present qualifying products as a numbered list. For each item use this exact format (plain text, no backticks, no code blocks, no bold, no italic):

   #<number>. <name> (ID:<product_id>) — $<price> ★<rating> — <organic or non-organic>

   Add a blank line between each product entry for readability. Always include (ID:X) so you can reference it later.
5. If only one product qualifies, still show it in the list and ask: 'Would you like to order it? Just say yes or give me the number.'
6. Do NOT call checkout at this stage.

ORDERING — when the user confirms they want to buy (e.g. 'yes', 'sure', 'go ahead', 'order number 2', 'the first one', 'get me #3'):
1. Look at your previous message to find the (ID:X) for the chosen product (if only one was listed and the user says 'yes', use that product's ID).
2. Call checkout with that product_id (the number from (ID:X)).
3. Confirm the order to the user in plain text.

Never place an order unless the user explicitly confirms. Never guess a product_id — always take it from the (ID:X) in your own previous message."""

SHOPPING_TOOLS = [search_products, get_rating, checkout, describe_product_image]

agent = create_agent(
    model=llm,
    tools=SHOPPING_TOOLS,
    system_prompt=system_prompt,
)


if __name__ == "__main__":
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "I want to buy honey. It's organic. It's a little expensive. I want to order it."
                }
            ]
        }
    )

    print(result["messages"][-1].content)
