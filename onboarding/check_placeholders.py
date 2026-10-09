#!/usr/bin/env python3
"""List unfilled {{PLACEHOLDER}} markers in files or folders.

    python3 check_placeholders.py PATH [PATH ...] [--ignore NAME ...]

Exit codes:
    0  every scanned file is clean
    1  at least one unfilled placeholder was found (each is printed)
    2  usage problem: a path is missing, or nothing was scanned

Zero scanned files is an error on purpose, so a mistyped folder cannot pass.
Folders are walked recursively. Hidden folders (".git", ".cache") and folders
named "archive" or "__pycache__" are skipped. Files that are binary or not
valid UTF-8 are skipped and counted.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Iterable, Iterator

PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")
SKIP_DIRS = {"archive", "__pycache__"}


def iter_files(path: str) -> Iterator[str]:
    """Yield file paths under `path` (a file or a folder)."""
    if os.path.isfile(path):
        yield path
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
        for name in sorted(files):
            yield os.path.join(root, name)


def read_text(path: str) -> str | None:
    """Return file text, or None for binary / non-UTF-8 files."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        if b"\0" in data:
            return None
        return data.decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def scan(paths: Iterable[str], ignore: Iterable[str] = ()) -> tuple[list[tuple[str, int, str]], int, int]:
    """Return (findings, scanned, skipped).

    findings is a list of (file, line_number, name), one per marker occurrence.
    """
    ignored = set(ignore)
    findings, scanned, skipped = [], 0, 0
    for path in paths:
        for file in iter_files(path):
            text = read_text(file)
            if text is None:
                skipped += 1
                continue
            scanned += 1
            for lineno, line in enumerate(text.splitlines(), start=1):
                for match in PATTERN.finditer(line):
                    if match.group(1) not in ignored:
                        findings.append((file, lineno, match.group(1)))
    return findings, scanned, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List unfilled {{PLACEHOLDER}} markers.")
    parser.add_argument("paths", nargs="+", metavar="PATH", help="file or folder to scan")
    parser.add_argument("--ignore", action="append", default=[], metavar="NAME",
                        help="placeholder name to allow (repeatable)")
    args = parser.parse_args(argv)

    for path in args.paths:
        if not os.path.exists(path):
            print(f"error: no such path: {path}", file=sys.stderr)
            return 2

    findings, scanned, skipped = scan(args.paths, args.ignore)
    if scanned == 0:
        print("error: no text files scanned", file=sys.stderr)
        return 2

    for file, lineno, name in findings:
        print(f"{file}:{lineno}: {{{{{name}}}}}")
    names = sorted({name for _, _, name in findings})
    files = len({file for file, _, _ in findings})
    note = f", {skipped} binary skipped" if skipped else ""
    if findings:
        print(f"{len(findings)} unfilled in {files} file(s); {len(names)} distinct: "
              + ", ".join(names) + f" ({scanned} scanned{note})")
        return 1
    print(f"ok: no unfilled placeholders ({scanned} files scanned{note})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
