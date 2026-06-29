"""Tests for the runner's pure helpers (no browser): route parsing + content types."""

from pathlib import Path

import pytest

import audit_responsive as ar


def test_guess_content_type_known_and_unknown():
    assert ar.guess_content_type("a/app.css") == "text/css; charset=utf-8"
    assert ar.guess_content_type("b/app.js") == "text/javascript; charset=utf-8"
    assert ar.guess_content_type("c/page.HTML") == "text/html; charset=utf-8"  # case-insensitive
    assert ar.guess_content_type("d/logo.svg") == "image/svg+xml"
    assert ar.guess_content_type("e/font.woff2") == "application/octet-stream"


def test_parse_route_specs_basic():
    rules = ar.parse_route_specs(["**/static/css/app.css=src/static/css/app.css"])
    assert rules == [("**/static/css/app.css", Path("src/static/css/app.css"))]


def test_parse_route_specs_multiple_and_strips_whitespace():
    rules = ar.parse_route_specs([" **/a.js = ./a.js ", "**/b.css=./b.css"])
    assert rules[0] == ("**/a.js", Path("./a.js"))
    assert rules[1] == ("**/b.css", Path("./b.css"))


def test_parse_route_specs_allows_equals_in_path():
    # split on the FIRST '=' only, so a path/query with '=' survives
    rules = ar.parse_route_specs(["**/app.js=/tmp/a=b/app.js"])
    assert rules == [("**/app.js", Path("/tmp/a=b/app.js"))]


def test_parse_route_specs_none_is_empty():
    assert ar.parse_route_specs(None) == []
    assert ar.parse_route_specs([]) == []


@pytest.mark.parametrize("bad", ["no-equals-sign", "=onlypath", "onlyglob=", "  =  "])
def test_parse_route_specs_rejects_malformed(bad):
    with pytest.raises(ValueError):
        ar.parse_route_specs([bad])


def test_parse_args_collects_repeated_routes():
    args = ar.parse_args(["http://x/", "--route", "**/a.css=./a.css", "--route", "**/b.js=./b.js"])
    assert args.route == ["**/a.css=./a.css", "**/b.js=./b.js"]
