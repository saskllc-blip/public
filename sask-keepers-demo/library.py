"""Load and query the committed fictional Keepers demo library.

Runtime is self-contained: this module never imports the private Keepers
package and never reads a real photo library.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "library.json"
TILE_DIR = HERE / "assets" / "tiles"

BYTES_PER_GB = 1024**3


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    """Load the generated JSON catalog."""
    payload = json.loads((path or DATA_PATH).read_text(encoding="utf-8"))
    if payload.get("generated") != "fictional-only":
        raise ValueError("demo catalog must be marked fictional-only")
    return payload


def items_of(catalog: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return the item list from a catalog (or the on-disk default)."""
    return list((catalog or load_catalog())["items"])


def bytes_to_gb(size_bytes: int) -> float:
    """Convert bytes to GB for dashboard metrics."""
    return round(size_bytes / BYTES_PER_GB, 3)


def tile_path(item: dict[str, Any]) -> Path:
    """Map an item to its label-family tile (CSS caption is applied in-app)."""
    label = (item.get("labels") or ["unknown"])[0]
    candidate = TILE_DIR / f"{label}.png"
    fallback = TILE_DIR / "unknown.png"
    return candidate if candidate.exists() else fallback


def search_library(items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Library Map: case-insensitive match on filename, labels, and place."""
    needle = query.strip().lower()
    if not needle:
        return list(items)
    hits = []
    for item in items:
        hay = " ".join(
            [
                item.get("filename") or "",
                item.get("place") or "unknown location",
                " ".join(item.get("labels") or []),
                item.get("source") or "",
                item.get("id") or "",
            ]
        ).lower()
        if needle in hay:
            hits.append(item)
    return hits


def place_counts(items: list[dict[str, Any]]) -> list[tuple[str, int, int]]:
    """Return (place, count, bytes) including the Unknown location bucket."""
    buckets: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for item in items:
        key = item.get("place") or "Unknown location"
        buckets[key][0] += 1
        buckets[key][1] += int(item.get("size_bytes") or 0)
    rows = [(name, counts[0], counts[1]) for name, counts in buckets.items()]
    rows.sort(key=lambda row: (row[0] == "Unknown location", -row[1], row[0]))
    return rows


def review_groups(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Burst/duplicate groups with the nominated keeper called out."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        if item.get("group_id"):
            grouped[str(item["group_id"])].append(item)
    groups = []
    for group_id, members in grouped.items():
        ordered = sorted(members, key=lambda row: row.get("quality_score") or 0, reverse=True)
        keeper = next((row for row in ordered if row.get("is_keeper")), ordered[0])
        reclaim = sum(int(row["size_bytes"]) for row in ordered if not row.get("is_keeper") and not row.get("is_favorite"))
        groups.append(
            {
                "group_id": group_id,
                "members": ordered,
                "keeper_id": keeper["id"],
                "place": keeper.get("place") or "Unknown location",
                "reclaim_bytes": reclaim,
            }
        )
    groups.sort(key=lambda row: row["group_id"])
    return groups


def rule_matches(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Public product rules, reimplemented locally for the demo.

    R1 — non-keeper burst/duplicate members (favorites stay locked).
    R2 — screenshots except favorites.
    R3 — no-people / scenery except favorites.
    """
    r1 = [
        item
        for item in items
        if item.get("group_id") and not item.get("is_keeper") and not item.get("is_favorite")
    ]
    r2 = [item for item in items if item.get("is_screenshot") and not item.get("is_favorite")]
    r3 = [
        item
        for item in items
        if not item.get("has_people") and not item.get("is_favorite") and "documents" not in (item.get("labels") or [])
    ]
    return {"R1": r1, "R2": r2, "R3": r3}


def dashboard_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Library size, reclaimable estimate, and per-rule counts."""
    rules = rule_matches(items)
    reclaim_ids = {item["id"] for bucket in rules.values() for item in bucket}
    reclaim_bytes = sum(int(item["size_bytes"]) for item in items if item["id"] in reclaim_ids)
    cards = []
    for code, title, detail in (
        ("R1", "Collapse bursts / duplicates", "Keep the nominated keeper; stage the rest"),
        ("R2", "Screenshots except favorites", "Favorites stay keeper-locked"),
        ("R3", "No-people / scenery", "Quarantine-only — scenery can be intentional"),
    ):
        bucket = rules[code]
        cards.append(
            {
                "code": code,
                "title": title,
                "detail": detail,
                "count": len(bucket),
                "bytes": sum(int(item["size_bytes"]) for item in bucket),
            }
        )
    return {
        "library_count": len(items),
        "library_bytes": sum(int(item["size_bytes"]) for item in items),
        "reclaim_count": len(reclaim_ids),
        "reclaim_bytes": reclaim_bytes,
        "unknown_location": sum(1 for item in items if not item.get("place")),
        "group_count": len({item["group_id"] for item in items if item.get("group_id")}),
        "cards": cards,
    }
