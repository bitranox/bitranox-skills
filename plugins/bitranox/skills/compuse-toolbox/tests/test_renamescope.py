"""Tests for `renamescope`: which function does each rename hit land in, and was it on my list?

The load-bearing test here is `TestTheMeasuredCase`, reconstructed from the real 2026-08-31
defect: an identifier that is a PARAMETER in the function being refactored is a LOOP VARIABLE in
the function next to it, a substitution by pattern hits both, and only one of them is the work.
That hit changed MEANING rather than breaking, nothing in the suite covered the sibling function,
and it survived to review because the substituted name happened to be undefined in that scope.

So the assertions that matter are the ones about the OUTSIDE bucket and about `binding` differing
between the two functions. A tool that reported both hits without separating them would be a
prettier grep.

`TestWhatItCannotSee` is deliberate: each test there names a blind spot rather than hiding it, so
a later reader learns the limit from the suite instead of from a bad rename.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import renamescope
from renamescope import (
    Binding,
    Bucket,
    SiteKind,
    Unparseable,
    indent_trap_warning,
    main,
    name_pattern,
    resolve_intended,
    scan_source,
)

# The real shape, reduced: `mac` is a parameter in the function under refactor and a loop
# variable in the guard beside it, whose loop exists to check the OTHER NICs.
MEASURED = '''
def _guest_new_iface(ip, mac, key, guest_os):
    return {"ip": ip, "addr": mac, "key": key, "os": guest_os}


def _no_nic_was_stranded(conf, target):
    for mac in other_nic_macs(conf, target.spare_mac):
        if not lease_for(mac):
            return False
    return True
'''


def scan(source: str, name: str, *intended: str):
    return scan_source(source, pattern=name_pattern(name), intended=list(intended))


def where(sites) -> set[str | None]:
    return {s.enclosing for s in sites}


class TestTheMeasuredCase:
    """The 2026-08-31 rename, and the one hit that would have shipped green."""

    def test_the_sibling_guard_lands_in_outside(self) -> None:
        """`_no_nic_was_stranded` was never opened, so every hit in it is the finding."""
        result = scan(MEASURED, "mac", "_guest_new_iface")
        assert where(result.bucket(Bucket.OUTSIDE)) == {"_no_nic_was_stranded"}

    def test_the_refactored_function_lands_in_intended(self) -> None:
        result = scan(MEASURED, "mac", "_guest_new_iface")
        assert where(result.bucket(Bucket.INTENDED)) == {"_guest_new_iface"}

    def test_the_same_name_is_a_parameter_here_and_a_loop_variable_there(self) -> None:
        """The whole defect in one assertion: the pattern matches both, only one is the work."""
        result = scan(MEASURED, "mac", "_guest_new_iface")
        intended = {s.binding for s in result.bucket(Bucket.INTENDED)}
        outside = {s.binding for s in result.bucket(Bucket.OUTSIDE)}
        assert intended == {Binding.PARAMETER}
        assert outside == {Binding.LOOP_VAR}

    def test_the_loop_target_itself_is_reported_as_a_loop_target(self) -> None:
        result = scan(MEASURED, "mac", "_guest_new_iface")
        kinds = {s.site_kind for s in result.bucket(Bucket.OUTSIDE)}
        assert SiteKind.LOOP_TARGET in kinds

    def test_naming_every_function_leaves_no_finding(self) -> None:
        """The control: with the real mandate declared, the same file is clean."""
        result = scan(MEASURED, "mac", "_guest_new_iface", "_no_nic_was_stranded")
        assert result.findings == ()

    def test_spare_mac_and_other_nic_macs_are_not_hits_for_mac(self) -> None:
        """Word-anchored. The for-loop line holds `mac`, `other_nic_macs` and `spare_mac`;

        only the first is a `mac`, and an unanchored pattern rewriting the other two is the
        neighbouring half of this same defect.
        """
        result = scan(MEASURED, "mac", "_guest_new_iface")
        on_the_loop_line = [s for s in result.sites if s.line == 7]
        assert len(on_the_loop_line) == 1
        assert on_the_loop_line[0].site_kind is SiteKind.LOOP_TARGET
        assert len(result.sites) == 4


class TestEnclosingFunctionByAst:
    """Resolved by AST, so nesting and methods are exact rather than guessed from indentation."""

    NESTED = '''
VALUE = 1


class Runner:
    def run(self, VALUE):
        def inner():
            return VALUE
        return inner


class Other:
    def run(self):
        VALUE = 2
        return VALUE
'''

    def test_a_nested_function_reports_the_innermost_enclosing_function(self) -> None:
        result = scan(self.NESTED, "VALUE")
        inner = [s for s in result.sites if s.line == 8]
        assert [s.enclosing for s in inner] == ["Runner.run.inner"]

    def test_a_method_reports_its_qualified_name(self) -> None:
        result = scan(self.NESTED, "VALUE")
        assert "Other.run" in {s.enclosing for s in result.sites}

    def test_a_module_level_hit_gets_its_own_bucket_and_is_not_dropped(self) -> None:
        result = scan(self.NESTED, "VALUE")
        module = result.bucket(Bucket.MODULE)
        assert [s.line for s in module] == [2]
        assert module[0].enclosing is None

    def test_module_scope_can_be_blessed_deliberately(self) -> None:
        result = scan(self.NESTED, "VALUE", "<module>")
        assert result.bucket(Bucket.MODULE) == ()
        assert 2 in [s.line for s in result.bucket(Bucket.INTENDED)]

    def test_a_module_hit_counts_as_a_finding_unless_blessed(self) -> None:
        """Silently passing an unclaimed module constant is the same defect one scope up."""
        assert scan(self.NESTED, "VALUE").findings != ()

    def test_a_class_body_hit_names_the_class_not_module(self) -> None:
        source = "class Cfg:\n    TIMEOUT = 5\n"
        result = scan(source, "TIMEOUT")
        assert result.sites[0].enclosing is None
        assert result.sites[0].scope == "Cfg"


class TestHowTheNameIsBound:
    """`binding` is the axis the measured defect turned on, so every shape gets a case."""

    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            ("def f(x):\n    return x\n", Binding.PARAMETER),
            ("def f(items):\n    for x in items:\n        return x\n", Binding.LOOP_VAR),
            ("def f(items):\n    return [x for x in items]\n", Binding.COMPREHENSION_VAR),
            ("def f(c):\n    with c as x:\n        return x\n", Binding.WITH_VAR),
            ("def f():\n    try:\n        pass\n    except OSError as x:\n        return x\n",
             Binding.EXCEPT_VAR),
            ("def f():\n    x = 1\n    return x\n", Binding.ASSIGNED),
            ("def f():\n    import os as x\n    return x\n", Binding.IMPORTED),
            ("def f():\n    def x():\n        pass\n    return x\n", Binding.DEFINED),
            ("def f():\n    global x\n    return x\n", Binding.GLOBAL_DECL),
            ("def f():\n    return x\n", Binding.FREE),
        ],
    )
    def test_binding_kinds(self, body: str, expected: Binding) -> None:
        result = scan(body, "x", "f")
        assert result.sites[0].binding is expected

    def test_tuple_unpacking_in_a_for_target_still_counts_as_a_loop_variable(self) -> None:
        """`for mac, ip in pairs:` binds both; missing that reads a loop var as a free load."""
        result = scan("def f(pairs):\n    for mac, ip in pairs:\n        return mac\n", "mac", "f")
        assert result.sites[0].binding is Binding.LOOP_VAR

    def test_a_nested_scopes_loop_variable_does_not_leak_into_its_parent(self) -> None:
        """Folding a nested scope's bindings upward would report a binding the parent lacks."""
        source = "def outer(items):\n    def inner():\n        for x in items:\n            return x\n    return x\n"
        result = scan(source, "x", "outer")
        outer_hit = [s for s in result.sites if s.enclosing == "outer"]
        assert [s.binding for s in outer_hit] == [Binding.FREE]

    def test_an_attribute_is_a_different_namespace_and_is_labelled_so(self) -> None:
        """`conf.mac` is not the local `mac`, and a regex cannot tell them apart."""
        result = scan("def f(conf):\n    return conf.mac\n", "mac", "f")
        assert result.sites[0].site_kind is SiteKind.ATTRIBUTE

    def test_a_keyword_argument_is_labelled_as_one(self) -> None:
        result = scan("def f(g):\n    return g(mac=1)\n", "mac", "f")
        assert result.sites[0].site_kind is SiteKind.KEYWORD_ARG

    def test_a_hit_in_a_docstring_is_named_a_string_not_guessed_at(self) -> None:
        result = scan('def f(mac):\n    """uses mac"""\n    return mac\n', "mac", "f")
        assert SiteKind.STRING in {s.site_kind for s in result.sites}

    def test_a_hit_in_a_comment_is_named_a_comment(self) -> None:
        result = scan("def f(a):\n    # mac goes here\n    return a\n", "mac", "f")
        assert result.sites[0].site_kind is SiteKind.COMMENT


