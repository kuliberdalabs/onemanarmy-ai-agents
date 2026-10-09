@AGENTS.md

<!-- Thin per-tool layer. Claude Code loads CLAUDE.md and expands the @import above, so the
     shared rules live once in AGENTS.md and every CLI reads the same text. Add here only what
     is true for Claude Code and false for the other tools. If a line would apply to Codex too,
     it belongs in AGENTS.md. Copying rules into both files is how they drift apart. -->

# Claude Code layer

- Hooks: {{HOOKS_IN_USE}} (for example `core/hooks/doctrine-guard`, which blocks Edit/Write on
  rule files; it does not see shell redirects).
- Subagents: {{WHEN_TO_USE_SUBAGENTS}}. Their output is a claim; verify it on the artifact.
- After `/compact`, re-read `{{STATE_FILE}}` and the last written approval line before acting.
