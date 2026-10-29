"""Read-only loader and metrics for the synthetic 90-day payment history.

The JSON files under ``data/`` are produced by ``data/generate_data.py``
(fixed seed, fixed anchor date). Every number the dashboard shows is
computed here from those rows — nothing is hardcoded in the UI.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Iterable

DATA_DIR = Path(__file__).resolve().parent / "data"

# Lifecycle order used for the per-order event story and the type filter.
EVENT_TYPES: tuple[str, ...] = (
    "payment_intent.created",
    "payment_intent.payment_failed",
    "charge.succeeded",
    "payment_intent.succeeded",
    "checkout.session.completed",
    "charge.refunded",
    "charge.dispute.created",
    "charge.dispute.closed",
)


class HistoryError(ValueError):
    """Raised when the dataset is missing or a lookup fails."""


@dataclass(frozen=True)
class Dataset:
    """All synthetic history collections plus id indexes."""

    manifest: dict
    products: list[dict]
    customers: list[dict]
    orders: list[dict]
    payment_attempts: list[dict]
    refunds: list[dict]
    disputes: list[dict]
    webhook_events: list[dict]

    @property
    def customers_by_id(self) -> dict[str, dict]:
        return {c["id"]: c for c in self.customers}

    @property
    def orders_by_id(self) -> dict[str, dict]:
        return {o["id"]: o for o in self.orders}


def _read(data_dir: Path, name: str):
    path = data_dir / name
    if not path.exists():
        raise HistoryError(
            f"Missing {path.name}. Run: python3 data/generate_data.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def load_dataset(data_dir: Path = DATA_DIR) -> Dataset:
    """Load every history file once per process (read-only)."""
    return Dataset(
        manifest=_read(data_dir, "manifest.json"),
        products=_read(data_dir, "products.json"),
        customers=_read(data_dir, "customers.json"),
        orders=_read(data_dir, "orders.json"),
        payment_attempts=_read(data_dir, "payment_attempts.json"),
        refunds=_read(data_dir, "refunds.json"),
        disputes=_read(data_dir, "disputes.json"),
        webhook_events=_read(data_dir, "webhook_events.json"),
    )


def parse_ts(value: str) -> datetime:
    """Parse the dataset's ``YYYY-MM-DDTHH:MM:SSZ`` timestamps."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def usd(cents: int) -> str:
    """Format cents as a USD string."""
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


# --- metrics -------------------------------------------------------------------


def summary_metrics(ds: Dataset) -> dict[str, int | float]:
    """Headline money and volume numbers, all summed from dataset rows.

    net = gross - refunds - disputed funds still withdrawn (lost or open);
    won disputes are reinstated and do not reduce net.
    """
    succeeded = [a for a in ds.payment_attempts if a["status"] == "succeeded"]
    failed = [a for a in ds.payment_attempts if a["status"] == "failed"]
    gross = sum(a["amount_cents"] for a in succeeded)
    refunded = sum(r["amount_cents"] for r in ds.refunds)
    disputed = sum(d["amount_cents"] for d in ds.disputes)
    dispute_withdrawn = sum(
        d["amount_cents"] for d in ds.disputes if d["status"] != "won"
    )
    attempts = len(ds.payment_attempts)
    return {
        "gross_cents": gross,
        "refunded_cents": refunded,
        "disputed_cents": disputed,
        "dispute_withdrawn_cents": dispute_withdrawn,
        "net_cents": gross - refunded - dispute_withdrawn,
        "orders": len(ds.orders),
        "customers": len(ds.customers),
        "payment_attempts": attempts,
        "succeeded_payments": len(succeeded),
        "failed_attempts": len(failed),
        "success_rate": len(succeeded) / attempts if attempts else 0.0,
        "refunds": len(ds.refunds),
        "disputes": len(ds.disputes),
        "webhook_events": len(ds.webhook_events),
        "average_order_cents": gross // len(succeeded) if succeeded else 0,
    }


def window_dates(ds: Dataset) -> list[date]:
    """Every calendar day in the dataset window, oldest first."""
    start = parse_ts(ds.manifest["window_start"]).date()
    return [start + timedelta(days=i) for i in range(ds.manifest["window_days"])]


def daily_series(ds: Dataset) -> list[dict]:
    """Per-day rows: gross, refunds, orders, succeeded and failed attempts."""
    rows = {
        d: {"date": d.isoformat(), "gross_cents": 0, "refunded_cents": 0,
            "orders": 0, "succeeded": 0, "failed": 0}
        for d in window_dates(ds)
    }
    for order in ds.orders:
        rows[parse_ts(order["created_at"]).date()]["orders"] += 1
    for attempt in ds.payment_attempts:
        row = rows[parse_ts(attempt["created_at"]).date()]
        if attempt["status"] == "succeeded":
            row["gross_cents"] += attempt["amount_cents"]
            row["succeeded"] += 1
        else:
            row["failed"] += 1
    for refund in ds.refunds:
        rows[parse_ts(refund["created_at"]).date()]["refunded_cents"] += refund["amount_cents"]
    return list(rows.values())


