#!/usr/bin/env python3
"""Validate skill folders without third-party dependencies.

Usage:
    python3 scripts/validate_skill.py              # every core/skills/*/SKILL.md
    python3 scripts/validate_skill.py core/skills/NAME  # one or more skill folders

Exit code 0 when every skill is valid, 1 otherwise.

The validator accepts only a narrow subset of YAML on purpose, so it rejects
some frontmatter that YAML would accept: block scalars (`|` or `>`), values
continued on the next line, comments, flow collections, anchors and tags,
blank lines, and any key other than `name` and `description`.

In detail, the frontmatter must use a subset of YAML that this script can
check exactly without a YAML library: one `name:` line and one `description:`
line, each starting at the beginning of its line, with the value on that same
line. A value is either plain text or wrapped in quotes. Plain text must not
start with a YAML indicator character, must not contain ": " or " #", must not
end with ":", and must not be a word YAML reads as something other than text
(true, no, null, a number or a date). "Double quotes" may hold \" and \\ as
the only escapes; 'single quotes' write a quote inside as ''. Nothing may
follow the closing quote. Tabs and control characters are not allowed.
Anything else is reported with its line number in SKILL.md.
"""

import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "core" / "skills"

FIELD_LINE = re.compile(r"([^\s:]+):(?: +(.*))?\Z")
INDICATORS = "-?:,[]{}#&*!|>%@`"
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029\ufeff]")
NOT_TEXT = re.compile(
    r"(?:~|null|true|false|yes|no|on|off|y|n"
    r"|[-+]?(?:[0-9][0-9_]*(?:\.[0-9_]*)?|\.[0-9]+)(?:e[-+]?[0-9]+)?"
    r"|[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+(?:\.[0-9_]*)?"
    r"|0[xob][0-9a-f_]+|[-+]?\.(?:inf|nan)"
    r"|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[t ].*)?)\Z",
    re.IGNORECASE,
)
QUOTE_HINT = "; put the whole value in double quotes"


def parse_value(raw: str) -> tuple[str | None, str]:
    """Read one frontmatter value. Return (text, "") or (None, reason)."""
    value = raw.rstrip(" ")
    if not value:
        return None, "has no value"
    if value[0] == '"':
        text, i = [], 1
        while i < len(value):
            char = value[i]
            if char == "\\":
                if i + 1 == len(value):
                    break
                if value[i + 1] not in ('"', "\\"):
                    return None, (f"uses the escape \\{value[i + 1]} inside double quotes;"
                                  ' only \\" and \\\\ are supported')
                text.append(value[i + 1])
                i += 2
            elif char == '"':
                if value[i + 1:]:
                    return None, ("has text after the closing double quote;"
                                  ' write a " inside the value as \\"')
                return "".join(text), ""
            else:
                text.append(char)
                i += 1
        return None, "opens a double quote that is not closed on the same line"
    if value[0] == "'":
        text, i = [], 1
        while i < len(value):
            if value[i] == "'":
                if value[i + 1:i + 2] == "'":
                    text.append("'")
                    i += 2
                    continue
                if value[i + 1:]:
                    return None, ("has text after the closing single quote;"
                                  " write a ' inside the value as ''")
                return "".join(text), ""
            text.append(value[i])
            i += 1
        return None, "opens a single quote that is not closed on the same line"
    if value[0] in INDICATORS:
        return None, f"starts with {value[0]!r}, which YAML reads as syntax, not text" + QUOTE_HINT
    if ": " in value:
        return None, 'contains ": ", which YAML reads as the start of another key' + QUOTE_HINT
    if value.endswith(":"):
        return None, 'ends with ":", which YAML reads as the start of another key' + QUOTE_HINT
    if " #" in value:
        return None, 'contains " #", which YAML reads as the start of a comment' + QUOTE_HINT
    if NOT_TEXT.match(value):
        return None, f"is {value!r}, which YAML reads as a boolean, null, number or date" + QUOTE_HINT
    return value, ""


def parse_frontmatter(block: str) -> tuple[dict[str, str], list[str]]:
    """Return (fields, problems) for the lines between the --- markers."""
    fields: dict[str, str] = {}
    problems = []
    for lineno, line in enumerate(block.split("\n"), start=2):  # line 1 is ---
        where = f"SKILL.md line {lineno}"
        control = CONTROL.search(line)
        if control:
            problems.append(f"{where}: character U+{ord(control.group()):04X} is not allowed;"
                            " use plain spaces and keep each value on one line")
            continue
        if not line.strip():
            problems.append(f"{where}: blank line inside the frontmatter")
            continue
        if line[0] == " ":
            problems.append(f"{where}: indented line; each value must stay on its key's line")
            continue
        match = FIELD_LINE.match(line)
        if not match:
            problems.append(f'{where}: expected "name: value" or "description: value", got {line!r}')
            continue
        key, raw = match.group(1), match.group(2) or ""
        if key not in ("name", "description"):
            problems.append(f"{where}: unknown key {key!r}; frontmatter must contain only name and description")
            continue
        if key in fields:
            problems.append(f"{where}: duplicate key {key!r}")
            continue
        value, reason = parse_value(raw)
        if value is None:
            problems.append(f"{where}: {key} {reason}")
            continue
        fields[key] = value
    return fields, problems


