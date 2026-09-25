#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["markitdown[all]"]
# ///
"""
Batch convert multiple files to Markdown using MarkItDown.

This script demonstrates how to efficiently convert multiple files
in a directory to Markdown format.

Output layout mirrors the input tree: in/sub/x.pdf becomes out/sub/x.md, so two
inputs with the same name in different subdirectories never share an output.
Two inputs that would still write the same file (a.html and a.htm side by side)
are both reported as failed rather than one silently overwriting the other.

Exit status: 0 every file converted, 1 no matching files found,
2 an error (bad input directory, a failed conversion, an output collision,
an unreadable subdirectory, or markitdown missing).
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, List, Optional

EXIT_OK = 0
EXIT_NONE_FOUND = 1
EXIT_ERROR = 2

DEFAULT_EXTENSIONS = ['.pdf', '.docx', '.pptx', '.xlsx', '.html', '.jpg', '.png']


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


def _make_converter(enable_plugins: bool) -> Any:
    """Build a MarkItDown instance.

    markitdown is imported here, not at module top, so --help, the "nothing to
    convert" path and the test suite work in an environment without it.
    """
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "markitdown is not installed: run this script with `uv run` (it declares its "
            "dependencies) or `pip install 'markitdown[all]'`"
        ) from exc
    return MarkItDown(enable_plugins=enable_plugins)


def _matches(name: str, extensions: List[str]) -> bool:
    lowered = name.lower()
    return any(lowered.endswith(ext.lower()) for ext in extensions)


def find_files(input_dir: Path, extensions: List[str], recursive: bool,
               walk_errors: List[str]) -> List[Path]:
    """
    List the files under input_dir whose name ends in one of the extensions.

    Matching ignores case, and each file is listed once however many extensions
    it matches. A directory that cannot be read is appended to walk_errors
    instead of being skipped silently.
    """
    def on_error(err: OSError) -> None:
        walk_errors.append(f"{err.filename}: {err.strerror or err}")

    found = []
    for root, dirs, names in os.walk(input_dir, onerror=on_error):
        found.extend(Path(root) / name for name in names if _matches(name, extensions))
        if not recursive:
            dirs.clear()
    return sorted(found)


def plan_outputs(files: List[Path], input_dir: Path,
                 output_dir: Path) -> tuple[dict[Path, Path], dict[Path, str]]:
    """
    Map each input to its output path, mirroring the input's subdirectory.

    Returns:
        (planned, collisions): planned maps input -> output for the inputs that
        can be converted; collisions maps each input that shares its output with
        another input to a failure message. Paths are compared case-folded,
        because Windows and macOS file systems do.
    """
    by_output: dict[str, List[Path]] = {}
    target = {}
    for file_path in files:
        rel = file_path.relative_to(input_dir)
        target[file_path] = output_dir / rel.parent / f"{file_path.stem}.md"
        by_output.setdefault(str(target[file_path]).casefold(), []).append(file_path)

    planned, collisions = {}, {}
    for group in by_output.values():
        if len(group) == 1:
            planned[group[0]] = target[group[0]]
            continue
        names = ", ".join(str(p.relative_to(input_dir)) for p in group)
        for file_path in group:
            collisions[file_path] = (
                f"[FAIL] Output collision: {names} would all write {target[file_path].name}"
            )
    return planned, collisions


def convert_file(md: Any, file_path: Path, output_file: Path) -> tuple[bool, str, str]:
    """
    Convert a single file to Markdown.

    Args:
        md: MarkItDown instance (anything with a compatible convert())
        file_path: Path to input file
        output_file: Path of the Markdown file to write

    Returns:
        Tuple of (success, input_path, message)
    """
    try:
        result = md.convert(str(file_path))

        # Write content with metadata header
        content = f"# {result.title or file_path.stem}\n\n"
        content += f"**Source**: {file_path.name}\n"
        content += f"**Format**: {file_path.suffix}\n\n"
        content += "---\n\n"
        content += result.text_content

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding='utf-8')

        return True, str(file_path), f"[OK] Converted to {output_file.name}"

    except Exception as e:
        return False, str(file_path), f"[FAIL] Error: {str(e)}"


def _record(results: dict, success: bool, path: str, message: str) -> None:
    results['success' if success else 'failed'] += 1
    results['details'].append({'file': path, 'success': success, 'message': message})
    print(message)


def batch_convert(
    input_dir: Path,
    output_dir: Path,
    extensions: Optional[List[str]] = None,
    recursive: bool = False,
    workers: int = 4,
    verbose: bool = False,
    enable_plugins: bool = False
) -> dict:
    """
    Batch convert files in a directory.

    Args:
        input_dir: Input directory
        output_dir: Output directory
        extensions: List of file extensions to convert (e.g., ['.pdf', '.docx'])
        recursive: Search subdirectories
        workers: Number of parallel workers
        verbose: Print detailed messages
        enable_plugins: Enable MarkItDown plugins

    Returns:
        Dictionary with conversion statistics: total, success, failed, details.
        An unreadable subdirectory and an output collision count as failures.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if extensions is None:
        extensions = DEFAULT_EXTENSIONS

    walk_errors: List[str] = []
    files = find_files(input_dir, extensions, recursive, walk_errors)
    results = {'total': len(files), 'success': 0, 'failed': 0, 'details': []}
    for error in walk_errors:
        _record(results, False, error, f"[FAIL] Cannot read directory {error}")

    if not files:
        print(f"No files found with extensions: {', '.join(extensions)}")
        return results

    print(f"Found {len(files)} file(s) to convert")
    planned, collisions = plan_outputs(files, input_dir, output_dir)
    for file_path, message in collisions.items():
        _record(results, False, str(file_path), message)
    if not planned:
        return results

    md = _make_converter(enable_plugins)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for file_path, output_file in planned.items():
            if verbose:
                print(f"Converting: {file_path}")
            futures.append(executor.submit(convert_file, md, file_path, output_file))
        for future in as_completed(futures):
            _record(results, *future.result())

    return results


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch convert files to Markdown using MarkItDown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all PDFs in a directory
  python batch_convert.py papers/ output/ --extensions .pdf

  # Convert multiple formats recursively (output mirrors the subdirectories)
  python batch_convert.py documents/ markdown/ --extensions .pdf .docx .pptx -r

  # Use 8 parallel workers
  python batch_convert.py input/ output/ --workers 8

  # Enable plugins
  python batch_convert.py input/ output/ --plugins

