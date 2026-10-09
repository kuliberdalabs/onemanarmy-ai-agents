#!/bin/sh
# Fake gate that rejects everything, valid input included. Third leg.
# The runner MUST file this gate as FALSE-ALARM. Without it, a runner that
# only looks at the bad side of the pair would accept gates that just
# always complain.
[ -f "${1:-}" ] && head -n 1 "$1" >/dev/null 2>&1
echo "FAIL: whatever this is, I do not like it"
exit 1
