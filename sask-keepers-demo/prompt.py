"""Demo-local prompt chips and the unknown-location safety rule.

Reimplements the public Prompt Builder contract enough to demonstrate
"screenshots not from Maui" — it does not import the private Keepers
parser or any LLM.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

# Canonical fictional places the builder can resolve from short tokens.
PLACE_ALIASES = {
    "maui": "Maui, Hawaii, US",
    "hawaii": "Maui, Hawaii, US",
    "kyoto": "Kyoto, Japan",
    "japan": "Kyoto, Japan",
    "swiss": "Swiss Alps",
    "alps": "Swiss Alps",
    "lisbon": "Lisbon, Portugal",
    "portugal": "Lisbon, Portugal",
    "banff": "Banff, Canada",
    "canada": "Banff, Canada",
    "reykjavik": "Reykjavik, Iceland",
    "iceland": "Reykjavik, Iceland",
    "santorini": "Santorini, Greece",
    "greece": "Santorini, Greece",
    "queenstown": "Queenstown, New Zealand",
    "new zealand": "Queenstown, New Zealand",
    "marrakech": "Marrakech, Morocco",
    "morocco": "Marrakech, Morocco",
    "patagonia": "Patagonia, Argentina",
    "argentina": "Patagonia, Argentina",
}

LABEL_WORDS = (
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
)


@dataclass(frozen=True)
class Chip:
    """One interpretation chip shown in the Prompt Builder."""

    kind: str
    op: str
    value: Any
    negated: bool = False

    def label(self) -> str:
        """Short chip text for the UI."""
        prefix = "not " if self.negated else ""
        if self.kind == "screenshot":
            return f"{prefix}screenshot"
        if self.kind == "favorite":
            return f"{prefix}favorite"
        if self.kind == "people":
            return f"{prefix}people"
        if self.kind == "source":
            return f"{prefix}source:{self.value}"
        if self.kind == "place":
            return f"{prefix}place:{self.value}"
        if self.kind == "label":
            return f"{prefix}label:{self.value}"
        return f"{prefix}{self.kind}:{self.value}"


def parse_prompt(text: str) -> list[Chip]:
    """Keyword parse a plain-English demo prompt into chips."""
    raw = (text or "").strip()
    lowered = raw.lower()
    chips: list[Chip] = []
    if not lowered:
        return chips

    if "screenshot" in lowered:
        chips.append(Chip("screenshot", "eq", True, negated=False))

    if re.search(r"\bfavorites?\b", lowered):
        # "except favorites" / "not favorites" → keep favorites out of the match.
        negated = bool(re.search(r"\b(except|not|without)\s+favorites?\b", lowered))
        chips.append(Chip("favorite", "eq", True, negated=negated))

    people_neg = bool(re.search(r"\b(no|without|not)\s+people\b", lowered))
    if people_neg:
        chips.append(Chip("people", "eq", True, negated=True))
    elif re.search(r"\bpeople\b", lowered):
        chips.append(Chip("people", "eq", True, negated=False))

    for source in ("phone", "camera", "screenshots"):
        if re.search(rf"\b{source}\b", lowered) and source != "screenshots":
            chips.append(Chip("source", "eq", source.title(), negated=False))

    for label in LABEL_WORDS:
        if label == "people":
            continue
        if re.search(rf"\b{re.escape(label)}\b", lowered):
            chips.append(Chip("label", "eq", label, negated=False))

    # "not from Maui" / "not in Kyoto" / "outside home" style place filters.
    place_neg = re.search(
        r"\b(?:not from|not in|outside)\s+([a-z][a-z ]+?)\s*$",
        lowered,
    )
    place_pos = re.search(r"\b(?:from|in|at)\s+([a-z][a-z ]+?)\s*$", lowered)
    token = None
    negated = False
    if place_neg:
        token = place_neg.group(1).strip()
        negated = True
    elif place_pos and "screenshot" in lowered:
        # "screenshots from Maui"
        token = place_pos.group(1).strip()
    elif place_pos and not any(chip.kind == "place" for chip in chips):
        token = place_pos.group(1).strip()

    if token:
        place = _resolve_place(token)
        if place:
            chips.append(Chip("place", "eq", place, negated=negated))

    return chips


def _resolve_place(token: str) -> str | None:
    """Map a typed token onto the fictional travel set."""
    key = token.strip().lower().rstrip(".")
    if key in PLACE_ALIASES:
        return PLACE_ALIASES[key]
    for alias, canonical in PLACE_ALIASES.items():
        if alias in key or key in alias:
            return canonical
    return None


def unknown_location_safety_applies(chips: list[Chip]) -> bool:
    """True when a negative place chip is present — unknown is not elsewhere."""
    return any(chip.kind == "place" and chip.negated for chip in chips)


def match_items(items: list[dict[str, Any]], chips: list[Chip]) -> tuple[list[dict[str, Any]], bool]:
    """Apply chips, enforcing the unknown-location safety rule.

    An item with no place NEVER matches a negative place filter.
    """
    safety = unknown_location_safety_applies(chips)
    if not chips:
        return list(items), safety

    hits = []
    for item in items:
        if _matches(item, chips, safety):
            hits.append(item)
    return hits, safety


def _matches(item: dict[str, Any], chips: list[Chip], safety: bool) -> bool:
    """AND-match every chip against one catalog row."""
    for chip in chips:
        if chip.kind == "screenshot":
            if bool(item.get("is_screenshot")) != (not chip.negated):
                return False
        elif chip.kind == "favorite":
            is_fav = bool(item.get("is_favorite"))
            if chip.negated and is_fav:
                return False
            if not chip.negated and not is_fav:
                return False
        elif chip.kind == "people":
            has = bool(item.get("has_people"))
            if chip.negated and has:
                return False
            if not chip.negated and not has:
                return False
        elif chip.kind == "source":
            if (item.get("source") == chip.value) == chip.negated:
                return False
        elif chip.kind == "label":
            labels = item.get("labels") or []
            if (chip.value in labels) == chip.negated:
                return False
        elif chip.kind == "place":
            place = item.get("place")
            if chip.negated:
                if safety and not place:
                    return False
                if place == chip.value:
                    return False
            else:
                if place != chip.value:
                    return False
    return True


def chips_as_dicts(chips: list[Chip]) -> list[dict[str, Any]]:
    """JSON-friendly chip list for tests and the UI."""
    return [asdict(chip) for chip in chips]