Exit status: 0 all converted, 1 no matching files, 2 an error.
        """
    )

    parser.add_argument('input_dir', type=Path, help='Input directory')
    parser.add_argument('output_dir', type=Path, help='Output directory')
    parser.add_argument(
        '--extensions', '-e',
        nargs='+',
        help='File extensions to convert, matched case-insensitively (e.g., .pdf .docx)'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Search subdirectories recursively'
    )
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--plugins', '-p',
        action='store_true',
        help='Enable MarkItDown plugins'
    )
    return parser.parse_args(argv)


def _print_summary(results: dict) -> None:
    print("\n" + "="*50)
    print("CONVERSION SUMMARY")
    print("="*50)
    print(f"Total files:     {results['total']}")
    print(f"Successful:      {results['success']}")
    print(f"Failed:          {results['failed']}")
    print(f"Success rate:    {results['success']/results['total']*100:.1f}%" if results['total'] > 0 else "N/A")

    if results['failed'] > 0:
        print("\nFailed conversions:")
        for detail in results['details']:
            if not detail['success']:
                print(f"  - {detail['file']}: {detail['message']}")


def _run(args: argparse.Namespace) -> int:
    if not args.input_dir.exists():
        print(f"Error: Input directory '{args.input_dir}' does not exist", file=sys.stderr)
        return EXIT_ERROR
    if not args.input_dir.is_dir():
        print(f"Error: '{args.input_dir}' is not a directory", file=sys.stderr)
        return EXIT_ERROR

    results = batch_convert(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        extensions=args.extensions,
        recursive=args.recursive,
        workers=args.workers,
        verbose=args.verbose,
        enable_plugins=args.plugins
    )
    _print_summary(results)

    if results['failed'] > 0:
        return EXIT_ERROR
    return EXIT_OK if results['total'] > 0 else EXIT_NONE_FOUND


def main(argv: Optional[List[str]] = None) -> int:
    _configure_console()
    args = _parse_args(argv)
    try:
        return _run(args)
    except Exception as exc:  # a crash must not share the "nothing found" exit code
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == '__main__':
    sys.exit(main())
