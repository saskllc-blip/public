"""Lightweight smoke tests for the Keepers public demo.

Covers catalog invariants, the unknown-location safety rule, and a
headless render of every tab via Streamlit AppTest.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from generate_data import N_ITEMS, NO_GPS_FRACTION, SEED  # noqa: E402
from library import dashboard_summary, items_of, load_catalog, review_groups, search_library  # noqa: E402
from prompt import match_items, parse_prompt, unknown_location_safety_applies  # noqa: E402


def test_catalog_is_fictional_and_sized() -> None:
    """Committed catalog is synthetic, seeded, and about 800 rows."""
    catalog = load_catalog()
    items = items_of(catalog)
    assert catalog["generated"] == "fictional-only"
    assert catalog["seed"] == SEED
    assert len(items) == N_ITEMS
    unknown = sum(1 for item in items if item.get("place") is None)
    assert abs(unknown / len(items) - NO_GPS_FRACTION) < 0.08
    assert all("http" not in (item.get("filename") or "").lower() for item in items)
    # No real-looking personal names in filenames.
    banned = ("kiran", "keshava", "family", "iphone photos")
    blob = " ".join(item["filename"].lower() for item in items)
    assert all(word not in blob for word in banned)


def test_groups_have_one_keeper() -> None:
    """Every burst group nominates exactly one keeper."""
    groups = review_groups(items_of())
    assert groups
    for group in groups:
        keepers = [row for row in group["members"] if row.get("is_keeper")]
        assert len(keepers) == 1
        assert keepers[0]["id"] == group["keeper_id"]


def test_screenshots_not_from_maui_applies_safety() -> None:
    """Sample prompt emits place + screenshot chips and excludes unknown GPS."""
    chips = parse_prompt("screenshots not from Maui")
    kinds = {chip.kind: chip for chip in chips}
    assert "screenshot" in kinds
    assert "place" in kinds
    assert kinds["place"].negated is True
    assert kinds["place"].value == "Maui, Hawaii, US"
    assert unknown_location_safety_applies(chips) is True

    items = items_of()
    hits, safety = match_items(items, chips)
    assert safety is True
    assert hits
    for item in hits:
        assert item.get("is_screenshot") is True
        assert item.get("place")
        assert item["place"] != "Maui, Hawaii, US"

    unknown_shots = [item for item in items if item.get("is_screenshot") and not item.get("place")]
    assert unknown_shots
    hit_ids = {item["id"] for item in hits}
    assert all(item["id"] not in hit_ids for item in unknown_shots)


def test_library_map_search() -> None:
    """Search matches filename / label / place including the unknown bucket."""
    items = items_of()
    maui = search_library(items, "Maui")
    assert maui
    assert all("maui" in ((row.get("place") or "") + row["filename"]).lower() for row in maui)
    unknown = search_library(items, "unknown location")
    assert unknown
    labels = search_library(items, "beach")
    assert labels


def test_dashboard_reclaim_positive() -> None:
    """Dashboard math has a library and a reclaimable estimate."""
    summary = dashboard_summary(items_of())
    assert summary["library_count"] == N_ITEMS
    assert summary["reclaim_bytes"] > 0
    assert {card["code"] for card in summary["cards"]} == {"R1", "R2", "R3"}


@pytest.mark.parametrize("tab", ["Dashboard", "Review Groups", "Prompt Builder", "Library Map", "Places"])
def test_each_tab_renders(tab: str) -> None:
    """Every tab renders headlessly without exceptions."""
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(HERE / "app.py"), default_timeout=20)
    app.run()
    assert not app.exception
    names = ["Dashboard", "Review Groups", "Prompt Builder", "Library Map", "Places"]
    # Tab buttons are the first five widgets (indexed, not keyed, in AppTest 1.50).
    app.button[names.index(tab)].click().run()
    assert not app.exception
    banner = " ".join(str(el.value) for el in app.markdown)
    assert "fictional library" in banner.lower()
    if tab == "Prompt Builder":
        assert app.session_state.last_safety is True
        assert app.session_state.last_match_count >= 1
        chips = app.session_state.last_chips
        assert any(chip["kind"] == "place" and chip["negated"] for chip in chips)
        assert any(chip["kind"] == "screenshot" for chip in chips)
    if tab == "Review Groups":
        assert any("Review Groups" in str(el.value) for el in app.subheader)
    if tab == "Places":
        assert any("Places" in str(el.value) for el in app.subheader)
