#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit|NotebookEdit) validator for JSON / YAML / XML files.

The files-edit-json / files-edit-yml / files-edit-xml skills teach the model to round-trip these
formats through a library so the result is valid by construction. This hook is the
deterministic safety net that does not depend on the model following the skill: it
parses the file the model just wrote and, if it does not parse, exits 2 so the
parse error is fed back to the model, which then corrects it.

Why PostToolUse and not PreToolUse: a Write carries the whole file, but an Edit /
MultiEdit only carries a fragment - you cannot judge whole-file validity from a
fragment. PostToolUse reads the finished file from disk, so it validates the same
way regardless of how the edit was produced (Write, Edit, MultiEdit, NotebookEdit,
or several edits in a row). NotebookEdit names its target in notebook_path rather
than file_path, and a .ipynb notebook is JSON, so it is validated as JSON. The bad
bytes briefly touch disk; the exit-2 feedback loop makes the model fix them
immediately.

It validates *provenance-blind* (it cannot tell library output from hand-typed
output - both are byte-identical when valid), so it only ever judges *validity*,
never *method*. That is exactly why it never fights a legitimate edit.

False-block avoidance is the priority - a noisy gate gets disabled. So it SKIPS
(exit 0) rather than blocks whenever it cannot be certain the file is meant to be
strict data:
  - templates (Helm / Jinja / Go / ERB markers {{ }}, {% %}, <% %>) are not data;
    a marker inside a quoted value (a JSON string, a quoted or block YAML scalar, an
    XML attribute value) is data and does not count, unless a quote inside the
    template expression cut that value short;
  - JSONC (tsconfig, .vscode/*, files with // or /* */ comments outside string
    literals) is parsed with a JSON5 reader if one is installed, and skipped if
    none is;
  - an XML document the hardened fallback parser refuses on security grounds
    (an entity declaration, when lxml is absent) is skipped, not blocked;
  - empty / whitespace-only files (intentional stubs);
  - the validating library not being installed (cannot validate -> do not block);
  - multi-document YAML is handled (safe_load_all), so k8s/--- manifests pass.

Pure standard library at import time; format libraries are imported lazily and a
missing one degrades to skip. Reads the PostToolUse event JSON on stdin. Exit 2
blocks (feeds stderr to the model); every other path - including any internal
error - exits 0, so a broken validator never wedges a turn.
"""
import bisect
import json
import os
import re
import sys

# Template markers: a file carrying these is a template, not strict data. ${VAR}
# (shell/compose interpolation) is deliberately NOT here - it is valid in a string.
# A template is not strict data, so this hook stays out of its way. But `{{` opens a Jinja/Helm
# tag AND is how an Edit most often breaks a JSON file - by doubling its opening brace - so the
# bare digraph skipped exactly the corruption this hook exists to catch. What follows a doubled
# JSON brace is another brace or an object KEY (a string, then a colon), possibly after a newline
# and indentation; a template expression is neither, so only that shape is excluded. A bare
# "a string follows" rule would also exclude `{{ "x" | quote }}`, a real Helm/Jinja expression.
TEMPLATE_RX = re.compile(r"\{\{(?!\s*(?:\{|\"(?:[^\"\\\r\n]|\\.)*\"\s*:))|\{%|<%")

# After a JSON string closes, only these may follow it (plus whitespace or end of text). A string
# holding a template marker and followed by anything else was cut short by a quote INSIDE a
# template expression ("{{ "x" | upper }}"), so the file is a template, not broken data.
_AFTER_JSON_STRING = frozenset(":,}]")

JSON_EXTS = (".json", ".ipynb")
YAML_EXTS = (".yml", ".yaml")
XML_EXTS = (".xml", ".svg", ".xsd", ".xsl", ".rss", ".wsdl", ".pom")

# Skill names to point the model at in the remediation message.
SKILL = {"json": "bitranox:files-edit-json", "yaml": "bitranox:files-edit-yml", "xml": "bitranox:files-edit-xml"}


def json_segments(text: str):
    """Split JSON text into (is_string, segment) runs, honouring backslash escapes.

    A string also ends at a line break: JSON forbids a raw newline inside one, so ending
    there re-synchronises the scan after an unterminated string in a broken file instead
    of treating the rest of the file as string content.
    """
    segments = []
    start, i, n = 0, 0, len(text)
    while i < n:
        if text[i] != '"':
            i += 1
            continue
        if i > start:
            segments.append((False, text[start:i]))
        j = i + 1
        while j < n and text[j] not in '"\r\n':
            j += 2 if text[j] == "\\" else 1
        end = min(j + 1, n) if j < n and text[j] == '"' else min(j, n)
        segments.append((True, text[i:end]))
        start = i = end
    if start < n:
        segments.append((False, text[start:]))
    return segments


def json_has_comment(text: str) -> bool:
    """True if a // or /* appears outside every string literal (a URL or glob is not a comment)."""
    return any(not is_str and ("//" in seg or "/*" in seg) for is_str, seg in json_segments(text))


