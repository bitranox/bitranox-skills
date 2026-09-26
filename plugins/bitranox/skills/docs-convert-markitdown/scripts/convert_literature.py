#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["markitdown[pdf]"]
# ///
"""
Convert scientific literature PDFs to Markdown for analysis and review.

This script is specifically designed for converting academic papers,
organizing them, and preparing them for literature review workflows.

Output layout: each paper keeps its subdirectory (with -r, in/a/x.pdf becomes
out/a/x.md), under a year directory when --organize-by-year is set. Two papers
that would still write the same file are both reported as failed rather than
one silently overwriting the other. INDEX.md links each paper's actual output.

Exit status: 0 every paper converted, 1 no PDF files found,
2 an error (bad input directory, a failed conversion, an output collision,
an unreadable subdirectory, or markitdown missing).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

EXIT_OK = 0
EXIT_NONE_FOUND = 1
EXIT_ERROR = 2


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


def _make_converter() -> Any:
    """Build a MarkItDown instance.

    markitdown is imported here, not at module top, so --help, the "no PDFs"
    path and the test suite work in an environment without it.
    """
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "markitdown is not installed: run this script with `uv run` (it declares its "
            "dependencies) or `pip install 'markitdown[pdf]'`"
        ) from exc
    return MarkItDown()


def extract_metadata_from_filename(filename: str) -> Dict[str, str]:
    """
    Try to extract metadata from filename.
    Supports patterns like: Author_Year_Title.pdf
    """
    metadata = {}

    # Remove extension
    name = Path(filename).stem

    # Try to extract year. NOT \b: an underscore is a word character, so \b never fires
    # between '_' and a digit and the year is missed in the documented Author_Year_Title form.
    year_match = re.search(r'(?<!\d)(19|20)\d{2}(?!\d)', name)
    if year_match:
        metadata['year'] = year_match.group()

    # Split by underscores or dashes
    parts = [p for p in re.split(r'[_\-]', name) if p]
    if 'year' in metadata:
        # the caller already gets the year in its own field; leaving it in the title too
        # means every downstream filename/citation carries it twice
        parts = [p for p in parts if p != metadata['year']]
    if len(parts) >= 2:
        metadata['author'] = parts[0]
        metadata['title'] = ' '.join(parts[1:])
    else:
        metadata['title'] = name.replace('_', ' ')

    return metadata


def find_pdfs(input_dir: Path, recursive: bool, walk_errors: List[str]) -> List[Path]:
    """
    List the PDFs under input_dir, matching the .pdf suffix in any case.

    A directory that cannot be read is appended to walk_errors instead of
    being skipped silently.
    """
    def on_error(err: OSError) -> None:
        walk_errors.append(f"{err.filename}: {err.strerror or err}")

    found = []
    for root, dirs, names in os.walk(input_dir, onerror=on_error):
        found.extend(Path(root) / name for name in names if name.lower().endswith(".pdf"))
        if not recursive:
            dirs.clear()
    return sorted(found)


def plan_outputs(pdf_files: List[Path], input_dir: Path, output_dir: Path,
                 organize_by_year: bool) -> tuple[Dict[Path, Path], Dict[Path, str]]:
    """
    Map each PDF to its Markdown output, keeping its subdirectory.

    Returns:
        (planned, collisions): planned maps input -> output for the papers that
        can be converted; collisions maps each paper that shares its output with
        another to a failure message. Paths are compared case-folded, because
        Windows and macOS file systems do.
    """
    target = {}
    by_output: Dict[str, List[Path]] = {}
    for pdf in pdf_files:
        base = output_dir
        year = extract_metadata_from_filename(pdf.name).get('year')
        if organize_by_year and year:
            base = base / year
        target[pdf] = base / pdf.relative_to(input_dir).parent / f"{pdf.stem}.md"
        by_output.setdefault(str(target[pdf]).casefold(), []).append(pdf)

    planned, collisions = {}, {}
    for group in by_output.values():
        if len(group) == 1:
            planned[group[0]] = target[group[0]]
            continue
        message = collision_message(group, input_dir, target)
        for pdf in group:
            collisions[pdf] = message
    return planned, collisions


def collision_message(group: List[Path], input_dir: Path, target: Dict[Path, Path]) -> str:
    """The failure line for papers that share one output, naming every output they would write.

    Names that differ only in case are one file on Windows and macOS, so they are refused on
    every platform and the line says why.
    """
    names = ", ".join(str(p.relative_to(input_dir)) for p in group)
    outputs = sorted({target[p].name for p in group})
    if len(outputs) == 1:
        return f"[FAIL] Output collision: {names} would all write {outputs[0]}"
    return (f"[FAIL] Output collision: {names} would write {', '.join(outputs)}, which differ "
            "only in case and are one file on a case-insensitive file system")


# Characters json.dumps leaves raw that YAML cannot carry raw in a double-quoted scalar: DEL and
# the C1 controls are not printable (a YAML reader refuses the whole document), and NEL plus the
# Unicode line and paragraph separators are read as line breaks and folded into a space.
_YAML_UNSAFE = re.compile('[\x7f-\x9f\u2028\u2029]')


def _yaml_str(value: str) -> str:
    """A YAML double-quoted scalar. JSON string syntax is a valid subset, so quotes and
    backslashes in a filename cannot break the front matter; the characters YAML would refuse
    or fold are written as \\uXXXX escapes, which both JSON and YAML read back unchanged."""
    quoted = json.dumps(value, ensure_ascii=False)
    return _YAML_UNSAFE.sub(lambda m: f"\\u{ord(m.group()):04x}", quoted)


def render_paper(metadata: Dict[str, str], text_content: str) -> str:
    """The Markdown document for one paper: YAML front matter, a header block, the text."""
    title = metadata['title']
    content = "---\n"
    content += f"title: {_yaml_str(title)}\n"
    if 'author' in metadata:
        content += f"author: {_yaml_str(metadata['author'])}\n"
    if 'year' in metadata:
        content += f"year: {metadata['year']}\n"
    content += f"source: {_yaml_str(metadata['source_file'])}\n"
    content += f"converted: {_yaml_str(metadata['converted_date'])}\n"
    content += "---\n\n"

    content += f"# {title}\n\n"

    content += "## Document Information\n\n"
    if 'author' in metadata:
        content += f"**Author**: {metadata['author']}\n"
    if 'year' in metadata:
        content += f"**Year**: {metadata['year']}\n"
    content += f"**Source File**: {metadata['source_file']}\n"
    content += f"**Converted**: {metadata['converted_date']}\n\n"
    content += "---\n\n"

    return content + text_content


def convert_paper(
    md: Any,
    input_file: Path,
    output_file: Path,
    output_dir: Path
) -> tuple[bool, Dict]:
    """
    Convert a single paper to Markdown with metadata extraction.

    Args:
        md: MarkItDown instance (anything with a compatible convert())
        input_file: Path to PDF file
        output_file: Markdown file to write (see plan_outputs)
        output_dir: Root output directory; metadata['output_file'] is relative to it

    Returns:
        Tuple of (success, metadata_dict)
    """
    print(f"Converting: {input_file.name}")
    try:
        result = md.convert(str(input_file))

        # The title always comes from the filename: extract_metadata_from_filename sets
        # one for every name, and markitdown reports no title for a PDF anyway.
        metadata = extract_metadata_from_filename(input_file.name)
        metadata['source_file'] = input_file.name
        metadata['converted_date'] = datetime.now().isoformat()
        metadata['output_file'] = output_file.relative_to(output_dir).as_posix()

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(render_paper(metadata, result.text_content), encoding='utf-8')
    except Exception as e:
        print(f"[FAIL] Error converting {input_file.name}: {str(e)}")
        return False, {'source_file': input_file.name, 'error': str(e)}

    print(f"[OK] Saved to: {output_file}")
    return True, metadata


def create_index(papers: List[Dict], output_dir: Path):
    """Create an index/catalog of all converted papers."""

    # Sort by year (if available) and title
    papers_sorted = sorted(
        papers,
        key=lambda x: (x.get('year', '9999'), x.get('title', ''))
    )

    # Create Markdown index
    index_content = "# Literature Review Index\n\n"
    index_content += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    index_content += f"**Total Papers**: {len(papers)}\n\n"
    index_content += "---\n\n"

    # Group by year
    by_year = {}
    for paper in papers_sorted:
        year = paper.get('year', 'Unknown')
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(paper)

    # Write by year
    for year in sorted(by_year.keys()):
        index_content += f"## {year}\n\n"
        for paper in by_year[year]:
            title = paper.get('title', paper.get('source_file', 'Unknown'))
            author = paper.get('author', 'Unknown Author')
            source = paper.get('source_file', '')

            # Link where the paper was actually written; the angle brackets keep a
            # name with spaces a single link target.
            md_file = paper.get('output_file') or Path(source).stem + ".md"

            index_content += f"- **{title}**\n"
            index_content += f"  - Author: {author}\n"
            index_content += f"  - Source: {source}\n"
            index_content += f"  - [Read Markdown](<{md_file}>)\n\n"

    # Write index
    index_file = output_dir / "INDEX.md"
    index_file.write_text(index_content, encoding='utf-8')
    print(f"\n[OK] Created index: {index_file}")

    # Also create JSON catalog
    catalog_file = output_dir / "catalog.json"
    with open(catalog_file, 'w', encoding='utf-8') as f:
        json.dump(papers_sorted, f, indent=2, ensure_ascii=False)
    print(f"[OK] Created catalog: {catalog_file}")


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert scientific literature PDFs to Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all PDFs in a directory
  python convert_literature.py papers/ output/

  # Organize by year
  python convert_literature.py papers/ output/ --organize-by-year

  # Create index of all papers
  python convert_literature.py papers/ output/ --create-index

Filename Conventions:
  For best results, name your PDFs using this pattern:
    Author_Year_Title.pdf

  Examples:
    Smith_2023_Machine_Learning_Applications.pdf
    Jones_2022_Climate_Change_Analysis.pdf

Exit status: 0 all converted, 1 no PDF files found, 2 an error.
        """
    )

    parser.add_argument('input_dir', type=Path, help='Directory with PDF files')
    parser.add_argument('output_dir', type=Path, help='Output directory for Markdown files')
    parser.add_argument(
        '--organize-by-year', '-y',
        action='store_true',
        help='Organize output into year subdirectories'
    )
    parser.add_argument(
        '--create-index', '-i',
        action='store_true',
        help='Create an index/catalog of all papers'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Search subdirectories recursively (output keeps the subdirectories)'
    )
    return parser.parse_args(argv)


