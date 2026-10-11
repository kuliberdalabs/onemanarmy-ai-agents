#!/usr/bin/env bash
# doctrine-guard: a Claude Code PreToolUse hook that stops an agent from
# editing "doctrine" files (the rules every later session reads) without a
# human saying yes.
#
# Why: adding a clause to a rules file costs one line; removing a bad one
# needs a human to notice it first. Left alone, constraints only grow, and
# every later agent reads the earlier agent's guess as settled policy. This
# hook keeps state files (what happened, what is in progress) fully editable
# and routes edits to doctrine files (what we are, how we work) to a human.
#
# Scope, stated honestly:
#   - Claude Code only. Input is the PreToolUse JSON on stdin; output is a
#     permissionDecision JSON on stdout.
#   - Catches the Edit, Write and MultiEdit tools. It does NOT catch writes
#     made through the shell (`cat >`, `sed -i`, `python3 -c ...`). It
#     catches routine drift and honest mistakes; a determined agent can still
#     write through the shell. Checking every shell command would flood
#     normal work with false alarms.
#   - Fails open: missing or malformed input means no decision, so other
#     hooks and the normal permission prompt still apply.
#
# Requires bash 3.2+ and python3 (stdlib only, used for JSON in and out).
#
# Configuration (edit the array below, or set environment variables):
#   DOCTRINE_GUARD_PROTECT  colon-separated globs; replaces the PROTECT list
#   DOCTRINE_GUARD_MODE     "ask" (default: the human approves or refuses)
#                           or "deny" (always refuse; the agent must propose
#                           the change in chat instead)
# Globs match the absolute file path after `.` and `..` segments are
# resolved; `*` also matches `/`.
#
# There is no allow list, and nothing overrides a PROTECT match. State files
# (STATE.md, HANDOFF.md, logs, scratchpads, source code) stay editable because
# no PROTECT glob names them. An allow list checked first is a hole: with
# `*/scratchpad/*` on it, every AGENTS.md below any folder named scratchpad
# went unguarded, and `*-log.md` did the same inside .claude/rules/.
# DOCTRINE_GUARD_ALLOW is ignored; to make a file editable, leave it out of
# DOCTRINE_GUARD_PROTECT.
#
# Usage:
#   doctrine-guard.sh < hook-input.json
#   doctrine-guard.sh --selftest     # runs allowed and blocked samples

set -uo pipefail

# --- PROTECT: doctrine files. Format: 'glob|why it matters' ----------------
PROTECT=(
  '*/CLAUDE.md|CLAUDE.md is loaded as instructions by every future session in this folder'
  '*/AGENTS.md|AGENTS.md holds the rules every agent working here reads first'
  '*/MEMORY.md|MEMORY.md is the memory index loaded at the start of every session'
  '*/SKILL.md|SKILL.md defines a tool that other sessions call without rereading it'
  '*/.claude/settings.json|settings.json configures the harness itself, including this hook'
  '*/.claude/settings.local.json|settings.local.json configures the harness itself, including this hook'
  '*/.claude/rules/*|files in .claude/rules/ load as standing rules for every session'
  '*/doctrine-guard.sh|this is the guard itself; an agent that can edit it can switch it off'
)

if [ -n "${DOCTRINE_GUARD_PROTECT:-}" ]; then
  IFS=':' read -r -a _globs <<< "$DOCTRINE_GUARD_PROTECT"
  PROTECT=()
  for g in "${_globs[@]}"; do
    PROTECT+=("$g|this path is listed in DOCTRINE_GUARD_PROTECT")
  done
fi
MODE="${DOCTRINE_GUARD_MODE:-ask}"
case "$MODE" in ask|deny) ;; *) MODE=ask ;; esac

