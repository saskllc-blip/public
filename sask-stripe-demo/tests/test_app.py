"""Headless Streamlit AppTest over the full synthetic dataset."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

import history  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app.py")
DS = history.load_dataset()


@pytest.fixture()
def app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def _markdown(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_all_tabs_render_without_exceptions(app: AppTest) -> None:
    labels = [t.label for t in app.tabs]
    assert labels == ["Storefront", "Checkout", "Webhook console", "Orders",
                      "Dashboard (90 days)"]
    assert any("Demo store — simulated payments only" in w.value for w in app.warning)
    # Storefront lists the full generated catalog.
    for product in DS.products:
        assert f"**{product['name']}**" in _markdown(app)


def test_dashboard_metrics_come_from_data(app: AppTest) -> None:
    m = history.summary_metrics(DS)
    values = {metric.label: metric.value for metric in app.metric}
    assert values["Gross volume"] == history.usd(m["gross_cents"])
    assert values["Refunds"] == history.usd(m["refunded_cents"])
    assert values["Disputes"] == history.usd(m["disputed_cents"])
    assert values["Net volume"] == history.usd(m["net_cents"])
    assert values["Orders"] == str(m["orders"])
    assert values["Payment attempts"] == str(m["payment_attempts"])
    assert values["Webhook events"] == str(m["webhook_events"])
    # Three bar charts rendered from the daily / weekday series.
    charts = app.get("vega_lite_chart")
    assert len(charts) == 3


def _caption_has(at: AppTest, text: str) -> bool:
    return any(text in c.value for c in at.caption)


def test_event_history_type_filter(app: AppTest) -> None:
    assert _caption_has(app, f"{len(DS.webhook_events)} matching rows")
    app.multiselect(key="hist_evt_types").set_value(["charge.refunded"]).run()
    assert not app.exception
    assert _caption_has(app, f"{len(DS.refunds)} matching rows")
    assert "**charge.refunded**" in _markdown(app)
    assert "**payment_intent.created**" not in _markdown(app)


def test_event_history_search_and_paging(app: AppTest) -> None:
    order_id = DS.disputes[0]["order_id"]
    expected = history.filter_events(DS, query=order_id)
    app.text_input(key="hist_evt_q").set_value(order_id).run()
    assert not app.exception
    assert _caption_has(app, f"{len(expected)} matching rows")
    assert "**charge.dispute.created**" in _markdown(app)
    app.text_input(key="hist_evt_q").set_value("").run()
    app.number_input(key="hist_evt_page").set_value(10).run()
    assert not app.exception


def test_order_history_drilldown(app: AppTest) -> None:
    refund = DS.refunds[0]
    app.text_input(key="hist_order_q").set_value(refund["order_id"]).run()
    assert not app.exception
    assert _caption_has(app, "1 matching rows")
    app.selectbox(key="hist_order_pick").set_value(refund["order_id"]).run()
    text = _markdown(app)
    assert f"refund `{refund['id']}`" in text
    app.multiselect(key="hist_order_status").set_value(["failed"]).run()
    assert not app.exception


def test_live_store_flow_still_works(app: AppTest) -> None:
    app.button(key="add_prod-api-audit").click().run()
    app.button[[b.label for b in app.button].index(
        "Place order (creates pending order)")].click().run()
    assert not app.exception
    store = app.session_state["demo_store"]
    assert len(store.orders) == 1
    order = store.orders[0]
    assert order.status == "pending" and order.total_cents == 14900
    store.submit_checkout(order.id, "4242 4242 4242 4242")
    store.deliver_webhook(order.id, "payment_intent.succeeded")
    assert order.status == "fulfilled"
    dup = store.deliver_webhook(
        order.id, "payment_intent.succeeded",
        event_id=store.webhooks.event_log[-1].event_id,
    )
    assert dup.processing_result == "duplicate"
    app.run()
    assert not app.exception
