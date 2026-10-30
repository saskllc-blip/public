"""Deterministic synthetic payment-history generator for the Stripe demo.

Hard rule: 100% synthetic, fictional data. Customer names are invented
combinations, every email is on example.com / example.org, products are
fictional SW-services SKUs, and every Stripe-shaped id is random hex from a
fixed seed. No real people, businesses, cards, or scraped rows.

Run from the app folder (or anywhere):

    python3 data/generate_data.py

Same seed + same anchor -> byte-identical JSON files. Re-running overwrites
the committed files with identical bytes (idempotent).
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

SEED = 20261025
# Fixed anchor: the window ends here regardless of when the script runs.
ANCHOR = datetime(2026, 10, 25, 23, 59, 59, tzinfo=timezone.utc)
WINDOW_DAYS = 90
WINDOW_START = datetime(2026, 10, 25, tzinfo=timezone.utc) - timedelta(
    days=WINDOW_DAYS - 1
)
GENERATOR_VERSION = "1.0.0"
API_VERSION = "2024-06-20"

N_CUSTOMERS = 120
N_ORDERS = 300
N_REFUNDS = 15  # ~5% of orders
N_DISPUTES = 3  # ~1% of orders

# Volume curve: weekday/weekend shape plus mild growth across the window.
WEEKEND_FACTOR = 0.55
GROWTH = 0.6  # last day ~1.6x the first day

# Payment attempt outcome model (tuned so ~450 attempts land on 300 orders).
P_FIRST_FAIL = 0.42
P_RETRY_FAIL = 0.35
P_RETRY_AFTER_FAIL = 0.85
MAX_ATTEMPTS = 4
P_CHECKOUT_CHANNEL = 0.65  # rest are direct API PaymentIntents

DATA_FILES = (
    "products.json",
    "customers.json",
    "orders.json",
    "payment_attempts.json",
    "refunds.json",
    "disputes.json",
    "webhook_events.json",
)

# id, name, description, price_cents, popularity weight.
# The first four are the storefront's original SKUs (same ids and prices).
PRODUCTS = (
    ("prod-api-audit", "API Integration Audit",
     "Fictional one-day review of webhook and auth patterns.", 14900, 7),
    ("prod-webhook-kit", "Webhook Starter Kit",
     "Sample handlers for signature checks and retries (demo only).", 7900, 10),
    ("prod-idempotency-clinic", "Idempotency Clinic",
     "Workshop-style walkthrough of duplicate-event handling.", 9900, 8),
    ("prod-retry-playbook", "Retry Playbook Pack",
     "Fictional runbooks for payment_failed and refund events.", 5900, 9),
    ("prod-signature-cheatsheet", "Signature Check Cheat Sheet",
     "One-page fictional reference for verifying webhook signatures.", 1500, 12),
    ("prod-test-card-deck", "Test Card Scenario Deck",
     "Printable deck of simulated decline and success scenarios.", 2900, 11),
    ("prod-refund-flow-review", "Refund Flow Review",
     "Fictional async review of refund and dispute handling.", 4900, 8),
    ("prod-event-replay-lab", "Event Replay Lab",
     "Guided lab replaying out-of-order webhook deliveries (demo only).", 19900, 5),
    ("prod-checkout-hardening", "Checkout Hardening Sprint",
     "Fictional two-day sprint on checkout error paths.", 24900, 4),
    ("prod-billing-migration", "Billing Migration Plan",
     "Fictional migration plan from ad-hoc charges to PaymentIntents.", 34900, 3),
    ("prod-dispute-defense", "Dispute Defense Toolkit",
     "Evidence templates for simulated chargeback responses.", 44900, 2),
    ("prod-integration-retainer", "Integration Retainer (Monthly)",
     "Fictional monthly retainer for payment-integration support.", 49900, 2),
)

FIRST_NAMES = (
    "Avery", "Blake", "Casey", "Dakota", "Emery", "Finley", "Harper", "Indigo",
    "Jordan", "Kendall", "Linden", "Marlow", "Nova", "Oakley", "Peyton", "Quinn",
    "Reese", "Sage", "Tatum", "Umber", "Vale", "Wren", "Yael", "Zephyr",
)
LAST_NAMES = (
    "Ashgrove", "Birchwell", "Cobalt", "Dunmere", "Elderfield", "Fernhollow",
    "Glimmerton", "Hollowbrook", "Ironvale", "Juniperline", "Kestrelby",
    "Larkspur", "Mistvale", "Northwind", "Oakhaven", "Pinecrest", "Quillmoor",
    "Ravensholt", "Silverlake", "Thornbury",
)
EMAIL_DOMAINS = ("example.com", "example.org")

# Simulated card shapes (Stripe test-card last4s), never real cards.
SUCCESS_CARDS = (
    (("visa", "4242"), 5),
    (("mastercard", "4444"), 3),
    (("amex", "8431"), 1),
    (("visa", "5556"), 1),
)
# (failure_code, decline_code, message, card) with weights.
FAILURES = (
    (("card_declined", "generic_decline", "Your card was declined.",
      ("visa", "0002")), 35),
    (("card_declined", "insufficient_funds", "Your card has insufficient funds.",
      ("visa", "9995")), 30),
    (("expired_card", None, "Your card has expired.", ("visa", "0069")), 15),
    (("incorrect_cvc", None, "Your card's security code is incorrect.",
      ("visa", "0127")), 12),
    (("processing_error", None,
      "An error occurred while processing your card. Try again in a little bit.",
      ("visa", "0119")), 8),
)
REFUND_REASONS = (("requested_by_customer", 8), ("duplicate", 1), ("fraudulent", 1))
DISPUTE_REASONS = ("fraudulent", "product_not_received", "unrecognized")
DISPUTE_OUTCOMES = ("won", "lost", "needs_response")

_HEX = "0123456789abcdef"
_ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


class _Ids:
    """Seeded, collision-checked Stripe-shaped id factory."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._seen: set[str] = set()

    def new(self, prefix: str, length: int = 14, alphabet: str = _ALNUM) -> str:
        while True:
            value = prefix + "".join(self._rng.choice(alphabet) for _ in range(length))
            if value not in self._seen:
                self._seen.add(value)
                return value


