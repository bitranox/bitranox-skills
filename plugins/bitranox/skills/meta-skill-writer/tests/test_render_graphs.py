"""render-graphs.js driven under node against SKILL.md fixtures built in tmp_path.

The script writes a diagrams/ folder beside the SKILL.md it is given, so every fixture is a copy
in tmp_path - never a skill inside the checkout. Skipped where node or graphviz is not installed.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "render-graphs.js"
SKILLS_ROOT = SKILL_DIR.parent
NODE = shutil.which("node")
DOT = shutil.which("dot")

pytestmark = pytest.mark.skipif(NODE is None or DOT is None, reason="node or graphviz is not installed")

GOOD = "digraph good {\n  a -> b;\n}"
BROKEN = "digraph broken {\n  a -> ;\n}"
# The 2026-08-27 shape: bare statements with no digraph wrapper, fenced as dot.
BARE = 'step1 [label="import fs"];\nstep2 [label="read file"];\nstep1 -> step2;'


def make_skill(root: Path, name: str, blocks: list[str], newline: str = "\n") -> Path:
    """Write a SKILL.md holding one ```dot fence per block into root/name and return the dir."""
    skill = root / name
    skill.mkdir(parents=True)
    parts = ["# Fixture skill", ""]
    for block in blocks:
        parts += ["```dot", block, "```", ""]
    (skill / "SKILL.md").write_bytes(newline.join(parts).encode("utf-8"))
    return skill


def run(skill: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([NODE or "node", str(SCRIPT), str(skill), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60, env=env,
                          check=False)


def node_count(svg: Path) -> int:
    return svg.read_text(encoding="utf-8").count('class="node"')


def outputs(skill: Path) -> list[str]:
    diagrams = skill / "diagrams"
    return sorted(p.name for p in diagrams.iterdir()) if diagrams.is_dir() else []


# --- 1. failure is an exit code, not only a line of text -----------------------------------------

def test_a_failed_block_exits_1_and_still_renders_the_good_one(tmp_path):
    skill = make_skill(tmp_path, "mixed", [GOOD, BROKEN])
    proc = run(skill)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert outputs(skill) == ["good.svg"]
    assert "1 rendered, 1 failed" in proc.stdout + proc.stderr


def test_all_good_blocks_exit_0_with_a_summary(tmp_path):
    skill = make_skill(tmp_path, "fine", [GOOD, "digraph other { x -> y; }"])
    proc = run(skill)
    assert proc.returncode == 0, proc.stderr
    assert outputs(skill) == ["good.svg", "other.svg"]
    assert "2 rendered, 0 failed" in proc.stdout


def test_a_failed_combine_exits_1(tmp_path):
    skill = make_skill(tmp_path, "mixed", [GOOD, BROKEN])
    proc = run(skill, "--combine")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert not [n for n in outputs(skill) if n.endswith(".svg")]


# --- NEW-2: dot's error printed once, debug source present when it is needed ---------------------

def test_dot_error_is_printed_once(tmp_path):
    skill = make_skill(tmp_path, "broken", [BROKEN])
    proc = run(skill)
    assert proc.returncode == 1
    assert proc.stderr.count("syntax error") == 1, proc.stderr


def test_combined_debug_source_exists_when_the_render_fails(tmp_path):
    skill = make_skill(tmp_path, "mixed", [GOOD, BROKEN])
    proc = run(skill, "--combine")
    assert proc.returncode == 1
    assert outputs(skill) == ["mixed_combined.dot"], proc.stdout + proc.stderr


def test_total_failure_leaves_no_empty_diagrams_dir(tmp_path):
    skill = make_skill(tmp_path, "broken", [BROKEN])
    run(skill)
    assert not (skill / "diagrams").exists()


# --- 2. duplicate names never overwrite (D5: suffix on collision) --------------------------------

def test_duplicate_digraph_names_get_a_suffix_instead_of_overwriting(tmp_path):
    skill = make_skill(tmp_path, "dup", ["digraph flow { a -> b; }", "digraph flow { c -> d -> e; }"])
    proc = run(skill)
    assert proc.returncode == 0, proc.stderr
    assert outputs(skill) == ["flow.svg", "flow_2.svg"]
    assert node_count(skill / "diagrams" / "flow.svg") == 2
    assert node_count(skill / "diagrams" / "flow_2.svg") == 3
    assert "flow_2" in proc.stderr


def test_a_suffix_never_lands_on_a_name_a_later_block_owns(tmp_path):
    skill = make_skill(tmp_path, "dup", ["digraph flow { a; }", "digraph flow { b; c; }",
                                         "digraph flow_2 { d; e; f; }"])
    proc = run(skill)
    assert proc.returncode == 0, proc.stderr
    names = outputs(skill)
    assert len(names) == 3 and len(set(names)) == 3, names


# --- 3. --combine with node ids shared between blocks (D6: detect, name, refuse) -----------------

def test_combine_refuses_node_ids_shared_between_blocks(tmp_path):
    skill = make_skill(tmp_path, "shared", ["digraph one { start -> a; }", "digraph two { start -> b; }"])
    proc = run(skill, "--combine")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "start" in proc.stderr and "one" in proc.stderr and "two" in proc.stderr
    assert not [n for n in outputs(skill) if n.endswith(".svg")]


def test_combine_sees_a_shared_id_however_it_is_spelled(tmp_path):
    # "start" and start are one node to graphviz; a regex over the source would call them two.
    skill = make_skill(tmp_path, "spelled", ['digraph one { "start" -> a; }', "digraph two { start -> b; }"])
    proc = run(skill, "--combine")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "start" in proc.stderr


def test_separate_mode_is_unaffected_by_shared_ids(tmp_path):
    skill = make_skill(tmp_path, "shared", ["digraph one { start -> a; }", "digraph two { start -> b; }"])
    proc = run(skill)
    assert proc.returncode == 0, proc.stderr
    assert outputs(skill) == ["one.svg", "two.svg"]


def test_combine_of_disjoint_blocks_keeps_every_node(tmp_path):
    skill = make_skill(tmp_path, "disjoint", ["digraph one { s1 -> a; }", "digraph two { s2 -> b; }"])
    proc = run(skill, "--combine")
    assert proc.returncode == 0, proc.stderr
    assert node_count(skill / "diagrams" / "disjoint_combined.svg") == 4


# --- 4 / NEW-1. --combine body extraction ---------------------------------------------------------

@pytest.mark.parametrize("block", [
    "digraph { a -> b; }",
    "strict digraph S { a -> b; }",
    'digraph "my flow" { a -> b; }',
    "DiGraph upper { a -> b; }",
    "// leading comment\ndigraph commented { a -> b; }",
    "digraph übersicht { a -> b; }",
], ids=["anonymous", "strict", "quoted", "keyword-case", "leading-comment", "non-ascii-name"])
def test_combine_extracts_every_digraph_header_form(tmp_path, block):
    skill = make_skill(tmp_path, "forms", [block])
    proc = run(skill, "--combine")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert node_count(skill / "diagrams" / "forms_combined.svg") == 2


def test_combine_refuses_an_undirected_graph_block(tmp_path):
    skill = make_skill(tmp_path, "undirected", [GOOD, "graph G { x -- y; }"])
    proc = run(skill, "--combine")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "undirected" in proc.stderr
    assert not [n for n in outputs(skill) if n.endswith(".svg")]


def test_separate_mode_still_renders_an_undirected_graph(tmp_path):
    skill = make_skill(tmp_path, "undirected", ["graph G { x -- y; }"])
    proc = run(skill)
    assert proc.returncode == 0, proc.stderr
    assert outputs(skill) == ["G.svg"]


def test_combine_fails_loudly_on_a_bare_statements_block(tmp_path):
    skill = make_skill(tmp_path, "bare", [GOOD, BARE])
    proc = run(skill, "--combine")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "graph_2" in proc.stderr
    assert not [n for n in outputs(skill) if n.endswith(".svg")]


def test_separate_mode_fails_on_a_bare_statements_block(tmp_path):
    skill = make_skill(tmp_path, "bare", [GOOD, BARE])
    proc = run(skill)
    assert proc.returncode == 1
    assert outputs(skill) == ["good.svg"]


# --- 5. folder basename as the combined graph id --------------------------------------------------

@pytest.mark.parametrize(("folder", "stem"), [
    ("2fa-skill", "2fa_skill"),
    ("f5.dot", "f5_dot"),
    ("f5 space", "f5_space"),
    ('quote"d', "quote_d"),
])
def test_combine_accepts_any_folder_name(tmp_path, folder, stem):
    skill = make_skill(tmp_path, folder, [GOOD])
    proc = run(skill, "--combine")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert outputs(skill) == [f"{stem}_combined.dot", f"{stem}_combined.svg"]


# --- 6. CRLF ------------------------------------------------------------------------------------

@pytest.mark.parametrize("mode", [[], ["--combine"]], ids=["separate", "combine"])
def test_crlf_skill_md_finds_its_blocks(tmp_path, mode):
    skill = make_skill(tmp_path, "crlf", [GOOD.replace("\n", "\r\n")], newline="\r\n")
    proc = run(skill, *mode)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Found 1 diagram" in proc.stdout


# --- 7. no shell, no `which` ----------------------------------------------------------------------

def _path_with(tmp_path: Path, *tools: str) -> dict[str, str]:
    """An env whose PATH holds only links to the named tools - no which, no sh."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in tools:
        (bin_dir / tool).symlink_to(shutil.which(tool) or tool)
    return {**os.environ, "PATH": str(bin_dir)}


@pytest.mark.skipif(os.name == "nt", reason="symlinked PATH fixture is POSIX-only")
def test_runs_where_dot_is_on_path_but_which_is_not(tmp_path):
    env = _path_with(tmp_path, "node", "dot")
    skill = make_skill(tmp_path, "nowhich", [GOOD])
    proc = run(skill, env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert outputs(skill) == ["good.svg"]


@pytest.mark.skipif(os.name == "nt", reason="symlinked PATH fixture is POSIX-only")
def test_missing_dot_exits_1_with_install_advice_for_every_os(tmp_path):
    env = _path_with(tmp_path, "node")
    skill = make_skill(tmp_path, "nodot", [GOOD])
    proc = run(skill, env=env)
    assert proc.returncode == 1
    assert "graphviz" in proc.stderr and "Windows" in proc.stderr, proc.stderr
    assert not (skill / "diagrams").exists()


# --- 8. every shipped skill renders in both modes ------------------------------------------------

SHIPPED = sorted(p.parent.name for p in SKILLS_ROOT.glob("*/SKILL.md")
                 if re.search(r"^```dot\s*$", p.read_text(encoding="utf-8"), re.MULTILINE))


