"""Headless render of every view with the full synthetic dataset (Streamlit AppTest)."""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGES = ["Dashboard", "Properties", "Tenants & Leases", "Payments", "Mortgages"]


def _run(page: str = "Dashboard") -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    if page != "Dashboard":
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception
    return at


@pytest.mark.parametrize("page", PAGES)
def test_every_view_renders(page: str) -> None:
    at = _run(page)
    assert "fictional" in at.warning[0].value
    assert at.dataframe or at.metric


def test_dashboard_shows_full_portfolio() -> None:
    at = _run()
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Properties"] == "30"
    assert metrics["Portfolio value"].startswith("$")
    assert len(at.dataframe[0].value) >= 8  # one row per country


def test_country_and_city_filter() -> None:
    at = _run()
    at.sidebar.multiselect[0].set_value(["India"]).run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Properties"] == "3"
    assert at.sidebar.multiselect[1].options == ["Bangalore"]
    at.sidebar.multiselect[0].set_value([]).run()
    at.sidebar.multiselect[1].set_value(["London", "Berlin"]).run()
    assert {m.label: m.value for m in at.metric}["Properties"] == "6"


def test_text_search_filters_every_view() -> None:
    at = _run()
    at.sidebar.text_input[0].set_value("Koramangala").run()
    assert {m.label: m.value for m in at.metric}["Properties"] == "1"
    for page in PAGES[1:]:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page


def test_mark_collected_from_payments_view() -> None:
    at = _run("Payments")
    before = {m.label: m.value for m in at.metric}["Total overdue"]
    collect = [b for b in at.button if (b.key or "").startswith("payment-")]
    assert collect, "expected outstanding payments to act on"
    collect[0].click().run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Total overdue"] != before