class TestDecoratorLines:
    """A decorator sits above the `def` and is evaluated in the OUTER scope; both matter."""

    DECORATED = "import functools\nLIMIT = 3\n\n\n@functools.lru_cache(maxsize=LIMIT)\ndef run(LIMIT):\n    return LIMIT\n"

    def test_a_decorator_hit_is_attributed_to_the_function_it_decorates(self) -> None:
        """`node.lineno` excludes decorators, so a naive span orphans this hit into module scope."""
        result = scan(self.DECORATED, "LIMIT", "run")
        deco = [s for s in result.sites if s.line == 5]
        assert [s.enclosing for s in deco] == ["run"]

    def test_a_decorator_hit_is_flagged_because_its_scope_differs(self) -> None:
        result = scan(self.DECORATED, "LIMIT", "run")
        assert [s.in_decorator for s in result.sites if s.line == 5] == [True]
        assert all(not s.in_decorator for s in result.sites if s.line > 5)


class TestTheIndentationTrap:
    """A 4-space literal is a SUBSTRING of the 8-space occurrence, and the diff looks fine."""

    def test_an_unanchored_indent_bearing_pattern_warns(self) -> None:
        assert indent_trap_warning("    if x:") is not None

    def test_a_line_anchored_pattern_does_not(self) -> None:
        assert indent_trap_warning(r"(?m)^(\s*)if x:$") is None

    def test_a_leading_backslash_s_also_warns(self) -> None:
        assert indent_trap_warning(r"\s+if x:") is not None

    def test_the_warning_reaches_stderr_with_the_depths_it_matched(
        self, capsys: pytest.CaptureFixture[str], tmp_path
    ) -> None:
        """The proof that the shallow pattern really did match the deeper line."""
        target = tmp_path / "m.py"
        target.write_text("def a():\n    if x:\n        pass\ndef b():\n    if x:\n        if x:\n            pass\n")
        main([str(target), "--regex", "    if x:", "--intended", "a"])
        err = capsys.readouterr().err
        assert "SUBSTRING" in err
        assert "[4, 8]" in err