def test_the_shipped_census_is_not_empty():
    # Guards the parametrised test below against passing vacuously on an empty glob.
    assert SHIPPED, f"no SKILL.md under {SKILLS_ROOT} holds a ```dot block"


@pytest.mark.parametrize("mode", [[], ["--combine"]], ids=["separate", "combine"])
@pytest.mark.parametrize("name", SHIPPED)
def test_every_shipped_skill_renders(tmp_path, name, mode):
    skill = tmp_path / name
    skill.mkdir()
    shutil.copyfile(SKILLS_ROOT / name / "SKILL.md", skill / "SKILL.md")
    proc = run(skill, *mode)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert [n for n in outputs(skill) if n.endswith(".svg")]


# --- 9. --combine keeps `strict`, and finds the brace that really closes the graph --------------

def edge_count(svg: Path) -> int:
    return svg.read_text(encoding="utf-8").count('class="edge"')


STRICT_DUP = "strict digraph s { a -> b; a -> b; }"


def test_combine_keeps_a_strict_blocks_duplicate_edges_merged(tmp_path):
    """`strict` merges duplicate edges; dropped by the merge, the combined diagram drew two."""
    alone = make_skill(tmp_path, "alone", [STRICT_DUP])
    assert run(alone).returncode == 0
    assert edge_count(alone / "diagrams" / "s.svg") == 1
    skill = make_skill(tmp_path, "strict", [STRICT_DUP, "strict digraph t { c -> d; }"])
    proc = run(skill, "--combine")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert edge_count(skill / "diagrams" / "strict_combined.svg") == 2