def weekday_profile(ds: Dataset) -> list[dict]:
    """Orders per weekday (Mon..Sun) — shows the weekday/weekend shape."""
    names = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    counts = Counter(parse_ts(o["created_at"]).weekday() for o in ds.orders)
    return [{"weekday": f"{i + 1}-{names[i]}", "orders": counts.get(i, 0)}
            for i in range(7)]


def failure_breakdown(ds: Dataset) -> list[tuple[str, int]]:
    """Failed attempts by decline reason (decline_code, else failure_code)."""
    counts = Counter(
        a["decline_code"] or a["failure_code"]
        for a in ds.payment_attempts if a["status"] == "failed"
    )
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def product_revenue(ds: Dataset) -> list[dict]:
    """Units and gross per product over paid orders (line items x price)."""
    paid = {a["order_id"] for a in ds.payment_attempts if a["status"] == "succeeded"}
    units: dict[str, int] = defaultdict(int)
    gross: dict[str, int] = defaultdict(int)
    for order in ds.orders:
        if order["id"] not in paid:
            continue
        for item in order["items"]:
            units[item["product_id"]] += item["quantity"]
            gross[item["product_id"]] += item["unit_price_cents"] * item["quantity"]
    rows = [{"product_id": p["id"], "name": p["name"], "price_cents": p["price_cents"],
             "units": units[p["id"]], "gross_cents": gross[p["id"]]}
            for p in ds.products]
    return sorted(rows, key=lambda r: (-r["gross_cents"], r["product_id"]))


# --- search / filter -----------------------------------------------------------


def filter_events(
    ds: Dataset,
    *,
    types: Iterable[str] | None = None,
    query: str = "",
    newest_first: bool = True,
) -> list[dict]:
    """Filter webhook events by type and a free-text query.

    The query matches (case-insensitive substring) event id, type, order id,
    PaymentIntent id, charge id, customer id, customer name, or email.
    """
    wanted = set(types) if types else None
    needle = query.strip().lower()
    customers = ds.customers_by_id
    out = []
    for event in ds.webhook_events:
        if wanted is not None and event["type"] not in wanted:
            continue
        if needle:
            customer = customers.get(event["customer_id"], {})
            haystack = " ".join(
                str(v) for v in (
                    event["id"], event["type"], event["order_id"],
                    event["payment_intent_id"], event["charge_id"] or "",
                    event["customer_id"], customer.get("name", ""),
                    customer.get("email", ""),
                )
            ).lower()
            if needle not in haystack:
                continue
        out.append(event)
    out.sort(key=lambda e: (e["created_at"], e["id"]), reverse=newest_first)
    return out


def filter_orders(
    ds: Dataset,
    *,
    statuses: Iterable[str] | None = None,
    query: str = "",
) -> list[dict]:
    """Orders newest first, filtered by status and id/customer text."""
    wanted = set(statuses) if statuses else None
    needle = query.strip().lower()
    customers = ds.customers_by_id
    out = []
    for order in ds.orders:
        if wanted is not None and order["status"] not in wanted:
            continue
        if needle:
            customer = customers[order["customer_id"]]
            haystack = " ".join((order["id"], order["payment_intent_id"],
                                 customer["id"], customer["name"],
                                 customer["email"])).lower()
            if needle not in haystack:
                continue
        out.append(order)
    out.sort(key=lambda o: (o["created_at"], o["id"]), reverse=True)
    return out


def paginate(rows: list, page: int, page_size: int) -> list:
    """1-based page slice; out-of-range pages clamp to the last page."""
    if not rows:
        return []
    pages = max(1, -(-len(rows) // page_size))
    page = min(max(1, page), pages)
    return rows[(page - 1) * page_size: page * page_size]


def order_story(ds: Dataset, order_id: str) -> dict:
    """Everything about one order: customer, attempts, refund, dispute, events."""
    order = ds.orders_by_id.get(order_id)
    if order is None:
        raise HistoryError(f"Unknown order {order_id}")
    return {
        "order": order,
        "customer": ds.customers_by_id[order["customer_id"]],
        "attempts": sorted(
            (a for a in ds.payment_attempts if a["order_id"] == order_id),
            key=lambda a: a["attempt_number"],
        ),
        "refunds": [r for r in ds.refunds if r["order_id"] == order_id],
        "disputes": [d for d in ds.disputes if d["order_id"] == order_id],
        "events": sorted(
            (e for e in ds.webhook_events if e["order_id"] == order_id),
            key=lambda e: (e["created_at"], EVENT_TYPES.index(e["type"])),
        ),
    }
