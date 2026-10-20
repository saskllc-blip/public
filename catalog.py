"""Fictional product catalog for the SASK LLC demo storefront."""
from __future__ import annotations

try:
    from .models import Product
except ImportError:  # standalone: streamlit run app.py from this folder
    from models import Product

# Four fictional SW-services style products — no real inventory or SKUs.
CATALOG: tuple[Product, ...] = (
    Product(
        id="prod-api-audit",
        name="API Integration Audit",
        description="Fictional one-day review of webhook and auth patterns.",
        price_cents=14900,
    ),
    Product(
        id="prod-webhook-kit",
        name="Webhook Starter Kit",
        description="Sample handlers for signature checks and retries (demo only).",
        price_cents=7900,
    ),
    Product(
        id="prod-idempotency-clinic",
        name="Idempotency Clinic",
        description="Workshop-style walkthrough of duplicate-event handling.",
        price_cents=9900,
    ),
    Product(
        id="prod-retry-playbook",
        name="Retry Playbook Pack",
        description="Fictional runbooks for payment_failed and refund events.",
        price_cents=5900,
    ),
)


def get_product(product_id: str) -> Product | None:
    """Return a catalog product by id, or None if unknown."""
    for product in CATALOG:
        if product.id == product_id:
            return product
    return None
