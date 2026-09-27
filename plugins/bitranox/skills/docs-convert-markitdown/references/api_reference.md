# MarkItDown API Reference

## Core Classes

### MarkItDown

The main class for converting files to Markdown.

```python
from markitdown import MarkItDown

md = MarkItDown(
    llm_client=None,
    llm_model=None,
    llm_prompt=None,
    docintel_endpoint=None,
    enable_plugins=False
)
```

#### Parameters

| Parameter           | Type          | Default | Description                                                           |
|---------------------|---------------|---------|-----------------------------------------------------------------------|
| `llm_client`        | OpenAI client | `None`  | OpenAI-compatible client for AI image descriptions                    |
| `llm_model`         | str           | `None`  | Model name (e.g., "anthropic/claude-opus-4.5") for image descriptions |
| `llm_prompt`        | str           | `None`  | Custom prompt for image description                                   |
| `docintel_endpoint` | str           | `None`  | Azure Document Intelligence endpoint                                  |
| `enable_plugins`    | bool          | `False` | Enable 3rd-party plugins                                              |

#### Methods

##### convert()

Convert a file to Markdown.

```python
result = md.convert(
    source,
    file_extension=None
)
```

**Parameters**:
- `source` (str): Path to the file to convert
- `file_extension` (str, optional): Override file extension detection

**Returns**: `DocumentConverterResult` object

**Example**:
```python
result = md.convert("document.pdf")
print(result.text_content)
```

##### convert_stream()

Convert from a file-like binary stream.

```python
result = md.convert_stream(
    stream,
    file_extension=".pdf",   # keyword-only; passing it positionally is a TypeError
)
```

**Parameters**:
- `stream` (BinaryIO): Binary file-like object (e.g., file opened in `"rb"` mode)
- `file_extension` (str, KEYWORD-ONLY): File extension to determine conversion method (e.g., ".pdf")
- `stream_info` (StreamInfo, keyword-only): richer alternative to `file_extension`

**Returns**: `DocumentConverterResult` object

**Example**:
```python
with open("document.pdf", "rb") as f:
    result = md.convert_stream(f, file_extension=".pdf")
    print(result.text_content)
```

**Important**: The stream must be opened in binary mode (`"rb"`), not text mode.

## Result Object

### DocumentConverterResult

The result of a conversion operation.

#### Attributes

| Attribute      | Type | Description                   |
|----------------|------|-------------------------------|
| `text_content` | str  | The converted Markdown text   |
| `title`        | str  | Document title (if available) |

#### Example

```python
result = md.convert("paper.pdf")

# Access content
content = result.text_content

# Access title (if available)
title = result.title
```

## Custom Converters

You can create custom document converters by implementing the `DocumentConverter` interface.

### DocumentConverter Interface

A converter implements TWO methods. `accepts()` is what gates it: markitdown asks every
registered converter whether it wants the stream, and a converter that does not implement it
inherits a base returning `False`, so it is never called and conversion falls through to a
generic converter with NO error. A wrong signature therefore fails silently, not loudly.

```python
from markitdown import DocumentConverter, DocumentConverterResult, StreamInfo

class CustomConverter(DocumentConverter):
    def accepts(self, file_stream, stream_info: StreamInfo, **kwargs) -> bool:
        """Return True if this converter handles the stream. Required."""
        return (stream_info.extension or "").lower() == ".custom"

    def convert(self, file_stream, stream_info: StreamInfo, **kwargs) -> DocumentConverterResult:
        """
        Parameters:
            file_stream (BinaryIO): Binary file-like object
            stream_info (StreamInfo): carries .extension, .mimetype, .charset, .filename

        Returns:
            DocumentConverterResult: Conversion result
        """
        content = file_stream.read().decode("utf-8")
        return DocumentConverterResult(markdown=f"# Custom Format\n\n{content}")
```

### Registering Custom Converters

`register_converter()` takes the converter ALONE -- there is no extension argument, and passing
one raises `TypeError: register_converter() takes 2 positional arguments but 3 were given`. The
extension is decided by the converter's own `accepts()`.

