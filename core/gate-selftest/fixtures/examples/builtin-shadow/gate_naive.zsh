#!/usr/bin/env zsh
# Gate: fail when the application log contains ERROR entries.
# Naive version. It expects `log` to be the helper in ./bin, but zsh has a
# builtin `log` that wins over PATH. The builtin prints "too many arguments"
# to stderr and nothing to stdout, grep counts zero matches, the gate says OK.
PATH="${0:A:h}/bin:$PATH"
errors=$(log show --file "$1" | grep -c ERROR)
if (( errors > 0 )); then
  echo "FAIL: $errors ERROR entries"
  exit 1
fi
echo "OK: 0 ERROR entries"
exit 0