def json_is_template(text: str) -> bool:
    """True if a template marker sits where JSON data would be, not inside a string value.

    A placeholder such as "{{VALUE}}" inside a string is ordinary data, so it must not exempt
    the file around it from validation.
    """
    segments = json_segments(text)
    # Match against the WHOLE text so the lookahead can see a key that follows `{{` in the next
    # segment, then judge each hit by the segment it starts in.
    starts, offset = [], 0
    for _, seg in segments:
        starts.append(offset)
        offset += len(seg)
    for match in TEMPLATE_RX.finditer(text):
        idx = bisect.bisect_right(starts, match.start()) - 1
        if not segments[idx][0] or _string_cut_by_template(segments, idx):
            return True
    return False


def _string_cut_by_template(segments, idx: int) -> bool:
    for is_str, seg in segments[idx + 1 : idx + 3]:
        if is_str:
            # Two strings with no separator between: JSON never does that, a quote inside a
            # template expression does.
            return True
        head = seg.lstrip()
        if head:
            return head[0] not in _AFTER_JSON_STRING
    return False  # the string ends the text


def looks_jsonc(path: str, text: str) -> bool:
    """True if this .json is plausibly JSONC (comments / trailing commas expected)."""
    base = os.path.basename(path).lower()
    norm = path.replace("\\", "/").lower()
    if "/.vscode/" in norm:
        return True
    if base.startswith("tsconfig.") or base in ("tsconfig.json", "jsconfig.json", "devcontainer.json"):
        return True
    if base.endswith(".code-workspace"):
        return True
    # Generic signal: a // or /* */ comment outside the JSON grammar.
    return json_has_comment(text)


def try_json5(text: str):
    """(True, None) parses, (False, msg) real error, (None, None) no JSON5 reader."""
    for mod in ("pyjson5", "json5"):
        try:
            reader = __import__(mod)
        except ImportError:
            continue
        try:
            (reader.loads if hasattr(reader, "loads") else reader.decode)(text)
            return True, None
        except Exception as exc:  # noqa: BLE001 - any parse failure is a real error
            return False, str(exc)
    return None, None


def validate_json(path: str, text: str):
    try:
        json.loads(text)
        return True, None
    except Exception as exc:  # noqa: BLE001
        if looks_jsonc(path, text):
            ok, msg = try_json5(text)
            if ok is True:
                return True, None
            if ok is None:
                return None, None  # JSONC but no JSON5 reader installed -> skip
            return False, msg  # JSON5 reader also rejected it -> real error
        return False, str(exc)


def validate_yaml(path: str, text: str):
    try:
        import yaml  # PyYAML
    except ImportError:
        try:
            from ruamel.yaml import YAML  # safe round-trip fallback
        except ImportError:
            return None, None  # no YAML library -> skip
        try:
            list(YAML(typ="safe").load_all(text))
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
    try:
        list(yaml.safe_load_all(text))  # safe_load_all: tolerate multi-doc (---) files
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def validate_xml(path: str, text: str):
    data = text.encode("utf-8")  # bytes: avoids "unicode string with encoding decl" errors
    # Preferred: lxml, parser hardened so validation itself cannot be an XXE /
    # billion-laughs vector (no entity resolution, no network fetch).
    try:
        from lxml import etree

        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        try:
            etree.fromstring(data, parser)
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
    except ImportError:
        pass
    # Fallback: defusedxml, which hardens stdlib parsing against XXE and the
    # billion-laughs entity-expansion bomb that bare xml.etree is vulnerable to.
    try:
        from defusedxml import DTDForbidden, EntitiesForbidden, ExternalReferenceForbidden
        from defusedxml.ElementTree import fromstring as defused_fromstring
    except ImportError:
        return None, None  # no safe XML parser installed -> skip (never parse unsafely)
    try:
        defused_fromstring(data)
        return True, None
    except (DTDForbidden, EntitiesForbidden, ExternalReferenceForbidden):
        # A security refusal, not a syntax verdict: the document may be well-formed (lxml,
        # which parses it without expanding entities, accepts it). Unable to judge -> skip.
        return None, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def classify(path: str):
    lower = path.lower()
    if lower.endswith(JSON_EXTS):
        return "json", validate_json
    if lower.endswith(YAML_EXTS):
        return "yaml", validate_yaml
    if lower.endswith(XML_EXTS):
        return "xml", validate_xml
    return None, None


