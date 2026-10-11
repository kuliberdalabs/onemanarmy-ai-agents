"""Shell blocks in the Markdown docs must paste cleanly into macOS zsh (stdlib unittest).

macOS starts zsh as its interactive shell, and interactive zsh does not treat '#'
as the start of a comment unless `interactivecomments` is set. Neither zsh nor
macOS sets it. A trailing `# note` after a command becomes extra arguments:
`cd dir   # note` fails with "too many arguments", and `mkdir dir   # a b` creates
folders named '#', 'a' and 'b'. A line holding only a comment runs '#' as a
command. So no fenced block tagged sh, bash, zsh or shell may hold a comment;
the explanation goes in the prose around the block.

    python3 -m unittest discover -s tests -p test_docs.py -v
    python3 tests/test_docs.py FILE.md ...     (check single files, exit 1 on a finding)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHELL_TAGS = {"sh", "bash", "zsh", "shell"}
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
HEREDOC_RE = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z0-9_.-]+)\2")
WORD_BREAK = set(" \t;&|()<>")


def shell_blocks(text):
    """Yield (first_line_number, lines) for every fenced block tagged as shell.

    Line numbers are 1-based positions in the Markdown file. A fence may be
    indented (code blocks inside list items are). An unclosed fence runs to the
    end of the file, as in CommonMark.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        fence, info = m.group(1), m.group(2).strip()
        tag = info.split()[0].lower() if info else ""
        body_start = i + 1
        j = body_start
        while j < len(lines):
            close = FENCE_RE.match(lines[j])
            if (close and close.group(1)[0] == fence[0]
                    and len(close.group(1)) >= len(fence) and not close.group(2).strip()):
                break
            j += 1
        if tag in SHELL_TAGS:
            yield body_start + 1, lines[body_start:j]
        i = j + 1


def comment_lines(block):
    """Return (index, kind) for each line of a shell block where '#' starts a comment.

    '#' starts a comment when it begins a word outside quotes, as in bash. So
    `$#`, `${#x}`, `a#b`, a URL fragment and a quoted '#' are not comments, and
    neither is anything inside a here-document body.
    """
    found = []
    quote = None
    heredocs = []
    pending = []
    word_start = True
    for index, line in enumerate(block):
        if heredocs:
            delim, strip_tabs = heredocs[0]
            if (line.lstrip("\t") if strip_tabs else line) == delim:
                heredocs.pop(0)
            continue
        if quote is None:
            word_start = True
        seen_command = False
        i = 0
        while i < len(line):
            c = line[i]
            if quote == "'":
                if c == "'":
                    quote = None
                i += 1
                continue
            if quote in ('"', "$'"):
                if c == "\\":
                    i += 2
                    continue
                if c == quote[-1]:
                    quote = None
                i += 1
                continue
            if c == "#" and word_start:
                found.append((index, "comment after a command" if seen_command
                              else "comment-only line"))
                break
            if c == "\\":
                word_start = False
                seen_command = True
                i += 2
                continue
            if c == "<" and line.startswith("<<", i) and not line.startswith("<<<", i):
                m = HEREDOC_RE.match(line, i)
                if m:
                    pending.append((m.group(3), m.group(1) == "-"))
                    i = m.end()
                    word_start = False
                    seen_command = True
                    continue
            if c == "$" and line.startswith("$'", i):
                quote = "$'"
                i += 2
            elif c in ("'", '"'):
                quote = c
                i += 1
            else:
                i += 1
            if not c.isspace():
                seen_command = True
            word_start = c in WORD_BREAK
        if quote is None and pending:
            heredocs.extend(pending)
            pending = []
    return found


def scan_text(text, name):
    """Return one finding string per comment line in the shell blocks of `text`."""
    findings = []
    for first, block in shell_blocks(text):
        for index, kind in comment_lines(block):
            findings.append(f"{name}:{first + index}: {kind}: {block[index].strip()}")
    return findings


def tracked_markdown():
    """Paths of the tracked *.md files, relative to the repository root.

    Uses `git ls-files`; without git (an unpacked zip) it walks the tree instead.
    """
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--", "*.md"], cwd=REPO,
                             capture_output=True, check=True).stdout
        paths = [p for p in out.decode("utf-8").split("\0") if p]
        if paths:
            return sorted(paths)
    except (OSError, subprocess.CalledProcessError):
        pass
    paths = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".md"):
                paths.append(os.path.relpath(os.path.join(root, f), REPO))
    return sorted(paths)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class RepositoryDocs(unittest.TestCase):
    def test_shell_blocks_hold_no_comments(self):
        findings = []
        blocks = 0
        for rel in tracked_markdown():
            text = read(os.path.join(REPO, rel))
            blocks += sum(1 for _ in shell_blocks(text))
            findings.extend(scan_text(text, rel))
        self.assertGreater(blocks, 0, "found no shell blocks at all; the fence parser is broken")
        self.assertEqual(findings, [], "\n'#' would not start a comment in interactive zsh; "
                         "move these into the prose:\n" + "\n".join(findings))


class DetectorFailsOnKnownBadInput(unittest.TestCase):
    """The check must fail on the lines that broke the docs before its green counts."""

    def test_comment_after_a_command_is_found(self):
        text = ("Intro\n\n```sh\n"
                "rm -rf ~/first-job && mkdir ~/first-job   # starts clean\n"
                "cd /path/to/your-project          # the project\n"
                "python3 -m unittest discover tests;# no space before it\n"
                "```\n")
        self.assertEqual(scan_text(text, "x.md"), [
            "x.md:4: comment after a command: rm -rf ~/first-job && mkdir ~/first-job   # starts clean",
            "x.md:5: comment after a command: cd /path/to/your-project          # the project",
            "x.md:6: comment after a command: python3 -m unittest discover tests;# no space before it",
        ])

    def test_comment_only_line_is_found(self):
        text = "```bash\n# setup first\nls\n    # indented\n```\n"
        self.assertEqual(scan_text(text, "y.md"), [
            "y.md:2: comment-only line: # setup first",
            "y.md:4: comment-only line: # indented",
        ])

    def test_every_shell_tag_is_checked_and_nothing_else(self):
        text = ("```zsh\nls # a\n```\n"
                "```shell\nls # b\n```\n"
                "1. In a list:\n\n   ```sh\n   ls # c\n   ```\n"
                "```\nls # untagged\n```\n"
                "```text\nls # text\n```\n"
                "```python\n# python comment\n```\n"
                "```yaml\nkey: value  # yaml comment\n```\n"
                "~~~sh\nls # tilde fence\n~~~\n")
        self.assertEqual([f.split(":", 2)[1] for f in scan_text(text, "z.md")],
                         ["2", "5", "10", "25"])

    def test_hash_that_is_not_a_comment_passes(self):
        text = "\n".join([
            "```sh",
            'echo "$#" ${#PATH} a#b',
            "grep -c '# not a comment' notes.txt",
            'echo "a # b" $\'c # d\'',
            "curl -s https://example.invalid/page#top",
            'printf \'%s\' "{\\"k\\":\\"# x\\"}" | jq .',
            "echo 'one line",
            "# still inside the single quotes'",
            "python3 - <<'PY'",
            "# a Python comment in a here-document is data, not shell",
            "print('ok')",
            "PY",
            "```",
        ]) + "\n"
        self.assertEqual(scan_text(text, "ok.md"), [])


def main(paths):
    findings = []
    for path in paths:
        findings.extend(scan_text(read(path), path))
    for line in findings:
        print(line)
    return 1 if findings else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        sys.exit(main(sys.argv[1:]))
    unittest.main()
