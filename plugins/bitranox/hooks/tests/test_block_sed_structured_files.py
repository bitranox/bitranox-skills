"""Tests for block-sed-structured-files.py (blocks sed -i on JSON/YAML/TOML/XML)."""

import io
import json

import block_sed_structured_files as H


def action(command):
    return H.assess(command)[0]


# ---- BLOCK: in-place text editors on structured files ----
def test_block_sed_i_json():
    assert action("sed -i 's/a/b/' config.json") == "block"


def test_block_sed_i_with_backup_suffix_yaml():
    assert action("sed -i.bak 's/a/b/' deploy.yaml") == "block"


def test_block_sed_long_inplace_yml():
    assert action("sed --in-place 's/a/b/' x.yml") == "block"


def test_block_gsed_i_xml():
    assert action("gsed -i 's/a/b/' pom.xml") == "block"


def test_block_perl_inplace_toml():
    assert action("perl -i -pe 's/a/b/' pyproject.toml") == "block"


def test_block_with_absolute_path_and_env_prefix():
    assert action("FOO=1 /usr/bin/sed -i 's/x/y/' /etc/app/settings.toml") == "block"


def test_block_in_a_pipeline_segment():
    assert action("make build && sed -i 's/1.0/2.0/' plugin.json") == "block"


# ---- NOT blocked ----
def test_no_block_sed_i_on_plain_text():
    assert action("sed -i 's/a/b/' notes.txt") is None


def test_no_block_sed_read_only_on_json():
    # no -i: reading, not editing in place
    assert action("sed -n '1,5p' config.json") is None


def test_no_block_echo_containing_sed_text():
    # the literal text inside an echo must not trip the guard (command-position anchoring)
    assert action('echo "sed -i s/a/b/ config.json"') is None


def test_no_block_sed_in_pipe_without_inplace():
    assert action("cat config.json | sed 's/a/b/'") is None


def test_no_block_perl_without_inplace():
    assert action("perl -e 'print 1' config.json") is None


# ---- WARN: redirect onto a structured file ----
def test_warn_redirect_overwrite_yaml():
    assert action("cat tmp > deploy.yaml") == "warn"


def test_warn_append_json():
    assert action("printf x >> data.json") == "warn"


def test_no_warn_redirect_to_text():
    assert action("echo x > out.txt") is None


# ---- main(): exit codes via stdin ----
def _run(monkeypatch, command):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_input": {"command": command}})))
    return H.main()


def test_main_blocks_with_exit_2(monkeypatch):
    assert _run(monkeypatch, "sed -i 's/a/b/' x.json") == 2


def test_main_warn_exits_0(monkeypatch):
    assert _run(monkeypatch, "cat a > b.yaml") == 0


def test_main_clean_exits_0(monkeypatch):
    assert _run(monkeypatch, "sed -i 's/a/b/' notes.txt") == 0


