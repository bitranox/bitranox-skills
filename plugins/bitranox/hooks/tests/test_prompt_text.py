"""Tests for prompt_text.py - what of a prompt a keyword matcher may score. ASCII."""

import prompt_text as P

# The measured envelope, in the shape the transcripts actually store (nested child elements, not
# attributes): its output-file path carried `claude`, `code` and `bitranox`, which is how 11 skills
# reached a 2-keyword threshold on a machine status line.
NOTIFICATION = (
    "<task-notification>\n"
    "<task-id>b6bgpwg53</task-id>\n"
    "<tool-use-id>toolu_01ABCdefGHIjklMNOpqrs</tool-use-id>\n"
    "<output-file>/tmp/claude-1000/-media-srv-main-softdev-bitranox-systems-openvmm/tasks/"
    "b6bgpwg53.output</output-file>\n"
    "<status>failed</status>\n"
    "<summary>preflight did not pass</summary>\n"
    "</task-notification>"
)


# ---- a whole machine-generated turn --------------------------------------------------------------

def test_a_machine_turn_is_not_typed_by_a_person():
    for text in ("<task-notification id=\"1\">done</task-notification>",
                 "<command-name>/clear</command-name>",
                 "<local-command-stdout>ok</local-command-stdout>",
                 "Another Claude session sent a message: look at this",
                 "<teammate-message>ping</teammate-message>"):
        assert not P.typed_by_a_person(text), text


def test_leading_whitespace_does_not_disguise_a_machine_turn():
    assert not P.typed_by_a_person("\n  <task-notification>done</task-notification>")


def test_a_real_prompt_is_typed_by_a_person():
    for text in ("run make test", "why does the router fire on a notification?",
                 "<thinking> is what I want to talk about"):
        assert P.typed_by_a_person(text), text


# ---- what is not prose, inside a prompt that IS typed --------------------------------------------

def test_prose_drops_a_path_s_directories_and_stem_and_keeps_its_file_type():
    # A path contributes its EXTENSION and nothing else. Measured over 3,483 typed prompts: the
    # directory segments are what carry project and tool names (the defect), the stem carries a
    # branch name or a scratch script (noise), and the extension is the file TYPE - which is what
    # the files-edit-* skills trigger on and what a request naming a file is usually about.
    # Dropping the whole path was the one real loss in the corpus replay: a prompt about
    # `src/bose_zonemaster/defaultconfig.toml` stopped reaching `files-edit-toml`.
    text = "look at /tmp/claude-1000/-media-srv-main-softdev-bitranox-systems-x/tasks/a.output"
    got = P.prose(text).lower()
    assert "look at" in got
    for word in ("claude", "bitranox", "tmp", "media", "softdev", "tasks"):
        assert word not in got, word
    assert "output" in got                      # the file type survives


def test_prose_keeps_the_file_type_a_request_names():
    got = P.prose("edit src/bose_zonemaster/defaultconfig.toml and split it by scope").lower()
    assert "toml" in got
    for word in ("src", "bose_zonemaster", "defaultconfig"):
        assert word not in got, word


def test_prose_gives_an_extensionless_path_nothing_to_contribute():
    # a git ref and a device node have no file type, so they contribute no token at all
    for text, gone in (("git update-ref refs/heads/fix/ragged-table-path-windows abc",
                        ("refs", "heads", "ragged")),
                       ("dd of=/dev/zvol/zpool-nvme/vm-63001-disk-0", ("zvol", "zpool", "nvme"))):
        got = P.prose(text).lower()
        for word in gone:
            assert word not in got, (text, word)


def test_prose_drops_a_relative_path_and_a_windows_path():
    got = P.prose("edit plugins/bitranox/hooks/skill-router.py and C:\\Users\\srvadmin\\code.txt")
    low = got.lower()
    assert "edit" in low and "and" in low
    for word in ("bitranox", "hooks", "router", "users", "srvadmin", "code"):
        assert word not in low, word
    assert " py" in " " + low and "txt" in low   # both file types survive


def test_prose_keeps_a_word_pair_that_merely_contains_a_slash():
    for text in ("and/or", "yes/no", "it runs 24/7"):
        assert P.prose(text) == text


def test_prose_drops_tag_markup_and_keeps_what_is_between_the_tags():
    got = P.prose("<system-reminder priority=\"high\">the deploy failed</system-reminder>")
    assert "the deploy failed" in got
    for word in ("system", "reminder", "priority", "high"):
        assert word not in got.lower(), word


def test_prose_drops_ids_hashes_and_slugs():
    text = ("session c68c2741-194f-44b7-9e52-11c2e5fd87b4 tool toolu_01ABCdefGHIjklMNO "
            "commit 5daaabe1f2c3d4e5a6b7c8d90123456789abcdef key "
            "-media-srv-main-softdev-projects-public failed")
    got = P.prose(text).lower()
    assert "session" in got and "commit" in got and "failed" in got
    for junk in ("c68c2741", "toolu", "5daaabe1f2c3d4e5a6b7c8d90123456789abcdef",
                 "softdev", "projects"):
        assert junk not in got, junk