class TestTheIntendedList:
    """The mandate is a LIST. A list that does not resolve is a broken mandate, not a pass."""

    FUNCS = ("Runner.run", "Other.run", "solo")

    def test_a_qualified_name_resolves_to_exactly_one(self) -> None:
        resolved, _, notes = resolve_intended(["Runner.run"], self.FUNCS)
        assert resolved == {"Runner.run"}
        assert notes == []

    def test_a_bare_name_matching_two_qualnames_blesses_both_and_warns(self) -> None:
        """The named blind spot: choosing one silently is how a wrong-class hit reads intended."""
        resolved, _, notes = resolve_intended(["run"], self.FUNCS)
        assert resolved == {"Runner.run", "Other.run"}
        assert any("ambiguous" in n for n in notes)

    def test_a_name_matching_nothing_warns_that_the_mandate_is_wrong(self) -> None:
        _, _, notes = resolve_intended(["typo"], self.FUNCS)
        assert any("matches no function" in n for n in notes)

    def test_module_is_recognised_as_a_scope_not_a_function_name(self) -> None:
        resolved, blessed, notes = resolve_intended(["<module>"], self.FUNCS)
        assert blessed is True
        assert resolved == set()
        assert notes == []


class TestTheCli:
    """Format-independent exit codes, JSON that survives failure, warnings off the parsed stream."""

    @staticmethod
    def _write(tmp_path, source: str):
        target = tmp_path / "net.py"
        target.write_text(source, encoding="utf-8")
        return str(target)

    def test_outside_hits_exit_1(self, tmp_path) -> None:
        assert main([self._write(tmp_path, MEASURED), "--name", "mac",
                     "--intended", "_guest_new_iface"]) == 1

    def test_no_outside_hits_exit_0(self, tmp_path) -> None:
        assert main([self._write(tmp_path, MEASURED), "--name", "mac",
                     "--intended", "_guest_new_iface",
                     "--intended", "_no_nic_was_stranded"]) == 0

    def test_a_pattern_matching_nothing_is_an_error_not_a_pass(self, tmp_path) -> None:
        """Exiting 0 here would be a green meaning "I examined nothing"."""
        assert main([self._write(tmp_path, MEASURED), "--name", "absent"]) == 2

    def test_unparseable_source_exits_2(self, tmp_path) -> None:
        assert main([self._write(tmp_path, "def broken(\n"), "--name", "broken"]) == 2

    def test_a_missing_file_exits_2(self, tmp_path) -> None:
        assert main([str(tmp_path / "nope.py"), "--name", "x"]) == 2

    def test_a_bad_regex_exits_2_rather_than_raising(self, tmp_path) -> None:
        assert main([self._write(tmp_path, MEASURED), "--regex", "("]) == 2

    def test_json_is_emitted_on_failure_too(
        self, capsys: pytest.CaptureFixture[str], tmp_path
    ) -> None:
        """A caller parsing stdout must not get an empty string and read it as "no hits"."""
        assert main([self._write(tmp_path, MEASURED), "--name", "absent", "--json"]) == 2
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is False
        assert "matched nothing" in payload["data"]["error"]

    def test_the_json_envelope_carries_the_verdict_and_the_buckets(
        self, capsys: pytest.CaptureFixture[str], tmp_path
    ) -> None:
        assert main([self._write(tmp_path, MEASURED), "--name", "mac",
                     "--intended", "_guest_new_iface", "--json"]) == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["command"] == "renamescope"
        assert payload["data"]["verdict"] == "outside_hits"
        assert payload["data"]["counts"]["outside"] == 2
        assert payload["data"]["counts"]["intended"] == 2
        assert payload["data"]["matches"] == 4

    def test_warnings_stay_on_stderr_and_out_of_the_parsed_stream(
        self, capsys: pytest.CaptureFixture[str], tmp_path
    ) -> None:
        main([self._write(tmp_path, MEASURED), "--name", "mac",
              "--intended", "typo", "--json"])
        captured = capsys.readouterr()
        json.loads(captured.out)
        assert "matches no function" in captured.err

    def test_intended_can_be_read_from_a_file(self, tmp_path) -> None:
        listing = tmp_path / "mandate.txt"
        listing.write_text("# the functions I opened\n_guest_new_iface\n_no_nic_was_stranded\n")
        assert main([self._write(tmp_path, MEASURED), "--name", "mac",
                     "--intended-file", str(listing)]) == 0


