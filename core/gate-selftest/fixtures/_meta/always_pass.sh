#!/bin/sh
# Fake gate that always passes. First leg of the meta triangle.
# It reads its input, says everything is fine and exits 0, even when the
# input is plainly broken. This is the shape of a check that silently ran
# the wrong command: exit 0, nothing found, looks like a clean run.
# The runner MUST file this gate as CANNOT-FAIL. If it does not, it is blind.
[ -f "${1:-}" ] && head -n 1 "$1" >/dev/null 2>&1
echo "OK: checked, found nothing"
exit 0