def file_state(path: Path) -> str | None:
    """None when path is a regular file, "missing" when nothing is there, else why it cannot be checked.

    Path.is_file() answers False when a folder on the way cannot be read, which
    would make an unreadable file look absent and the skill look valid.
    """
    try:
        info = path.stat()
    except (FileNotFoundError, NotADirectoryError):
        return "missing"
    except OSError as error:
        return f"cannot read {path}: {error.strerror or error}"
    return None if stat.S_ISREG(info.st_mode) else "missing"


def find_files(folder: Path, suffix: str, recursive: bool) -> tuple[list[Path], list[str]]:
    """Files with this suffix under folder, and a problem for every folder that cannot be listed.

    A folder the validator cannot read is reported, never skipped: "valid" must
    mean every file was checked. Linked folders are followed, each real folder once.
    """
    if not folder.exists():
        return [], []
    found: list[Path] = []
    problems: list[str] = []

    def unreadable(error: OSError) -> None:
        problems.append(f"cannot read {error.filename}: {error.strerror}")

    seen = set()
    for dirpath, dirnames, filenames in os.walk(folder, onerror=unreadable, followlinks=True):
        real = os.path.realpath(dirpath)
        if real in seen:
            dirnames[:] = []
            continue
        seen.add(real)
        dirnames.sort()
        found.extend(Path(dirpath) / name for name in sorted(filenames) if name.endswith(suffix))
        if not recursive:
            break
    return found, problems


def validate(skill: Path) -> list[str]:
    """Return a list of problems for one skill folder; empty means valid."""
    skill_file = skill / "SKILL.md"
    state = file_state(skill_file)
    if state == "missing":
        return [f"missing {skill_file}"]
    if state:
        return [state]

    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [f"cannot read {skill_file}: {error}"]
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not frontmatter:
        return ["SKILL.md needs YAML frontmatter"]

    fields, problems = parse_frontmatter(frontmatter.group(1))
    if problems:
        return problems
    missing = {"name", "description"} - set(fields)
    if missing:
        return ["frontmatter must contain only name and description"
                f" (missing: {', '.join(sorted(missing))})"]

    if fields["name"] != skill.name:
        problems.append("skill name must match its directory")
    if not re.fullmatch(r"[a-z0-9-]{1,63}", fields["name"]):
        problems.append("skill name must use lowercase letters, digits, and hyphens")
    if len(fields["description"]) < 80:
        problems.append("description is too short to trigger reliably")
    if "TODO" in text:
        problems.append("unresolved TODO in SKILL.md")

    for relative in re.findall(r"\]\(((?:references|scripts|assets)/[^)]+)\)", text):
        state = file_state(skill / relative)
        if state == "missing":
            problems.append(f"missing referenced file: {relative}")
        elif state:
            problems.append(state)

    json_files, unreadable = find_files(skill / "assets", ".json", recursive=True)
    problems.extend(unreadable)
    for json_file in json_files:
        try:
            json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            problems.append(f"invalid JSON in {json_file}: {error}")
        except (OSError, UnicodeDecodeError) as error:
            problems.append(f"cannot read {json_file}: {error}")

    scripts, unreadable = find_files(skill / "scripts", ".py", recursive=True)
    problems.extend(unreadable)
    for script in scripts:
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except SyntaxError as error:
            problems.append(f"invalid Python in {script}: {error}")
        except (OSError, UnicodeDecodeError) as error:
            problems.append(f"cannot read {script}: {error}")

    # agents/openai.yaml is optional; when present, check the Codex interface.
    openai_file = skill / "agents" / "openai.yaml"
    state = file_state(openai_file)
    if state and state != "missing":
        problems.append(state)
    if state is None:
        try:
            openai_yaml = openai_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            problems.append(f"cannot read {openai_file}: {error}")
            return problems
        interface: dict[str, str] = {}
        for key in ("display_name", "short_description", "default_prompt"):
            match = re.search(rf'^  {key}: "([^"]+)"$', openai_yaml, re.MULTILINE)
            if match:
                interface[key] = match.group(1)
            else:
                problems.append(f"agents/openai.yaml needs a quoted {key}")
        short = interface.get("short_description", "")
        if short and not 25 <= len(short) <= 64:
            problems.append("agents/openai.yaml short_description must be 25-64 characters")
        prompt = interface.get("default_prompt", "")
        if prompt and f"${fields['name']}" not in prompt:
            problems.append("agents/openai.yaml default prompt must mention the skill")

    return problems


def main(argv: list[str]) -> int:
    if argv:
        skills = [Path(arg).resolve() for arg in argv]
    else:
        skills = sorted(path.parent for path in SKILLS.glob("*/SKILL.md"))
    if not skills:
        print(f"INVALID: no skills found under {SKILLS}")
        return 1

    failed = 0
    for skill in skills:
        problems = validate(skill)
        if problems:
            failed += 1
            for problem in problems:
                print(f"INVALID {skill.name}: {problem}")
        else:
            print(f"ok {skill.name}")

    if failed:
        print(f"{failed} of {len(skills)} skill(s) invalid")
        return 1
    print(f"All {len(skills)} skill(s) valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
