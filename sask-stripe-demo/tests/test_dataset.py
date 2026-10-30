"""Referential integrity, lifecycle ordering, and money reconciliation."""
from __future__ import annotations

from collections import Counter, defaultdict

import pytest

import history
from catalog import CATALOG
from history import parse_ts

DS = history.load_dataset()
ANCHOR = parse_ts(DS.manifest["anchor"])
WINDOW_START = parse_ts(DS.manifest["window_start"])
ORDERS = DS.orders_by_id
CUSTOMERS = DS.customers_by_id
PRODUCTS = {p["id"]: p for p in DS.products}
ATTEMPTS = {a["id"]: a for a in DS.payment_attempts}


def _events_by_order() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for event in DS.webhook_events:
        out[event["order_id"]].append(event)
    return out


EVENTS_BY_ORDER = _events_by_order()


# --- provenance ----------------------------------------------------------------


def test_customers_are_synthetic_on_example_domains() -> None:
    emails = [c["email"] for c in DS.customers]
    assert len(set(emails)) == len(emails)
    assert all(e.split("@")[1] in ("example.com", "example.org") for e in emails)
    assert len({c["id"] for c in DS.customers}) == len(DS.customers)


def test_catalog_spread_and_storefront_share_one_source() -> None:
    prices = [p["price_cents"] for p in DS.products]
    assert min(prices) >= 1500 and max(prices) <= 50000
    assert {p.id: p.price_cents for p in CATALOG} == {
        p["id"]: p["price_cents"] for p in DS.products
    }


def test_all_ids_unique() -> None:
    for rows in (DS.orders, DS.payment_attempts, DS.refunds, DS.disputes,
                 DS.webhook_events):
        assert len({r["id"] for r in rows}) == len(rows)
    assert len({o["payment_intent_id"] for o in DS.orders}) == len(DS.orders)


# --- referential integrity ---------------------------------------------------


def test_orders_reference_real_customers_and_products() -> None:
    for order in DS.orders:
        assert order["customer_id"] in CUSTOMERS
        assert order["items"]
        for item in order["items"]:
            product = PRODUCTS[item["product_id"]]
            assert item["unit_price_cents"] == product["price_cents"]
            assert item["name"] == product["name"]
            assert item["quantity"] >= 1
        assert order["total_cents"] == sum(
            i["unit_price_cents"] * i["quantity"] for i in order["items"]
        )


def test_attempts_reference_real_orders_and_match_totals() -> None:
    for attempt in DS.payment_attempts:
        order = ORDERS[attempt["order_id"]]
        assert attempt["customer_id"] == order["customer_id"]
        assert attempt["payment_intent_id"] == order["payment_intent_id"]
        assert attempt["amount_cents"] == order["total_cents"]


def test_events_reference_real_orders_and_charges() -> None:
    for event in DS.webhook_events:
        order = ORDERS[event["order_id"]]
        assert event["customer_id"] == order["customer_id"]
        assert event["payment_intent_id"] == order["payment_intent_id"]
        if event["charge_id"] is not None:
            assert ATTEMPTS[event["charge_id"]]["order_id"] == order["id"]
        payload = event["payload"]
        assert payload["id"] == event["id"]
        assert payload["type"] == event["type"]
        assert payload["livemode"] is False
        assert payload["created"] == int(parse_ts(event["created_at"]).timestamp())
        assert payload["data"]["object"]["metadata"]["order_id"] == order["id"]


def test_refunds_and_disputes_reference_succeeded_charges() -> None:
    for row in DS.refunds + DS.disputes:
        charge = ATTEMPTS[row["charge_id"]]
        assert charge["status"] == "succeeded"
        assert charge["order_id"] == row["order_id"]
        assert row["amount_cents"] == charge["amount_cents"]


# --- timestamps and lifecycle ------------------------------------------------


def test_everything_inside_the_window() -> None:
    stamps = [parse_ts(r["created_at"]) for rows in (
        DS.orders, DS.payment_attempts, DS.refunds, DS.disputes, DS.webhook_events
    ) for r in rows]
    stamps += [parse_ts(d["closed_at"]) for d in DS.disputes if d["closed_at"]]
    assert min(stamps) >= WINDOW_START
    assert max(stamps) <= ANCHOR


def test_customer_created_before_first_order() -> None:
    first: dict[str, str] = {}
    for order in DS.orders:
        first[order["customer_id"]] = min(
            first.get(order["customer_id"], order["created_at"]), order["created_at"]
        )
    for cid, created in first.items():
        assert parse_ts(CUSTOMERS[cid]["created_at"]) <= parse_ts(created)


def test_event_never_precedes_its_parent() -> None:
    for event in DS.webhook_events:
        ts = parse_ts(event["created_at"])
        assert ts >= parse_ts(ORDERS[event["order_id"]]["created_at"])
        if event["charge_id"]:
            assert ts >= parse_ts(ATTEMPTS[event["charge_id"]]["created_at"])


