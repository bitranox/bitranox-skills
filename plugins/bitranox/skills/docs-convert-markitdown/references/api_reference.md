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

Plugins are Python packages that register converters with MarkItDown.

**Plugin Structure**:
```
my-markitdown-plugin/
+-- setup.py
+-- my_plugin/
|   +-- __init__.py
|   +-- converter.py
+-- README.md
```

**setup.py**:
```python
from setuptools import setup

setup(
    name="markitdown-my-plugin",
    version="0.1.0",
    packages=["my_plugin"],
    entry_points={
        "markitdown.plugins": [
            "my_plugin = my_plugin.converter:MyConverter",
        ],
    },
)
```

**converter.py**:
```python
from markitdown import DocumentConverter, DocumentConverterResult

class MyConverter(DocumentConverter):
    def convert(self, stream, file_extension):
        # Your conversion logic
        content = stream.read()
        markdown = self.process(content)
        return DocumentConverterResult(
            text_content=markdown,
            title="My Document"
        )
    
    def process(self, content):
        # Process content
        return "# Converted Content\n\n..."
```

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
    llm_model="anthropic/claude-opus-4.5",  # a current vision model as of 2026-08; check
                                        # openrouter.ai/models for what is current now
    llm_prompt="Describe this image in detail for scientific documentation"
)

# Convert files with images
result = md.convert("presentation.pptx")
```

### Available Models via OpenRouter

Popular models with vision support:
- `anthropic/claude-opus-4.5` - **Recommended for scientific vision**
- `google/gemini-3-pro-preview` - Gemini Pro Vision

See https://openrouter.ai/models for the complete list.

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

