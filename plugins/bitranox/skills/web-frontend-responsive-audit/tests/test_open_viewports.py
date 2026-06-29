"""Tests for open_viewports.main guard paths that return before any browser launch."""

import open_viewports as ov


def test_module_is_import_safe():
    # importing must not open a browser or run anything at module top level
    assert callable(ov.main)
    assert callable(ov.open_windows)


def test_unknown_profile_returns_2_without_launching():
    # no matching profile -> early return 2, never reaches Playwright
    assert ov.main(["http://example.com/", "--profiles", "Nokia 3310"]) == 2


def test_malformed_route_returns_2_without_launching():
    assert ov.main(["http://example.com/", "--route", "no-equals-sign"]) == 2


def test_delay_flag_is_accepted():
    # --delay must parse (and the unknown-profile guard still returns 2 before any browser)
    assert ov.main(["http://example.com/", "--profiles", "Nokia 3310", "--delay", "0.5"]) == 2


def test_open_windows_default_delay_is_staggered():
    import inspect
    assert inspect.signature(ov.open_windows).parameters["delay"].default == 1.0
