"""
Reviews API — reads from the `reviews` table in store.db and returns
aggregated rating information for products.
"""

from sqlalchemy import URL, create_engine, func, select
from sqlalchemy.orm import Session

from database import DB_PATH, Review

engine = create_engine(URL.create("sqlite", database=DB_PATH))


def get_product_rating(product_id: int) -> dict:
    """Return average rating and review count for a single product."""
    statement = select(func.avg(Review.rating), func.count()).where(
        Review.product_id == product_id
    )
    with Session(engine) as session:
        average_rating, review_count = session.execute(statement).one()

    return {
        "product_id": product_id,
        "average_rating": round(average_rating, 2) if average_rating is not None else 0.0,
        "review_count": review_count,
    }


def get_ratings_for_products(product_ids: list[int]) -> list[dict]:
    """Return ratings for a list of product IDs."""
    if not product_ids:
        return []

    statement = (
        select(Review.product_id, func.avg(Review.rating), func.count())
        .where(Review.product_id.in_(product_ids))
        .group_by(Review.product_id)
    )
    with Session(engine) as session:
        rows = session.execute(statement).all()

    ratings_map = {
        product_id: {
            "average_rating": round(average_rating, 2),
            "review_count": review_count,
        }
        for product_id, average_rating, review_count in rows
    }
    return [
        {
            "product_id": pid,
            "average_rating": ratings_map.get(pid, {}).get("average_rating", 0.0),
            "review_count": ratings_map.get(pid, {}).get("review_count", 0),
        }
        for pid in product_ids
    ]


if __name__ == "__main__":
    # Single product
    result = get_product_rating(1)
    print("Single product rating:")
    print(
        f"  Product {result['product_id']}: {result['average_rating']} stars ({result['review_count']} reviews)")

    # Multiple products
    print("\nBatch ratings:")
    results = get_ratings_for_products([1, 3, 5, 7])
    for r in results:
        print(
            f"  Product {r['product_id']}: {r['average_rating']} stars ({r['review_count']} reviews)")