def test_prose_keeps_the_identifiers_a_trigger_map_is_built_from():
    # These ARE keywords in skill_triggers.json (infra-windows-servicing, coding-rust and
    # friends): an over-eager id filter would silence the skills a user in trouble types for.
    for tok in ("0xc1900200", "setup.exe", "windows.old", "utf-8", "non-constant-time", "0x7b"):
        assert tok in P.prose("it failed with %s on the reboot" % tok), tok


def test_prose_leaves_ordinary_prose_untouched():
    text = "the zpool scrub reported checksum errors on two disks"
    assert P.prose(text) == text


# ---- the two answers compose ---------------------------------------------------------------------

def test_scorable_prose_is_empty_for_a_machine_turn():
    assert P.scorable_prose(NOTIFICATION) == ""


def test_scorable_prose_is_the_stripped_prose_of_a_typed_prompt():
    got = P.scorable_prose("fix /tmp/claude-1000/x/tasks/a.output please").lower()
    assert "fix" in got and "please" in got and "claude" not in got


def test_scorable_prose_survives_none_and_empty():
    assert P.scorable_prose(None) == "" and P.scorable_prose("") == ""


# ---- a notification's OWN fields, for the classifier shadow ---------------------------------------
# A machine turn scores no keywords, but it is still an event worth routing: a background task that
# just FAILED may well need a skill. So the shadow gets the envelope's own fields instead of the
# envelope as a pretend prompt - and deliberately not its ids or its output-file path, which is
# what made it match eleven skills in the first place.

def test_notification_fields_are_its_status_and_summary():
    assert P.notification_fields(NOTIFICATION) == {
        "task_status": "failed", "task_summary": "preflight did not pass"}


def test_notification_fields_leave_out_the_ids_and_the_output_path():
    flat = " ".join(P.notification_fields(NOTIFICATION).values())
    for junk in ("toolu", "b6bgpwg53", "/tmp", "claude-1000", ".output"):
        assert junk not in flat, junk


def test_notification_fields_read_the_stored_element_shape():
    # the exact shape from the corpus: nested child elements, one per line
    text = ("<task-notification>\n<task-id>bo23dn57j</task-id>\n"
            "<tool-use-id>toolu_01GQEKg2QdL2Hnf6oiXXaX1e</tool-use-id>\n"
            "<output-file>/tmp/claude-1000/-media-srv-main-softdev/tasks/bo23dn57j.output"
            "</output-file>\n<status>completed</status>\n"
            "<summary>Background command \"Run the repo CI-parity gate\" completed</summary>\n"
            "</task-notification>")
    assert P.notification_fields(text) == {
        "task_status": "completed",
        "task_summary": "Background command \"Run the repo CI-parity gate\" completed"}


def test_notification_fields_keep_a_multi_line_summary():
    text = "<task-notification>\n<status>failed</status>\n<summary>line one\nline two</summary>\n"
    assert P.notification_fields(text)["task_summary"] == "line one line two"


def test_notification_fields_are_empty_for_anything_else():
    for text in ("run make test", "<command-name>/clear</command-name>",
                 "<task-notification>\n<task-id>x</task-id>\n</task-notification>", "", None):
        assert P.notification_fields(text) == {}, text


# ---- harness turns that no PREFIX can match ---------------------------------------------------
# Measured over the corpus: of 1,409 turns this module called typed, 112 (7.9%) were the harness
# talking - 82 interruption notices, 16 opening with a tag the prefix tuple does not list, and 14
# beginning with a COUNT, which a prefix tuple structurally cannot match. Each one is scored by
# the keyword matcher and costs a Jev request, and each spends a skill's once-per-session nudge.


def test_an_interruption_notice_is_not_something_a_person_typed():
    assert not P.typed_by_a_person("[Request interrupted by user for tool use]")
    assert not P.typed_by_a_person("[Request interrupted by user]")


def test_a_turn_opening_with_a_COUNT_is_not_something_a_person_typed():
    # The shape rank 115 records: it starts with a number, so no prefix tuple can reach it.
    assert not P.typed_by_a_person(
        '5 background agents were stopped by the user: "You are authoring ONE test case"')
    assert not P.typed_by_a_person("1 background agent was stopped by the user: \"x\"")


def test_the_shell_escape_and_its_output_are_not_prose_for_a_router():
    assert not P.typed_by_a_person("<bash-input>git status</bash-input>")
    assert not P.typed_by_a_person("<bash-stdout>On branch master</bash-stdout>")


def test_pasted_content_IS_the_person_and_must_stay_scored():
    # The opposite verdict from its neighbours above, and the reason no blanket "starts with a
    # tag" rule may be written: a person pasting a question wraps it in exactly this.
    assert P.typed_by_a_person('<pasted_content id="190a">what can we improve?</pasted_content>')


def test_a_person_writing_about_those_shapes_is_still_a_person():
    # The negative direction, which is the one a widened matcher breaks: these must stay typed.
    for text in ("why was my request interrupted by user for tool use?",
                 "3 agents finished, please review what they found",
                 "the [Request interrupted] banner keeps appearing, can we suppress it",
                 "run make test"):
        assert P.typed_by_a_person(text), text
