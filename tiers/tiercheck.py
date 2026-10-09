"""Static checks for the tier fragments (OpenClaw and Claude Code).

Run `python3 tiers/tiercheck.py` for a report, or use the functions from tests.
Each check returns a list of violation strings; an empty list means the files
pass. The checks read files only. They prove the tiers are well formed and get
stricter as the number goes up. They do not prove a running agent obeys them:
that is the job of the behavioral hold test (see README.md and hold_test.py).
"""

import json
import os
import sys
from typing import Any, Dict, List, Set

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import json5lite  # noqa: E402

TIERS = (0, 1, 2)

# Tool groups as listed on https://docs.openclaw.ai/gateway/config-tools/tool-policy
# (read 2026-10-10). Only the groups the fragments use need to be here; an unknown
# group in a deny list is reported instead of guessed at.
OPENCLAW_GROUPS: Dict[str, Set[str]] = {
    "group:runtime": {"exec", "process", "code_execution"},
    "group:fs": {"read", "write", "edit", "apply_patch"},
    "group:sessions": {
        "sessions", "sessions_list", "sessions_history", "sessions_search",
        "conversations_list", "conversations_send", "conversations_turn",
        "sessions_send", "sessions_spawn", "sessions_yield", "subagents",
        "session_status", "suggest_task", "dismiss_task",
    },
    "group:memory": {"memory_search", "memory_get"},
    "group:web": {"web_search", "x_search", "web_fetch"},
    "group:ui": {"browser", "screen", "theme", "dashboard", "terminal", "portal",
                 "canvas", "show_widget"},
    "group:automation": {"heartbeat_respond", "automations", "cron", "gateway",
                         "plugins", "openclaw"},
    "group:messaging": {"message"},
    "group:nodes": {"nodes", "computer"},
    "group:media": {"view_image", "image_generate", "music_generate",
                    "video_generate", "tts", "pdf"},
    "group:plugins": {"<plugin tools>"},
}

# Strictness ranks: a higher number is stricter.
EXEC_MODE_RANK = {"full": 0, "auto": 1, "ask": 2, "allowlist": 3, "deny": 4}
SANDBOX_MODE_RANK = {"off": 0, "non-main": 1, "all": 2}
WORKSPACE_ACCESS_RANK = {"rw": 0, "ro": 1, "none": 2}
VISIBILITY_RANK = {"all": 0, "agent": 1, "tree": 2, "self": 3}
CLAUDE_MODE_RANK = {"bypassPermissions": 0, "auto": 1, "acceptEdits": 2,
                    "default": 3, "dontAsk": 4}

OPENCLAW_REQUIRED = [
    ("tools", "profile"),
    ("tools", "deny"),
    ("tools", "exec", "mode"),
    ("tools", "fs", "workspaceOnly"),
    ("tools", "elevated", "enabled"),
    ("tools", "sessions", "visibility"),
    ("tools", "agentToAgent", "enabled"),
    ("agents", "defaults", "sandbox", "mode"),
    ("agents", "defaults", "sandbox", "workspaceAccess"),
]
OPENCLAW_PROFILES = {"minimal", "coding", "messaging", "full"}

CLAUDE_REQUIRED = [
    ("permissions", "defaultMode"),
    ("permissions", "allow"),
    ("permissions", "ask"),
    ("permissions", "deny"),
]
# Mode values that the permission-modes page lists for defaultMode.
CLAUDE_MODES = {"default", "acceptEdits", "plan", "auto", "dontAsk", "bypassPermissions"}


def _get(doc: Dict[str, Any], path: tuple) -> Any:
    cur: Any = doc
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def load_openclaw(base: str = HERE) -> Dict[int, Dict[str, Any]]:
    return {t: json5lite.load(os.path.join(base, "openclaw", "tier%d.json5" % t))
            for t in TIERS}


def load_claude(base: str = HERE) -> Dict[int, Dict[str, Any]]:
    out = {}
    for t in TIERS:
        with open(os.path.join(base, "claude-code", "tier%d.settings.json" % t),
                  encoding="utf-8") as fh:
            out[t] = json.load(fh)
    return out


def expand_openclaw_deny(deny: List[str]) -> Set[str]:
    """Group names expand to members; a group the table does not know is kept as is."""
    names: Set[str] = set()
    for item in deny:
        names |= OPENCLAW_GROUPS.get(item, {item})
    return names


