#!/bin/sh
# Fake honest gate: rejects input that contains BROKEN, accepts the rest.
# Second leg of the meta triangle. The runner MUST file this gate as PASS.
# Without it, a runner that files everything as CANNOT-FAIL would look smart.
IN="${1:?usage: honest_gate.sh <file>}"
if grep -q "BROKEN" "$IN"; then
  echo "FAIL: input contains BROKEN"
  exit 1
fi
echo "PASS: input is clean"
exit 0
