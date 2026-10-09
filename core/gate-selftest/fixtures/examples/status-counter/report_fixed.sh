#!/bin/sh
# Report: how many queue items are still open.
# Fixed version. Open means READY or BLOCKED, and any status outside the
# known vocabulary stops the report instead of being skipped. It still exits
# 0 when items are open, because it is a report; gate-selftest flags that.
awk -F '\t' '
  NR == 1 { next }
  $3 == "READY" || $3 == "BLOCKED" { n++; next }
  $3 == "DONE" || $3 == "PARKED" { next }
  { printf "UNKNOWN status %s on line %d\n", $3, NR; bad = 1; exit }
  END { if (bad) exit 2; printf "open: %d\n", n }
' "$1"