def _rank_check(problems: List[str], label: str, ranks: Dict[str, int],
                values: Dict[int, Any]) -> None:
    for t, v in values.items():
        if v not in ranks:
            problems.append("%s: tier %d has unknown value %r" % (label, t, v))
            return
    for lo, hi in ((0, 1), (1, 2)):
        if ranks[values[hi]] < ranks[values[lo]]:
            problems.append("%s: tier %d (%s) is looser than tier %d (%s)"
                            % (label, hi, values[hi], lo, values[lo]))


def check_openclaw(docs: Dict[int, Dict[str, Any]]) -> List[str]:
    problems: List[str] = []
    for t, doc in docs.items():
        for path in OPENCLAW_REQUIRED:
            if _get(doc, path) is None:
                problems.append("openclaw tier %d: missing key %s" % (t, ".".join(path)))
        if _get(doc, ("tools", "profile")) not in OPENCLAW_PROFILES:
            problems.append("openclaw tier %d: tools.profile %r is not one of %s"
                            % (t, _get(doc, ("tools", "profile")), sorted(OPENCLAW_PROFILES)))
        for item in _get(doc, ("tools", "deny")) or []:
            if item.startswith("group:") and item not in OPENCLAW_GROUPS:
                problems.append("openclaw tier %d: unknown tool group %s" % (t, item))
    if problems:
        return problems  # later comparisons assume the keys exist

    # Deny sets only grow with the tier.
    denied = {t: expand_openclaw_deny(docs[t]["tools"]["deny"]) for t in TIERS}
    for lo, hi in ((0, 1), (1, 2)):
        missing = denied[lo] - denied[hi]
        if missing:
            problems.append("openclaw: tier %d does not deny %s that tier %d denies"
                            % (hi, sorted(missing), lo))

    def vals(path: tuple) -> Dict[int, Any]:
        return {t: _get(docs[t], path) for t in TIERS}

    _rank_check(problems, "tools.exec.mode", EXEC_MODE_RANK, vals(("tools", "exec", "mode")))
    _rank_check(problems, "sandbox.mode", SANDBOX_MODE_RANK,
                vals(("agents", "defaults", "sandbox", "mode")))
    _rank_check(problems, "sandbox.workspaceAccess", WORKSPACE_ACCESS_RANK,
                vals(("agents", "defaults", "sandbox", "workspaceAccess")))
    _rank_check(problems, "tools.sessions.visibility", VISIBILITY_RANK,
                vals(("tools", "sessions", "visibility")))
    # Booleans: elevated and agentToAgent may only turn off as the tier rises;
    # workspaceOnly may only turn on.
    for label, path, strict_value in (
        ("tools.elevated.enabled", ("tools", "elevated", "enabled"), False),
        ("tools.agentToAgent.enabled", ("tools", "agentToAgent", "enabled"), False),
        ("tools.fs.workspaceOnly", ("tools", "fs", "workspaceOnly"), True),
    ):
        v = vals(path)
        for lo, hi in ((0, 1), (1, 2)):
            if v[lo] == strict_value and v[hi] != strict_value:
                problems.append("%s: tier %d is looser than tier %d" % (label, hi, lo))

    # Pinned shape of each tier, so a wrong edit cannot slide through monotonicity.
    if docs[0]["tools"]["exec"]["mode"] != "full" or docs[0]["agents"]["defaults"]["sandbox"]["mode"] != "off":
        problems.append("openclaw tier 0 must be exec full with the sandbox off")
    if docs[2]["tools"]["exec"]["mode"] != "deny":
        problems.append("openclaw tier 2 must set tools.exec.mode deny")
    for must in ("write", "edit", "apply_patch", "exec", "message"):
        if must not in denied[2]:
            problems.append("openclaw tier 2 must deny %s" % must)
    if "message" not in denied[1]:
        problems.append("openclaw tier 1 must deny message (no documented ask gate)")
    if "read" in denied[2]:
        problems.append("openclaw tier 2 must keep read available")
    return problems


def _tool_name(rule: str) -> str:
    return rule.split("(", 1)[0]