def _weighted(rng: random.Random, pairs):
    values = [value for value, _ in pairs]
    weights = [weight for _, weight in pairs]
    return rng.choices(values, weights=weights, k=1)[0]


def iso(ts: datetime) -> str:
    """UTC ISO-8601 with a Z suffix, second precision."""
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _unix(ts: datetime) -> int:
    return int(ts.timestamp())


def _daily_order_counts(rng: random.Random) -> list[int]:
    """Allocate exactly N_ORDERS across the window with weekday + growth shape."""
    weights = []
    for day in range(WINDOW_DAYS):
        date = WINDOW_START + timedelta(days=day)
        weight = 1.0 + GROWTH * day / (WINDOW_DAYS - 1)
        if date.weekday() >= 5:
            weight *= WEEKEND_FACTOR
        weight *= rng.uniform(0.85, 1.15)
        weights.append(weight)
    total = sum(weights)
    expected = [w / total * N_ORDERS for w in weights]
    counts = [int(e) for e in expected]
    # Largest-remainder rounding keeps the total exact and deterministic.
    order = sorted(range(WINDOW_DAYS), key=lambda i: (-(expected[i] - counts[i]), i))
    for i in order[: N_ORDERS - sum(counts)]:
        counts[i] += 1
    return counts


def _order_time(rng: random.Random, day: int) -> datetime:
    """Business-hours-skewed timestamp inside a window day (UTC)."""
    hour = _weighted(
        rng,
        [(h, 1) for h in range(0, 7)]
        + [(h, 4) for h in range(7, 12)]
        + [(h, 6) for h in range(12, 19)]
        + [(h, 3) for h in range(19, 24)],
    )
    return WINDOW_START + timedelta(
        days=day, hours=hour, minutes=rng.randrange(60), seconds=rng.randrange(60)
    )