def test_attempts_are_contiguous_and_chronological() -> None:
    by_order: dict[str, list[dict]] = defaultdict(list)
    for attempt in DS.payment_attempts:
        by_order[attempt["order_id"]].append(attempt)
    assert set(by_order) == set(ORDERS)  # every order has >= 1 attempt
    for order_id, attempts in by_order.items():
        attempts.sort(key=lambda a: a["attempt_number"])
        assert [a["attempt_number"] for a in attempts] == list(range(1, len(attempts) + 1))
        times = [parse_ts(a["created_at"]) for a in attempts]
        assert times == sorted(times) and len(set(times)) == len(times)
        assert times[0] > parse_ts(ORDERS[order_id]["created_at"])
        statuses = [a["status"] for a in attempts]
        # Only the final attempt may succeed; nothing is charged after success.
        assert "succeeded" not in statuses[:-1]


@pytest.mark.parametrize("order", DS.orders, ids=lambda o: o["id"])
def test_order_lifecycle_story(order: dict) -> None:
    events = EVENTS_BY_ORDER[order["id"]]
    times = [parse_ts(e["created_at"]) for e in events]
    # Strict chronological order within one order's lifecycle.
    assert times == sorted(times) and len(set(times)) == len(times)
    types = [e["type"] for e in events]
    assert types[0] == "payment_intent.created"
    assert types.count("payment_intent.created") == 1

    attempts = [a for a in DS.payment_attempts if a["order_id"] == order["id"]]
    failed = [a for a in attempts if a["status"] == "failed"]
    succeeded = [a for a in attempts if a["status"] == "succeeded"]
    assert types.count("payment_intent.payment_failed") == len(failed)
    for attempt in failed:
        match = [e for e in events if e["charge_id"] == attempt["id"]]
        assert [e["type"] for e in match] == ["payment_intent.payment_failed"]
        error = match[0]["payload"]["data"]["object"]["last_payment_error"]
        assert error["code"] == attempt["failure_code"]

    if not succeeded:
        assert order["status"] == "failed"
        assert order["paid_at"] is None
        assert set(types) <= {"payment_intent.created", "payment_intent.payment_failed"}
        return

    charge = succeeded[0]
    assert order["paid_at"] == charge["created_at"]
    paid_types = [e["type"] for e in events if e["charge_id"] == charge["id"]]
    expected = ["charge.succeeded", "payment_intent.succeeded"]
    if order["channel"] == "checkout":
        expected.append("checkout.session.completed")
    tail = [t for t in paid_types
            if t not in ("charge.refunded", "charge.dispute.created", "charge.dispute.closed")]
    assert tail == expected
    # Payment events come after every failed attempt's event.
    first_paid = types.index("charge.succeeded")
    assert "payment_intent.payment_failed" not in types[first_paid:]

    refunds = [r for r in DS.refunds if r["order_id"] == order["id"]]
    disputes = [d for d in DS.disputes if d["order_id"] == order["id"]]
    assert not (refunds and disputes)
    if refunds:
        refund = refunds[0]
        assert order["status"] == "refunded" and order["refund_id"] == refund["id"]
        assert parse_ts(refund["created_at"]) > parse_ts(order["paid_at"])
        refund_events = [e for e in events if e["type"] == "charge.refunded"]
        assert len(refund_events) == 1
        assert refund_events[0]["created_at"] == refund["created_at"]
        obj = refund_events[0]["payload"]["data"]["object"]
        assert obj["refunded"] is True and obj["amount_refunded"] == refund["amount_cents"]
        assert types[-1] == "charge.refunded"
    else:
        assert order["status"] == "fulfilled"
        assert "charge.refunded" not in types
    if disputes:
        dispute = disputes[0]
        assert order["dispute_id"] == dispute["id"]
        opened = parse_ts(dispute["created_at"])
        assert opened > parse_ts(order["paid_at"])
        created_evt = [e for e in events if e["type"] == "charge.dispute.created"]
        closed_evt = [e for e in events if e["type"] == "charge.dispute.closed"]
        assert len(created_evt) == 1 and created_evt[0]["created_at"] == dispute["created_at"]
        if dispute["status"] in ("won", "lost"):
            assert len(closed_evt) == 1
            assert closed_evt[0]["created_at"] == dispute["closed_at"]
            assert parse_ts(dispute["closed_at"]) > opened
            assert closed_evt[0]["payload"]["data"]["object"]["status"] == dispute["status"]
        else:
            assert not closed_evt and dispute["closed_at"] is None
    else:
        assert not any(t.startswith("charge.dispute") for t in types)


def test_two_to_four_events_per_paid_lifecycle() -> None:
    for order in DS.orders:
        events = EVENTS_BY_ORDER[order["id"]]
        core = [e for e in events if e["type"] not in (
            "payment_intent.payment_failed", "charge.refunded",
            "charge.dispute.created", "charge.dispute.closed")]
        if order["paid_at"]:
            assert 3 <= len(core) <= 4
        else:
            assert len(core) == 1


# --- realism -----------------------------------------------------------------


