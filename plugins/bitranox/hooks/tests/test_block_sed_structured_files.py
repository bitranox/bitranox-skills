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
