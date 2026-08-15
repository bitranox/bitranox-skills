# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest"]
# ///
"""Prove srccount's safety tests are not vacuous, by breaking the code and requiring them to fail.

Why this exists as a FILE rather than a claim: "mutation-checked" in a commit message is
unverifiable by the next reader. Twice in one session a mutation run disproved something already
written into a comment - all three fail-open tests reaching one branch (they reach two), and a
fixture helper quietly repairing eight tests. A run anyone can repeat is the difference between
evidence and assertion.

Each mutant states the tests it MUST kill, and the check requires an EXACT match: a mutant that
kills fewer means a test is vacuous, one that kills more means coverage moved and the expectation
needs deciding rather than drifting.

`except-OSError-reraise` deliberately does NOT list the denied-by-permissions test, which skips
when euid is 0. Coverage of that arm must not depend on a test that can silently vanish, so the
harness runs with it deselected and still requires the arm to be covered.

SCOPE, so the name does not overclaim. Eight mutants cover the content-marker validators, the
exact-name list, the glob shapes, subtree propagation, the default extension set and the
no-source exit gate. NOT yet mutated: the audit's three sections individually, --top, --exclude,
the render/table formatting and the JSON envelope shape - tests for those exist but have not been
shown to fail against a deliberate break. Add a mutant before claiming they have.

Run: `uv run tests/mutation_check.py`   (exit 0 = every mutant killed exactly its tests)
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "scripts" / "srccount.py"
# Copied explicitly, never the whole dir: copying tests/ wholesale would include THIS file and
# the sub-run would recurse into another mutation check.
TEST_FILES = ("conftest.py", "test_srccount.py")

# A test that skips rather than runs would satisfy any expectation, so it is excluded from the
# run entirely and the mutants must be killed without it.
SKIPPABLE = "test_a_marker_denied_by_permissions_leaves_the_tree_counted"


@dataclass(frozen=True)
class Mutant:
    """One deliberate break, and which tests must notice it.

    `mode` is per-mutant because exactness buys different things at different blast radii:

    * "exact" - the mutant is SURGICAL and its kill set is a deliberate, small claim, so a
      change either way is worth stopping for. Extra kills mean coverage moved and should be
      decided, not absorbed.
    * "at_least" - the mutant REMOVES A WHOLE MECHANISM, so any future test touching that area
      legitimately joins the set. Demanding exactness there would turn ordinary test-writing
      into a harness edit, and a check with that much friction is one that gets deleted. Extras
      are still REPORTED, just not failed on; a shortfall still fails, which is the signal that
      actually matters (a test went vacuous).
    """

    name: str
    find: str
    replace: str
    must_kill: frozenset[str]
    mode: str = "exact"


MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        name="except-OSError-reraise",
        find="    except OSError:\n        return False",
        replace="    except OSError:\n        raise",
        must_kill=frozenset({"test_validator_returns_false_on_an_unreadable_path"}),
    ),
    Mutant(
        name="cachedir-validator-always-accepts",
        find="        return path.read_bytes()[: len(_CACHEDIR_SIGNATURE)] == _CACHEDIR_SIGNATURE",
        replace="        return True",
        must_kill=frozenset({
            "test_a_cachedir_tag_without_the_signature_does_not_exclude",
            "test_an_unrecognised_marker_leaves_the_tree_counted",
            # this one asserts BOTH validators return False for a directory, and an
            # always-accepting _is_cachedir_tag returns True before the except arm is reached
            "test_validator_returns_false_on_an_unreadable_path",
        }),
    ),
    Mutant(
        name="pyvenv-validator-always-accepts",
        find='    return any(line.split("=", 1)[0].strip() == "home" for line in text.splitlines() if "=" in line)',
        replace="    return True",
        # NOT the direct-call test: for a directory read_text raises first, so the except arm
        # still returns False and that assertion holds. The asymmetry with the cachedir mutant
        # is real and is why each mutant states its own set.
        must_kill=frozenset({"test_a_pyvenv_cfg_without_the_home_key_does_not_exclude"}),
    ),
    Mutant(
        name="exact-names-dropped",
        find="EXCLUDED_EXACT: frozenset[str] = frozenset(EXCLUDED_REASONS)",
        replace="EXCLUDED_EXACT: frozenset[str] = frozenset()",
        must_kill=frozenset({
            "test_a_high_excluded_share_is_normal_and_exits_zero",
            "test_audit_content_only_is_empty_when_the_name_list_covers_it",
            "test_audit_does_not_flag_an_already_excluded_venv",
            "test_audit_exits_zero_when_nothing_is_content_proven",
            "test_audit_reports_a_member_that_matches_nothing",
            "test_cli_json_envelope",
            "test_counts_only_first_party_source",
            "test_every_excluded_name_carries_a_stated_reason",
            "test_every_venv_shape_is_recognised",
            "test_excluded_share_makes_the_inflation_visible",
            "test_extra_exclude_is_honoured",
            "test_reports_which_pattern_excluded_what",
            "test_several_extensions",
            "test_the_names_that_survived_are_the_ones_that_occur",
            "test_tool_written_generated_dirs_are_excluded",
        }),
        mode="at_least",
    ),
    Mutant(
        name="glob-shapes-dropped",
        find="EXCLUDED_GLOBS: tuple[str, ...] = tuple(EXCLUDED_GLOB_REASONS)",
        replace="EXCLUDED_GLOBS: tuple[str, ...] = ()",
        must_kill=frozenset({
            "test_a_high_excluded_share_is_normal_and_exits_zero",
            "test_cli_json_envelope",
            "test_counts_only_first_party_source",
            "test_every_venv_shape_is_recognised",
            "test_excluded_share_makes_the_inflation_visible",
            "test_extra_exclude_is_honoured",
            "test_several_extensions",
            "test_the_names_that_survived_are_the_ones_that_occur",
        }),
        mode="at_least",
    ),
    Mutant(
        name="content-exclusion-does-not-propagate",
        find="            content_excluded[dirpath] = reason\n        for name in filenames:",
        replace="            pass\n        for name in filenames:",
        must_kill=frozenset({
            "test_a_build_cache_is_excluded_by_content",
            "test_a_real_pyvenv_cfg_does_exclude",
            "test_a_venv_is_excluded_by_content_whatever_its_name",
            "test_content_exclusion_reaches_the_whole_subtree",
        }),
    ),
    Mutant(
        name="default-extensions-narrowed-to-py",
        find="        return list(DEFAULT_EXTENSIONS)",
        replace='        return [".py"]',
        must_kill=frozenset({
            "test_default_extensions_span_more_than_python",
            "test_default_set_members_are_executed_or_compiled",
        }),
    ),
    Mutant(
        name="no-source-exit-gate-inverted",
        find="    if not any(c.source for c in counts):",
        replace="    if any(c.source for c in counts):",
        must_kill=frozenset({
            "test_a_high_excluded_share_is_normal_and_exits_zero",
            "test_cli_json_envelope",
            "test_no_source_found_anywhere_exits_one",
            "test_one_empty_root_among_several_is_data_not_failure",
            "test_the_total_is_never_printed_without_its_decomposition",
        }),
        mode="at_least",
    ),
)

FAILED_RX = re.compile(r"^FAILED [^:]+::(\w+)", re.M)
# pytest always prints a counts line when it actually collected and ran something.
SUMMARY_RX = re.compile(r"\d+ (passed|failed|error)", re.M)


def run_mutant(mutant: Mutant, workdir: Path) -> set[str]:
    """Apply one mutant in an isolated copy and return the set of test names that failed."""
    source = TOOL.read_text(encoding="utf-8")
    if mutant.find not in source:
        raise SystemExit(f"mutant '{mutant.name}' no longer applies - its anchor is gone from {TOOL.name}")
    (workdir / "scripts").mkdir(parents=True, exist_ok=True)
    (workdir / "tests").mkdir(parents=True, exist_ok=True)
    (workdir / "scripts" / TOOL.name).write_text(source.replace(mutant.find, mutant.replace), encoding="utf-8")
    for name in TEST_FILES:
        shutil.copy2(HERE / name, workdir / "tests" / name)
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "--tb=no", "-p", "no:cacheprovider",
         # nodeid form, NOT an absolute path: an absolute --deselect matches nothing and
         # silently leaves the skippable test in the run.
         "--deselect", f"tests/test_srccount.py::{SKIPPABLE}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=workdir,
    )
    report = done.stdout + done.stderr
    if not SUMMARY_RX.search(report):
        raise SystemExit(
            f"mutant '{mutant.name}': the sub-run never reported a test result, so a verdict of "
            f"VACUOUS would be this harness lying the way it exists to catch.\n"
            f"--- sub-run output ---\n{report[-2000:]}"
        )
    return set(FAILED_RX.findall(report))


def _run(mutant: Mutant) -> tuple[Mutant, set[str]]:
    with tempfile.TemporaryDirectory(prefix=f"mut-{mutant.name}-") as tmp:
        return mutant, run_mutant(mutant, Path(tmp))


def main() -> int:
    problems: list[str] = []
    # Each mutant is an independent pytest subprocess in its own temp copy, so they overlap
    # freely. Serial this cost 16s and tripled the suite; a check that slow is one that gets
    # run less, which costs more than it buys.
    with ThreadPoolExecutor(max_workers=min(8, len(MUTANTS))) as pool:
        results = dict(pool.map(_run, MUTANTS))
    for mutant in MUTANTS:
        killed = results[mutant]
        missing = mutant.must_kill - killed
        extra = killed - mutant.must_kill
        fails = bool(missing) or (bool(extra) and mutant.mode == "exact")
        print(f"[{'MISMATCH' if fails else 'ok'}] {mutant.name} ({mutant.mode}): killed {len(killed)}"
              + (f", {len(extra)} beyond the stated set" if extra and mutant.mode == "at_least" else ""))
        if missing:
            problems.append(f"{mutant.name}: VACUOUS - these did not notice the break: {sorted(missing)}")
        if extra and mutant.mode == "exact":
            problems.append(f"{mutant.name}: coverage moved - also killed {sorted(extra)}; decide, do not drift")
    for line in problems:
        print(f"  {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