def _event(ids: _Ids, etype: str, ts: datetime, order: dict, obj: dict,
           charge_id: str | None = None) -> dict:
    """One webhook event: index fields for the console + a Stripe-shaped payload."""
    evt_id = ids.new("evt_", 24)
    return {
        "id": evt_id,
        "type": etype,
        "created_at": iso(ts),
        "order_id": order["id"],
        "customer_id": order["customer_id"],
        "payment_intent_id": order["payment_intent_id"],
        "charge_id": charge_id,
        "payload": {
            "id": evt_id,
            "object": "event",
            "api_version": API_VERSION,
            "created": _unix(ts),
            "livemode": False,
            "pending_webhooks": 0,
            "request": {"id": None, "idempotency_key": None},
            "type": etype,
            "data": {"object": obj},
        },
    }


def _pi_object(order: dict, ts_created: datetime, status: str,
               last_error: dict | None = None, latest_charge: str | None = None) -> dict:
    return {
        "id": order["payment_intent_id"],
        "object": "payment_intent",
        "amount": order["total_cents"],
        "amount_received": order["total_cents"] if status == "succeeded" else 0,
        "currency": "usd",
        "customer": order["customer_id"],
        "created": _unix(ts_created),
        "status": status,
        "latest_charge": latest_charge,
        "last_payment_error": last_error,
        "metadata": {"order_id": order["id"]},
    }


def _charge_object(order: dict, attempt: dict, *, amount_refunded: int = 0,
                   refund: dict | None = None, disputed: bool = False) -> dict:
    succeeded = attempt["status"] == "succeeded"
    obj = {
        "id": attempt["id"],
        "object": "charge",
        "amount": attempt["amount_cents"],
        "amount_captured": attempt["amount_cents"] if succeeded else 0,
        "amount_refunded": amount_refunded,
        "captured": succeeded,
        "currency": "usd",
        "customer": order["customer_id"],
        "payment_intent": order["payment_intent_id"],
        "created": _unix(datetime.fromisoformat(attempt["created_at"])),
        "paid": succeeded,
        "refunded": amount_refunded == attempt["amount_cents"] and amount_refunded > 0,
        "disputed": disputed,
        "status": attempt["status"],
        "failure_code": attempt["failure_code"],
        "failure_message": attempt["failure_message"],
        "outcome": {
            "type": "authorized" if succeeded else "issuer_declined",
            "network_status": "approved_by_network" if succeeded else "declined_by_network",
            "reason": attempt["decline_code"] or attempt["failure_code"],
        },
        "payment_method_details": {
            "type": "card",
            "card": {"brand": attempt["card_brand"], "last4": attempt["card_last4"]},
        },
        "metadata": {"order_id": order["id"]},
    }
    if refund is not None:
        obj["refunds"] = {
            "object": "list",
            "data": [{
                "id": refund["id"],
                "object": "refund",
                "amount": refund["amount_cents"],
                "charge": attempt["id"],
                "reason": refund["reason"],
                "status": "succeeded",
                "created": _unix(datetime.fromisoformat(refund["created_at"])),
            }],
        }
    return obj


def _dispute_object(dispute: dict, order: dict, status: str) -> dict:
    created = datetime.fromisoformat(dispute["created_at"])
    return {
        "id": dispute["id"],
        "object": "dispute",
        "amount": dispute["amount_cents"],
        "charge": dispute["charge_id"],
        "currency": "usd",
        "payment_intent": order["payment_intent_id"],
        "reason": dispute["reason"],
        "status": status,
        "created": _unix(created),
        "evidence_details": {"due_by": _unix(created + timedelta(days=7))},
        "metadata": {"order_id": order["id"]},
    }


