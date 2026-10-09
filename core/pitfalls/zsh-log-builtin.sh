#!/usr/bin/env bash
# Pitfall: in zsh, `log` is a builtin (it lists logins), so `log show ...`
# never reaches the system's /usr/bin/log. The builtin prints
# "too many arguments" to stderr and produces no stdout. A check that
# discards stderr and counts matching lines reports 0 with exit status 0.
# A "zero lines means clean" check built this way can never find anything.
#
# Needs: zsh. Runs the same on macOS and Linux, because the builtin wins
# over any `log` binary on PATH.
# Fix: call the binary by absolute path (/usr/bin/log on macOS), and give
# every "zero lines = clean" check a positive control: material that does
# contain the thing, which the check must find.
# Prints REPRODUCED and exits 0 when the pitfall shows; exits 1 otherwise.

if ! command -v zsh >/dev/null 2>&1; then
  echo "NOT REPRODUCED: zsh not installed"; exit 1
fi

# The check as it was written: count matching log lines, zero means clean.
out=$(zsh -f -c '
  n=$(log show --last 1h --predicate "eventMessage CONTAINS \"prompt\"" 2>/dev/null | wc -l)
  rc=$?
  print -r -- "$(whence -w log) lines=${n// /} rc=$rc"
')

case "$out" in
  "log: builtin lines=0 rc=0")
    echo "REPRODUCED: zsh resolved 'log' to its builtin; the check counted 0 lines and exited 0 ($out)"
    exit 0 ;;
  *)
    echo "NOT REPRODUCED: got '$out'"
    exit 1 ;;
esac
