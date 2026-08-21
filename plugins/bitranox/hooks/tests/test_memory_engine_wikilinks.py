"""Tests for memory_engine.dangling_wikilinks - write-time [[ref]] validation. ASCII only."""
import memory_engine as ME


def test_flags_missing_target_and_suggests_closest():
    out = ME.dangling_wikilinks("see [[foo-bar]] and [[real-slug]] here", {"real-slug", "foo-baz"})
    assert ("foo-bar", "foo-baz") in out            # missing slug + closest existing suggestion
    assert all(t != "real-slug" for t, _ in out)    # an EXISTING slug is not flagged


def test_none_when_all_targets_exist():
    assert ME.dangling_wikilinks("[[a]] and [[b]]", {"a", "b"}) == []


def test_no_suggestion_when_nothing_close():
    assert ME.dangling_wikilinks("[[zzz-nothing-like-it]]", {"a", "b"}) == [("zzz-nothing-like-it", None)]


def test_deduplicates_repeated_missing_target():
    assert ME.dangling_wikilinks("[[gone]] ... [[gone]] again", set()) == [("gone", None)]


# ---- quoted syntax is not a reference -----------------------------------------------------------
# A fact that TEACHES a config format has to quote it, and several formats spell a construct with
# double square brackets - TOML's array-of-tables `[[tool.importlinter.contracts]]` is the one that
# hit the store. Read as a wikilink it becomes a ref to a fact that will never exist, so the fact
# reports as an orphan ref forever and the only way out is to reword what it teaches.

def test_mask_code_regions_blanks_an_inline_span_and_keeps_length():
    text = "prose `[[toml.table]]` prose"
    masked = ME.mask_code_regions(text)
    assert len(masked) == len(text)                  # offsets stay usable against the raw text
    assert "[[toml.table]]" not in masked
    assert masked.startswith("prose `") and masked.endswith("` prose")


def test_mask_code_regions_blanks_a_fenced_block():
    text = "before\n```toml\n[[tool.importlinter.contracts]]\n```\nafter [[real-ref]]\n"
    masked = ME.mask_code_regions(text)
    assert "tool.importlinter.contracts" not in masked
    assert "[[real-ref]]" in masked                  # prose after the block still counts
    assert masked.count("\n") == text.count("\n")    # line structure preserved


def test_mask_code_regions_leaves_prose_untouched():
    text = "see [[a-fact]] and [[b-fact]]\n"
    assert ME.mask_code_regions(text) == text


def test_mask_code_regions_leaves_an_unmatched_backtick_run_literal():
    # CommonMark: a backtick run with no matching closer is literal text, so it opens nothing and
    # must not swallow the rest of the line.
    text = "a ` stray tick then [[real-ref]]"
    assert "[[real-ref]]" in ME.mask_code_regions(text)


def test_dangling_wikilinks_ignores_a_ref_inside_an_inline_code_span():
    out = ME.dangling_wikilinks("declare it as `[[tool.importlinter.contracts]]` in pyproject", set())
    assert out == []


def test_dangling_wikilinks_ignores_a_ref_inside_a_fenced_block():
    text = "how to write it:\n\n```toml\n[[tool.importlinter.contracts]]\n```\n"
    assert ME.dangling_wikilinks(text, set()) == []


def test_dangling_wikilinks_still_flags_a_real_ref_beside_a_code_span():
    # the masking must not blind the check on a line that legitimately does both
    out = ME.dangling_wikilinks("`[[quoted]]` but see [[missing-fact]]", set())
    assert out == [("missing-fact", None)]


def test_retarget_refs_does_not_rewrite_inside_a_code_span():
    text = "rename me [[old-slug]] but not `[[old-slug]]`"
    got = ME._retarget_refs(text, "old-slug", "new-slug")
    assert got == "rename me [[new-slug]] but not `[[old-slug]]`"


def test_mask_code_regions_does_not_open_a_fence_on_a_line_of_inline_spans():
    # CommonMark: a BACKTICK fence's info string may not contain a backtick. A prose line that
    # merely BEGINS with an inline span is therefore not an opener - reading it as one opens a
    # block that never closes and blanks the rest of the fact, taking every real ref with it.
    # Found by replaying the live store, where all the unit tests above were already green.
    text = "```text, ```bash) or use ```rust,ignore for snippets\nlater prose cites [[real-ref]].\n"
    assert "[[real-ref]]" in ME.mask_code_regions(text)


def test_mask_code_regions_still_opens_a_fence_on_a_plain_info_string():
    text = "```toml\n[[tool.importlinter.contracts]]\n```\nprose [[real-ref]]\n"
    masked = ME.mask_code_regions(text)
    assert "tool.importlinter.contracts" not in masked and "[[real-ref]]" in masked


def test_mask_code_regions_allows_a_backtick_in_a_tilde_fence_info_string():
    # only backtick fences carry the restriction; a tilde fence's info string is unconstrained
    text = "~~~`odd`\n[[quoted.syntax]]\n~~~\nprose [[real-ref]]\n"
    masked = ME.mask_code_regions(text)
    assert "quoted.syntax" not in masked and "[[real-ref]]" in masked