# After a quoted YAML scalar closes, only these may follow it on its line (plus spaces or the end
# of the text). Anything else means a quote INSIDE a template expression cut it short
# (`"{{ include "x" . }}"`), so the file is a template.
_AFTER_YAML_STRING = frozenset(":,]}#\r\n")

# The styles of a YAML scalar whose content is opaque text: double- and single-quoted, literal
# and folded block. A marker inside one is a value, not structure.
_YAML_DATA_STYLES = frozenset({'"', "'", "|", ">"})


def _yaml_data_spans(yaml, text: str):
    """[(start, end)] of the quoted and block scalars the scanner reached before any error."""
    spans = []
    try:
        for token in yaml.scan(text, Loader=yaml.SafeLoader):
            if not isinstance(token, yaml.ScalarToken) or token.style not in _YAML_DATA_STYLES:
                continue
            start, end = token.start_mark.index, token.end_mark.index
            if token.style in ('"', "'"):
                rest = text[end:].lstrip(" \t")
                if rest and rest[0] not in _AFTER_YAML_STRING:
                    continue  # cut short by a template quote: not a clean value
            spans.append((start, end))
    except yaml.YAMLError:
        pass  # markers past the error stay unclassified, so they still read as a template
    return spans


def yaml_is_template(text: str) -> bool:
    """True if a template marker sits anywhere but inside a clean quoted or block scalar.

    A marker the scanner never reached (behind a scan error) counts as a template, as does every
    marker when PyYAML is absent: unable to tell, the hook stays out of the way.
    """
    try:
        import yaml  # PyYAML; optional, like every format library here
    except ImportError:
        return bool(TEMPLATE_RX.search(text))
    spans = _yaml_data_spans(yaml, text)
    return any(not any(s <= m.start() < e for s, e in spans) for m in TEMPLATE_RX.finditer(text))


# An XML start or empty-element tag whose attribute values are all well-formed quotes, and one
# attribute value inside it. `<` is illegal in an attribute value, so a value holding one is not
# matched and its marker stays a template marker - which also keeps `<% %>` a template always.
_XML_TAG = re.compile(r"""<[A-Za-z_][\w:.-]*(?:\s+[\w:.-]+\s*=\s*(?:"[^"<]*"|'[^'<]*'))*\s*/?>""")
_XML_VALUE = re.compile(r"""=\s*("[^"<]*"|'[^'<]*')""")


def xml_is_template(text: str) -> bool:
    """True if a template marker sits anywhere but inside a well-formed attribute value.

    A marker in element text (`{% for %}` between elements) is template structure; one in a
    quoted attribute value is a value. A value cut short by a quote inside a template expression
    (`href="{{ "x" }}"`) does not form a well-formed tag, so its marker is not exempted.
    """
    spans = []
    for tag in _XML_TAG.finditer(text):
        for value in _XML_VALUE.finditer(tag.group(0)):
            spans.append((tag.start() + value.start(1), tag.start() + value.end(1)))
    return any(not any(s <= m.start() < e for s, e in spans) for m in TEMPLATE_RX.finditer(text))


def is_template(kind: str, text: str) -> bool:
    # A marker inside a quoted value is data in every format here, so each format tells a value
    # from structure with its own quoting rules.
    if kind == "json":
        return json_is_template(text)
    if kind == "yaml":
        return yaml_is_template(text)
    return xml_is_template(text)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    tool_input = event.get("tool_input") or {}
    # NotebookEdit names its target notebook_path; every other matched tool uses file_path.
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path:
        return 0

    kind, validator = classify(path)
    if kind is None:
        return 0

    try:
        # utf-8-sig: a byte-order mark is legal at the start of a UTF-8 file and says nothing
        # about validity; plain utf-8 hands it to json.loads, which rejects it.
        with open(path, "r", encoding="utf-8-sig") as fh:
            text = fh.read()
    except Exception:  # noqa: BLE001 - unreadable/binary/gone -> nothing to validate
        return 0

    if not text.strip():
        return 0  # empty / whitespace-only stub: intentional, not the failure class we guard
    if is_template(kind, text):
        return 0  # Helm / Jinja / Go / ERB template: not strict data

    result, detail = validator(path, text)
    if result is None or result is True:
        return 0  # skipped (cannot validate) or valid

    skill = SKILL[kind]
    label = {"json": "JSON", "yaml": "YAML", "xml": "XML"}[kind]
    msg = [
        f"BLOCKED: {os.path.basename(path)} is not valid {label} after this edit.",
        f"  {detail}",
        "",
        f"The file on disk no longer parses. Fix it, then re-validate. Use the {skill}",
        "skill: load the file into a data structure, make the change there, dump it back,",
        "and re-load to confirm it parses - never patch the raw text with sed/regex.",
    ]
    print("\n".join(msg), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken validator must never wedge a turn
        sys.exit(0)