```python
from markitdown import MarkItDown, DocumentConverter, DocumentConverterResult, StreamInfo

class MyCustomConverter(DocumentConverter):
    def accepts(self, file_stream, stream_info: StreamInfo, **kwargs) -> bool:
        return (stream_info.extension or "").lower() == ".custom"

    def convert(self, file_stream, stream_info: StreamInfo, **kwargs) -> DocumentConverterResult:
        content = file_stream.read().decode("utf-8")
        return DocumentConverterResult(markdown=f"# Custom Format\n\n{content}")

md = MarkItDown()

# priority is keyword-only; lower runs first. PRIORITY_SPECIFIC_FILE_FORMAT (0.0) is the
# default, PRIORITY_GENERIC_FILE_FORMAT (10.0) is for catch-all converters.
md.register_converter(MyCustomConverter())

result = md.convert("myfile.custom")   # -> "# Custom Format\n\nhello"
```

## Plugin System

### Finding Plugins

Search GitHub for `#markitdown-plugin` tag.

### Using Plugins

```python
from markitdown import MarkItDown

# Enable plugins
md = MarkItDown(enable_plugins=True)
result = md.convert("document.pdf")
```

### Creating Plugins

A plugin is an installed package that declares an entry point in the group `markitdown.plugin`
(singular). The entry point names a MODULE, not a converter class. `MarkItDown(enable_plugins=True)`
(or `markitdown -p` on the command line) loads every such module and calls its
`register_converters(markitdown, **kwargs)`, which registers converters exactly as in
"Registering Custom Converters" above; `kwargs` are the ones passed to the `MarkItDown(...)`
constructor. The converters use the same `accepts()` plus `convert()` interface as any other.

Two mistakes fail differently. A package under any other group name (`markitdown.plugins` with an
`s` included) is never loaded and nothing warns: conversion silently falls through to a built-in
converter. An entry point that resolves to something without `register_converters` (a converter
class, for instance) is loaded, then skipped with a `Plugin ... failed to register converters`
warning.

**Plugin Structure**:
```
markitdown-my-plugin/
+-- pyproject.toml
+-- markitdown_my_plugin/
    +-- __init__.py
```

**pyproject.toml**:
```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "markitdown-my-plugin"
version = "0.1.0"
dependencies = ["markitdown"]

# Group "markitdown.plugin" (singular); the value is the MODULE that defines register_converters.
[project.entry-points."markitdown.plugin"]
my_plugin = "markitdown_my_plugin"

[tool.setuptools]
packages = ["markitdown_my_plugin"]
```

**markitdown_my_plugin/__init__.py**:
```python
from typing import Any, BinaryIO

from markitdown import DocumentConverter, DocumentConverterResult, MarkItDown, StreamInfo

# Declared by the upstream sample plugin; markitdown 0.1.8 does not read it yet.
__plugin_interface_version__ = 1


class MyConverter(DocumentConverter):
    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> bool:
        return (stream_info.extension or "").lower() == ".custom"

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        text = file_stream.read().decode(stream_info.charset or "utf-8")
        # The result takes markdown= (not text_content=); title is optional and keyword-only.
        return DocumentConverterResult(markdown=f"# Converted Content\n\n{text}", title="My Document")


def register_converters(markitdown: MarkItDown, **kwargs: Any) -> None:
    """Called once by every MarkItDown(enable_plugins=True)."""
    markitdown.register_converter(MyConverter())
```

**Install and check it is loaded**:
```bash
uv pip install -e ./markitdown-my-plugin     # or: pip install -e ./markitdown-my-plugin
markitdown --list-plugins                    # must list my_plugin
markitdown -p sample.custom                  # -> "# Converted Content" followed by the file text
```

