#!/usr/bin/env python3
"""List unfilled {{PLACEHOLDER}} markers in files or folders.

    python3 check_placeholders.py PATH [PATH ...] [--ignore NAME ...]

Exit codes:
    0  every scanned file is clean
    1  at least one unfilled placeholder was found (each is printed)
    2  the check could not finish: a path is missing, nothing was scanned, or
       a file or folder could not be read or is not UTF-8 text (each is
       printed on stderr)

Zero scanned files is an error on purpose, so a mistyped folder cannot pass,
and so is any file the checker cannot read: a placeholder in it would go
unseen. Folders are walked recursively. Hidden folders (".git", ".cache") and
folders named "archive" or "__pycache__" are skipped. Binary files (any file
containing a NUL byte, unless it starts with a UTF-16 byte order mark) are
skipped and counted.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Iterable, Iterator

PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")
SKIP_DIRS = {"archive", "__pycache__"}
UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")


def iter_files(path: str, errors: list[str]) -> Iterator[str]:
    """Yield file paths under `path` (a file or a folder).

    A folder that cannot be listed is added to `errors` instead of being
    passed over in silence. Linked folders are followed, each real folder once,
    so a shared knowledge/ folder linked into a profile is checked too.
    """
    if os.path.isfile(path):
        yield path
        return

    def onerror(exc: OSError) -> None:
        errors.append(f"cannot list {exc.filename or path}: {exc.strerror or exc}")

    seen = set()
    for root, dirs, files in os.walk(path, onerror=onerror, followlinks=True):
        real = os.path.realpath(root)
        if real in seen:
            dirs[:] = []
            continue
        seen.add(real)
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
        for name in sorted(files):
            yield os.path.join(root, name)


def read_text(path: str) -> str | None:
    """Return file text, or None for a binary file (one that contains a NUL byte).

    Raises OSError when the file cannot be read, and ValueError naming the
    reason when it is text but not UTF-8, so the caller can report both.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if data.startswith(UTF16_BOMS):
        raise ValueError("it is UTF-16")
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        line = data.count(b"\n", 0, exc.start) + 1
        raise ValueError(f"byte 0x{data[exc.start]:02x} on line {line}") from None


def scan(paths: Iterable[str], ignore: Iterable[str] = ()) -> tuple[list[tuple[str, int, str]], int, int, list[str]]:
    """Return (findings, scanned, skipped, errors).

    findings is a list of (file, line_number, name), one per marker occurrence.
    errors lists each file or folder that could not be read, with the reason.
    """
    ignored = set(ignore)
    findings, scanned, skipped, errors = [], 0, 0, []
    for path in paths:
        for file in iter_files(path, errors):
            try:
                text = read_text(file)
            except OSError as exc:
                errors.append(f"cannot read {file}: {exc.strerror or exc}")
                continue
            except ValueError as exc:
                errors.append(f"{file} is not UTF-8 text ({exc}); save it as UTF-8 and run again")
                continue
            if text is None:
                skipped += 1
                continue
            scanned += 1
            for lineno, line in enumerate(text.splitlines(), start=1):
                for match in PATTERN.finditer(line):
                    if match.group(1) not in ignored:
                        findings.append((file, lineno, match.group(1)))
    return findings, scanned, skipped, errors


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

    findings, scanned, skipped, errors = scan(args.paths, args.ignore)
    for message in errors:
        print(f"error: {message}", file=sys.stderr)
    if scanned == 0 and not errors:
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
    if errors:
        sys.stdout.flush()
        print(f"error: could not check {len(errors)} path(s), so the result is incomplete "
              f"({scanned} scanned{note})", file=sys.stderr)
        return 2
    if findings:
        return 1
    print(f"ok: no unfilled placeholders ({scanned} files scanned{note})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