def test_status_mix_is_realistic() -> None:
    attempts = Counter(a["status"] for a in DS.payment_attempts)
    assert attempts["succeeded"] > attempts["failed"] > 0.2 * len(DS.payment_attempts)
    codes = Counter(a["decline_code"] or a["failure_code"]
                    for a in DS.payment_attempts if a["status"] == "failed")
    assert {"generic_decline", "insufficient_funds", "expired_card"} <= set(codes)
    recovered = {a["order_id"] for a in DS.payment_attempts
                 if a["status"] == "succeeded" and a["attempt_number"] > 1}
    assert len(recovered) >= 20  # failed attempts retried to success
    assert {d["status"] for d in DS.disputes} == {"won", "lost", "needs_response"}


def test_volume_curve_has_weekday_shape_and_growth() -> None:
    daily = history.daily_series(DS)
    weekday = [r["orders"] for r in daily if parse_ts(r["date"] + "T00:00:00Z").weekday() < 5]
    weekend = [r["orders"] for r in daily if parse_ts(r["date"] + "T00:00:00Z").weekday() >= 5]
    assert sum(weekday) / len(weekday) > 1.4 * sum(weekend) / len(weekend)
    half = len(daily) // 2
    first = sum(r["orders"] for r in daily[:half])
    second = sum(r["orders"] for r in daily[half:])
    assert second > 1.15 * first
    assert all(r["orders"] >= 0 for r in daily) and sum(r["orders"] for r in daily) == len(DS.orders)


# --- money reconciliation ----------------------------------------------------


def test_dashboard_money_equals_dataset_sums() -> None:
    m = history.summary_metrics(DS)
    paid_orders = [o for o in DS.orders if o["paid_at"]]
    gross = sum(o["total_cents"] for o in paid_orders)
    assert m["gross_cents"] == gross
    assert m["gross_cents"] == sum(
        e["payload"]["data"]["object"]["amount"]
        for e in DS.webhook_events if e["type"] == "charge.succeeded"
    )
    refunded = sum(r["amount_cents"] for r in DS.refunds)
    assert m["refunded_cents"] == refunded == sum(
        e["payload"]["data"]["object"]["amount_refunded"]
        for e in DS.webhook_events if e["type"] == "charge.refunded"
    )
    assert m["refunded_cents"] == sum(
        o["total_cents"] for o in DS.orders if o["status"] == "refunded"
    )
    withdrawn = sum(d["amount_cents"] for d in DS.disputes if d["status"] != "won")
    assert m["disputed_cents"] == sum(d["amount_cents"] for d in DS.disputes)
    assert m["net_cents"] == gross - refunded - withdrawn
    assert m["orders"] == len(DS.orders)
    assert m["payment_attempts"] == len(DS.payment_attempts)
    assert m["webhook_events"] == len(DS.webhook_events)


def test_chart_series_reconcile_to_totals() -> None:
    m = history.summary_metrics(DS)
    daily = history.daily_series(DS)
    assert len(daily) == DS.manifest["window_days"]
    assert sum(r["gross_cents"] for r in daily) == m["gross_cents"]
    assert sum(r["refunded_cents"] for r in daily) == m["refunded_cents"]
    assert sum(r["succeeded"] for r in daily) == m["succeeded_payments"]
    assert sum(r["failed"] for r in daily) == m["failed_attempts"]
    assert sum(r["gross_cents"] for r in history.product_revenue(DS)) == m["gross_cents"]
    assert sum(r["orders"] for r in history.weekday_profile(DS)) == len(DS.orders)
    assert sum(n for _, n in history.failure_breakdown(DS)) == m["failed_attempts"]


# --- search helpers ----------------------------------------------------------


def test_event_filters_and_search() -> None:
    refunds = history.filter_events(DS, types=["charge.refunded"])
    assert len(refunds) == len(DS.refunds)
    order = DS.refunds[0]["order_id"]
    by_order = history.filter_events(DS, query=order)
    assert {e["order_id"] for e in by_order} == {order}
    assert len(by_order) == len(EVENTS_BY_ORDER[order])
    customer = CUSTOMERS[ORDERS[order]["customer_id"]]
    by_email = history.filter_events(DS, query=customer["email"].upper())
    assert by_email and all(e["customer_id"] == customer["id"] for e in by_email)
    assert history.filter_events(DS, query="no-such-thing") == []
    newest = history.filter_events(DS)
    assert newest[0]["created_at"] >= newest[-1]["created_at"]


def test_order_filters_pagination_and_story() -> None:
    failed = history.filter_orders(DS, statuses=["failed"])
    assert failed and all(o["status"] == "failed" for o in failed)
    rows = history.filter_orders(DS)
    pages = [history.paginate(rows, p, 25) for p in range(1, 14)]
    assert sum(len(p) for p in pages[:12]) == len(rows)
    assert history.paginate(rows, 999, 25) == pages[11]
    dispute = DS.disputes[0]
    story = history.order_story(DS, dispute["order_id"])
    assert story["disputes"] == [dispute]
    assert story["events"][0]["type"] == "payment_intent.created"
    with pytest.raises(history.HistoryError):
        history.order_story(DS, "ord_missing")
