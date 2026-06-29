"""Behaviour tests for the device matrix (pure data + helpers)."""

import device_profiles as dp


def test_default_matrix_has_both_orientations_for_phones_and_tablets():
    profiles = dp.default_profiles(include_landscape=True)
    names = [p["name"] for p in profiles]
    assert "iPhone SE (portrait)" in names
    assert "iPhone SE (landscape)" in names
    # desktop has no landscape twin
    assert "Laptop 1440" in names
    assert not any(n.startswith("Laptop") and "landscape" in n for n in names)


def test_no_landscape_flag_drops_landscape_twins():
    portrait_only = dp.default_profiles(include_landscape=False)
    assert all(p["orientation"] != "landscape" or p["kind"] == "desktop" for p in portrait_only)
    assert len(portrait_only) < len(dp.default_profiles(include_landscape=True))


def test_landscape_of_swaps_dimensions_and_marks_orientation():
    se = dp.profile_by_name("iPhone SE (portrait)")
    land = dp.landscape_of(se)
    assert land["width"] == se["height"]
    assert land["height"] == se["width"]
    assert land["orientation"] == "landscape"
    assert land["kind"] == se["kind"]


def test_kinds_and_touch_flags_are_consistent():
    for p in dp.default_profiles():
        assert p["kind"] in ("phone", "tablet", "desktop")
        assert p["is_mobile"] == (p["kind"] in ("phone", "tablet"))
        if p["kind"] == "desktop":
            assert p["has_touch"] is False


def test_profile_by_name_returns_none_for_unknown():
    assert dp.profile_by_name("Nokia 3310") is None
    assert dp.profile_by_name("iPad mini (landscape)") is not None
