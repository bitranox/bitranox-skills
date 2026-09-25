"""Tests for open_viewports: the guard paths, and open_windows/main with a scripted browser."""

import inspect

import open_viewports as ov
from responsive_fake_browser import MISSING_EXECUTABLE, MISSING_HOST_DEPS, Script, fake_launcher

URL = "http://127.0.0.1:9/"  # never contacted: the fake browser answers


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
    assert inspect.signature(ov.open_windows).parameters["delay"].default == 1.0


def test_unknown_profile_is_refused_even_when_another_matches(capsys):
    launch = fake_launcher()
    rc = ov.main([URL, "--profiles", "Laptop 1440", "iPad mini"], launch=launch)
    assert rc == 2
    assert "'iPad mini'" in capsys.readouterr().err
    assert launch.browser.contexts_made == []


def test_returns_once_the_human_closes_every_window(capsys):
    launch = fake_launcher()
    rc = ov.main([URL, "--profiles", "Laptop 1440", "iPad mini (portrait)", "--delay", "0"], launch=launch)
    assert rc == 0
    pages = launch.browser.pages
    assert len(pages) == 2
    assert all(p.close_waits == 1 for p in pages)  # waited on each window's own close event
    assert "Opened 2 interactive windows" in capsys.readouterr().out


def test_window_titles_name_the_profile():
    launch = fake_launcher()
    ov.open_windows(URL, [_laptop()], delay=0, launch=launch)
    assert launch.browser.pages[0].title == "Laptop 1440  1440x900"


def test_failed_loads_are_counted_separately_and_exit_1_when_none_loaded(capsys):
    script = Script(goto_error=RuntimeError("Page.goto: net::ERR_CONNECTION_REFUSED"))
    launch = fake_launcher(script)
    rc = ov.main([URL, "--profiles", "Laptop 1440", "iPad mini (portrait)", "--delay", "0"], launch=launch)
    out = capsys.readouterr()
    assert rc == 1
    assert "ERR_CONNECTION_REFUSED" in out.err
    assert "Opened 0 interactive windows (2 failed to load)" in out.out


def test_open_windows_reports_loaded_and_failed():
    launch = fake_launcher()
    assert ov.open_windows(URL, [_laptop()], delay=0, launch=launch) == (1, 0)


def test_a_browser_that_is_gone_ends_the_wait():
    # the user quit the browser: waiting on a page raises instead of returning
    launch = fake_launcher()
    original = launch.browser.new_context

    def new_context(**options):
        ctx = original(**options)
        make_page = ctx.new_page

        def new_page():
            page = make_page()

            def wait_for_event(event, timeout=None):
                raise RuntimeError("Target page, context or browser has been closed")

            page.wait_for_event = wait_for_event
            return page

        ctx.new_page = new_page
        return ctx

    launch.browser.new_context = new_context
    assert ov.open_windows(URL, [_laptop()], delay=0, launch=launch) == (1, 0)


def test_missing_browser_exits_3(capsys):
    rc = ov.main([URL, "--profiles", "Laptop 1440"], launch=fake_launcher(error=RuntimeError(MISSING_EXECUTABLE)))
    assert rc == 3
    assert "playwright install chromium" in capsys.readouterr().err


def test_missing_host_libraries_exit_3_naming_install_deps(capsys):
    rc = ov.main([URL, "--profiles", "Laptop 1440"], launch=fake_launcher(error=RuntimeError(MISSING_HOST_DEPS)))
    err = capsys.readouterr().err
    assert rc == 3
    assert "install-deps" in err and "Chromium not installed" not in err


def test_unrelated_launch_failure_exits_1(capsys):
    rc = ov.main([URL, "--profiles", "Laptop 1440"], launch=fake_launcher(error=RuntimeError("boom")))
    assert rc == 1
    assert "boom" in capsys.readouterr().err


def _laptop():
    import device_profiles

    return device_profiles.profile_by_name("Laptop 1440")