def generate(seed: int = SEED) -> dict[str, list[dict]]:
    """Build the full synthetic dataset in memory (pure function of seed)."""
    rng = random.Random(seed)
    ids = _Ids(rng)

    products = [
        {"id": pid, "name": name, "description": desc, "price_cents": price,
         "currency": "usd", "active": True}
        for pid, name, desc, price, _ in PRODUCTS
    ]
    product_weights = [(p, w) for p, (*_, w) in zip(products, PRODUCTS)]

    # --- customers -----------------------------------------------------------
    name_pairs = [(f, l) for f in FIRST_NAMES for l in LAST_NAMES]
    rng.shuffle(name_pairs)
    customers = []
    for first, last in name_pairs[:N_CUSTOMERS]:
        domain = rng.choice(EMAIL_DOMAINS)
        customers.append({
            "id": ids.new("cus_", 14),
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}@{domain}",
            "created_at": None,  # filled once first order time is known
        })
    # Heavy-tailed buying frequency: a few repeat customers, many one-offs.
    customer_weights = [rng.paretovariate(1.6) for _ in customers]

    # --- orders + payment attempts + core lifecycle events --------------------
    counts = _daily_order_counts(rng)
    order_times = sorted(
        _order_time(rng, day) for day, n in enumerate(counts) for _ in range(n)
    )

    orders: list[dict] = []
    attempts: list[dict] = []
    events: list[dict] = []
    first_order_at: dict[str, datetime] = {}

    for created in order_times:
        customer = rng.choices(customers, weights=customer_weights, k=1)[0]
        first_order_at.setdefault(customer["id"], created)

        n_lines = _weighted(rng, [(1, 70), (2, 22), (3, 8)])
        chosen: list[dict] = []
        while len(chosen) < n_lines:
            product = _weighted(rng, product_weights)
            if product not in chosen:
                chosen.append(product)
        items = [{
            "product_id": p["id"],
            "name": p["name"],
            "unit_price_cents": p["price_cents"],
            "quantity": _weighted(rng, [(1, 85), (2, 15)]),
        } for p in chosen]
        order = {
            "id": ids.new("ord_", 10, _HEX),
            "customer_id": customer["id"],
            "items": items,
            "total_cents": sum(i["unit_price_cents"] * i["quantity"] for i in items),
            "currency": "usd",
            "channel": "checkout" if rng.random() < P_CHECKOUT_CHANNEL else "api",
            "payment_intent_id": ids.new("pi_", 24),
            "status": "pending",
            "created_at": iso(created),
            "updated_at": iso(created),
            "paid_at": None,
            "refund_id": None,
            "dispute_id": None,
        }
        orders.append(order)

        pi_created = created + timedelta(seconds=rng.randint(2, 20))
        events.append(_event(ids, "payment_intent.created", pi_created, order,
                             _pi_object(order, pi_created, "requires_payment_method")))

        t = pi_created + timedelta(seconds=rng.randint(20, 180))
        for attempt_no in range(1, MAX_ATTEMPTS + 1):
            fail_p = P_FIRST_FAIL if attempt_no == 1 else P_RETRY_FAIL
            failed = rng.random() < fail_p
            if failed:
                code, decline, message, card = _weighted(rng, FAILURES)
            else:
                code, decline, message = None, None, None
                card = _weighted(rng, SUCCESS_CARDS)
            attempt = {
                "id": ids.new("ch_", 24),
                "order_id": order["id"],
                "customer_id": order["customer_id"],
                "payment_intent_id": order["payment_intent_id"],
                "attempt_number": attempt_no,
                "amount_cents": order["total_cents"],
                "currency": "usd",
                "status": "failed" if failed else "succeeded",
                "failure_code": code,
                "decline_code": decline,
                "failure_message": message,
                "card_brand": card[0],
                "card_last4": card[1],
                "created_at": iso(t),
            }
            attempts.append(attempt)

            if failed:
                ts = t + timedelta(seconds=rng.randint(1, 3))
                error = {"type": "card_error", "code": code, "decline_code": decline,
                         "message": message, "charge": attempt["id"]}
                events.append(_event(
                    ids, "payment_intent.payment_failed", ts, order,
                    _pi_object(order, pi_created, "requires_payment_method",
                               last_error=error, latest_charge=attempt["id"]),
                    charge_id=attempt["id"]))
                order["updated_at"] = iso(ts)
                next_t = ts + timedelta(minutes=rng.randint(2, 480))
                retry = (attempt_no < MAX_ATTEMPTS
                         and rng.random() < P_RETRY_AFTER_FAIL
                         and next_t < ANCHOR - timedelta(minutes=5))
                if not retry:
                    order["status"] = "failed"
                    break
                t = next_t
                continue

            ts = t + timedelta(seconds=1)
            events.append(_event(ids, "charge.succeeded", ts, order,
                                 _charge_object(order, attempt), charge_id=attempt["id"]))
            ts += timedelta(seconds=1)
            events.append(_event(
                ids, "payment_intent.succeeded", ts, order,
                _pi_object(order, pi_created, "succeeded", latest_charge=attempt["id"]),
                charge_id=attempt["id"]))
            if order["channel"] == "checkout":
                ts += timedelta(seconds=1)
                events.append(_event(ids, "checkout.session.completed", ts, order, {
                    "id": ids.new("cs_test_", 24),
                    "object": "checkout.session",
                    "amount_total": order["total_cents"],
                    "currency": "usd",
                    "customer": order["customer_id"],
                    "customer_details": {"name": customer["name"],
                                         "email": customer["email"]},
                    "mode": "payment",
                    "payment_intent": order["payment_intent_id"],
                    "payment_status": "paid",
                    "status": "complete",
                    "created": _unix(pi_created),
                    "metadata": {"order_id": order["id"]},
                }, charge_id=attempt["id"]))
            # Matches the live console: payment_intent.succeeded auto-fulfills.
            order["status"] = "fulfilled"
            order["paid_at"] = iso(t)
            order["updated_at"] = iso(ts)
            break

    customers_by_id = {c["id"]: c for c in customers}
    for cid, first in first_order_at.items():
        lead = timedelta(days=rng.uniform(0, 30), seconds=rng.randint(60, 3600))
        customers_by_id[cid]["created_at"] = iso(first - lead)
    for customer in customers:
        if customer["created_at"] is None:  # signed up, never bought
            day = rng.randrange(WINDOW_DAYS)
            customer["created_at"] = iso(_order_time(rng, day))

    succeeded_charge = {a["order_id"]: a for a in attempts if a["status"] == "succeeded"}

    # --- refunds (~5%) --------------------------------------------------------
    refunds: list[dict] = []
    eligible = [o for o in orders if o["status"] == "fulfilled"
                and datetime.fromisoformat(o["paid_at"]) <= ANCHOR - timedelta(days=3)]
    for order in sorted(rng.sample(eligible, N_REFUNDS), key=lambda o: o["paid_at"]):
        charge = succeeded_charge[order["id"]]
        paid = datetime.fromisoformat(order["paid_at"])
        latest = min(paid + timedelta(days=21), ANCHOR - timedelta(hours=1))
        when = paid + timedelta(seconds=rng.randint(3600, int((latest - paid).total_seconds())))
        refund = {
            "id": ids.new("re_", 24),
            "order_id": order["id"],
            "charge_id": charge["id"],
            "payment_intent_id": order["payment_intent_id"],
            "amount_cents": charge["amount_cents"],  # full refunds only
            "currency": "usd",
            "reason": _weighted(rng, REFUND_REASONS),
            "status": "succeeded",
            "created_at": iso(when),
        }
        refunds.append(refund)
        events.append(_event(ids, "charge.refunded", when, order,
                             _charge_object(order, charge,
                                            amount_refunded=refund["amount_cents"],
                                            refund=refund),
                             charge_id=charge["id"]))
        order["status"] = "refunded"
        order["refund_id"] = refund["id"]
        order["updated_at"] = iso(when)

    # --- disputes (~1%) -------------------------------------------------------
    disputes: list[dict] = []
    eligible = [o for o in orders if o["status"] == "fulfilled"
                and datetime.fromisoformat(o["paid_at"]) <= ANCHOR - timedelta(days=45)]
    outcomes = list(DISPUTE_OUTCOMES)
    rng.shuffle(outcomes)
    picked = sorted(rng.sample(eligible, N_DISPUTES), key=lambda o: o["paid_at"])
    for order, outcome in zip(picked, outcomes):
        charge = succeeded_charge[order["id"]]
        paid = datetime.fromisoformat(order["paid_at"])
        opened = paid + timedelta(days=rng.uniform(3, 20))
        closed = opened + timedelta(days=rng.uniform(6, 18)) if outcome != "needs_response" else None
        dispute = {
            "id": ids.new("dp_", 24),
            "order_id": order["id"],
            "charge_id": charge["id"],
            "payment_intent_id": order["payment_intent_id"],
            "amount_cents": charge["amount_cents"],
            "currency": "usd",
            "reason": rng.choice(DISPUTE_REASONS),
            "status": outcome,
            "created_at": iso(opened),
            "closed_at": iso(closed) if closed else None,
        }
        disputes.append(dispute)
        events.append(_event(ids, "charge.dispute.created", opened, order,
                             _dispute_object(dispute, order, "needs_response"),
                             charge_id=charge["id"]))
        if closed is not None:
            events.append(_event(ids, "charge.dispute.closed", closed, order,
                                 _dispute_object(dispute, order, outcome),
                                 charge_id=charge["id"]))
        order["dispute_id"] = dispute["id"]
        order["updated_at"] = iso(closed or opened)

    events.sort(key=lambda e: (e["created_at"], e["order_id"], e["id"]))
    return {
        "products": products,
        "customers": customers,
        "orders": orders,
        "payment_attempts": attempts,
        "refunds": refunds,
        "disputes": disputes,
        "webhook_events": events,
    }


