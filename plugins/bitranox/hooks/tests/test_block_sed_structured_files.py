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
