#!/usr/bin/env python3
"""
Scientific schematic generation using Nano Banana 2.

Generate any scientific diagram by describing it in natural language.
Nano Banana 2 handles everything automatically with smart iterative refinement.

Smart iteration: Only regenerates if quality is below threshold for your document type.
Quality review: Uses Gemini 3.1 Pro Preview for professional scientific evaluation.

Usage:
    # Generate for journal paper (highest quality threshold)
    python generate_schematic.py "CONSORT flowchart" -o flowchart.png --doc-type journal
    
    # Generate for presentation (lower threshold, faster)
    python generate_schematic.py "Transformer architecture" -o transformer.png --doc-type presentation
    
    # Generate for poster
    python generate_schematic.py "MAPK signaling pathway" -o pathway.png --doc-type poster

Exit status: the AI script's own code is passed through unchanged - 0 the image met the
threshold, 1 the best image's score is below the threshold (the image is still written), 2 the
quality question could not be answered (no image, an unverified image, httpx2 missing, an
unexpected error) or a usage error. The wrapper's own failures are 2 as well: no API key, or the
AI script cannot be found or launched.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


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


def main():
    """Command-line interface."""
    _configure_console()
    parser = argparse.ArgumentParser(
        description="Generate scientific schematics using AI with smart iterative refinement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
How it works:
  Simply describe your diagram in natural language
  Nano Banana 2 generates it automatically with:
  - Smart iteration (only regenerates if quality is below threshold)
  - Quality review by Gemini 3.1 Pro Preview
  - Document-type aware quality thresholds
  - Publication-ready output

Document Types (quality thresholds):
  journal      8.5/10  - Nature, Science, peer-reviewed journals
  conference   8.0/10  - Conference papers
  thesis       8.0/10  - Dissertations, theses
  grant        8.0/10  - Grant proposals
  preprint     7.5/10  - arXiv, bioRxiv, etc.
  report       7.5/10  - Technical reports
  poster       7.0/10  - Academic posters
  presentation 6.5/10  - Slides, talks
  default      7.5/10  - General purpose

Examples:
  # Generate for journal paper (strict quality)
  python generate_schematic.py "CONSORT participant flow" -o flowchart.png --doc-type journal
  
  # Generate for poster (moderate quality)
  python generate_schematic.py "Transformer architecture" -o arch.png --doc-type poster
  
  # Generate for slides (faster, lower threshold)
  python generate_schematic.py "System diagram" -o system.png --doc-type presentation
  
  # Custom max iterations
  python generate_schematic.py "Complex pathway" -o pathway.png --iterations 2
  
  # Verbose output
  python generate_schematic.py "Circuit diagram" -o circuit.png -v

Environment Variables:
  OPENROUTER_API_KEY    Required for AI generation (the only way to pass the key)

Exit status: the AI script's own code is passed through unchanged - 0 the image met the
threshold, 1 the best image's score is below the threshold (the image is still written), 2 the
quality question could not be answered (no image, an unverified image, httpx2 missing, an
unexpected error) or a usage error. The wrapper's own failures are 2 as well: no API key, or the
AI script cannot be found or launched.
        """
    )
    
    parser.add_argument("prompt", 
                       help="Description of the diagram to generate")
    parser.add_argument("-o", "--output", required=True,
                       help="Output file path")
    parser.add_argument("--doc-type", default="default",
                       choices=["journal", "conference", "poster", "presentation",
                               "report", "grant", "thesis", "preprint", "default"],
                       help="Document type for quality threshold (default: default)")
    parser.add_argument("--iterations", type=int, default=2,
                       help="Maximum refinement iterations (default: 2, range: 1-2)")
    # No default here: the AI script owns the default IDs, so only an explicit choice is forwarded.
    parser.add_argument("--image-model", metavar="ID",
                       help="OpenRouter model that generates the image (default: the AI script's)")
    parser.add_argument("--review-model", metavar="ID",
                       help="OpenRouter model that reviews the image (default: the AI script's)")
    # Refused below, never used: the key comes from OPENROUTER_API_KEY only.
    parser.add_argument("--api-key", help=argparse.SUPPRESS)
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    if args.api_key is not None:
        # The value is never echoed. Refusing is all that is left to do: it is already in this
        # process's argv, and forwarding it would keep it in the process list for the whole run.
        parser.error("--api-key is not accepted: a key on the command line is visible in the "
                     "process list for the whole run. Set OPENROUTER_API_KEY in the environment.")
    
    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    # Errors go to stderr: stdout carries the AI script's progress lines.
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set", file=sys.stderr)
        print("\nFor AI generation, you need an OpenRouter API key.", file=sys.stderr)
        print("Get one at: https://openrouter.ai/keys", file=sys.stderr)
        print("\nSet it with:", file=sys.stderr)
        print("  export OPENROUTER_API_KEY='your_api_key'", file=sys.stderr)
        sys.exit(2)
    
    # Find AI generation script
    script_dir = Path(__file__).parent
    ai_script = script_dir / "generate_schematic_ai.py"
    
    if not ai_script.exists():
        print(f"Error: AI generation script not found: {ai_script}", file=sys.stderr)
        sys.exit(2)
    
    # Build command. The output travels as --output=VALUE and the prompt after "--", so a
    # value that starts with a dash is never re-read by the child as an option.
    cmd = [sys.executable, str(ai_script), f"--output={args.output}"]
    
    if args.doc_type != "default":
        cmd.extend(["--doc-type", args.doc_type])
    
    # Enforce 1-2 iterations: the AI script refuses anything outside that range with a
    # usage error, so bound both ends here instead of forwarding an invalid value.
    iterations = max(1, min(args.iterations, 2))
    if iterations != 2:
        cmd.extend(["--iterations", str(iterations)])
    
    # --flag=VALUE, like --output: a value that starts with a dash stays a value.
    if args.image_model is not None:
        cmd.append(f"--image-model={args.image_model}")
    if args.review_model is not None:
        cmd.append(f"--review-model={args.review_model}")
    
    if args.verbose:
        cmd.append("-v")
    cmd.extend(["--", args.prompt])
    
    # Execute. The child inherits the key through the environment, never through its argv.
    try:
        env = os.environ.copy()
        env["OPENROUTER_API_KEY"] = api_key
        result = subprocess.run(cmd, check=False, env=env)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Error executing AI generation: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

