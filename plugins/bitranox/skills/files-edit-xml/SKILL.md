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

See **bitranox:coding-python-use-modern-libraries** for the wider list.

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
host = etree.SubElement(unbound, "hosts")
for tag, text in (("host", "media"), ("domain", "example.com"), ("ip", "192.0.2.10")):
    etree.SubElement(host, tag).text = text

xml_bytes = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="UTF-8")
with open("config.xml", "wb") as f:
    f.write(xml_bytes)

# validate: re-parse the output (raises XMLSyntaxError if malformed)
etree.fromstring(xml_bytes)
```

For a quick well-formedness check without editing:
`python3 -c "import sys; from lxml import etree; etree.parse(sys.argv[1]); print('ok')" config.xml`
For schema validation: `etree.XMLSchema(etree.parse('schema.xsd')).assertValid(tree)`.

## Common mistakes

| Mistake                                              | Do instead                                                  |
|------------------------------------------------------|-------------------------------------------------------------|
| `sed`/regex/f-strings to change a value or add a tag | `parse` -> edit the tree -> `tostring`                      |
| Building XML by string concatenation                 | `etree.SubElement` / set `.text`, `.attrib`                 |
| Ignoring namespaces (find fails silently)            | Use the namespace map: `root.find("ns:tag", nsmap)`         |
| Manually escaping `&`, `<`, quotes                   | The serializer escapes correctly; never do it by hand       |
| Parsing untrusted XML with defaults                  | Disable entities: `resolve_entities=False, no_network=True` |
| Committing/deploying without re-parsing              | Re-parse the serialized bytes before you ship it            |
