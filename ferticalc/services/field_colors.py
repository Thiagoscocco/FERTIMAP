"""Shared color palette helpers for field-based notebook pages."""

from __future__ import annotations


CULTURE_COLORS = {
    "soja": "#f7d154",
    "milho": "#6ec174",
    "trigo": "#f79a3b",
    "azevem": "#e2b13c",
    "aveia": "#cfc6a0",
}

DEFAULT_CULTURE_COLOR = "#d2d2d2"


def color_for_culture(name: str | None) -> str:
    """Return a stable color for the provided culture name."""

    if not name:
        return DEFAULT_CULTURE_COLOR
    return CULTURE_COLORS.get(name.strip().lower(), DEFAULT_CULTURE_COLOR)
