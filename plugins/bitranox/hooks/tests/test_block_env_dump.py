"""Tests for block-env-dump.py: an environment dump is refused unless its output is narrowed."""

import json

import block_env_dump as G
import pytest

import shell_text

BLOCKED = [
    "env",
    "printenv",
    "printenv -0",
    "env | sort",
    "env | tail -3",
    "sudo env",
    "env -i FOO=bar",
    "env -u VIRTUAL_ENV printenv",
    "pwshpy env",
    "pwshpy env --jsonl | head -5",
    ".venv/bin/pwshpy env --jsonl",
    ".venv/bin/python -m pwshpy env",
    "uvx pwshpy env --json",
    "cat /proc/1234/environ",
    "tr '\\0' '\\n' < /proc/$pid/environ",
    "tr '\\0' '\\n' </proc/self/environ | sort",
    "env | grep -v PATH",
    "printenv | jq .",
    "env >&2",
    "cd /repo && env",
    # The incident shape: the dump goes to a file, then the same command prints the file.
    "pwshpy env --jsonl > $O/env.out 2>&1; echo rc=$?; tail -3 $O/env.out",
    "env > /tmp/e.txt && cat /tmp/e.txt",
    "env | sort > e.txt; head e.txt",
    "for v in a b; do env ZZ=$v pwshpy env; done",
    "pwshpy env > m1.txt 2>&1; tail -2 m1.txt | cut -c1-200",
    "env | cut -d= -f2",
    "env \"$(printf 'PWSHPY_PROBE_BAD=\\xff')\" .venv/bin/python -m pwshpy env --jsonl > $O/b.out 2>&1; tail -3 $O/b.out",
    # A launcher option naming the package is not the program: the program comes after it.
    "uvx --from pwshpy pwshpy env --jsonl",
    "uv run --with pwshpy pwshpy env",
    "uv run env",
    # uv's global options (and the values of those that take one) may stand before `run`.
    "uv --quiet run env",
    "uv --directory x run env",
    "uv -q --directory=x --color never run printenv",
    "time -p env",
    "command env",
]

ALLOWED = [
    "env -u VIRTUAL_ENV python3 -m pytest -q",
    "env FOO=1 make test",
    "env -S 'python3 x.py'",
    "printenv HOME",
    "printenv PATH HOME",
    "env | grep -c '^VIRTUAL_ENV='",
    "env | grep -i rustc_wrapper",
    "env | cut -d= -f1",
    "env | wc -l",
    "env | awk -F= '{print $1}'",
    "env > /tmp/e.txt",
    "env > /dev/null",
    "pwshpy env --jsonl > $O/env.out 2>&1; grep -c PROBE $O/env.out",
    "pwshpy env --help",
    "pwshpy get_process",
    "tr '\\0' '\\n' < /proc/1/environ | grep -E '^DISPLAY='",
    "mapfile -d '' envv < /proc/$src/environ",
    "grep -c PATH /proc/1/environ",
    "echo env",
    "git commit -m 'print env'",
    "cat notes.txt",
    "tail -3 err.txt; env > out.txt",
    "python3 - <<'EOF'\nimport os\nos.system('env')\nEOF",
    "env | jq -r '.name'",
    # `command -v/-V` looks a name up and prints its path; it runs nothing.
    "command -v env",
    "command -V env",
    "command -v printenv",
    # `-i` empties the environment and no assignment adds to it: nothing is printed.
    "env -i",
    "pwshpy --version env",
    # A global option's VALUE is not the program: this runs pytest in a directory named env.
    "uv --directory env run pytest -q",
]


@pytest.mark.parametrize("command", BLOCKED)
def test_an_unfiltered_dump_is_found(command):
    assert G.dump_leaks(command) != []


@pytest.mark.parametrize("command", ALLOWED)
def test_a_narrowed_or_non_dump_command_passes(command):
    assert G.dump_leaks(command) == []


def _main(command, tool_name="Bash"):
    event = {"tool_name": tool_name, "tool_input": {"command": command}}
    return G.main(json.dumps(event))


def test_main_refuses_with_the_shared_footer(capsys):
    assert _main("env | tail -3") == 2
    err = capsys.readouterr().err
    assert "environment dump" in err
    assert err.rstrip("\n").endswith(shell_text.WHOLE_CALL_REFUSED)


def test_main_allows_a_narrowed_dump(capsys):
    assert _main("env | grep -c '^HOME='") == 0
    assert capsys.readouterr().err == ""


def test_main_fails_open_on_bad_input():
    assert G.main("not json") == 0
    assert G.main(json.dumps({"tool_input": "x"})) == 0


@pytest.mark.parametrize("command", ["uv --quiet run env", "uv --directory x run env"])
def test_main_refuses_a_dump_run_by_uv_behind_a_global_option(command):
    assert _main(command) == 2
