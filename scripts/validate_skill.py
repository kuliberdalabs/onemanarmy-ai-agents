#!/usr/bin/env python3
"""Validate skill folders without third-party dependencies.

Usage:
    python3 scripts/validate_skill.py              # every core/skills/*/SKILL.md
    python3 scripts/validate_skill.py core/skills/NAME  # one or more skill folders

Exit code 0 when every skill is valid, 1 otherwise.
"""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "core" / "skills"


def validate(skill: Path) -> list[str]:
    """Return a list of problems for one skill folder; empty means valid."""
    skill_file = skill / "SKILL.md"
    if not skill_file.is_file():
        return [f"missing {skill_file}"]

    text = skill_file.read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not frontmatter:
        return ["SKILL.md needs YAML frontmatter"]

    fields = {}
    for line in frontmatter.group(1).splitlines():
        if ":" not in line:
            return [f"invalid frontmatter line: {line!r}"]
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    if set(fields) != {"name", "description"}:
        return ["frontmatter must contain only name and description"]

    problems = []
    if fields["name"] != skill.name:
        problems.append("skill name must match its directory")
    if not re.fullmatch(r"[a-z0-9-]{1,63}", fields["name"]):
        problems.append("skill name must use lowercase letters, digits, and hyphens")
    if len(fields["description"]) < 80:
        problems.append("description is too short to trigger reliably")
    if "TODO" in text:
        problems.append("unresolved TODO in SKILL.md")

    for relative in re.findall(r"\]\(((?:references|scripts|assets)/[^)]+)\)", text):
        if not (skill / relative).is_file():
            problems.append(f"missing referenced file: {relative}")

    for json_file in (skill / "assets").rglob("*.json"):
        try:
            json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            problems.append(f"invalid JSON in {json_file}: {error}")

    for script in (skill / "scripts").glob("*.py"):
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except SyntaxError as error:
            problems.append(f"invalid Python in {script}: {error}")

    # agents/openai.yaml is optional; when present, check the Codex interface.
    openai_file = skill / "agents" / "openai.yaml"
    if openai_file.is_file():
        openai_yaml = openai_file.read_text(encoding="utf-8")
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