class TestWhatItCannotSee:
    """Each of these names a limit. A tool that went quiet here would be worse than one that fails."""

    def test_a_dynamically_bound_name_is_invisible_to_any_ast(self) -> None:
        """`globals()["mac"] = v` binds `mac`, and no AST shows it. The hit is still REPORTED."""
        source = 'def f(v):\n    globals()["mac"] = v\n'
        result = scan(source, "mac", "f")
        assert len(result.sites) == 1
        assert result.sites[0].site_kind is SiteKind.STRING
        assert result.sites[0].binding is Binding.FREE

    def test_it_only_sees_the_files_it_was_handed(self) -> None:
        """A file-wide rename touching a sibling module is invisible unless that module is passed."""
        result = scan("def f(mac):\n    return mac\n", "mac", "f")
        assert result.findings == ()

    def test_an_unparseable_file_refuses_rather_than_reporting_no_hits(self) -> None:
        with pytest.raises(Unparseable):
            scan_source("def broken(\n", pattern=name_pattern("broken"))

    def test_a_non_ascii_line_does_not_shift_the_site_kind(self) -> None:
        """AST columns are UTF-8 BYTE offsets and match columns are CHARACTER offsets.

        The non-ASCII must sit on the SAME line and BEFORE the hit, or the two offsets never
        diverge and this test asserts nothing. Here the line is 23 characters and 26 bytes, so
        without the conversion the lookup misses and the kind degrades to `unclassified` -
        silently, on any file with an accented string or a comment in German.
        """
        source = 'def f(mac):\n    return {"\u00e4\u00f6\u00fc": mac}\n'
        assert len(source.splitlines()[1].encode("utf-8")) > len(source.splitlines()[1])
        result = scan(source, "mac", "f")
        assert [s.site_kind for s in result.sites] == [
            SiteKind.PARAMETER_DECL,
            SiteKind.LOAD,
        ]


