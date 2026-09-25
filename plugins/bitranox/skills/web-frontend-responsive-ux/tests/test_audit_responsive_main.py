"""audit_responsive.main() end to end with a scripted browser at the ``launch`` seam.

Everything above the seam is the real code: profile selection, route parsing, the per-profile
collection, analysis, report.json and the exit code (0 pass, 1 failure, 2 usage, 3 browser
not installed, 4 findings).
"""

import io
import json
import sys

import pytest

import audit_responsive as ar
from responsive_fake_browser import MISSING_EXECUTABLE, MISSING_HOST_DEPS, Script, fake_launcher

URL = "http://127.0.0.1:9/"  # never contacted: the fake browser answers


def run(tmp_path, *extra, script=None, error=None):
    out = tmp_path / "out"
    launch = fake_launcher(script, error=error)
    rc = ar.main([URL, "--out", str(out), "--profiles", "iPhone SE (portrait)", *extra], launch=launch)
    report = json.loads((out / "report.json").read_text(encoding="utf-8")) if (out / "report.json").exists() else None
    return rc, report, launch.browser


def test_clean_page_passes_with_exit_0(tmp_path, capsys):
    rc, report, browser = run(tmp_path, "--no-axe")
    assert rc == 0
    assert report["passed"] is True
    assert "Audit PASS" in capsys.readouterr().out
    assert browser.contexts_made[0].options["viewport"] == {"width": 375, "height": 667}
    assert (tmp_path / "out" / "iphone-se-portrait.png").exists()


def test_findings_fail_with_exit_4(tmp_path):
    script = Script(raw={"scroll_width": 500, "client_width": 375})
    rc, report, _ = run(tmp_path, "--no-axe", script=script)
    assert rc == 4
    assert report["totals"]["SEVERE"] == 1


def test_axe_that_fails_to_load_fails_the_audit(tmp_path):
    script = Script(axe_tag_error=RuntimeError("Page.add_script_tag: net::ERR_ABORTED 404"))
    rc, report, _ = run(tmp_path, script=script)
    device = report["devices"][0]
    assert rc == 4
    assert "404" in device["axe_error"]
    assert device["findings"][0]["check"] == "a11y-not-measured"


def test_axe_clean_run_passes(tmp_path):
    rc, report, _ = run(tmp_path, script=Script(axe=[]))
    assert rc == 0 and "axe_error" not in report["devices"][0]


def test_i18n_pass_that_throws_is_not_a_pass(tmp_path):
    script = Script(i18n=RuntimeError("NodeFilter is not defined"))
    rc, report, _ = run(tmp_path, "--no-axe", "--i18n", script=script)
    device = report["devices"][0]
    assert rc == 4
    assert device["i18n_error"] == "NodeFilter is not defined"
    assert "text_expansion_overflow" not in json.dumps(device["findings"])


def test_i18n_overflow_is_reported(tmp_path):
    rc, report, _ = run(tmp_path, "--no-axe", "--i18n", script=Script(i18n=True))
    assert rc == 4
    assert [f["check"] for f in report["devices"][0]["findings"]] == ["i18n-layout"]


def test_unknown_profile_names_are_refused_even_when_one_matches(tmp_path, capsys):
    launch = fake_launcher()
    rc = ar.main([URL, "--out", str(tmp_path), "--profiles", "iPhone SE (landscape)", "iPhone SE",
                  "Pixel 7 (landscpae)"], launch=launch)
    err = capsys.readouterr().err
    assert rc == 2
    assert "'iPhone SE'" in err and "'Pixel 7 (landscpae)'" in err
    assert launch.browser.contexts_made == []


def test_route_to_a_missing_file_is_refused_before_launching(tmp_path, capsys):
    launch = fake_launcher()
    rc = ar.main([URL, "--out", str(tmp_path), "--route", f"**/app.css={tmp_path / 'app_local.cs'}"],
                 launch=launch)
    assert rc == 2
    assert "not a readable file" in capsys.readouterr().err
    assert launch.browser.contexts_made == []


def test_routes_are_registered_on_every_page(tmp_path):
    local = tmp_path / "app.css"
    local.write_text("body{}", encoding="utf-8")
    rc, _, browser = run(tmp_path, "--no-axe", "--route", f"**/app.css={local}")
    assert rc == 0
    assert [glob for glob, _ in browser.pages[0].routes] == ["**/app.css"]


def test_missing_browser_exits_3_with_the_install_command(tmp_path, capsys):
    rc, _, _ = run(tmp_path, error=RuntimeError(MISSING_EXECUTABLE))
    err = capsys.readouterr().err
    assert rc == 3
    assert "playwright install chromium" in err


def test_missing_host_libraries_exit_3_naming_install_deps(tmp_path, capsys):
    rc, _, _ = run(tmp_path, error=RuntimeError(MISSING_HOST_DEPS))
    err = capsys.readouterr().err
    assert rc == 3
    assert "install-deps" in err
    assert "Chromium not installed" not in err


def test_unrelated_failure_exits_1(tmp_path, capsys):
    rc, _, _ = run(tmp_path, script=Script(goto_error=RuntimeError("net::ERR_CONNECTION_REFUSED")))
    assert rc == 1
    assert "ERR_CONNECTION_REFUSED" in capsys.readouterr().err


def test_cp1252_stdout_does_not_crash_on_a_non_cp1252_out_dir(tmp_path, monkeypatch):
    buf = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buf, encoding="cp1252"))
    out = tmp_path / "π-out"
    rc = ar.main([URL, "--out", str(out), "--profiles", "Laptop 1440", "--no-axe"], launch=fake_launcher())
    sys.stdout.flush()
    assert rc == 0
    assert b"Audit PASS" in buf.getvalue()


@pytest.mark.parametrize("stream_factory", [lambda: io.StringIO(), lambda: object()])
def test_make_console_safe_tolerates_streams_it_cannot_reconfigure(monkeypatch, stream_factory):
    monkeypatch.setattr(sys, "stdout", stream_factory())
    ar.make_console_safe()  # must not raise
