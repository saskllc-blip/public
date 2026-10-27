"""Keepers public demo — Streamlit showcase over a fictional library.

Self-contained: no import of the private Keepers package, no network
image fetches, no deletes. Quarantine is session-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    import streamlit as st
except ImportError as exc:  # pragma: no cover - launch-time guard
    raise SystemExit("streamlit is required. Install with: pip install -r requirements.txt") from exc

from library import (
    bytes_to_gb,
    dashboard_summary,
    items_of,
    load_catalog,
    place_counts,
    review_groups,
    search_library,
    tile_path,
)
from prompt import chips_as_dicts, match_items, parse_prompt
from theme import BANNER, BRAND, TAB_STYLE, TABS, TAGLINE, css

st.set_page_config(page_title=BRAND, layout="wide", initial_sidebar_state="collapsed")


def _catalog_items() -> list[dict]:
    """Load the committed fictional catalog once per session."""
    if "library_items" not in st.session_state:
        st.session_state.catalog = load_catalog()
        # Do not store this as session_state.items — that name is a dict method.
        st.session_state.library_items = items_of(st.session_state.catalog)
        st.session_state.quarantine = []
        st.session_state.active_tab = TABS[0]
        st.session_state.prompt_text = "screenshots not from Maui"
        st.session_state.review_index = 0
        st.session_state.map_query = ""
    return st.session_state.library_items


def _render_header() -> None:
    """Title, tagline, and the persistent fictional-data banner."""
    st.markdown(css(), unsafe_allow_html=True)
    st.markdown(
        f'<div class="keepers-header"><h1>{BRAND}</h1>'
        f'<span class="keepers-tag">{TAGLINE}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="keepers-banner">{BANNER}</div>', unsafe_allow_html=True)


def _render_tabs() -> str:
    """Session-backed tab bar — only the active screen runs below."""
    active = st.session_state.get("active_tab", TABS[0])
    columns = st.columns(len(TABS))
    for index, name in enumerate(TABS):
        style = TAB_STYLE[name]
        label = f"{'▸ ' if name == active else ''}{name}"
        if columns[index].button(label, key=f"tab_{index}", use_container_width=True):
            st.session_state.active_tab = name
            st.rerun()
        columns[index].markdown(
            f"<div style='height:4px;border-radius:2px;background:{style['accent'] if name == active else '#E6DFD0'};'></div>",
            unsafe_allow_html=True,
        )
    return st.session_state.active_tab


def _tile(item: dict, keeper: bool = False) -> None:
    """Show a generated family tile plus a filename/place caption."""
    cap = f"{item['filename']} · {item.get('place') or 'Unknown location'}"
    st.image(str(tile_path(item)), caption=cap, use_container_width=True)
    if keeper:
        st.markdown('<span class="keepers-chip keeper">Keeper</span>', unsafe_allow_html=True)
    if item.get("is_favorite"):
        st.markdown('<span class="keepers-chip">Favorite · locked</span>', unsafe_allow_html=True)


def render_dashboard(items: list[dict]) -> None:
    """Library size, reclaimable GB, and counts by rule."""
    summary = dashboard_summary(items)
    st.subheader("Dashboard")
    st.caption("Estimated reclaim is staged only — this demo never deletes files.")
    cols = st.columns(4)
    cols[0].metric("Library size", f"{summary['library_count']:,} items")
    cols[1].metric("Library volume", f"{bytes_to_gb(summary['library_bytes'])} GB")
    cols[2].metric("Reclaimable (est.)", f"{bytes_to_gb(summary['reclaim_bytes'])} GB")
    cols[3].metric("Unknown location", f"{summary['unknown_location']:,}")

    st.markdown("#### Counts by rule")
    cards = st.columns(3)
    for card, column in zip(summary["cards"], cards):
        with column:
            st.markdown(f"**{card['code']} · {card['title']}**")
            st.metric("Matches", f"{card['count']:,}")
            st.caption(f"{bytes_to_gb(card['bytes'])} GB staged · {card['detail']}")
    st.caption(
        f"{summary['group_count']} burst/duplicate groups in this fictional library. "
        "Favorites are keeper-locked in every rule."
    )


def render_review(items: list[dict]) -> None:
    """Burst sets side-by-side with the Keeper badge and score chips."""
    groups = review_groups(items)
    if not groups:
        st.info("No burst groups in this catalog.")
        return
    index = int(st.session_state.get("review_index", 0)) % len(groups)
    group = groups[index]
    st.subheader("Review Groups")
    st.caption("Read-only review. Quarantine is simulated in this session only.")
    nav = st.columns([1, 2, 1, 1])
    if nav[0].button("← Previous group"):
        st.session_state.review_index = (index - 1) % len(groups)
        st.rerun()
    nav[1].markdown(
        f"**{group['group_id']}** · {len(group['members'])} shots · "
        f"{group['place']} · reclaim {bytes_to_gb(group['reclaim_bytes'])} GB"
    )
    if nav[2].button("Next group →"):
        st.session_state.review_index = (index + 1) % len(groups)
        st.rerun()
    if nav[3].button("Simulate quarantine"):
        staged = [row["id"] for row in group["members"] if not row.get("is_keeper") and not row.get("is_favorite")]
        existing = set(st.session_state.quarantine)
        st.session_state.quarantine = sorted(existing | set(staged))
        st.success(f"Staged {len(staged)} items in-session. Nothing was deleted.")

    members = group["members"][:7]
    tiles = st.columns(len(members))
    for member, column in zip(members, tiles):
        with column:
            is_keeper = member["id"] == group["keeper_id"]
            _tile(member, keeper=is_keeper)
            scores = member.get("quality") or {}
            st.markdown(
                f"sharp {scores.get('sharpness', 0):.2f} · "
                f"exp {scores.get('exposure', 0):.2f} · "
                f"faces {scores.get('faces', 0):.2f}"
            )
            if is_keeper:
                for reason in member.get("keeper_reasons") or []:
                    st.markdown(f'<span class="keepers-chip">{reason}</span>', unsafe_allow_html=True)
    if st.session_state.quarantine:
        st.caption(f"Session quarantine: {len(st.session_state.quarantine)} fictional items staged.")


def render_prompt(items: list[dict]) -> None:
    """Plain-English builder → chips, safety rule, match count, sample grid."""
    st.subheader("Prompt Builder")
    st.caption("Type a rule in plain English. Try the sample: screenshots not from Maui.")
    text = st.text_input("Rule", value=st.session_state.get("prompt_text", ""), key="prompt_box")
    st.session_state.prompt_text = text
    chips = parse_prompt(text)
    hits, safety = match_items(items, chips)

    st.markdown("**Interpretation chips**")
    if chips:
        chip_html = " ".join(f'<span class="keepers-chip">{chip.label()}</span>' for chip in chips)
        st.markdown(chip_html, unsafe_allow_html=True)
    else:
        st.info("No chips yet — enter a rule to see the interpretation.")

    if safety:
        st.markdown(
            '<span class="keepers-chip safety">Unknown-location safety applied</span>',
            unsafe_allow_html=True,
        )
        st.warning(
            "Unknown is not elsewhere. Items without GPS / place never match a "
            "negative place filter such as “not from Maui”, so they stay out of this result."
        )

    reclaim = sum(int(item["size_bytes"]) for item in hits if not item.get("is_favorite"))
    stats = st.columns(3)
    stats[0].metric("Matched", f"{len(hits):,}")
    stats[1].metric("Sample shown", f"{min(12, len(hits))}")
    stats[2].metric("Staged volume", f"{bytes_to_gb(reclaim)} GB")
    st.caption("LOCAL · FREE — this demo parses chips in-process. No photos leave the machine.")

    sample = hits[:12]
    if sample:
        rows = [sample[i : i + 4] for i in range(0, len(sample), 4)]
        for row in rows:
            cols = st.columns(4)
            for item, column in zip(row, cols):
                with column:
                    _tile(item)
    elif chips:
        st.info("No fictional items match these chips.")
    # Expose chip dicts for AppTest / debugging without leaking internals.
    st.session_state.last_chips = chips_as_dicts(chips)
    st.session_state.last_match_count = len(hits)
    st.session_state.last_safety = safety


def render_map(items: list[dict]) -> None:
    """Search box over filename, labels, and place."""
    st.subheader("Library Map")
    query = st.text_input(
        "Search filename, labels, or place",
        value=st.session_state.get("map_query", ""),
        key="map_box",
    )
    st.session_state.map_query = query
    hits = search_library(items, query)
    st.metric("Matches", f"{len(hits):,}")
    preview = hits[:20]
    st.dataframe(
        [
            {
                "id": item["id"],
                "filename": item["filename"],
                "place": item.get("place") or "Unknown location",
                "labels": ", ".join(item.get("labels") or []),
                "source": item["source"],
                "screenshot": item.get("is_screenshot"),
            }
            for item in preview
        ],
        use_container_width=True,
        hide_index=True,
    )
    if preview:
        cols = st.columns(min(5, len(preview)))
        for item, column in zip(preview[:5], cols):
            with column:
                _tile(item)


def render_places(items: list[dict]) -> None:
    """Counts by fictional place, including the Unknown location bucket."""
    st.subheader("Places")
    st.caption("About 40% of this fictional library has no GPS — that is the point of the safety rule.")
    rows = place_counts(items)
    st.dataframe(
        [
            {
                "place": name,
                "items": count,
                "volume_gb": bytes_to_gb(size),
            }
            for name, count, size in rows
        ],
        use_container_width=True,
        hide_index=True,
    )
    known = [row for row in rows if row[0] != "Unknown location"]
    if known:
        st.bar_chart({name: count for name, count, _ in known})
    unknown = next((row for row in rows if row[0] == "Unknown location"), None)
    if unknown:
        st.info(f"Unknown location bucket: {unknown[1]:,} items ({bytes_to_gb(unknown[2])} GB).")


def main() -> None:
    """Render the active Keepers demo tab."""
    items = _catalog_items()
    _render_header()
    active = _render_tabs()
    if active == "Dashboard":
        render_dashboard(items)
    elif active == "Review Groups":
        render_review(items)
    elif active == "Prompt Builder":
        render_prompt(items)
    elif active == "Library Map":
        render_map(items)
    else:
        render_places(items)
    st.markdown(
        '<footer class="keepers-foot">© 2026 SASK LLC — SW Services · Keepers demo · '
        "fictional library · no private-repo dependency</footer>",
        unsafe_allow_html=True,
    )


# Streamlit (`streamlit run app.py`) and AppTest.from_file both execute the
# script body. Pytest imports sibling modules, not this file.
main()