def test_main_empty_stdin_exits_0(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert H.main() == 0


_B = chr(92)


def test_a_powershell_pathed_sed_is_still_blocked():
    """Two separate defects had to be fixed for this to work, and the split alone was not enough.

    POSIX shlex first eats the separators, so the token becomes one word; and even split
    correctly, a basename taken on "/" alone leaves the whole path, which never matches "sed".
    Either one on its own lets the guard wave through exactly what it exists to block.
    """
    cmd = "C:" + _B + "tools" + _B + "sed.exe -i s/a/b/ config.json"
    assert H.assess(cmd, "PowerShell")[0] == "block"


def test_the_plain_posix_form_still_blocks_on_both_arms():
    """The case the guard was built for, kept as a control on both arms."""
    assert H.assess("sed -i 's/a/b/' config.json", "Bash")[0] == "block"
    assert H.assess("sed -i 's/a/b/' config.json", "PowerShell")[0] == "block"


def test_sed_exe_is_blocked_under_bash_too():
    """Git Bash on Windows runs sed.exe; this arm carries nearly all the traffic."""
    assert H.assess("sed.exe -i s/a/b/ config.json", "Bash")[0] == "block"
    assert H.assess("sed.exe -i s/a/b/ config.json", "PowerShell")[0] == "block"


def test_a_separator_inside_a_quoted_string_does_not_start_a_sed_statement():
    """`echo "step 1; sed -i s/a/b/ package.json"` prints a string. The `;` is inside double
    quotes, so it separates nothing, and splitting there manufactured a sed invocation out of
    an echo argument - blocking a command that edits no file at all."""
    import io, json, sys as _s
    _s.stdin = io.StringIO(json.dumps({"tool_name": "Bash", "tool_input": {
        "command": 'echo "step 1; sed -i s/a/b/ package.json"'}}))
    assert H.main() == 0


def test_a_real_sed_on_a_structured_file_is_still_blocked():
    """The direction where it must NOT apply."""
    import io, json, sys as _s
    _s.stdin = io.StringIO(json.dumps({"tool_name": "Bash", "tool_input": {
        "command": "sed -i s/a/b/ package.json"}}))
    assert H.main() == 2


# ---- perl clustered switches ----
def test_perl_clustered_pi_is_in_place():
    """`-pi` is `-p -i` in one cluster; only a token STARTING with `-i` was read as in-place."""
    assert action("perl -pi -e 's/1.0/2.0/' pyproject.toml") == "block"
    assert action("perl -lpi -e 's/1.0/2.0/' pyproject.toml") == "block"
    assert action("perl -pi.bak -e 's/1.0/2.0/' pyproject.toml") == "block"
    assert action("perl -ni -e 'print unless /x/' config.json") == "block"


def test_perl_clusters_without_in_place_are_not_blocked():
    """Controls: no `i` switch, and an `i` that is part of another switch's argument."""
    assert action("perl -pe 's/1.0/2.0/' pyproject.toml") is None
    assert action("perl -lne 'print' config.json") is None
    assert action("perl -Mlib=inc -pe 's/a/b/' config.json") is None
    assert action("perl -I/opt/lib -pe 's/a/b/' config.json") is None


def test_a_hyphenated_file_name_is_not_a_perl_switch():
    """`"-p" in t` read `my-plan.json` as the -p switch; `-i` then made it an in-place edit."""
    assert action("perl -i -e 'print' my-plan.json") is None


# ---- a launcher in front of the editor ----
def test_a_launcher_in_front_of_sed_does_not_hide_it():
    """`sudo`, `env`, `command`, `nice`, `timeout` run the sed after them; only `argv[0]` was judged."""
    for prefix in ("sudo", "command", "env LC_ALL=C", "nice -n 19", "timeout 30", "sudo -u root",
                   "exec", "time"):
        assert action(prefix + " sed -i s/a/b/ /etc/app/config.json") == "block", prefix


def test_a_launcher_without_in_place_is_not_blocked():
    """Controls: the launcher changes nothing when the editor is not in-place, or not an editor."""
    assert action("sudo sed s/a/b/ /etc/app/config.json") is None
    assert action("sudo cat /etc/app/config.json") is None
    assert action("timeout 30 ssh host 'sed -i s/a/b/ config.json'") is None


# ---- a command shlex cannot split ----
def test_an_unbalanced_quote_falls_back_to_a_whitespace_split_and_still_blocks():
    """shlex raises ValueError on the stray `"`. The fallback keeps judging the words rather than
    giving up, so a stray quote cannot switch the guard off for the sed in front of it. Pinned as
    BLOCK: the program, its `-i` and its target all stand outside the unbalanced quote."""
    assert action('sed -i s/a/b/ package.json "') == "block"
    assert action('sed s/a/b/ package.json "') is None


# ---- statements the SEP regex could not separate ----
import pytest  # noqa: E402 - grouped with the cases that need parametrize


@pytest.mark.parametrize("command", [
    "(sed -i s/a/b/ config.json)",
    "cd /tmp && (sed -i s/a/b/ config.json)",
    "x=$(sed -i s/a/b/ config.json)",
    'echo "$(sed -i s/a/b/ config.json)"',
    "echo `sed -i s/a/b/ config.json`",
    "( cd sub; sed -i s/a/b/ config.json )",
])
def test_a_sed_inside_a_subshell_or_substitution_is_blocked(command):
    """SEP has no paren (adding one cut quoted `echo "(must PASS)"` labels in a replay), so a
    subshell's sed read as the program `(sed` and a substitution's as `x=$(sed`: neither is
    `sed`, and the guard said nothing about a command that really rewrites config.json."""
    assert action(command) == "block"


@pytest.mark.parametrize("command", [
    'echo "(sed -i s/a/b/ config.json)"',
    "echo '$(sed -i s/a/b/ config.json)'",
    "echo 'a; (sed -i s/a/b/ config.json)'",
    "grep -n 'sed -i' notes.md # (sed -i x.json)",
])
def test_a_quoted_or_commented_subshell_shape_is_not_a_sed(command):
    """The direction where it must NOT apply: the same text as data runs nothing."""
    assert action(command) is None