# ---- several files, one mandate ------------------------------------------------------------


def _files(tmp_path, **sources: str) -> list[str]:
    out = []
    for name, source in sources.items():
        p = tmp_path / f"{name}.py"
        p.write_text(source, encoding="utf-8")
        out.append(str(p))
    return out


HELPER = "def helper(mac):\n    return mac\n"


class TestSeveralFiles:
    def test_the_same_function_name_in_two_files_warns(self, tmp_path, capsys) -> None:
        a, b = _files(tmp_path, a=HELPER, b=HELPER)
        rc = main([a, b, "--name", "mac", "--intended", "helper"])
        err = capsys.readouterr().err
        assert rc == 0
        assert "ambiguous" in err
        assert "a.py::helper" in err and "b.py::helper" in err

    def test_a_file_qualified_name_blesses_only_that_file(self, tmp_path, capsys) -> None:
        a, b = _files(tmp_path, a=HELPER, b=HELPER)
        assert main([a, b, "--name", "mac", "--intended", "a.py::helper", "--json"]) == 1
        payload = json.loads(capsys.readouterr().out)
        outside = {s["path"] for s in payload["data"]["sites"] if s["bucket"] == "outside"}
        assert outside == {b}
        assert payload["data"]["counts"] == {"intended": 2, "outside": 2, "module": 0}

    def test_the_full_path_qualifies_too(self, tmp_path) -> None:
        a, b = _files(tmp_path, a=HELPER, b=HELPER)
        assert main([a, b, "--name", "mac", "--intended", f"{b}::helper",
                     "--intended", f"{a}::helper"]) == 0

    def test_a_file_qualifier_naming_no_scanned_file_warns(self, tmp_path, capsys) -> None:
        (a,) = _files(tmp_path, a=HELPER)
        assert main([a, "--name", "mac", "--intended", "zzz.py::helper"]) == 1
        assert "zzz.py" in capsys.readouterr().err

    def test_control_one_file_with_two_classes_still_warns(self, tmp_path, capsys) -> None:
        (c,) = _files(tmp_path, c="class A:\n    def helper(self, mac):\n        return mac\n"
                                  "class B:\n    def helper(self, mac):\n        return mac\n")
        main([c, "--name", "mac", "--intended", "helper"])
        assert "['A.helper', 'B.helper']" in capsys.readouterr().err

    def test_a_directory_argument_is_refused_not_skipped(self, tmp_path, capsys) -> None:
        (a,) = _files(tmp_path, a=HELPER)
        adir = tmp_path / "adir"
        adir.mkdir()
        (adir / "x.py").write_text("def other(mac):\n    return mac\n", encoding="utf-8")
        assert main([a, str(adir), "--name", "mac", "--intended", "helper"]) == 2
        assert "directory" in capsys.readouterr().err

    def test_a_directory_alone_says_why(self, tmp_path, capsys) -> None:
        adir = tmp_path / "adir"
        adir.mkdir()
        assert main([str(adir), "--name", "mac"]) == 2
        assert "directory" in capsys.readouterr().err

    @pytest.mark.skipif(sys.platform == "win32" or not hasattr(os, "geteuid") or os.geteuid() == 0,
                        reason="chmod 000 does not deny access on Windows or to root")
    def test_an_unreadable_file_makes_the_run_exit_2(self, tmp_path, capsys) -> None:
        a, locked = _files(tmp_path, a=HELPER, locked="def other(mac):\n    return mac\n")
        Path(locked).chmod(0)
        try:
            assert main([a, locked, "--name", "mac", "--intended", "helper", "--json"]) == 2
            captured = capsys.readouterr()
            payload = json.loads(captured.out)
            assert payload["ok"] is False
            assert any("locked.py" in s for s in payload["skipped"])
            assert "locked.py" in captured.err
        finally:
            Path(locked).chmod(0o644)

    def test_control_both_files_readable_reports_the_outside_hit(self, tmp_path) -> None:
        a, x = _files(tmp_path, a=HELPER, x="def other(mac):\n    return mac\n")
        assert main([a, x, "--name", "mac", "--intended", "helper"]) == 1