`markitdown --list-plugins` is the quickest proof: a plugin missing from that list was registered
under the wrong entry-point group. The upstream sample plugin
(https://github.com/microsoft/markitdown/tree/main/packages/markitdown-sample-plugin) is a complete
working package to copy from.

## AI-Enhanced Conversions

### Using OpenRouter for Image Descriptions

```python
from markitdown import MarkItDown
from openai import OpenAI

# Initialize OpenRouter client (OpenAI-compatible API)
client = OpenAI(
    api_key="your-openrouter-api-key",
    base_url="https://openrouter.ai/api/v1"
)

# Create MarkItDown with AI support
md = MarkItDown(
    llm_client=client,
    llm_model="anthropic/claude-opus-4.5",  # a vision model as of 2026-09; see the list below
    llm_prompt="Describe this image in detail for scientific documentation"
)

# Convert files with images
result = md.convert("presentation.pptx")
```

### Available Models via OpenRouter

Vision-capable model IDs as of 2026-09. OpenRouter adds and retires IDs often, so a name here is
a starting point, not a guarantee: check https://openrouter.ai/models before relying on one.

- `anthropic/claude-sonnet-4.5` - the default of `scripts/convert_with_ai.py`
- `anthropic/claude-opus-4.5` - for hard figures and dense text
- `google/gemini-3.1-pro-preview` - a Gemini alternative

To see which IDs accept images right now (the endpoint is public, no key needed):

```bash
curl -s https://openrouter.ai/api/v1/models | python3 -c "import json,sys; print('\n'.join(sorted(m['id'] for m in json.load(sys.stdin)['data'] if 'image' in m['architecture']['input_modalities'])))"
```

### Custom Prompts

```python
# For scientific diagrams
scientific_prompt = """
Analyze this scientific diagram or chart. Describe:
1. The type of visualization (graph, chart, diagram, etc.)
2. Key data points or trends
3. Labels and axes
4. Scientific significance
Be precise and technical.
"""

md = MarkItDown(
    llm_client=client,
    llm_model="anthropic/claude-opus-4.5",
    llm_prompt=scientific_prompt
)
```

## Azure Document Intelligence

### Setup

1. Create Azure Document Intelligence resource
2. Get endpoint URL
3. Set authentication

### Usage

```python
from markitdown import MarkItDown

md = MarkItDown(
    docintel_endpoint="https://YOUR-RESOURCE.cognitiveservices.azure.com/"
)

result = md.convert("complex_document.pdf")
```

### Authentication

Set environment variables:
```bash
export AZURE_API_KEY="your-key"
```

Or pass credentials programmatically.

## Error Handling

```python
from markitdown import MarkItDown

md = MarkItDown()

try:
    result = md.convert("document.pdf")
    print(result.text_content)
except FileNotFoundError:
    print("File not found")
except ValueError as e:
    print(f"Invalid file format: {e}")
except Exception as e:
    print(f"Conversion error: {e}")
```

## Performance Tips

### 1. Reuse MarkItDown Instance

```python
# Good: Create once, use many times
md = MarkItDown()

for file in files:
    result = md.convert(file)
    process(result)
```

### 2. Use Streaming for Large Files

```python
# For large files
with open("large_file.pdf", "rb") as f:
    result = md.convert_stream(f, file_extension=".pdf")
```

### 3. Batch Processing

```python
from concurrent.futures import ThreadPoolExecutor

md = MarkItDown()

def convert_file(filepath):
    return md.convert(filepath)

with ThreadPoolExecutor(max_workers=4) as executor:
    results = executor.map(convert_file, file_list)
```

## API notes

1. **Dependencies** are organized into optional feature groups:
   ```bash
   pip install 'markitdown[all]'
   ```

2. **convert_stream()** requires a BINARY file-like object, plus the extension hint:
   ```python
   with open("file.pdf", "rb") as f:  # binary mode
       result = md.convert_stream(f, file_extension=".pdf")
   ```

3. **DocumentConverter** reads from streams, not file paths:
   - No temporary files created
   - More memory efficient

## Version Compatibility

- **Python**: 3.10 or higher required
- **Dependencies**: Check `setup.py` for version constraints
- **OpenAI**: Compatible with OpenAI Python SDK v1.0+

## Environment Variables

| Variable                               | Description                                                      | Example        |
|----------------------------------------|------------------------------------------------------------------|----------------|
| `OPENROUTER_API_KEY`                   | OpenRouter API key for image descriptions                        | `sk-or-v1-...` |
| `AZURE_API_KEY`                        | Azure DI authentication (falls back to `DefaultAzureCredential`) | `key123...`    |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Azure DI endpoint                                                | `https://...`  |

