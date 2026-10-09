#!/bin/sh
# Report: how many queue items are still open.
# Naive version. It counts status "pending", a status this queue never uses
# (the vocabulary is READY, BLOCKED, DONE, PARKED). The count is zero by
# construction, and zero looks like information. Like most reports, it
# exits 0 whatever it finds.
awk -F '\t' 'NR > 1 && $3 == "pending" { n++ } END { printf "open: %d\n", n }' "$1"
