#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["markitdown[all]", "openai"]
# ///
"""
Convert documents to Markdown with AI-enhanced image descriptions.

This script demonstrates how to use MarkItDown with OpenRouter to generate
detailed descriptions of images: image files (.png, .jpg, .jpeg) and the
pictures in PowerPoint decks (.pptx). markitdown sends nothing else to the LLM
- a PDF's images are never described - so any other input is refused; convert
it with plain markitdown instead.

A deck whose picture descriptions fail is reported as a failure: markitdown
itself swallows those errors and would otherwise write a Markdown file with no
descriptions under an "AI Model" header.

The OpenRouter API key comes from the OPENROUTER_API_KEY environment variable
only. A key on the command line (--api-key/-k) is refused with exit 2: argv is
visible in the process list, shell history and CI logs for the whole run.

Exit status: 0 converted, 1 an error, 2 a usage error.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

# The inputs markitdown 0.1.x asks the LLM about: ImageConverter and PptxConverter.
AI_DESCRIBED_SUFFIXES = (".png", ".jpg", ".jpeg", ".pptx")


# Predefined prompts for different use cases
PROMPTS = {
    'scientific': """
Analyze this scientific image or diagram. Provide:
1. Type of visualization (graph, chart, microscopy, diagram, etc.)
2. Key data points, trends, or patterns
3. Axes labels, legends, and scales
4. Notable features or findings
5. Scientific context and significance
Be precise, technical, and detailed.
    """.strip(),
    
    'presentation': """
Describe this presentation slide image. Include:
1. Main visual elements and their arrangement
2. Key points or messages conveyed
3. Data or information presented
4. Visual hierarchy and emphasis
Keep the description clear and informative.
    """.strip(),
    
    'general': """
Describe this image in detail. Include:
1. Main subjects and objects
2. Visual composition and layout
3. Text content (if any)
4. Notable details
5. Overall context and purpose
Be comprehensive and accurate.
    """.strip(),
    
    'data_viz': """
Analyze this data visualization. Provide:
1. Type of chart/graph (bar, line, scatter, pie, etc.)
2. Variables and axes
3. Data ranges and scales
4. Key patterns, trends, or outliers
5. Statistical insights
Focus on quantitative accuracy.
    """.strip(),
    
    'medical': """
Describe this medical image. Include:
1. Type of medical imaging (X-ray, MRI, CT, microscopy, etc.)
2. Anatomical structures visible
3. Notable findings or abnormalities
4. Image quality and contrast
5. Clinical relevance
Be professional and precise.
    """.strip()
}


def _configure_console() -> None:
    """Replace unencodable characters instead of crashing on a narrow console (cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


class CaptionCounter:
    """An OpenAI-compatible client wrapper that counts image-description calls.

    markitdown's PPTX converter catches a failed description call and carries on,
    so without this count a deck whose every call failed (a bad key, a 401) would
    convert "successfully" with no descriptions in it.
    """

    def __init__(self, client: Any):
        self._client = client
        self.attempts = 0
        self.failures = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, *args: Any, **kwargs: Any) -> Any:
        self.attempts += 1
        try:
            return self._client.chat.completions.create(*args, **kwargs)
        except Exception:
            self.failures += 1
            raise


def _make_client(api_key: str) -> Any:
    """The OpenRouter client (OpenAI-compatible).

    openai is imported here, not at module top, so --help and --list-prompts
    work without it.
    """
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


def _make_converter(client: Any, model: str, prompt: str) -> Any:
    from markitdown import MarkItDown
    return MarkItDown(llm_client=client, llm_model=model, llm_prompt=prompt)


def convert_with_ai(
    input_file: Path,
    output_file: Path,
    api_key: str,
    model: str = "anthropic/claude-sonnet-4.5",
    prompt_type: str = "general",
    custom_prompt: str = None
) -> bool:
    """
    Convert a file to Markdown with AI image descriptions.

    Args:
        input_file: Path to input file (.png, .jpg, .jpeg or .pptx)
        output_file: Path to output Markdown file
        api_key: OpenRouter API key
        model: Model name (default: anthropic/claude-sonnet-4.5; use opus for hard vision/OCR)
        prompt_type: Type of prompt to use
        custom_prompt: Custom prompt (overrides prompt_type)

    Returns:
        True if successful, False otherwise. A failed image description is a
        failure even when the Markdown file was written.
    """
    prompt = custom_prompt or PROMPTS.get(prompt_type, PROMPTS['general'])
    print(f"Using model: {model}")
    print(f"Prompt type: {prompt_type if not custom_prompt else 'custom'}")
    print(f"Converting: {input_file}")

    try:
        counter = CaptionCounter(_make_client(api_key))
        md = _make_converter(counter, model, prompt)
        result = md.convert(str(input_file))

        # Create output with metadata
        content = f"# {result.title or input_file.stem}\n\n"
        content += f"**Source**: {input_file.name}\n"
        content += f"**Format**: {input_file.suffix}\n"
        content += f"**AI Model**: {model}\n"
        content += f"**Prompt Type**: {prompt_type if not custom_prompt else 'custom'}\n\n"
        content += "---\n\n"
        content += result.text_content

        # Write output
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding='utf-8')
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}", file=sys.stderr)
        return False

    if counter.failures:
        print(
            f"[FAIL] {counter.failures} of {counter.attempts} image description call(s) failed; "
            f"{output_file} was written without those descriptions",
            file=sys.stderr,
        )
        return False
    print(f"[OK] Successfully converted to: {output_file}")
    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert images and PowerPoint decks to Markdown with AI-enhanced image descriptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Supported inputs: {', '.join(AI_DESCRIBED_SUFFIXES)} (markitdown describes no other format's
images, so anything else is refused - convert it with plain markitdown).

