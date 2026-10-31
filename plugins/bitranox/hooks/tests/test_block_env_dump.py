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


# A git remote listing prints each URL, and a URL can carry a token in its userinfo.
GIT_REMOTE_BLOCKED = [
    "git remote -v",
    "git remote --verbose",
    "git -C /opt/app remote -v",
    "cd /opt/app && git remote -v",
    "git remote -v | head -2",
    "git --no-pager remote -v",
    "git remote -v > r.txt; cat r.txt",
]
GIT_REMOTE_ALLOWED = [
    "git remote",
    "git remote get-url origin | sed -E 's#//[^@/]*@#//***@#'",
    "git remote -v | sed -E 's#//[^@/]*@#//***@#'",
    "git remote -v > /tmp/remotes.txt",
    "git remote add origin https://example.com/app.git",
    "git remote set-url origin git@example.com:app.git",
    # `-v` with a verb is that verb run verbosely, not the URL listing.
    "git remote -v update",
]

# A full git config listing prints insteadOf URLs, credential helpers and http extraheaders.
GIT_CONFIG_BLOCKED = [
    "git config -l",
    "git config --list",
    "git config --global --list",
    "git config --list --show-origin",
    "git -C /opt/app config --list",
    "git -c core.pager=cat config -l | sort",
    "git config list",
    "git config --system list",
]
GIT_CONFIG_ALLOWED = [
    "git config --get user.name",
    "git config user.name",
    "git config --list --name-only",
    "git config -l | grep -c insteadof",
    "git config --list > /tmp/cfg.txt",
    "git config --global core.fileMode false",
    "git config --get-regexp '^user\\.'",
]

# A reader of a .env file, or of a file under a credentials directory, prints the secrets in it.
SECRET_FILE_BLOCKED = [
    "cat .env",
    "cat /opt/app/.env",
    "head -5 .env.local",
    "tail .env.production",
    "less ./config/.env",
    "cat .env | sort",
    "tr '\\n' ' ' < .env",
    "sudo cat /opt/app/credentials/db_password.txt",
    "cat ~/.credentials/token",
    "cat $HOME/.credentials/api.key | head -1",
    "cat \"/opt/app/credentials/key one.txt\"",
]
SECRET_FILE_ALLOWED = [
    "cat .env.example",
    "cat .env.sample",
    "cat /opt/app/.env.template",
    "grep -c API_TOKEN .env",
    "cut -d= -f1 .env",
    "cat .env | cut -d= -f1",
    "cat .env | grep -c NAME",
    "wc -c /opt/app/credentials/token",
    "sudo cat /opt/app/credentials/token | ssh host 'umask 077; cat > /opt/k'",
    "cat .envrc",
    "cat app.env.md",
    "cat credentials.json",
    "cat /opt/app/credentials",
    "ls /opt/app/credentials/",
    "source .env",
]


@pytest.mark.parametrize(
    "command", GIT_REMOTE_BLOCKED + GIT_CONFIG_BLOCKED + SECRET_FILE_BLOCKED
)
def test_a_secret_bearing_print_is_found(command):
    assert G.dump_leaks(command) != []


@pytest.mark.parametrize(
    "command", GIT_REMOTE_ALLOWED + GIT_CONFIG_ALLOWED + SECRET_FILE_ALLOWED
)
def test_a_narrow_secret_query_passes(command):
    assert G.dump_leaks(command) == []


@pytest.mark.parametrize(
    ("command", "shape"),
    [
        ("env", G.Shape.ENVIRONMENT),
        ("git remote -v", G.Shape.GIT_REMOTE),
        ("git config --list", G.Shape.GIT_CONFIG),
        ("cat .env", G.Shape.SECRET_FILE),
        ("env FOO=1 git remote -v", G.Shape.GIT_REMOTE),
        ("git config -l > c.txt; tail c.txt", G.Shape.GIT_CONFIG),
    ],
)
def test_each_print_is_classified_by_its_shape(command, shape):
    assert [found for found, _ in G.secret_prints(command)] == [shape]


@pytest.mark.parametrize(
    ("command", "narrow_form"),
    [
        ("git remote -v", "git remote get-url origin | sed -E 's#//[^@/]*@#//***@#'"),
        ("git config --list", "git config --get <key>"),
        ("cat .env", "grep -c NAME .env"),
        ("env | tail -3", "printenv NAME"),
    ],
)
def test_main_names_the_narrow_form_for_the_shape(capsys, command, narrow_form):
    assert _main(command) == 2
    err = capsys.readouterr().err
    assert narrow_form in err
    assert err.rstrip("\n").endswith(shell_text.WHOLE_CALL_REFUSED)


_REDACTED_LISTING = "git remote -v | sed -E 's#//[^@/]*@#//***@#'"


def test_git_remote_refusal_offers_the_full_listing_redacted_and_the_offer_passes(capsys):
    # A blocked `git remote -v | head` must be one retry away from the answer it wanted.
    assert _main("git remote -v | head -5") == 2
    assert _REDACTED_LISTING in capsys.readouterr().err
    assert G.secret_prints(_REDACTED_LISTING) == []


def test_main_names_only_the_shapes_the_command_has(capsys):
    assert _main("git remote -v") == 2
    err = capsys.readouterr().err
    assert "git remote get-url" in err
    assert "printenv NAME" not in err
    assert "git config --get" not in err


def test_main_names_every_shape_of_a_mixed_command(capsys):
    assert _main("git config -l; cat .env") == 2
    err = capsys.readouterr().err
    assert "git config --get <key>" in err
    assert "grep -c NAME .env" in err


# A print captured into a variable, or a group whose combined output goes elsewhere, shows nothing.
CAPTURED_OR_GROUPED_ALLOWED = [
    "TOK=$(sudo cat /opt/app/credentials/t.token | tr -d '\\r\\n'); echo ok",
    "a=$(cat .env | sha256sum | cut -c1-12); echo \"$a\"",
    "for f in a b; do t=$(sudo cat \"/opt/app/credentials/$f\" | tr -d '\\r\\n'); done",
    "X=`cat .env | tr -d x`",
    "{ printf 'u:'; cat ~/.credentials/pw; } | ssh host 'sudo chpasswd'",
    "{ printf 'A: '; sudo cat /opt/app/credentials/t | tr -d x; printf '\\n'; } > \"$D/h\"",
    "{ git remote -v; git config -l; } > /tmp/both.txt",
    "{ cat .env; }>/tmp/e.txt",
    # The word split leaves a lone backtick: the words after it are the substitution's command.
    "X=` cat .env | tr -d x`",
]
CAPTURED_OR_GROUPED_BLOCKED = [
    "{ printf 'u:'; cat ~/.credentials/pw; }",
    "{ cat .env; } | sort",
    "{ git remote -v; } > r.txt; tail r.txt",
    "X=$(mktemp) git remote -v",
    # What the group is piped into prints on its own.
    "{ echo a; } | cat .env",
    # A group never closed is judged as if it printed.
    "{ cat .env",
    "{ echo start; { cat .env; } | head -2; } > /dev/null; cat /opt/app/credentials/k",
]


@pytest.mark.parametrize("command", CAPTURED_OR_GROUPED_ALLOWED)
def test_a_captured_or_redirected_group_print_passes(command):
    assert G.dump_leaks(command) == []


@pytest.mark.parametrize("command", CAPTURED_OR_GROUPED_BLOCKED)
def test_a_group_or_assignment_that_still_prints_is_found(command):
    assert G.dump_leaks(command) != []
