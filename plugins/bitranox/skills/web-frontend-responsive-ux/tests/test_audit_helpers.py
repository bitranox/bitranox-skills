"""Tests for the runner's pure helpers (no browser): route parsing + content types."""

from pathlib import Path

import pytest

import audit_responsive as ar
from responsive_fake_browser import FakeRoute


def test_guess_content_type_known_and_unknown():
    assert ar.guess_content_type("a/app.css") == "text/css; charset=utf-8"
    assert ar.guess_content_type("b/app.js") == "text/javascript; charset=utf-8"
    assert ar.guess_content_type("c/page.HTML") == "text/html; charset=utf-8"  # case-insensitive
    assert ar.guess_content_type("d/logo.svg") == "image/svg+xml"
    assert ar.guess_content_type("e/font.woff2") == "application/octet-stream"


@pytest.fixture
def assets(tmp_path, monkeypatch):
    """A cwd holding the local files the route specs point at (paths resolve against cwd)."""
    monkeypatch.chdir(tmp_path)
    for rel in ("src/static/css/app.css", "a.js", "b.css", "a=b/app.js", "app_local.css"):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("/* local */", encoding="utf-8")
    return tmp_path


def test_parse_route_specs_basic(assets):
    rules = ar.parse_route_specs(["**/static/css/app.css=src/static/css/app.css"])
    assert rules == [("**/static/css/app.css", Path("src/static/css/app.css"))]


def test_parse_route_specs_multiple_and_strips_whitespace(assets):
    rules = ar.parse_route_specs([" **/a.js = ./a.js ", "**/b.css=./b.css"])
    assert rules[0] == ("**/a.js", Path("./a.js"))
    assert rules[1] == ("**/b.css", Path("./b.css"))


def test_parse_route_specs_allows_equals_in_path(assets):
    # the split lands where the right-hand side is an existing file, so a path with '=' survives
    rules = ar.parse_route_specs(["**/app.js=a=b/app.js"])
    assert rules == [("**/app.js", Path("a=b/app.js"))]


def test_parse_route_specs_allows_equals_in_glob(assets):
    rules = ar.parse_route_specs(["**/app.css?v=*=app_local.css"])
    assert rules == [("**/app.css?v=*", Path("app_local.css"))]


def test_parse_route_specs_rejects_a_missing_local_file(assets):
    with pytest.raises(ValueError, match="not a readable file"):
        ar.parse_route_specs(["**/app.css=app_local.cs"])  # the typo from the audit


def test_parse_route_specs_rejects_a_directory(assets):
    with pytest.raises(ValueError, match="not a readable file"):
        ar.parse_route_specs(["**/app.css=src"])


def test_parse_route_specs_none_is_empty():
    assert ar.parse_route_specs(None) == []
    assert ar.parse_route_specs([]) == []


@pytest.mark.parametrize("bad", ["no-equals-sign", "=onlypath", "onlyglob=", "  =  "])
def test_parse_route_specs_rejects_malformed(bad):
    with pytest.raises(ValueError, match="GLOB=LOCALPATH"):
        ar.parse_route_specs([bad])


def test_parse_args_collects_repeated_routes():
    args = ar.parse_args(["http://x/", "--route", "**/a.css=./a.css", "--route", "**/b.js=./b.js"])
    assert args.route == ["**/a.css=./a.css", "**/b.js=./b.js"]


def test_route_handler_serves_the_local_file(assets):
    route = FakeRoute("https://live.example/app.css")
    ar._make_route_handler(assets / "app_local.css")(route)
    assert route.served == b"/* local */" and not route.continued


def test_route_handler_fallback_to_the_live_asset_is_reported(assets, capsys):
    gone = assets / "app_local.css"
    handler = ar._make_route_handler(gone)
    gone.unlink()  # deleted between parsing and the request
    route = FakeRoute("https://live.example/app.css")
    handler(route)
    assert route.continued
    err = capsys.readouterr().err
    assert "app_local.css" in err and "live" in err