def covered_by_deny(rule: str, deny: List[str]) -> bool:
    """True if a deny list blocks everything `rule` would match.

    A rule is covered when it appears verbatim, when its tool is denied whole
    (bare name, so the tool leaves the model's context), or when a bare
    `mcp__*` glob denies an MCP rule.
    """
    if rule in deny:
        return True
    name = _tool_name(rule)
    if name in deny:
        return True
    return name.startswith("mcp__") and "mcp__*" in deny


def check_claude(docs: Dict[int, Dict[str, Any]]) -> List[str]:
    problems: List[str] = []
    for t, doc in docs.items():
        for path in CLAUDE_REQUIRED:
            if _get(doc, path) is None:
                problems.append("claude tier %d: missing key %s" % (t, ".".join(path)))
        mode = _get(doc, ("permissions", "defaultMode"))
        if mode not in CLAUDE_MODES:
            problems.append("claude tier %d: defaultMode %r is not a documented mode" % (t, mode))
        for kind in ("allow", "ask", "deny"):
            rules = _get(doc, ("permissions", kind))
            if rules is not None and not all(isinstance(r, str) for r in rules):
                problems.append("claude tier %d: permissions.%s must be a list of strings" % (t, kind))
    if problems:
        return problems

    perms = {t: docs[t]["permissions"] for t in TIERS}
    _rank_check(problems, "permissions.defaultMode", CLAUDE_MODE_RANK,
                {t: perms[t]["defaultMode"] for t in TIERS})

    # Deny only grows. Ask rules of a lower tier must be denied or asked above it.
    for lo, hi in ((0, 1), (1, 2)):
        for rule in perms[lo]["deny"]:
            if not covered_by_deny(rule, perms[hi]["deny"]):
                problems.append("claude: tier %d does not deny %r that tier %d denies"
                                % (hi, rule, lo))
        for rule in perms[lo]["ask"]:
            if not (covered_by_deny(rule, perms[hi]["deny"]) or rule in perms[hi]["ask"]):
                problems.append("claude: ask rule %r of tier %d is neither asked nor denied at tier %d"
                                % (rule, lo, hi))

    # An allow rule must not be contradicted by a deny or ask rule of the same tier:
    # deny and ask win over allow, so such a rule is dead and hides a mistake.
    for t in TIERS:
        for rule in perms[t]["allow"]:
            if covered_by_deny(rule, perms[t]["deny"]) or rule in perms[t]["ask"]:
                problems.append("claude tier %d: allow rule %r is shadowed by deny or ask" % (t, rule))

    # Pinned shape of each tier.
    if perms[0]["defaultMode"] != "bypassPermissions":
        problems.append("claude tier 0 must use bypassPermissions")
    for t in (1, 2):
        if perms[t].get("disableBypassPermissionsMode") != "disable":
            problems.append("claude tier %d must set permissions.disableBypassPermissionsMode to disable" % t)
        if perms[t]["defaultMode"] == "bypassPermissions":
            problems.append("claude tier %d must not start in bypassPermissions" % t)
    if perms[2].get("disableAutoMode") != "disable":
        problems.append("claude tier 2 must set permissions.disableAutoMode to disable")
    if perms[2]["defaultMode"] != "dontAsk":
        problems.append("claude tier 2 must use dontAsk so nothing can be approved by accident")
    for tool in ("Edit", "Write", "Bash", "WebFetch", "mcp__*"):
        if tool not in perms[2]["deny"]:
            problems.append("claude tier 2 must deny %s" % tool)
    for tool in ("Read", "Grep", "Glob"):
        if tool in perms[2]["deny"]:
            problems.append("claude tier 2 must keep %s available" % tool)
    for needed in ("Bash(git push *)", "Bash(curl *)", "Bash(rm *)", "mcp__*"):
        if needed not in perms[1]["ask"]:
            problems.append("claude tier 1 must ask before %s" % needed)
    sandbox = docs[1].get("sandbox", {})
    if sandbox.get("enabled") is not True or sandbox.get("allowUnsandboxedCommands") is not False:
        problems.append("claude tier 1 must enable the sandbox and disable unsandboxed retries")
    return problems


def main() -> int:
    problems = check_openclaw(load_openclaw()) + check_claude(load_claude())
    if problems:
        print("tier check FAILED")
        for p in problems:
            print("  -", p)
        return 1
    print("tier check ok: openclaw and claude-code tiers parse and get stricter with the tier number")
    return 0


if __name__ == "__main__":
    sys.exit(main())
