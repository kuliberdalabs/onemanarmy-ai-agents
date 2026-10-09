#!/usr/bin/env bash
# Pitfall: `producer | grep -q pattern` under `set -o pipefail` can fail
# exactly when the pattern IS found. grep -q exits on the first match and
# closes the pipe; a producer still writing gets SIGPIPE and dies with 141;
# pipefail reports that 141 as the pipeline status. Under `set -e` the script
# exits at that line with no message.
#
# Needs: bash (3.2 or later). Any producer that writes more than one pipe
# buffer (64 KiB on Linux and macOS) after the match triggers it.
# Fix: capture first, then test: out=$(producer); grep -q pattern <<<"$out"
# Prints REPRODUCED and exits 0 when the pitfall shows; exits 1 otherwise.

set -o pipefail

producer() { echo "PermitRootLogin no"; seq 1 1000000; }

producer | grep -q "PermitRootLogin no"
piped=$?

out=$(producer)
grep -q "PermitRootLogin no" <<<"$out"
captured=$?

if [ "$piped" -ne 0 ] && [ "$captured" -eq 0 ]; then
  echo "REPRODUCED: the line is present, yet 'producer | grep -q' returned $piped under pipefail; capture-then-grep returned $captured"
  exit 0
fi
echo "NOT REPRODUCED: piped=$piped captured=$captured"
exit 1
