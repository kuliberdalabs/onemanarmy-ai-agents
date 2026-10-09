#!/usr/bin/env zsh
# Gate: fail when the application log contains ERROR entries.
# Fixed version. `command log` skips shell builtins and functions, the
# helper's own exit status is checked, and reading zero lines is reported
# as unknown instead of clean.
PATH="${0:A:h}/bin:$PATH"
lines=$(command log show --file "$1") || { echo "ERROR: log helper failed"; exit 2; }
if [[ -z $lines ]]; then
  echo "UNKNOWN: read 0 log lines, refusing to call that clean"
  exit 2
fi
errors=$(print -r -- "$lines" | grep -c ERROR)
if (( errors > 0 )); then
  echo "FAIL: $errors ERROR entries"
  exit 1
fi
echo "OK: 0 ERROR entries in $(print -r -- "$lines" | wc -l | tr -d ' ') lines"
exit 0