def _print_summary(total: int, success_count: int, failures: List[str],
                   unreadable_dirs: int = 0) -> None:
    """Print the run summary. total counts every paper found plus every unreadable
    directory, so total == successful + failed."""
    print("\n" + "="*50)
    print("CONVERSION SUMMARY")
    print("="*50)
    note = (f" (including {unreadable_dirs} unreadable "
            f"director{'y' if unreadable_dirs == 1 else 'ies'})")
    print(f"Total:           {total}{note if unreadable_dirs else ''}")
    print(f"Successful:      {success_count}")
    print(f"Failed:          {len(failures)}")
    if total:
        print(f"Success rate:    {success_count/total*100:.1f}%")
    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"  - {failure}")


def _run(args: argparse.Namespace) -> int:
    if not args.input_dir.exists():
        print(f"Error: Input directory '{args.input_dir}' does not exist", file=sys.stderr)
        return EXIT_ERROR
    if not args.input_dir.is_dir():
        print(f"Error: '{args.input_dir}' is not a directory", file=sys.stderr)
        return EXIT_ERROR

    walk_errors: List[str] = []
    pdf_files = find_pdfs(args.input_dir, args.recursive, walk_errors)
    failures = [f"cannot read directory {error}" for error in walk_errors]
    for failure in failures:
        print(f"[FAIL] {failure[0].upper()}{failure[1:]}")
    if not pdf_files:
        print("No PDF files found")
        return EXIT_ERROR if failures else EXIT_NONE_FOUND

    print(f"Found {len(pdf_files)} PDF file(s)")
    planned, collisions = plan_outputs(pdf_files, args.input_dir, args.output_dir,
                                       args.organize_by_year)
    for message in collisions.values():
        print(message)
    failures += list(collisions.values())

    results = []
    if planned:
        md = _make_converter()
        for pdf_file, output_file in planned.items():
            success, metadata = convert_paper(md, pdf_file, output_file, args.output_dir)
            if success:
                results.append(metadata)
            else:
                failures.append(f"{pdf_file}: {metadata['error']}")

    if args.create_index and results:
        create_index(results, args.output_dir)

    # An unreadable directory is one of the failures, so it counts in the total as well.
    _print_summary(len(pdf_files) + len(walk_errors), len(results), failures, len(walk_errors))
    return EXIT_ERROR if failures else EXIT_OK


def main(argv: Optional[List[str]] = None) -> int:
    _configure_console()
    args = _parse_args(argv)
    try:
        return _run(args)
    except Exception as exc:  # a crash must not share the "no PDFs found" exit code
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == '__main__':
    sys.exit(main())
