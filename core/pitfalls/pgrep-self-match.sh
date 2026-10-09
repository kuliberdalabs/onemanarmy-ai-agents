#!/usr/bin/env bash
# Pitfall: `pgrep -f "phrase"` matches every process whose command line holds
# the phrase, and a waiting loop started as `bash -c "while pgrep -f '...'"`
# carries the phrase in its own command line. The wait never ends and nothing
# errors.
#   - Linux (procps pgrep) excludes only pgrep itself, so a single loop
#     matches its own shell.
#   - macOS pgrep also excludes its ancestors, so a single loop is safe there,
#     but any other process holding the phrase keeps it alive: for example a
#     second wait loop left behind when the first wait timed out.
# This script starts two such loops so it reproduces on both systems.
#
# Needs: bash and pgrep.
# Fix: a character class keeps the pattern from matching its own text:
#   pgrep -f "render[ ]out.mp4"
# Prints REPRODUCED and exits 0 when the pitfall shows; exits 1 otherwise.

if ! command -v pgrep >/dev/null 2>&1; then
  echo "NOT REPRODUCED: pgrep not installed"; exit 1
fi

tag="pitfall-render-$$"   # unique per run so nothing else on the box matches

# Start a 1 s job, two loops waiting for it with pattern $1, then count how
# many loops are still waiting 1.5 s after the job ended.
waiters_left() {
  sh -c 'sleep 1; :' "$tag out.mp4" & job=$!
  sleep 0.2
  bash -c "while pgrep -f '$1' >/dev/null; do sleep 0.1; done" & w1=$!
  bash -c "while pgrep -f '$1' >/dev/null; do sleep 0.1; done" & w2=$!
  wait "$job"
  sleep 1.5
  left=0
  kill -0 "$w1" 2>/dev/null && left=$((left + 1))
  kill -0 "$w2" 2>/dev/null && left=$((left + 1))
  kill "$w1" "$w2" 2>/dev/null
  wait "$w1" "$w2" 2>/dev/null
  echo "$left"
}

naive=$(waiters_left "$tag out.mp4")
fixed=$(waiters_left "$tag[ ]out.mp4")

if [ "$naive" -gt 0 ] && [ "$fixed" -eq 0 ]; then
  echo "REPRODUCED: job finished, $naive of 2 plain-pattern wait loops still waiting; with '[ ]' $fixed left"
  exit 0
fi
echo "NOT REPRODUCED: naive=$naive fixed=$fixed"
exit 1
