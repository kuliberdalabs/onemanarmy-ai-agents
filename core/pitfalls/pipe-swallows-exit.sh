#!/usr/bin/env bash
# Pitfall: without pipefail a pipeline returns the exit status of its LAST
# command. `run_tests | tail -n 5 && git commit ...` commits after a red test
# run, because tail succeeded. The same holds for `| tee log`, `| head`, etc.
#
# Needs: bash or any POSIX sh.
# Fix: write the output to a file and keep the status before trimming:
#   run_tests >test.log 2>&1; rc=$?; tail -n 5 test.log; [ "$rc" -eq 0 ]
# or `set -o pipefail` (and mind pipefail-grep-q.sh).
# Prints REPRODUCED and exits 0 when the pitfall shows; exits 1 otherwise.

run_tests() { echo "Ran 12 tests"; echo "FAILED (failures=1)"; return 1; }

run_tests | tail -n 1 >/dev/null
piped=$?

run_tests >/dev/null 2>&1
direct=$?

if [ "$piped" -eq 0 ] && [ "$direct" -ne 0 ]; then
  echo "REPRODUCED: the tests exit $direct, but 'run_tests | tail' exits $piped"
  exit 0
fi
echo "NOT REPRODUCED: piped=$piped direct=$direct"
exit 1
