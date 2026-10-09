#!/usr/bin/env bash
# Runs every reproducer in core/pitfalls/ and fails if any of them does
# not reproduce. A reproducer that stops reproducing (new shell version, new
# OS) is a finding: fix it or cut it, never keep it as prose.
#
# Needs: bash, zsh, python3, pgrep. Usage: tests/test_pitfalls.sh
# PITFALLS_DIR overrides the directory (used to check that this runner fails
# on a reproducer that reports NOT REPRODUCED).

here=$(cd "$(dirname "$0")" && pwd)
dir=${PITFALLS_DIR:-"$here/../core/pitfalls"}

total=0
failed=0
for script in "$dir"/*.sh; do
  [ -e "$script" ] || continue
  total=$((total + 1))
  name=$(basename "$script")
  out=$(bash "$script" 2>&1)
  rc=$?
  last=$(printf '%s\n' "$out" | tail -n 1)
  case "$last" in
    REPRODUCED:*)
      if [ "$rc" -eq 0 ]; then
        echo "ok    $name"
        continue
      fi ;;
  esac
  failed=$((failed + 1))
  echo "FAIL  $name (exit $rc): $last"
done

if [ "$total" -eq 0 ]; then
  echo "FAIL  no reproducers found in $dir"
  exit 1
fi
echo "$((total - failed))/$total reproduced"
[ "$failed" -eq 0 ]