def _dumps(records: list[dict]) -> str:
    """One JSON record per line: compact, stable, and diff-friendly."""
    lines = [json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
             for r in records]
    return "[\n" + ",\n".join(lines) + "\n]\n"


def render_files(dataset: dict[str, list[dict]]) -> dict[str, str]:
    """Serialize every data file plus manifest.json (with per-file sha256)."""
    files = {f"{name}.json": _dumps(rows) for name, rows in dataset.items()}
    digest = hashlib.sha256()
    for name in DATA_FILES:
        digest.update(name.encode())
        digest.update(files[name].encode())
    manifest = {
        "generated": "synthetic-fictional-only",
        "generator": "data/generate_data.py",
        "generator_version": GENERATOR_VERSION,
        "seed": SEED,
        "anchor": iso(ANCHOR),
        "window_start": iso(WINDOW_START),
        "window_days": WINDOW_DAYS,
        "counts": {name: len(rows) for name, rows in dataset.items()},
        "files": {name: hashlib.sha256(files[name].encode()).hexdigest()
                  for name in DATA_FILES},
        "dataset_sha256": digest.hexdigest(),
    }
    files["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return files


def write(out_dir: Path = DATA_DIR, seed: int = SEED) -> dict:
    """Generate and write all files; return the manifest."""
    files = render_files(generate(seed))
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
    return json.loads(files["manifest.json"])


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR
    result = write(target)
    print(json.dumps({"counts": result["counts"],
                      "dataset_sha256": result["dataset_sha256"]}, indent=2))
