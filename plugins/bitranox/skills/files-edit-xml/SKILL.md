---
name: files-edit-xml
description: Use when creating, generating, editing, or validating an XML file - app config, pfSense config.xml, pom.xml/build config, SVG, RSS, SOAP, .NET/Java config - especially when modifying an existing document or producing one programmatically. Use instead of hand-typing XML or editing it with sed/regex/string concatenation.
---

# Edit XML with a Python library, never by hand

## Overview

Build and edit XML by parsing into an element tree, modifying the tree, then serializing - and
re-parse to confirm it is well-formed. Editing XML as raw text (`sed`, regex, f-strings) breaks on
namespaces, attribute escaping, CDATA, and entity quoting, and silently produces malformed or
wrong-structured documents. A library serialization is well-formed by construction; re-parsing
verifies it.

## Library

- **`lxml`** (`from lxml import etree`) - fast C parser, full XPath, namespaces, pretty-print, and
  DTD/XML-Schema/RelaxNG validation. `pip install lxml`. Preferred over stdlib
  `xml.etree.ElementTree` (weaker XPath, no schema validation) and over `minidom`/`xmltodict`.

See **bitranox:coding-python-use-modern-libraries** for the wider list. Reach for the structured editors
for the other formats too: **bitranox:files-edit-json**, **bitranox:files-edit-toml**, **bitranox:files-edit-yml**.

**Safety:** for XML from an untrusted source, disable entity expansion and network access to avoid
XXE / billion-laughs: `etree.XMLParser(resolve_entities=False, no_network=True, dtd_validation=False)`.

## Pattern: parse -> edit the tree -> serialize -> re-parse to validate

```python
from lxml import etree

parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
tree = etree.parse("config.xml", parser)      # parse into an element tree
root = tree.getroot()

# edit via XPath: append a host override under <unbound>
unbound = root.find("unbound")
hosts = etree.SubElement(unbound, "hosts")
for tag, text in (("host", "media"), ("domain", "example.com"), ("ip", "192.0.2.10")):
    etree.SubElement(hosts, tag).text = text

xml_bytes = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="UTF-8")
with open("config.xml", "wb") as f:
    f.write(xml_bytes)

# validate: re-parse the output (raises XMLSyntaxError if malformed)
etree.fromstring(xml_bytes)
```

For a quick well-formedness check without editing:
`python3 -c "import sys; from lxml import etree; etree.parse(sys.argv[1]); print('ok')" config.xml`
For schema validation: `etree.XMLSchema(etree.parse('schema.xsd')).assertValid(tree)`.

## Editing a file you must DIFF: prove the round-trip first

The pattern above guarantees the output is WELL-FORMED. It says nothing about the output being
MINIMAL, and on an existing file it will not be: an lxml round-trip rewrites the whole document in
lxml's style, so a two-value edit lands in a diff thousands of lines long. Measured on a pfSense
`config.xml`: **6863 changed lines, of which 6 were intended.** On a production config that diff
cannot be reviewed, so a real mistake hides in it and the change gets approved anyway.

Three losses account for most of it, and none is a bug - each is lxml choosing a legal equivalent:

| What you wrote   | What comes back | Fix                                             |
|------------------|-----------------|-------------------------------------------------|
| `<tag></tag>`    | `<tag/>`        | restore the empty-tag form after serializing    |
| CDATA in `.text` | escaped text    | assign `etree.CDATA(value)`, not a plain string |
| `&quot;` in text | a bare `"`      | re-escape when the document uses that form      |

So when the file is one you will DIFF - a firewall, app or CI config someone reviews - do not edit
first. **Prove the transform is byte-identical on the UNTOUCHED file, then edit:**

```python
original = path.read_bytes()
tree = etree.parse(io.BytesIO(original), parser)
assert serialize(tree) == original, "round-trip is lossy - fix the serializer before editing"
```

`serialize()` is your normalizing writer: it restores the empty-tag form, re-escapes what the
document escaped, and keeps the original XML declaration verbatim. Until that assertion passes, any
diff you produce is unreadable. Once it passes, the diff shows exactly your change and nothing else.

The same discipline applies to any format with more than one legal spelling - JSON key order and
indentation, YAML quoting and flow style. The test is always the same: round-trip the untouched
file and require zero diff.

## Common mistakes

| Mistake                                              | Do instead                                                  |
|------------------------------------------------------|-------------------------------------------------------------|
| `sed`/regex/f-strings to change a value or add a tag | `parse` -> edit the tree -> `tostring`                      |
| Building XML by string concatenation                 | `etree.SubElement` / set `.text`, `.attrib`                 |
| Ignoring namespaces (find fails silently)            | Use the namespace map: `root.find("ns:tag", nsmap)`         |
| Manually escaping `&`, `<`, quotes                   | The serializer escapes correctly; never do it by hand       |
| Parsing untrusted XML with defaults                  | Disable entities: `resolve_entities=False, no_network=True` |
| Committing/deploying without re-parsing              | Re-parse the serialized bytes before you ship it            |