def test_combine_keeps_a_plain_blocks_duplicate_edges(tmp_path):
    """Control: without `strict` both edges are drawn, alone and combined."""
    skill = make_skill(tmp_path, "plain", ["digraph p { a -> b; a -> b; }"])
    proc = run(skill, "--combine")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert edge_count(skill / "diagrams" / "plain_combined.svg") == 2


def test_combine_refuses_a_mix_of_strict_and_plain_blocks(tmp_path):
    """One merged graph is strict or not as a whole, so a mix cannot be drawn faithfully."""
    skill = make_skill(tmp_path, "mixed", [STRICT_DUP, "digraph p { c -> d; c -> d; }"])
    proc = run(skill, "--combine")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "strict" in proc.stderr
    assert not [n for n in outputs(skill) if n.endswith(".svg")]


@pytest.mark.parametrize("block", [
    "digraph x { a -> b; } // a trailing } in a comment",
    "digraph x { a -> b; } /* } */",
    "digraph x { a -> b; }\n# a preprocessor line with }",
], ids=["line-comment", "block-comment", "hash-line"])
def test_combine_body_ends_at_the_brace_that_closes_the_graph(tmp_path, block):
    skill = make_skill(tmp_path, "trail", [block])
    assert run(skill).returncode == 0  # dot itself accepts the block
    proc = run(skill, "--combine")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert node_count(skill / "diagrams" / "trail_combined.svg") == 2


@pytest.mark.parametrize("block", [
    'digraph q { a [label="}"]; a -> b; }',
    "digraph c { a -> b; /* } */ }",
    "digraph h { a [label=<<b>}</b>>]; a -> b; }",
    "digraph n { subgraph cluster_x { a; } a -> b; }",
], ids=["quoted-brace", "comment-brace", "html-brace", "nested-subgraph"])
def test_combine_skips_braces_that_do_not_close_the_graph(tmp_path, block):
    """Controls: a brace in a string, comment or HTML label, or a subgraph's own brace, is not the
    end of the body."""
    skill = make_skill(tmp_path, "inner", [block])
    proc = run(skill, "--combine")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert node_count(skill / "diagrams" / "inner_combined.svg") == 2
