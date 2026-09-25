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


def test_landscape_of_a_landscape_profile_is_unchanged():
    land = dp.profile_by_name("iPad mini (landscape)")
    again = dp.landscape_of(land)
    assert (again["width"], again["height"]) == (1024, 768)
    assert again == land


def test_resolve_profiles_reports_every_unknown_name():
    profiles, unknown = dp.resolve_profiles(["iPhone SE (landscape)", "iPhone SE", "Pixel 7 (landscpae)"])
    assert [p["name"] for p in profiles] == ["iPhone SE (landscape)"]
    assert unknown == ["iPhone SE", "Pixel 7 (landscpae)"]


def test_resolve_profiles_all_known():
    profiles, unknown = dp.resolve_profiles(["Laptop 1440", "iPad mini (portrait)"])
    assert [p["name"] for p in profiles] == ["Laptop 1440", "iPad mini (portrait)"]
    assert unknown == []


def test_unknown_profiles_message_names_them_and_the_valid_choices():
    msg = dp.unknown_profiles_message(["iPhone SE", "Nokia 3310"])
    assert "'iPhone SE'" in msg and "'Nokia 3310'" in msg
    assert "iPhone SE (portrait)" in msg  # the valid names are listed


def test_docstring_matches_which_kinds_get_the_vertical_fit_check():
    # the module doc must not claim tablets are checked for vertical fit: analysis checks phones only
    import analysis
    assert analysis.vertical_fit_finding(3000, 1024, "tablet", "portrait") is None
    assert analysis.vertical_fit_finding(3000, 667, "phone", "portrait") is not None
    doc = " ".join(dp.__doc__.replace("`", "").split())
    assert "phone is checked for vertical fit" in doc
    assert "are checked for vertical fit" not in doc
