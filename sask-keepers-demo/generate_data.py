"""Deterministic fictional photo-library generator for the Keepers demo.

Hard rule: 100% synthetic data. No real photos, names, or library rows.
Re-run with the same seed to recreate data/library.json and the small
label-family tiles in assets/tiles/.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "library.json"
TILE_DIR = HERE / "assets" / "tiles"

SEED = 20261026
N_ITEMS = 800
NO_GPS_FRACTION = 0.40

# Fictional travel set — none of these rows come from a real library.
PLACES = [
    "Maui, Hawaii, US",
    "Kyoto, Japan",
    "Swiss Alps",
    "Lisbon, Portugal",
    "Banff, Canada",
    "Reykjavik, Iceland",
    "Santorini, Greece",
    "Queenstown, New Zealand",
    "Marrakech, Morocco",
    "Patagonia, Argentina",
]

LABELS = [
    "beach",
    "mountains",
    "food",
    "people",
    "documents",
    "city",
    "wildlife",
    "sunset",
    "architecture",
    "water",
]

SOURCES = ("Phone", "Camera", "Screenshots")

# Gradient pairs per label family — generated tiles, never stock photos.
TILE_COLORS = {
    "beach": ((56, 168, 201), (244, 214, 140)),
    "mountains": ((74, 96, 112), (196, 206, 196)),
    "food": ((168, 74, 58), (232, 186, 112)),
    "people": ((92, 78, 120), (214, 186, 176)),
    "documents": ((90, 98, 108), (226, 226, 220)),
    "city": ((58, 72, 92), (168, 176, 188)),
    "wildlife": ((62, 96, 58), (176, 196, 112)),
    "sunset": ((184, 86, 52), (246, 198, 112)),
    "architecture": ((88, 84, 78), (206, 196, 178)),
    "water": ((36, 92, 132), (132, 196, 210)),
    "unknown": ((110, 110, 118), (188, 188, 194)),
}


def _quality() -> dict[str, float]:
    """Return a 0–1 score breakdown; keeper nomination uses the mean."""
    sharpness = round(random.uniform(0.42, 0.98), 3)
    exposure = round(random.uniform(0.40, 0.97), 3)
    faces = round(random.uniform(0.35, 0.96), 3)
    resolution = round(random.uniform(0.50, 0.99), 3)
    overall = round((sharpness * 0.35 + exposure * 0.25 + faces * 0.20 + resolution * 0.20), 3)
    return {
        "sharpness": sharpness,
        "exposure": exposure,
        "faces": faces,
        "resolution": resolution,
        "overall": overall,
    }


def _keeper_reasons(scores: dict[str, float]) -> list[str]:
    """Human-readable chips for the nominated keeper — never a naked percent."""
    ranked = sorted(
        (
            ("Sharpest", scores["sharpness"]),
            ("Best exposure", scores["exposure"]),
            ("Eyes open", scores["faces"]),
            ("Highest resolution", scores["resolution"]),
        ),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return [name for name, _ in ranked[:2]]


def _filename(index: int, source: str, is_screenshot: bool, place: str | None, label: str) -> str:
    """Invent a camera-like filename. No real people or original paths."""
    if is_screenshot or source == "Screenshots":
        day = 1 + (index % 28)
        month = 1 + (index % 12)
        hour = 8 + (index % 12)
        minute = (index * 7) % 60
        second = (index * 13) % 60
        return f"Screen Shot 2024-{month:02d}-{day:02d} at {hour:02d}.{minute:02d}.{second:02d}.png"
    if source == "Camera":
        return f"DSCF{1000 + index:04d}.JPG"
    slug = (place or "unknown").split(",")[0].replace(" ", "")
    return f"IMG_{1400 + index:04d}_{slug}_{label}.JPG"


def _size_bytes(source: str, is_screenshot: bool) -> int:
    """Plausible fictional file sizes so reclaimable-GB math is visible."""
    if is_screenshot or source == "Screenshots":
        return random.randint(180_000, 2_200_000)
    if source == "Camera":
        return random.randint(4_200_000, 9_800_000)
    return random.randint(1_400_000, 6_400_000)


def _timestamp(index: int) -> str:
    """Spread items across a two-year fictional window."""
    start = datetime(2023, 3, 1, 8, 0, 0)
    stamp = start + timedelta(hours=index * 5 + (index % 11), minutes=(index * 3) % 60)
    return stamp.isoformat(timespec="seconds")


def _draw_tile(label: str, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    """Write a small gradient/pattern tile — no photographic content."""
    TILE_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 320, 220
    image = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        mix = y / max(height - 1, 1)
        color = tuple(int(top[i] * (1 - mix) + bottom[i] * mix) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    # Geometric pattern so tiles feel distinct per family without using photos.
    step = 28 if label in {"documents", "architecture", "city"} else 36
    overlay = tuple(min(255, c + 28) for c in bottom)
    for x in range(-height, width, step):
        draw.line([(x, 0), (x + height, height)], fill=overlay, width=1)
    band = (0, height - 36, width, height)
    draw.rectangle(band, fill=(20, 24, 30))
    draw.text((12, height - 26), label.upper(), fill=(244, 236, 214))
    image.save(TILE_DIR / f"{label}.png", "PNG")


def generate_tiles() -> None:
    """Build one PIL tile per label family (the lighter-than-800-photos route)."""
    for label, colors in TILE_COLORS.items():
        _draw_tile(label, colors[0], colors[1])


def generate_library() -> list[dict]:
    """Return ~800 fictional items with groups, GPS gaps, and rule flags."""
    rng_state = random.Random(SEED)
    random.seed(SEED)

    items: list[dict] = []
    n_groups = 48
    group_sizes = [rng_state.randint(3, 6) for _ in range(n_groups)]
    grouped_count = sum(group_sizes)
    assert grouped_count < N_ITEMS

    def _base_item(index: int, source_bias: str | None = None) -> dict:
        roll = rng_state.random()
        if source_bias:
            source = source_bias
        elif roll < 0.16:
            source = "Screenshots"
        elif roll < 0.48:
            source = "Camera"
        else:
            source = "Phone"
        is_screenshot = source == "Screenshots" or rng_state.random() < 0.03
        if is_screenshot:
            source = "Screenshots"
        unknown = rng_state.random() < NO_GPS_FRACTION
        place = None if unknown else PLACES[index % len(PLACES)]
        primary = LABELS[index % len(LABELS)]
        extra = []
        has_people = rng_state.random() < (0.62 if primary == "people" else 0.38)
        if has_people and primary != "people":
            extra.append("people")
        if primary != "sunset" and rng_state.random() < 0.12:
            extra.append("sunset")
        labels = [primary, *extra]
        scores = _quality()
        return {
            "id": f"demo-{index:04d}",
            "filename": _filename(index, source, is_screenshot, place, primary),
            "timestamp": _timestamp(index),
            "size_bytes": _size_bytes(source, is_screenshot),
            "source": source,
            "place": place,
            "is_screenshot": is_screenshot,
            "is_favorite": rng_state.random() < 0.08,
            "labels": labels,
            "has_people": has_people,
            "group_id": None,
            "quality": scores,
            "quality_score": scores["overall"],
            "is_keeper": False,
            "keeper_reasons": [],
        }

    index = 0
    for group_n, size in enumerate(group_sizes, start=1):
        group_id = f"burst-{group_n:02d}"
        # Keep a group in one fictional place so Review reads as a burst.
        forced_place = None if rng_state.random() < 0.22 else PLACES[group_n % len(PLACES)]
        members = []
        for _ in range(size):
            item = _base_item(index, source_bias="Phone" if rng_state.random() < 0.7 else "Camera")
            item["group_id"] = group_id
            item["place"] = forced_place
            item["is_screenshot"] = False
            if item["source"] == "Screenshots":
                item["source"] = "Phone"
            primary = (item.get("labels") or ["photo"])[0]
            item["filename"] = _filename(index, item["source"], False, forced_place, primary)
            members.append(item)
            index += 1
        keeper = max(members, key=lambda row: row["quality_score"])
        keeper["is_keeper"] = True
        keeper["keeper_reasons"] = _keeper_reasons(keeper["quality"])
        items.extend(members)

    while index < N_ITEMS:
        items.append(_base_item(index))
        index += 1

    # Guarantee the Prompt Builder sample "screenshots not from Maui" has hits.
    maui = "Maui, Hawaii, US"
    extras = [
        (True, maui, "documents"),
        (True, "Kyoto, Japan", "documents"),
        (True, "Lisbon, Portugal", "city"),
        (True, None, "documents"),
        (True, None, "city"),
        (False, maui, "beach"),
    ]
    for offset, (shot, place, label) in enumerate(extras):
        row = items[-(offset + 1)]
        row["is_screenshot"] = shot
        row["source"] = "Screenshots" if shot else "Phone"
        row["place"] = place
        row["labels"] = [label]
        row["group_id"] = None
        row["is_keeper"] = False
        row["filename"] = _filename(9000 + offset, row["source"], shot, place, label)

    items.sort(key=lambda row: row["id"])
    return items


def write_library(items: list[dict]) -> None:
    """Persist the generated catalog the app loads at runtime."""
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": SEED,
        "generated": "fictional-only",
        "item_count": len(items),
        "places": PLACES,
        "items": items,
    }
    DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Generate tiles + library.json and print a one-line summary."""
    generate_tiles()
    items = generate_library()
    write_library(items)
    unknown = sum(1 for item in items if item["place"] is None)
    groups = {item["group_id"] for item in items if item["group_id"]}
    print(
        f"wrote {len(items)} items, {len(groups)} groups, "
        f"{unknown} unknown-location ({unknown / len(items):.0%}) → {DATA_PATH}"
    )


if __name__ == "__main__":
    main()