Available prompt types:
  scientific    - For scientific diagrams, graphs, and charts
  presentation  - For presentation slides
  general       - General-purpose image description
  data_viz      - For data visualizations and charts
  medical       - For medical imaging

Examples:
  # Describe a scientific figure
  python convert_with_ai.py figure.png figure.md --prompt-type scientific

  # Convert a presentation with custom model
  python convert_with_ai.py slides.pptx slides.md --model anthropic/claude-opus-4.5 --prompt-type presentation

  # Use custom prompt with advanced vision model
  python convert_with_ai.py diagram.png diagram.md --model anthropic/claude-opus-4.5 --custom-prompt "Describe this technical diagram"

  # The API key comes from the environment only
  export OPENROUTER_API_KEY="sk-or-v1-..."
  python convert_with_ai.py image.jpg image.md

Environment Variables:
  OPENROUTER_API_KEY    OpenRouter API key (required; the only way to pass the key - a key on
                        the command line would be visible in the process list)

Popular Models (use with --model):
  anthropic/claude-opus-4.5 - Recommended for scientific vision
  google/gemini-3-pro-preview   - Gemini Pro Vision

Exit status: 0 converted, 1 an error (including a failed image description), 2 a usage error.
        """
    )

    parser.add_argument('input', type=Path, nargs='?', help='Input file (.png, .jpg, .jpeg or .pptx)')
    parser.add_argument('output', type=Path, nargs='?', help='Output Markdown file')
    # Refused in main(), never used: the key comes from OPENROUTER_API_KEY only. Registered
    # (hidden) so that passing it is refused with the remedy named, not a bare "unrecognized".
    parser.add_argument('--api-key', '-k', dest='api_key', help=argparse.SUPPRESS)
    parser.add_argument(
        '--model', '-m',
        default='anthropic/claude-sonnet-4.5',
        help='Model via OpenRouter (default: anthropic/claude-sonnet-4.5; pass an opus model for hard vision/OCR)'
    )
    parser.add_argument(
        '--prompt-type', '-t',
        choices=list(PROMPTS.keys()),
        default='general',
        help='Type of prompt to use (default: general)'
    )
    parser.add_argument(
        '--custom-prompt', '-p',
        help='Custom prompt (overrides --prompt-type)'
    )
    parser.add_argument(
        '--list-prompts', '-l',
        action='store_true',
        help='List available prompt types and exit'
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.api_key is not None:
        # Exit 2 before anything runs. A key on the command line sits in the process list, shell
        # history and CI logs for the whole run; ignoring it silently would let a caller believe
        # the argv key was the one used.
        parser.error("--api-key/-k is not accepted: a key on the command line is visible in the "
                     "process list for the whole run. Set OPENROUTER_API_KEY in the environment.")

    # List prompts and exit
    if args.list_prompts:
        print("Available prompt types:\n")
        for name, prompt in PROMPTS.items():
            print(f"[{name}]")
            print(prompt)
            print("\n" + "="*60 + "\n")
        return 0

    # input/output are optional only so --list-prompts can stand alone
    if args.input is None or args.output is None:
        parser.error("the following arguments are required: input, output")

    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("Error: OpenRouter API key required. Set the OPENROUTER_API_KEY environment variable "
              "(the only way to pass the key).", file=sys.stderr)
        print("Get your API key at: https://openrouter.ai/keys", file=sys.stderr)
        return 1

    # Validate input file. Errors go to stderr: stdout carries the progress lines.
    if not args.input.exists():
        print(f"Error: Input file '{args.input}' does not exist", file=sys.stderr)
        return 1
    if not args.input.is_file():
        # A directory named like an image otherwise reaches markitdown, whose failure names the
        # converter rather than the input.
        print(f"Error: Input '{args.input}' is not a file", file=sys.stderr)
        return 1

    if args.input.suffix.lower() not in AI_DESCRIBED_SUFFIXES:
        print(
            f"Error: {args.input.suffix or 'this input'} gets no AI image descriptions from "
            f"markitdown (only {', '.join(AI_DESCRIBED_SUFFIXES)} do); convert it with plain "
            "markitdown instead",
            file=sys.stderr,
        )
        return 1

    # Convert file
    success = convert_with_ai(
        input_file=args.input,
        output_file=args.output,
        api_key=api_key,
        model=args.model,
        prompt_type=args.prompt_type,
        custom_prompt=args.custom_prompt
    )

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