# ---- regex positions ---------------------------------------------------------------------


NESTED = "def outer():\n    y = 1\n\n    def target():\n        pass\n"


class TestRegexPositions:
    def test_a_leading_backslash_s_that_crosses_a_blank_line_lands_on_the_def(self) -> None:
        pattern = re.compile(r"(?m)^(\s*)def target\(")
        result = scan_source(NESTED, pattern=pattern, intended=["outer"])
        assert [(s.line, s.enclosing, s.bucket) for s in result.sites] == [
            (4, "outer.target", Bucket.OUTSIDE)]

    def test_the_cli_is_no_longer_a_false_green(self, tmp_path, capsys) -> None:
        (nl2,) = _files(tmp_path, nl2=NESTED)
        assert main([nl2, "--regex", r"(?m)^(\s*)def target\(", "--intended", "outer"]) == 1
        assert "crosses" in capsys.readouterr().err

    def test_control_blank_free_file(self) -> None:
        pattern = re.compile(r"(?m)^([ \t]*)def target\(")
        result = scan_source(NESTED, pattern=pattern, intended=["outer"])
        assert [s.bucket for s in result.sites] == [Bucket.OUTSIDE]

    def test_an_indent_led_regex_still_gets_binding_and_kind(self) -> None:
        source = "def f(mac):\n    x = 1\n\n    mac = 2\n"
        result = scan_source(source, pattern=re.compile(r"(?m)^([ \t]*)mac = "), intended=["f"])
        (site,) = result.sites
        assert (site.line, site.col) == (4, 4)
        assert site.binding is Binding.PARAMETER
        assert site.site_kind is SiteKind.ASSIGN_TARGET

    def test_control_the_bare_regex(self) -> None:
        source = "def f(mac):\n    x = 1\n\n    mac = 2\n"
        (site,) = scan_source(source, pattern=re.compile("mac = "), intended=["f"]).sites
        assert (site.binding, site.site_kind) == (Binding.PARAMETER, SiteKind.ASSIGN_TARGET)

    def test_the_docstring_recommends_the_newline_safe_form(self) -> None:
        doc = renamescope.__doc__ or ""
        assert r"(?m)^(\s*)" not in doc
        assert r"(?m)^([ \t]*)" in doc
        assert "uv run tools/" not in doc
        assert "uv run scripts/renamescope.py" in doc


