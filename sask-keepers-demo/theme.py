"""Keepers-demo theme tokens: per-tab accents and injected CSS.

Mirrors the public Keepers tab approach (distinct type + accent per tab,
active weight + underline so color is never the only signal) without
importing the private theme module.
"""
from __future__ import annotations

TABS = (
    "Dashboard",
    "Review Groups",
    "Prompt Builder",
    "Library Map",
    "Places",
)

# Tasteful, not rainbow — navy/gold studio palette plus muted companions.
TAB_STYLE = {
    "Dashboard": {
        "accent": "#B8912A",
        "font": '"Iowan Old Style", Palatino, "Palatino Linotype", serif',
        "tracking": "0.01em",
    },
    "Review Groups": {
        "accent": "#3D5A6C",
        "font": '"Avenir Next", "Segoe UI", sans-serif',
        "tracking": "0.02em",
    },
    "Prompt Builder": {
        "accent": "#6B5344",
        "font": "Georgia, 'Times New Roman', serif",
        "tracking": "0.03em",
    },
    "Library Map": {
        "accent": "#3F5D4A",
        "font": '"IBM Plex Sans", "Helvetica Neue", Helvetica, sans-serif',
        "tracking": "0.04em",
    },
    "Places": {
        "accent": "#7A4E3A",
        "font": '"Trebuchet MS", Verdana, sans-serif',
        "tracking": "0.06em",
    },
}

BANNER = "Demo — fictional library, no real photos."
BRAND = "Keepers by SASK"
TAGLINE = "Keep the keepers. Lose the rest."


def css() -> str:
    """Return the stylesheet injected once per page render."""
    tab_rules = []
    for index, name in enumerate(TABS):
        style = TAB_STYLE[name]
        tab_rules.append(
            f"""
        div[data-testid="stHorizontalBlock"] button[kind="secondary"]:nth-of-type({index + 1}),
        .keepers-tabs button[data-tab="{index}"] {{
            font-family: {style["font"]};
            letter-spacing: {style["tracking"]};
            color: {style["accent"]};
            border-bottom: 2px solid transparent;
        }}
        .keepers-tabs button[data-tab="{index}"].active {{
            font-weight: 700;
            border-bottom-color: {style["accent"]};
            background: color-mix(in srgb, {style["accent"]} 12%, #fff);
        }}
        """
        )
    return f"""
    <style>
    [data-testid="stSidebar"] {{ display: none; }}
    .block-container {{ padding-top: 1.2rem; max-width: 1200px; }}
    .keepers-banner {{
        background: #FFF6D8;
        border: 1px solid #E2C56A;
        color: #3D3208;
        padding: 0.65rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        margin: 0.4rem 0 1rem 0;
    }}
    .keepers-header {{
        display: flex; justify-content: space-between; align-items: baseline;
        border-bottom: 1px solid #E6DFD0; padding-bottom: 0.4rem;
    }}
    .keepers-header h1 {{
        font-family: Georgia, serif; color: #0E1B2C; margin: 0;
        font-size: 1.85rem;
    }}
    .keepers-tag {{ color: #5C5346; font-style: italic; }}
    .keepers-tabs {{
        display: flex; gap: 0.4rem; flex-wrap: wrap;
        margin: 0.8rem 0 1.1rem 0;
        border-bottom: 1px solid #E6DFD0;
        padding-bottom: 0.15rem;
    }}
    .keepers-tabs button {{
        background: #F7F3EA; border: 0; border-radius: 8px 8px 0 0;
        padding: 0.55rem 0.9rem; cursor: pointer; font-size: 0.95rem;
    }}
    .keepers-tabs button:hover {{ filter: brightness(0.97); }}
    {''.join(tab_rules)}
    .keepers-card {{
        background: #FFFFFF; border: 1px solid #E6DFD0; border-radius: 12px;
        padding: 1rem 1.1rem; height: 100%;
    }}
    .keepers-card h3 {{ margin-top: 0; color: #0E1B2C; }}
    .keepers-chip {{
        display: inline-block; background: #F7F3EA; border: 1px solid #D9CFAE;
        border-radius: 999px; padding: 0.15rem 0.65rem; margin: 0.15rem;
        font-size: 0.85rem; color: #3D3208;
    }}
    .keepers-chip.safety {{
        background: #F4E7D4; border-color: #C48A4A; color: #5A3A12;
        font-weight: 600;
    }}
    .keepers-chip.keeper {{
        background: #B8912A; color: #fff; border-color: #8F7018; font-weight: 700;
    }}
    .tile {{
        border-radius: 10px; overflow: hidden; border: 1px solid #E6DFD0;
        background: #F7F3EA; margin-bottom: 0.6rem;
    }}
    .tile.keeper {{ outline: 3px solid #B8912A; }}
    .tile-cap {{
        font-size: 0.78rem; color: #3D3208; padding: 0.35rem 0.5rem 0.5rem;
    }}
    .metric-sub {{ color: #5C5346; font-size: 0.85rem; }}
    footer.keepers-foot {{
        margin-top: 2rem; color: #7A7366; font-size: 0.8rem;
        border-top: 1px solid #E6DFD0; padding-top: 0.6rem;
    }}
    </style>
    """
