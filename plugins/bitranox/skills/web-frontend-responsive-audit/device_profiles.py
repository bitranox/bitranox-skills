"""The device matrix the audit sweeps - pure data + small helpers, no browser.

A deliberately small but representative set: the smallest common phone, a modern phone,
a large phone, a small and a large tablet, and a laptop. Each is swept in both
orientations where it makes sense (phones/tablets), so the audit catches the landscape
defects that portrait-only testing misses. Widths/heights are CSS px (the layout viewport),
``dpr`` is the device pixel ratio used to emulate retina rendering.

Kinds drive severity (see analysis.py): ``phone`` and ``tablet`` get SEVERE for horizontal
overflow and are checked for vertical fit; ``desktop`` is checked for over-sparse layouts.
"""

from __future__ import annotations

# name, css width, css height (portrait), device pixel ratio, kind, touch
_BASE = [
    ("iPhone SE", 375, 667, 2.0, "phone", True),
    ("iPhone 14 Pro", 393, 852, 3.0, "phone", True),
    ("Pixel 7", 412, 915, 2.625, "phone", True),
    ("iPad mini", 768, 1024, 2.0, "tablet", True),
    ("iPad Pro 11", 834, 1194, 2.0, "tablet", True),
    ("Laptop 1440", 1440, 900, 1.0, "desktop", False),
]


def _profile(name: str, width: int, height: int, dpr: float, kind: str, touch: bool, orientation: str) -> dict:
    return {
        "name": f"{name} ({orientation})" if kind != "desktop" else name,
        "base_name": name,
        "width": width,
        "height": height,
        "dpr": dpr,
        "kind": kind,
        "has_touch": touch,
        "is_mobile": kind in ("phone", "tablet"),
        "orientation": orientation,
    }


def landscape_of(profile: dict) -> dict:
    """Return the landscape twin of a portrait profile (width/height swapped)."""
    return _profile(
        profile["base_name"],
        profile["height"],
        profile["width"],
        profile["dpr"],
        profile["kind"],
        profile["has_touch"],
        "landscape",
    )


def default_profiles(*, include_landscape: bool = True) -> list[dict]:
    """The full sweep: every base profile portrait, plus landscape for phones/tablets.

    Desktop has no landscape twin (a laptop is already landscape). When
    ``include_landscape`` is False, only portrait/native orientations are returned.
    """
    out: list[dict] = []
    for name, w, h, dpr, kind, touch in _BASE:
        orientation = "landscape" if kind == "desktop" else "portrait"
        out.append(_profile(name, w, h, dpr, kind, touch, orientation))
        if include_landscape and kind in ("phone", "tablet"):
            out.append(landscape_of(out[-1]))
    return out


def profile_by_name(name: str) -> dict | None:
    """Look up a single profile by its display name (portrait or landscape)."""
    for p in default_profiles(include_landscape=True):
        if p["name"] == name:
            return p
    return None