# Print the decision JSON for a protected path, or nothing for any other path.
decide() {
  local path="$1" glob entry reason=""

  # Relative paths get a leading slash so '*/NAME' globs still match.
  case "$path" in /*) ;; *) path="/$path" ;; esac

  for entry in ${PROTECT[@]+"${PROTECT[@]}"}; do
    glob="${entry%%|*}"
    # shellcheck disable=SC2254  # $glob is a pattern on purpose
    case "$path" in $glob) reason="${entry#*|}"; break ;; esac
  done
  [ -z "$reason" ] && return 0

  python3 -c '
import json, sys
path, reason, mode = sys.argv[1:4]
tail = ("If you asked for this change, approve it. If the agent decided on its own, "
        "refuse and have it state in chat what it wants to change and why.")
if mode == "deny":
    tail = ("Doctrine files change only by a human. Propose the change as a diff "
            "in chat and let a human apply it.")
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": mode,
    "permissionDecisionReason": "DOCTRINE FILE: %s\n%s.\n\n%s" % (path, reason, tail),
}}))
' "$path" "$reason" "$MODE"
}

# Read the hook payload and print tool_input.file_path with `.` and `..`
# segments resolved (so /repo/x/../CLAUDE.md is seen as /repo/CLAUDE.md),
# or nothing.
extract_path() {
  python3 -c '
import json, os, sys
try:
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path") or ""
except Exception:
    path = ""
print(os.path.normpath(path) if isinstance(path, str) and path else "")
'
}

selftest() {
  local fails=0 out name input expect self="${BASH_SOURCE[0]}"
  # Cases must not inherit the caller's configuration.
  unset DOCTRINE_GUARD_PROTECT DOCTRINE_GUARD_ALLOW DOCTRINE_GUARD_MODE
  run_case() {
    name="$1"; expect="$2"; input="$3"
    out=$(printf '%s' "$input" | bash "$self")
    case "$expect" in
      allow) [ -z "$out" ] || { echo "FAIL $name: expected no decision, got: $out"; fails=$((fails+1)); return; } ;;
      *)     printf '%s' "$out" | grep -q "\"permissionDecision\": \"$expect\"" \
               || { echo "FAIL $name: expected $expect, got: ${out:-<nothing>}"; fails=$((fails+1)); return; } ;;
    esac
    echo "ok   $name -> $expect"
  }
  run_case "state file"          allow '{"tool_name":"Edit","tool_input":{"file_path":"/repo/STATE.md"}}'
  run_case "source file"         allow '{"tool_name":"Write","tool_input":{"file_path":"/repo/src/app.py"}}'
  run_case "malformed json"      allow '{"tool_name":'
  run_case "no file_path"        allow '{"tool_name":"Edit","tool_input":{}}'
  run_case "AGENTS.md"           ask   '{"tool_name":"Edit","tool_input":{"file_path":"/repo/AGENTS.md"}}'
  run_case "nested CLAUDE.md"    ask   '{"tool_name":"MultiEdit","tool_input":{"file_path":"/repo/sub/CLAUDE.md"}}'
  run_case "relative SKILL.md"   ask   '{"tool_name":"Write","tool_input":{"file_path":"skills/x/SKILL.md"}}'
  run_case "rules dir"           ask   '{"tool_name":"Write","tool_input":{"file_path":"/home/u/.claude/rules/web.md"}}'
  run_case "harness settings"    ask   '{"tool_name":"Edit","tool_input":{"file_path":"/repo/.claude/settings.json"}}'
  run_case "the guard itself"    ask   '{"tool_name":"Edit","tool_input":{"file_path":"/repo/.claude/hooks/doctrine-guard.sh"}}'
  run_case "quote in path"       ask   '{"tool_name":"Edit","tool_input":{"file_path":"/repo/it\"s/AGENTS.md"}}'
  # A folder named like state must not switch protection off below it.
  run_case "scratch file"        allow '{"tool_name":"Write","tool_input":{"file_path":"/repo/scratchpad/notes.md"}}'
  run_case "log file"            allow '{"tool_name":"Edit","tool_input":{"file_path":"/repo/notes/audit-log.md"}}'
  run_case "AGENTS.md in scratchpad"   ask '{"tool_name":"Edit","tool_input":{"file_path":"/repo/scratchpad/AGENTS.md"}}'
  run_case "CLAUDE.md below scratchpad" ask '{"tool_name":"Edit","tool_input":{"file_path":"/x/scratchpad/proj/CLAUDE.md"}}'
  run_case "settings below scratchpad"  ask '{"tool_name":"Edit","tool_input":{"file_path":"/x/scratchpad/proj/.claude/settings.json"}}'
  run_case "local settings below scratchpad" ask '{"tool_name":"Write","tool_input":{"file_path":"/x/scratchpad/proj/.claude/settings.local.json"}}'
  run_case "rules file named like a log" ask '{"tool_name":"Write","tool_input":{"file_path":"/repo/.claude/rules/audit-log.md"}}'
  run_case "dot-dot to CLAUDE.md"       ask '{"tool_name":"Edit","tool_input":{"file_path":"/repo/scratchpad/../CLAUDE.md"}}'
  run_case "dot-dot to settings"        ask '{"tool_name":"Edit","tool_input":{"file_path":"/repo/.claude/hooks/../settings.json"}}'
  DOCTRINE_GUARD_MODE=deny run_case "deny mode" deny '{"tool_name":"Edit","tool_input":{"file_path":"/repo/AGENTS.md"}}'
  DOCTRINE_GUARD_PROTECT='*/POLICY.md' run_case "env list: listed"   ask   '{"tool_name":"Edit","tool_input":{"file_path":"/repo/POLICY.md"}}'
  DOCTRINE_GUARD_PROTECT='*/POLICY.md' run_case "env list: replaced" allow '{"tool_name":"Edit","tool_input":{"file_path":"/repo/AGENTS.md"}}'
  DOCTRINE_GUARD_ALLOW='*/AGENTS.md' run_case "old allow variable ignored" ask '{"tool_name":"Edit","tool_input":{"file_path":"/repo/AGENTS.md"}}'
  if [ "$fails" -eq 0 ]; then echo "selftest: all cases passed"; return 0; fi
  echo "selftest: $fails case(s) failed"; return 1
}

if [ "${1:-}" = "--selftest" ]; then
  selftest
  exit $?
fi

path=$(extract_path)
[ -z "$path" ] && exit 0
decide "$path"
exit 0
