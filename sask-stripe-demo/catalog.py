"""Fictional product catalog for the SASK LLC demo storefront.

Loaded from ``data/products.json`` — the same catalog the synthetic 90-day
payment history is priced from (written by ``data/generate_data.py``), so
storefront prices and historical order totals always agree.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from .models import Product
except ImportError:  # standalone: streamlit run app.py from this folder
    from models import Product

PRODUCTS_PATH = Path(__file__).resolve().parent / "data" / "products.json"


def load_catalog(path: Path = PRODUCTS_PATH) -> tuple[Product, ...]:
    """Read active fictional products from the generated catalog file."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        Product(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            price_cents=row["price_cents"],
        )
        for row in rows
        if row.get("active", True)
    )


# Twelve fictional SW-services style products — no real inventory or SKUs.
CATALOG: tuple[Product, ...] = load_catalog()


def get_product(product_id: str) -> Product | None:
    """Return a catalog product by id, or None if unknown."""
    for product in CATALOG:
        if product.id == product_id:
            return product
    return None