class TestSourceShapes:
    def test_a_form_feed_does_not_shift_the_line_text(self) -> None:
        source = "x = 1\n\x0c\ndef mac():\n    a = 1\n"
        (site,) = scan(source, "mac", "mac").sites
        assert site.text == "def mac():"
        assert site.site_kind is SiteKind.DEF_NAME
        assert site.binding is Binding.DEFINED

    def test_a_lambda_parameter_is_bound_as_a_parameter(self) -> None:
        result = scan("def f(items):\n    return sorted(items, key=lambda mac: mac.x)\n", "mac", "f")
        assert [(s.site_kind, s.binding) for s in result.sites] == [
            (SiteKind.PARAMETER_DECL, Binding.PARAMETER), (SiteKind.LOAD, Binding.PARAMETER)]

    def test_control_outside_the_lambda_the_name_stays_free(self) -> None:
        result = scan("def f(items):\n    g = lambda mac: mac\n    return mac\n", "mac", "f")
        assert [s.binding for s in result.sites] == [
            Binding.PARAMETER, Binding.PARAMETER, Binding.FREE]

    def test_fstring_literal_text_is_a_string_on_every_version(self) -> None:
        result = scan('def f(x):\n    return f"mac is {x}"\n', "mac", "f")
        assert [s.site_kind for s in result.sites] == [SiteKind.STRING]

    def test_a_name_inside_an_fstring_field_is_still_a_load(self) -> None:
        result = scan('def f(mac):\n    return f"is {mac}"\n', "mac", "f")
        assert [s.site_kind for s in result.sites] == [SiteKind.PARAMETER_DECL, SiteKind.LOAD]

    @pytest.mark.parametrize("pattern", ["(?mi)    if x:", "(?im)    if x:", "(?m)(?i)    if x:",
                                         "(?m)    if x:"])
    def test_combined_inline_flags_still_get_the_indent_warning(self, pattern) -> None:
        assert indent_trap_warning(pattern) is not None

    def test_a_non_utf8_source_with_a_coding_cookie_is_read(self, tmp_path) -> None:
        p = tmp_path / "lat.py"
        p.write_bytes(b"# -*- coding: latin-1 -*-\ndef f(mac):\n    return '\xe4' + mac\n")
        assert main([str(p), "--name", "mac", "--intended", "f"]) == 0

    def test_an_undecodable_source_exits_2(self, tmp_path, capsys) -> None:
        p = tmp_path / "bad.py"
        p.write_bytes(b"def f(mac):\n    return '\xe4' + mac\n")
        assert main([str(p), "--name", "mac", "--intended", "f", "--json"]) == 2
        assert json.loads(capsys.readouterr().out)["ok"] is False

    def test_a_bom_source_is_read(self, tmp_path) -> None:
        p = tmp_path / "bom.py"
        p.write_bytes(b"\xef\xbb\xbfdef f(mac):\n    return mac\n")
        assert main([str(p), "--name", "mac", "--intended", "f"]) == 0

    def test_a_nul_byte_is_unparseable_not_a_crash(self) -> None:
        with pytest.raises(Unparseable):
            scan_source("def f(mac):\n    return mac\x00\n", pattern=name_pattern("mac"))

    def test_cp1252_stdout_does_not_crash(self, tmp_path) -> None:
        p = tmp_path / "arrow.py"
        p.write_text("def f(mac):\n    return mac  # a \u2192 b\n", encoding="utf-8")
        script = Path(__file__).resolve().parent.parent / "scripts" / "renamescope.py"
        env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        r = subprocess.run([sys.executable, str(script), str(p), "--name", "mac", "--intended", "f"],
                           capture_output=True, env=env, check=False)
        assert r.returncode == 0, r.stderr


class TestCoverageGaps:
    def test_a_decorator_hit_binds_in_the_outer_scope(self) -> None:
        """`@deco(LIMIT)` is evaluated before `run` exists, so its LIMIT is the module's."""
        result = scan(TestDecoratorLines.DECORATED, "LIMIT", "run")
        assert [s.binding for s in result.sites if s.line == 5] == [Binding.ASSIGNED]
        assert [s.binding for s in result.sites if s.line == 7] == [Binding.PARAMETER]

    def test_a_missing_intended_file_exits_2(self, tmp_path, capsys) -> None:
        (a,) = _files(tmp_path, a=HELPER)
        assert main([a, "--name", "mac", "--intended-file", str(tmp_path / "nope.txt")]) == 2
        assert "--intended-file" in capsys.readouterr().err

    def test_an_intended_file_with_a_bom_and_crlf(self, tmp_path) -> None:
        (a,) = _files(tmp_path, a=HELPER)
        listing = tmp_path / "m.txt"
        listing.write_bytes(b"\xef\xbb\xbfhelper\r\n")
        assert main([a, "--name", "mac", "--intended-file", str(listing)]) == 0

    def test_nothing_matched_is_not_a_dead_exception_class(self) -> None:
        assert not hasattr(renamescope, "NothingMatched")
